
# Цвета и функции выбора цвета

RED    = (255, 0, 0)
GREEN  = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE   = (0, 0, 255)
WHITE  = (255, 255, 255)

def temp_color(temp_c):
    if temp_c is None:
        return RED
    if temp_c < 60:
        return GREEN
    if temp_c < 70:
        return YELLOW
    return RED

def sshd_color(cpu):
    if cpu is None:
        return RED
    if cpu < 10:
        return GREEN
    if cpu < 50:
        return YELLOW
    return RED

def volts_color(v):
    if v is None:
        return RED
    if v >= 1.1:
        return GREEN
    if v >= 1.0:
        return YELLOW
    return RED

def disk_color(used, total):
    if used is None or total is None or total <= 0:
        return RED
    p = (used / total) * 100.0
    if p < 70:
        return GREEN
    if p < 85:
        return YELLOW
    return RED

def cpu_freq_color(mhz):
    if mhz is None:
        return RED
    if mhz == 600:
        return GREEN
    if mhz < 1000:
        return YELLOW
    return RED

def sshd_style(sshd_cpu, sshd_cnt):
    if sshd_cnt is None:
        sshd_cnt = 0
    if sshd_cpu is None:
        return RED
    if sshd_cpu > 100:
        return RED
    if sshd_cnt > 5:
        return YELLOW
    return sshd_color(sshd_cpu)
