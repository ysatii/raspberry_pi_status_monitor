# проект статус монитор!
from PIL import Image
import os, time

import time
from datetime import datetime, timedelta, timezone
import socket
import subprocess
from luma.core.interface.serial import spi
from luma.lcd.device import st7735
from PIL import Image, ImageDraw, ImageFont
import os
import RPi.GPIO as GPIO
GPIO.setwarnings(False)




RED    = (255, 0, 0)
GREEN  = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE   = (0, 0, 255)
WHITE  = (255, 255, 255)

# --- SPI / TFT ---
serial = spi(
    port=0,
    device=0,
    gpio_DC=25,
    gpio_RST=24,
    bus_speed_hz=32000000
)

device = st7735(serial, width=128, height=128, rotate=0, bgr=True)

SPLASH_PATH = os.path.join(os.path.dirname(__file__), "splash.png")
try:
    splash = Image.open(SPLASH_PATH).convert("RGB")
    splash = splash.resize((128, 128), Image.NEAREST)
    device.display(splash)
    time.sleep(2)
except Exception as e:
    print("Splash skipped:", e)


font = ImageFont.load_default()
line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]

# --- IP ---
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "no ip"

# --- CPU temperature ---
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read()) / 1000.0
    except Exception:
        return None

def temp_color(temp):
    if temp < 50:
        return GREEN
    elif temp < 65:
        return YELLOW 
    else:
        return RED

# --- Throttling ---
def throttling_status(throttled_hex: str):
    """
    Returns (text, color)
    """
    try:
        v = int(throttled_hex, 16)
    except Exception:
        return ("THROTTLING READ ERROR", YELLOW)

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

    # Priority: what is happening NOW
    if temp_now or throttle_now:
        return ("OVERHEAT NOW", RED)  

    if undervolt_now:
        return ("UNDERVOLT NOW", RED)

    if freq_cap_now:
        return ("FREQ CAPPED NOW", RED)

    # If NOW is ok, but WAS happened
    if temp_was or throttle_was:
        return ("OVERHEAT WAS", YELLOW)

    if undervolt_was:
        return ("UNDERVOLT WAS", YELLOW)

    if freq_cap_was:
        return ("FREQ CAPPED WAS", YELLOW)

    return (f"THROTTLED {throttled_hex}", YELLOW)

        
    

def sshd_color(cpu):
    if cpu < 20:
        return GREEN
    elif cpu < 70:
        return YELLOW
    else:
        return RED
        
def get_throttled_hex():
    try:
        out = subprocess.check_output(["vcgencmd", "get_throttled"], text=True).strip()
        return out.split("=")[1] # 0x50005
    except Exception:
        return None


# --- Load average (1 min) ---
def get_load1():
    try:
        with open("/proc/loadavg") as f:
            return float(f.read().split()[0])
    except Exception:
        return None

# ---SSH---
def get_ssh_load():
    try:
        out = subprocess.check_output(
            ["ps", "-C", "ssh", "-o", "%cpu="],
            text=True
        )
        values = [float(x) for x in out.split()]
        return sum(values)
    except Exception:
        return None
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

_prev_total_jiffies = None
_prev_sshd_jiffies = {}  # pid -> jiffies

def _read_total_jiffies():
    # ????????? jiffies ?? CPU (user+nice+system+idle+iowait+irq+softirq+steal)
    with open("/proc/stat", "r") as f:
        cpu = f.readline().split()[1:]
    return sum(int(x) for x in cpu)

def _list_sshd_pids():
    pids = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        try:
            with open(f"/proc/{pid}/comm", "r") as f:
                comm = f.read().strip()
            if comm == "ssh":
                pids.append(pid)
        except Exception:
            pass
    return pids

def _read_proc_jiffies(pid):
    # utime + stime ?? /proc/<pid>/stat
    with open(f"/proc/{pid}/stat", "r") as f:
        parts = f.read().split()
    utime = int(parts[13])
    stime = int(parts[14])
    return utime + stime

def get_sshd_cpu_percent():
    global _prev_total_jiffies, _prev_sshd_jiffies

    try:
        total_now = _read_total_jiffies()
        pids = _list_sshd_pids()

        # ??????? jiffies sshd ?? pid
        sshd_now = {}
        for pid in pids:
            try:
                sshd_now[pid] = _read_proc_jiffies(pid)
            except Exception:
                pass

        # ?????? ?????? ? ??? ??????
        if _prev_total_jiffies is None:
            _prev_total_jiffies = total_now
            _prev_sshd_jiffies = sshd_now
            return 0.0

        total_delta = total_now - _prev_total_jiffies
        if total_delta <= 0:
            _prev_total_jiffies = total_now
            _prev_sshd_jiffies = sshd_now
            return 0.0

        # ????? ????? ?? pid (???? pid ????? ? ??????? 0 ?? ?????? ?????)
        sshd_delta = 0
        for pid, j in sshd_now.items():
            prev = _prev_sshd_jiffies.get(pid, j)
            d = j - prev
            if d > 0:
                sshd_delta += d

        _prev_total_jiffies = total_now
        _prev_sshd_jiffies = sshd_now

        # %CPU ???????????? ???? ??????? (?? ???? ?????), ??? ? top ????????
        percent = (sshd_delta / total_delta) * 100.0
        return percent

    except Exception:
        return None
