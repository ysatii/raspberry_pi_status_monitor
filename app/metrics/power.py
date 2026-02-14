# Метрики питания (напряжения)

import subprocess

def get_core_volts():
    """
    Возвращает напряжение CORE в вольтах. Если ошибка — None
    """
    try:
        out = subprocess.check_output(["vcgencmd", "measure_volts", "core"], text=True)
        # volt=0.8375V
        return float(out.split("=")[1].replace("V", "").strip())
    except Exception:
        return None
