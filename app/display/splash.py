# Показ заставки splash.png

import time
from PIL import Image

def show_splash(device, splash_path):
    """
    Показ splash без изменения логики.
    """
    try:
        splash = Image.open(splash_path).convert("RGB")
        splash = splash.resize((128, 128), Image.NEAREST)
        device.display(splash)
        time.sleep(2)
    except Exception as e:
        print("Splash skipped:", e)
