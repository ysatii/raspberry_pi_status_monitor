# Метрики диска

import subprocess

def get_disk_usage(path="/"):
    """
    Возвращает (used_mb, total_mb). Если ошибка — (None, None)
    """
    try:
        st = subprocess.check_output(["df", "-m", path], text=True).splitlines()
        cols = st[1].split()
        total = int(cols[1])
        used = int(cols[2])
        return used, total
    except Exception:
        return None, None

