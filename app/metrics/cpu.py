# Метрики CPU

import subprocess
from app.ui.colors import GREEN, YELLOW, RED


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

def get_cpu_freq_mhz():
    """
    Возвращает частоту CPU в MHz. Если ошибка — None
    """
    try:
        out = subprocess.check_output(["vcgencmd", "measure_clock", "arm"], text=True)
        # frequency(48)=1500000000
        hz = int(out.split("=")[1].strip())
        return hz // 1_000_000
    except Exception:
        return None

def get_throttled_hex():
    """
    Возвращает строку вида 0x50005. Если ошибка — '0x0'
    """
    try:
        out = subprocess.check_output(["vcgencmd", "get_throttled"], text=True)
        # throttled=0x50005
        return out.strip().split("=")[1]
    except Exception:
        return "0x0"

def throttling_status(throttled_hex: str):
    """
    Возвращает (текст, цвет) строго из 2 значений.
    """
    try:
        v = int(throttled_hex, 16)
    except Exception:
        return ("THROTTLING READ ERROR", RED)

    if v == 0:
        return ("NO THROTTLING", GREEN)

    # NOW flags
    undervolt_now = bool(v & 0x1)
    freq_cap_now  = bool(v & 0x2)
    throttle_now  = bool(v & 0x4)
    temp_now      = bool(v & 0x8)

    # WAS flags (sticky)
    undervolt_was = bool(v & 0x10000)
    freq_cap_was  = bool(v & 0x20000)
    throttle_was  = bool(v & 0x40000)
    temp_was      = bool(v & 0x80000)

    parts = []
    if undervolt_now: parts.append("UNDERVOLT_NOW")
    if freq_cap_now:  parts.append("FREQCAP_NOW")
    if throttle_now:  parts.append("THROTTLE_NOW")
    if temp_now:      parts.append("TEMP_NOW")

    if undervolt_was: parts.append("UNDERVOLT_WAS")
    if freq_cap_was:  parts.append("FREQCAP_WAS")
    if throttle_was:  parts.append("THROTTLE_WAS")
    if temp_was:      parts.append("TEMP_WAS")

    text = " ".join(parts)

    # Если есть NOW-флаги — красный, если только WAS — жёлтый
    if undervolt_now or freq_cap_now or throttle_now or temp_now:
        return (text, RED)
    return (text, YELLOW)
