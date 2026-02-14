# Метрики сети

import socket

def get_ip():
    """
    Возвращает IPv4 адрес. Если ошибка — 'no ip'
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "no ip"

