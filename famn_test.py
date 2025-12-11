import time
import RPi.GPIO as GPIO

FAN_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)

try:
    print("Fan ON for 5 seconds...")
    GPIO.output(FAN_PIN, GPIO.HIGH)
    time.sleep(5)

    print("Fan OFF for 5 seconds...")
    GPIO.output(FAN_PIN, GPIO.LOW)
    time.sleep(5)

    print("Fan ON again for 5 seconds...")
    GPIO.output(FAN_PIN, GPIO.HIGH)
    time.sleep(5)

    print("Done.")

finally:
    GPIO.output(FAN_PIN, GPIO.LOW)
    GPIO.cleanup()
