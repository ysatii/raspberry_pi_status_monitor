# проект статус монитор!
import os
import time
from datetime import datetime


from PIL import Image, ImageDraw, ImageFont

import RPi.GPIO as GPIO
GPIO.setwarnings(False)

from app.display.fonts import load_font
from app.ui.formatters import get_moscow_time_str
from app.display.device import create_device

from app.ui.colors import (
    RED, GREEN, YELLOW, BLUE, WHITE,
    temp_color, sshd_color, volts_color,
    disk_color, cpu_freq_color, sshd_style
)

from app.metrics.ram import get_ram_used_mb
from app.metrics.disk import get_disk_usage
from app.metrics.network import get_ip
from app.metrics.cpu import (
    get_cpu_temp, get_load1,
    get_cpu_freq_mhz, get_throttled_hex, throttling_status
)
from app.metrics.power import get_core_volts
from app.metrics.uptime import get_uptime_parts
from app.metrics.ssh import get_ssh_load, get_sshd_cpu_top_with_count
from app.ui.heartbeat import Heartbeat

from app.display.splash import show_splash
from app.config.settings import SLEEP_SECONDS
from app.config.settings import (
    DEBUG,
    SLEEP_SECONDS,  # если ещё используется
    DISK_PERIOD, IP_PERIOD, SSHD_PERIOD,
    THROTTLED_PERIOD, VOLTS_PERIOD,
    CPU_FREQ_PERIOD, LOAD1_PERIOD, CPU_TEMP_PERIOD,
    DISPLAY_PERIOD
)

try:
    from app.config.settings import FRAME_PERIOD
except Exception:
    FRAME_PERIOD = 1.0

import threading
from app.config.settings import DEBUG




device = create_device()


SPLASH_PATH = os.path.join(os.path.dirname(__file__), "splash.png")
show_splash(device, SPLASH_PATH)
font, line_h = load_font()


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


        
        
        

        
        
state_lock = threading.Lock()
state = {
    "tick": 0,
    "disk": None,
    "disk_ts": 0.0,
    "net_ip": None,
    "net_ts": 0.0,
    "sshd": None,
    "sshd_ts": 0.0,
    "throttled_hex": None,
    "throttled_ts": 0.0,
    "volts": None,
    "volts_ts": 0.0,
    "cpu_temp": None,
    "cpu_temp_ts": 0.0,
    "cpu_freq": None,
    "cpu_freq_ts": 0.0,
    "load1": None,
    "load1_ts": 0.0,
}



stop_event = threading.Event()

def collector():
    while not stop_event.is_set():
        now = time.monotonic()
        need_disk = False
        need_net = False
        need_sshd = False
        need_throttled = False
        need_volts = False
        need_temp = False
        need_freq = False
        need_load = False

        # решаем под lock, надо ли обновлять диск
        with state_lock:
            state["tick"] += 1
            need_disk = (now - state["disk_ts"] >= DISK_PERIOD)
            if need_disk:
                state["disk_ts"] = now
            
            need_net = (now - state["net_ts"] >= IP_PERIOD)
            if need_net:
                state["net_ts"] = now
            
            if now - state["sshd_ts"] >= SSHD_PERIOD:
                state["sshd_ts"] = now
                need_sshd = True
            
            if now - state["throttled_ts"] >= THROTTLED_PERIOD:
                state["throttled_ts"] = now
                need_throttled = True
           
            if now - state["volts_ts"] >= VOLTS_PERIOD:
                state["volts_ts"] = now
                need_volts = True
            
            if now - state["cpu_temp_ts"] >= CPU_TEMP_PERIOD:
                state["cpu_temp_ts"] = now
                need_temp = True    
                
            if now - state["cpu_freq_ts"] >= CPU_FREQ_PERIOD:
                state["cpu_freq_ts"] = now
                need_freq = True

            if now - state["load1_ts"] >= LOAD1_PERIOD:
                state["load1_ts"] = now
                need_load = True


        # тяжёлое делаем БЕЗ lock
        if need_disk:
            if DEBUG:
                print("DISK UPDATE:", time.strftime("%H:%M:%S"))
            d = get_disk_usage()
            with state_lock:
                state["disk"] = d
        if need_net:
            if DEBUG:
                print("ip:", time.strftime("%H:%M:%S"))
            ip = get_ip()
            with state_lock:
                state["net_ip"] = ip
        
        if need_sshd:
            if DEBUG:
                print("sshd:", time.strftime("%H:%M:%S"))
            ssh_load = get_ssh_load()
            top_cpu, top_pid = get_sshd_cpu_top_with_count()
            with state_lock:
                state["sshd"] = (ssh_load, top_cpu, top_pid)
        
        if need_throttled:
            th = get_throttled_hex()
            if DEBUG:
                print("throttled_hex:", th, time.strftime("%H:%M:%S"))
            with state_lock:
                state["throttled"] = th
        
        if need_volts:
            v = get_core_volts()
            if DEBUG:
                print("volts:", v, time.strftime("%H:%M:%S"))
            with state_lock:
                state["volts"] = v
                
        if need_temp:
            t = get_cpu_temp()
            if DEBUG:
                print("temp:", time.strftime("%H:%M:%S"), t)
            with state_lock:
                state["cpu_temp"] = t
                
        if need_freq:
            f = get_cpu_freq_mhz()
            if DEBUG and need_freq:
                print("freq:", time.strftime("%H:%M:%S"), f)
            with state_lock:
                state["cpu_freq"] = f

        if need_load:
            l1 = get_load1()
            if DEBUG and need_load:
                print("load1:", time.strftime("%H:%M:%S"), l1)
            with state_lock:
                state["load1"] = l1       



        time.sleep(1)


