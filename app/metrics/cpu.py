# Метрики CPU

import subprocess

def get_cpu_temp():
    """
    Возвращает температуру CPU в °C. Если ошибка — None
    """
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
        # temp=48.2'C
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return None

def get_load1():
    """
    Возвращает loadavg за 1 минуту. Если ошибка — None
    """
    try:
        with open("/proc/loadavg") as f:
            return float(f.read().split()[0])
    except Exception:
        return None

