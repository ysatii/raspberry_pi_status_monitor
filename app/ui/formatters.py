# Форматирование строк для UI

from datetime import datetime, timedelta, timezone

def get_moscow_time_str(blink: bool):
    try:
        utc_now = datetime.now(timezone.utc)
        msk = utc_now + timedelta(hours=3)

        sep = ":" if blink else " "   # 
        return f"MSK {msk:%H}{sep}{msk:%M}{sep}{msk:%S}"
    except Exception:
        return "MSK n/a"
 
