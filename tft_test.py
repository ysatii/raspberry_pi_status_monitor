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
from app.ui.formatters import get_moscow_time_str



from app.ui.colors import (
    RED, GREEN, YELLOW, BLUE, WHITE,
    temp_color, sshd_color, volts_color,
    disk_color, cpu_freq_color, sshd_style
)

from app.metrics.ram import get_ram_used_mb
from app.metrics.disk import get_disk_usage
from app.metrics.network import get_ip
from app.metrics.cpu import get_cpu_temp, get_load1
from app.metrics.cpu import (
    get_cpu_temp, get_load1,
    get_cpu_freq_mhz, get_throttled_hex, throttling_status
)
from app.metrics.power import get_core_volts
from app.metrics.uptime import get_uptime_parts
from app.metrics.ssh import get_ssh_load, get_sshd_cpu_top_with_count
from app.ui.heartbeat import Heartbeat



 

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
     
     
        
        
blink = False
ssh_overload = False


 

# --- heartbeat state ---
HB_LEN = 50   # как у тебя было
hb = Heartbeat(hb_len=HB_LEN, step=9, start_pos=0)

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
            up_text = f"UP: {d}d{sep}{h:02d}h{sep}{m:02d}m"
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


    hb_bar = hb.tick()

    draw.text(
        (0, line_h * 11),
        f"SYS {hb_bar}",
        fill=BLUE,
        font=font
)

 
    blink = not blink



    device.display(img)
    time.sleep(1)
