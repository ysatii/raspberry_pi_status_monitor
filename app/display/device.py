import os
import time
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.lcd.device import st7735

DC_PIN = 25
RST_PIN = 24


def wait_spi(timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists("/dev/spidev0.0"):
            return True
        time.sleep(0.2)
    return False


def hardware_reset():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RST_PIN, GPIO.OUT)

    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.10)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.20)


def build_device(bus_speed_hz):
    serial = spi(
        port=0,
        device=0,
        gpio_DC=DC_PIN,
        gpio_RST=RST_PIN,
        bus_speed_hz=bus_speed_hz
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
    return device


def create_device():
    if not wait_spi():
        raise RuntimeError("SPI device /dev/spidev0.0 not ready")

    time.sleep(2.0)
    hardware_reset()
    time.sleep(0.3)

    # безопасный старт
    device = build_device(8000000)
    time.sleep(0.5)

    # переход на рабочую скорость
    device = build_device(32000000)
    time.sleep(0.3)

    return device
