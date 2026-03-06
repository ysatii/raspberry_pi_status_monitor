import time
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.lcd.device import st7735

DC_PIN = 25
RST_PIN = 24

def hardware_reset():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RST_PIN, GPIO.OUT)

    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(1)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(1)

def create_device():
    GPIO.cleanup()
    time.sleep(1)

    hardware_reset()
    time.sleep(1)

    serial = spi(
        port=0,
        device=0,
        gpio_DC=DC_PIN,
        gpio_RST=RST_PIN,
        bus_speed_hz=32000000
    )

    device = st7735(
        serial,
        width=128,
        height=128,
        rotate=1,
        bgr=True,
        h_offset=1,
        v_offset=2
    )

    time.sleep(0.2)
    return device
