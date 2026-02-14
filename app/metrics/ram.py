# Метрики памяти (RAM)

def get_ram_used_mb():
    """
    Возвращает (used_mb, total_mb). Если ошибка — (None, None)
    """
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":")
                mem[k] = int(v.strip().split()[0])  # kB

        total = mem["MemTotal"] // 1024
        available = mem["MemAvailable"] // 1024
        used = total - available

        return used, total
    except Exception:
        return None, None