collector_thread = threading.Thread(target=collector, daemon=True)
collector_thread.start()

snap_counter = 0   # ← вот тут объявляем



 

     
     
        
        
blink = False
ssh_overload = False

time_bar_pos = 0
TIME_BAR_LEN = 5




blink = False
blink_last = time.monotonic()
BLINK_PERIOD = 0.5   # секунды, можно 0.5 если хочешь чаще

 

# --- heartbeat state ---
HB_LEN = 50   # как у тебя было
hb = Heartbeat(hb_len=HB_LEN, step=6, start_pos=0)

# --- inside main render loop ---



frame_counter = 0
fps_last = time.monotonic()


# РіР»Р°РІРЅС‹Р№ С†РёРєР»
# --- Main loop ---
while True:
    with state_lock:
        snap = dict(state)
        
    snap_counter += 1
    if snap_counter % 10 == 0:
        if DEBUG:
            print("SNAP OK, tick=", snap.get("tick"))

    
    frame_start = time.monotonic()
    
    img = Image.new("RGB", (128, 128), "black")
    draw = ImageDraw.Draw(img)

    ip = snap.get("net_ip")
    if not ip:
        ip = get_ip()
    
    temp = snap.get("cpu_temp")
    if temp is None:
        temp = get_cpu_temp()
    
    
    #throttled = throttling_status
    throttled = get_throttled_hex()

    load1 = snap.get("load1")
    if load1 is None:
        load1 = get_load1()
    
    
    s = snap.get("sshd")
    if s is None:
        ssh_load = get_ssh_load()
        top_cpu, top_pid = get_sshd_cpu_top_with_count()
    else:
        ssh_load, top_cpu, top_pid = s

    sshd_cpu = top_cpu
    sshd_load = ssh_load
    
    th = get_throttled_hex()


    
    
    if sshd_cpu is not None and sshd_cpu > 100:
        ssh_overload = True 
    else:
        ssh_overload = False
        
    #blink = False
    

    
    upt = get_uptime_parts()
    ram_used, ram_total = get_ram_used_mb()
    msk_time = get_moscow_time_str(blink)
    
    vcore = snap.get("volts")
    if vcore is None:
        vcore = get_core_volts()
        
        
    d = snap.get("disk")

    if d is None:
        disk_used, disk_total = get_disk_usage()
    else:
        disk_used, disk_total = d

    if disk_used is not None and disk_total:
        disk_pct = int((disk_used / disk_total) * 100)
    else:
        disk_pct = 0

    
    
    cpu_freq = snap.get("cpu_freq")
    if cpu_freq is None:
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
    
    if th:
        t_text, t_color = throttling_status(th)
        if t_color==RED:
            t_color = WHITE if blink else RED
        draw.text((0, line_h * 2), t_text, fill=t_color, font=font)
        
    else:
        draw.text((0, line_h * 2), "THROTTLING n/a", fill=GREEN, font=font)
    

    # 4 ?????? ? LOAD
    if load1 is not None:
        draw.text((0, line_h * 3), f"LOAD: {load1:.2f}", fill="white", font=font)
    else:
        draw.text((0, line_h * 3), "LOAD: n/a", fill="red", font=font)
        
    # 5 ?????? ? SSHD %CPU (??? top)
    # 5 ?????? ? SSHD %CPU + count, ????? ???? + ??????? ??? >100%

    if DEBUG:
        print("DEBUG SSHD:", sshd_cpu, sshd_load)

    if sshd_cpu is not None:
        color = sshd_color(sshd_cpu)
         
        # ???? ???????? (ssh_overload=True) ? ?????? ???????<->?????
        if ssh_overload:
            color = WHITE if blink else RED

        draw.text(
            (0, line_h * 4),
            f"SSHD:{sshd_cpu:.1f}% (load {sshd_load})",
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
    
    
    bar = (" " * time_bar_pos) + "|" + (" " * (TIME_BAR_LEN - time_bar_pos - 1))
    time_bar_pos = (time_bar_pos + 1) % TIME_BAR_LEN
    draw.text((0, line_h * 7), f"{msk_time} {bar}", fill=WHITE, font=font)
    
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
 
    now_b = time.monotonic()
    if now_b - blink_last >= BLINK_PERIOD:
        blink = not blink
        blink_last = now_b

    frame_counter += 1
    now_fps = time.monotonic()

    if now_fps - fps_last >= 1.0:
        if DEBUG:
            print("FPS:", frame_counter)
        frame_counter = 0
        fps_last = now_fps

    device.display(img)
    time.sleep(DISPLAY_PERIOD)
