import time
import spidev

spi = spidev.SpiDev()
spi.open(0, 0)           # bus 0, device 0
spi.max_speed_hz = 1350000

def read_adc(channel):
    if not 0 <= channel <= 7:
        return -1
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    value = ((adc[1] & 3) << 8) + adc[2]
    return value

try:
    while True:
        values = [read_adc(ch) for ch in range(8)]
        print("CH0–CH7:", values)
        time.sleep(0.5)
except KeyboardInterrupt:
    spi.close()