def get_sshd_cpu_top():
    try:
        pids = subprocess.check_output(["pgrep", "ssh"], text=True).split()
        if not pids:
            return 0.0

        pid_list = ",".join(pids)
        out = subprocess.check_output(
            ["top", "-b", "-n", "1", "-p", pid_list],
            text=True,
            stderr=subprocess.DEVNULL
        )

        total = 0.0
        for line in out.splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            cols = line.split()
            total += float(cols[8].replace(",", "."))  # %CPU
        return total
    except subprocess.CalledProcessError:
        return 0.0
    except Exception:
        return None

def get_sshd_cpu_top_with_count():
    try:
        pids = subprocess.check_output(["pgrep", "ssh"], text=True).split()
        if not pids:
            return 0.0, 0

        pid_list = ",".join(pids)
        out = subprocess.check_output(
            ["top", "-b", "-n", "1", "-p", pid_list],
            text=True,
            stderr=subprocess.DEVNULL
        )

        total = 0.0
        found_lines = 0

        for line in out.splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue

            cols = line.split()
            # ? standard top: ... S %CPU %MEM ...
            # %CPU ?????? cols[8]
            try:
                total += float(cols[8].replace(",", "."))
                found_lines += 1
            except Exception:
                pass

        return total, found_lines

    except subprocess.CalledProcessError:
        return 0.0, 0
    except Exception:
        return None, 0

def sshd_style(sshd_cpu):
    # ???? ?? ????? ???????
    if sshd_cpu < 20:
        return "green"
    elif sshd_cpu < 70:
        return "yellow"
    else:
        return "red"

def get_sshd_cpu_top_with_count():
    try:
        pids = subprocess.check_output(["pgrep", "ssh"], text=True).split()
        if not pids:
            return 0.0, 0

        pid_list = ",".join(pids)
        out = subprocess.check_output(
            ["top", "-b", "-n", "1", "-p", pid_list],
            text=True,
            stderr=subprocess.DEVNULL
        )

        total = 0.0
        lines = 0
        for line in out.splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            cols = line.split()

            # ?????? %CPU ????? ???? ?? ?? 8 ??????? ??-?? ?????? ?????? top.
            # ????????? ?????????: ?????? ???????, ??????? ?? ????? ? ??????, ????? ? %MEM.
            # ?? ??????? ? ??????????? ???????:
            try:
                total += float(cols[8].replace(",", "."))
                lines += 1
                continue
            except Exception:
                pass

        return total, lines
    except subprocess.CalledProcessError:
        return 0.0, 0
    except Exception:
        return None, 0
        



def get_ram_used_mb():
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

        
        
        
blink = False
ssh_overload = False


def get_core_volts():
    try:
        out = subprocess.check_output(["vcgencmd", "measure_volts", "core"], text=True).strip()
        # volt=0.8625V
        v = float(out.split("=")[1].replace("V", ""))
        return v
    except Exception:
        return None

def volts_color(v):
    if v is None:
        return RED
    if v >= 0.85:
        return GREEN
    elif v >= 0.83:
        return YELLOW
    else:
        return RED





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


def get_ram_used_mb():
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
        
def get_moscow_time_str(blink: bool):
    try:
        utc_now = datetime.now(timezone.utc)
        msk = utc_now + timedelta(hours=3)

        sep = ":" if blink else " "   # 
        return f"MSK {msk:%H}{sep}{msk:%M}{sep}{msk:%S}"
    except Exception:
        return "MSK n/a"


def get_disk_usage():
    try:
        st = os.statvfs("/")
        total = (st.f_blocks * st.f_frsize) // (1024 * 1024)
        free  = (st.f_bavail * st.f_frsize) // (1024 * 1024)
        used  = total - free
        return used, total
    except Exception:
        return None, None

def disk_color(used, total):
    if total == 0:
        return RED
    pct = used / total * 100
    if pct < 70:
        return GREEN
    elif pct < 85:
        return YELLOW
    else:
        return RED



def get_cpu_freq_mhz():
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_clock", "arm"],
            text=True
        ).strip()
        # frequency(48)=1500000000
        hz = int(out.split("=")[1])
        return hz // 1_000_000
    except Exception:
        return None

def cpu_freq_color(mhz):
    if mhz is None:
        return RED
    if mhz == 600:
        return GREEN
    elif mhz < 1000:
        return YELLOW
    else:
        return RED

# --- heartbeat state ---
hb_pos = 0
HB_LEN = 50
# --- inside main render loop ---




