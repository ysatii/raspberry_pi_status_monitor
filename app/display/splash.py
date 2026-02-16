# Показ заставки splash.png

import time
from PIL import Image
from app.config.settings import SPLASH_SECONDS


def show_splash(device, splash_path):
    """
    Показ splash без изменения логики.
    """
    try:
        splash = Image.open(splash_path).convert("RGB")
        splash = splash.resize((128, 128), Image.NEAREST)
        device.display(splash)
        time.sleep(SPLASH_SECONDS)
    except Exception as e:
        print("Splash skipped:", e)
