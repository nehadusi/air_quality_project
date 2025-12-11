from pathlib import Path
import time
import csv
from datetime import datetime
import os

import spidev
import RPi.GPIO as GPIO
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# CONFIG
FAN_PIN = 18              # GPIO 18 to 2N7000 gate (through resistor)
BUTTON_PIN = 23           # Pushbutton between GPIO 23 and GND
THRESHOLD = 300           # tweak based on test values
SAMPLE_INTERVAL = 0.5     # seconds between samples
MAX_POINTS = 300          # keep last 300 points (~150 s at 0.5 s)
DEBOUNCE_TIME = 0.3       # seconds

# CSV file in the SAME folder as this script
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "air_quality_log.csv"

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.output(FAN_PIN, GPIO.LOW)

# Button: use internal pull-up so we wire button to GND
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# SPI setup for MCP3008 
spi = spidev.SpiDev()
spi.open(0, 0)                 # bus 0, device 0 (CE0)
spi.max_speed_hz = 1350000


def read_adc(channel: int) -> int:
    """Read a channel (0-7) from MCP3008 and return 0-1023."""
    if channel < 0 or channel > 7:
        raise ValueError("ADC channel must be 0-7")
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    value = ((adc[1] & 3) << 8) + adc[2]
    return value


def set_fan(on: bool) -> None:
    GPIO.output(FAN_PIN, GPIO.HIGH if on else GPIO.LOW)


def init_csv() -> None:
    """Create CSV with header if it doesn't exist."""
    if not LOG_FILE.exists():
        with open(str(LOG_FILE), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "gas_value", "fan_on"])


init_csv()

# Data and state for plotting & control 
x_data = []  # time in seconds since start
y_data = []  # gas values
start_time = time.time()

collecting = False          # start in PAUSED mode
last_button_state = GPIO.input(BUTTON_PIN)
last_toggle_time = time.time()

fig, ax = plt.subplots()
line, = ax.plot([], [], lw=2)

ax.set_xlabel("Time (s)")
ax.set_ylabel("Gas sensor value (0–1023)")
ax.set_ylim(0, 1023)
ax.grid(True)


def update_title():
    mode = "RUNNING" if collecting else "PAUSED"
    ax.set_title(
        f"MQ-2 Air Quality (Live) - {mode}\n"
        f"Press button (GPIO 23) to toggle"
    )


update_title()


def check_button():
    """Check the button and toggle collecting on press (with debounce)."""
    global collecting, last_button_state, last_toggle_time

    current_state = GPIO.input(BUTTON_PIN)  # 1 = not pressed, 0 = pressed
    now = time.time()

    # detect transition from HIGH -> LOW (button press)
    if (last_button_state == 1 and current_state == 0 and
            (now - last_toggle_time) > DEBOUNCE_TIME):
        collecting = not collecting
        last_toggle_time = now
        update_title()
        print(f"Button pressed → collecting = {collecting}")
        if not collecting:
            # make sure fan is off when paused
            set_fan(False)

    last_button_state = current_state


def update(_frame):
    """Runs every SAMPLE_INTERVAL to check button, maybe collect data, update plot."""
    check_button()  # always check button first

    now = time.time()
    t = now - start_time

    if collecting:
        gas = read_adc(0)  # MQ-2 on CH0
        fan_on = gas > THRESHOLD
        set_fan(fan_on)

        # Store data in memory
        x_data.append(t)
        y_data.append(gas)

        # Keep last MAX_POINTS
        if len(x_data) > MAX_POINTS:
            x_data.pop(0)
            y_data.pop(0)

        # Log to CSV
        with open(str(LOG_FILE), "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), gas, int(fan_on)])

        # Debug print
        print(
            f"{datetime.now().strftime('%H:%M:%S')}  "
            f"Gas={gas:4d}  Fan={'ON' if fan_on else 'OFF'}"
        )
    else:
        # When paused, fan is off and we don't change data/log
        set_fan(False)

    # Update line with whatever data we have
    line.set_data(x_data, y_data)

    # Adjust x-axis to follow time (scrolling window)
    if x_data:
        xmin = max(0, x_data[-1] - (MAX_POINTS * SAMPLE_INTERVAL))
        xmax = xmin + (MAX_POINTS * SAMPLE_INTERVAL)
        ax.set_xlim(xmin, xmax)

    return line,


ani = animation.FuncAnimation(
    fig,
    update,
    interval=int(SAMPLE_INTERVAL * 1000),
    blit=False
)

print("Air-quality monitor ready.")
print("Press the physical button (GPIO 23 -> GND) to START/STOP collection.")
print("Close the graph window to exit.")

try:
    plt.show()
finally:
    print("Cleaning up GPIO and SPI...")
    set_fan(False)
    spi.close()
    GPIO.cleanup()
    print("Done.")

