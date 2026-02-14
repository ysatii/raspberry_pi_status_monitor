# Инициализация SPI/TFT ST7735

from luma.core.interface.serial import spi
from luma.lcd.device import st7735

def create_device():
    serial = spi(
        port=0,
        device=0,
        gpio_DC=25,
        gpio_RST=24,
        bus_speed_hz=32000000
    )

    device = st7735(serial, width=128, height=128, rotate=0, bgr=True)
    return device