# РіР»Р°РІРЅС‹Р№ С†РёРєР»
# --- Main loop ---
while True:
    
    img = Image.new("RGB", (128, 128), "black")
    draw = ImageDraw.Draw(img)

    ip = get_ip()
    temp = get_cpu_temp()
    #throttled = throttling_status
    throttled = get_throttled_hex()

    load1 = get_load1()
    ssh_load = get_ssh_load()
    sshd_cpu, sshd_cnt = get_sshd_cpu_top_with_count()
    if sshd_cpu is not None and sshd_cpu > 100:
        ssh_overload = True 
    else:
        ssh_overload = False
        
    #blink = False
    

    
    upt = get_uptime_parts()
    ram_used, ram_total = get_ram_used_mb()
    msk_time = get_moscow_time_str(blink)
    vcore = get_core_volts()
    disk_used, disk_total = get_disk_usage()
    cpu_freq = get_cpu_freq_mhz()
    



    # 1 Выводим ИП адрес
    # 
    draw.text((0, 0), f"IP: {ip}:1081", fill=GREEN, font=font)

    # 2 СЃС‚СЂРѕРєР° С‚РµРјРїРµСЂР°С‚СѓСЂР° РїСЂРѕС†РµСЃСЃРѕСЂР°
    if temp is not None:
        draw.text((0, line_h * 1), f"CPU: {temp:.1f} C", fill=temp_color(temp), font=font)
    else:
        draw.text((0, line_h * 1), "CPU: n/a", fill="red", font=font)

    # 3 ?????? ? Throttling (?????)
    
    if throttled:
        t_text, t_color = throttling_status(throttled)
        if t_color==RED:
            t_color = WHITE if blink else RED
        draw.text((0, line_h * 2), t_text, fill=t_color, font=font)
        print("throttled:", t_text)
    else:
        draw.text((0, line_h * 2), "THROTTLING n/a", fill=GREEN, font=font)
    

    # 4 ?????? ? LOAD
    if load1 is not None:
        draw.text((0, line_h * 3), f"LOAD: {load1:.2f}", fill="white", font=font)
    else:
        draw.text((0, line_h * 3), "LOAD: n/a", fill="red", font=font)
        
    # 5 ?????? ? SSHD %CPU (??? top)
    # 5 ?????? ? SSHD %CPU + count, ????? ???? + ??????? ??? >100%

    print("DEBUG SSHD:", sshd_cpu, sshd_cnt)

    if sshd_cpu is not None:
        color = sshd_color(sshd_cpu)
         
        # ???? ???????? (ssh_overload=True) ? ?????? ???????<->?????
        if ssh_overload:
            color = WHITE if blink else RED

        draw.text(
            (0, line_h * 4),
            f"SSHD:{sshd_cpu:.1f}% ({sshd_cnt})",
            fill=color,
            font=font
        )
    else:
        draw.text((0, line_h * 4), "SSHD: n/a", fill=RED, font=font)

     
     
     
    sep = ":" if blink else " "
    if upt is not None:
        d, h, m = upt
        
       #up_text = f"UP: {d}d{sep}{h:02d}{sep}{m:02d}" if d > 0 else f"UP: {h:02d}{sep}{m:02d}"
        if d > 0:
            up_text = f"UP: {d}d{sep}{h:02d}{sep}{m:02d}"
        elif h > 0:
           up_text = f"UP: {h:02d}h{sep}{m:02d}m"
        else:
           up_text = f"UP: {m}m"

        draw.text((0, line_h * 5), up_text, fill=GREEN, font=font)
    else:
        draw.text((0, line_h * 5), "UP n/a", fill=RED, font=font)
     
     
     
     
     
    if ram_used is not None:
       draw.text(
           (0, line_h * 6),
           f"RAM USED: {ram_used} / {ram_total} MB",
           fill=WHITE,
           font=font
        )
    else:
        draw.text(
            (0, line_h * 6),
            "RAM: n/a",
            fill=RED,
            font=font
        )

    draw.text((0, line_h * 7), msk_time, fill=WHITE, font=font)
    
    if vcore is not None:
        draw.text((0, line_h * 8), f"VCORE: {vcore:.3f}V", fill=volts_color(vcore), font=font)
    else:
        draw.text((0, line_h * 8), "VCORE: n/a", fill=RED, font=font)

  

    if disk_used is not None:
        color = disk_color(disk_used, disk_total)
        draw.text(
            (0, line_h * 9),
            f"DISK: {disk_used} / {disk_total}MB",
            fill=color,
            font=font
        )
    else:
        draw.text((0, line_h * 9), "DISK: n/a", fill=RED, font=font)

    if cpu_freq is not None:
        draw.text(
            (0, line_h * 10),
            f"CPUF:{cpu_freq}MHz",
            fill=cpu_freq_color(cpu_freq),
            font=font
        )
    else:
        draw.text((0, line_h * 10), "CPUF: n/a", fill=RED, font=font)


    bar = [" "] * HB_LEN

    if hb_pos >= 2:
        bar[hb_pos - 2] = "="
    if hb_pos >= 1:
        bar[hb_pos - 1] = "="
    bar[hb_pos] = ">"
    hb_pos = (hb_pos + 9) % HB_LEN
    bar_text = "".join(bar)
    draw.text(
        (0, line_h * 11),
        f"SYS {bar_text}",
        fill=BLUE,
        font=font
    )
 
    blink = not blink



    device.display(img)
    time.sleep(1)
