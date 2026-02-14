# Метрики аптайма



def get_uptime_parts():
    try:
        with open("/proc/uptime") as f:
            seconds = int(float(f.read().split()[0]))
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        mins = (seconds % 3600) // 60
        return days, hours, mins
    except Exception:
        return None
