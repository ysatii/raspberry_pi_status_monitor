# Raspberry Pi Status Monitor (TFT)

Системный монитор для Raspberry Pi с выводом основных параметров на TFT-дисплей (SPI).  
Приложение рассчитано на постоянную работу и отображает состояние системы в реальном времени.

---

## 📊 Отображаемые параметры

- Температура CPU  
- Частота CPU (MHz)  
- Загрузка CPU  
- Использование RAM  
- Диск (занято / свободно)  
- Сеть  
- Питание и троттлинг (undervoltage / перегрев / ограничения частоты)  
- Uptime  
- Heartbeat-индикатор  

---

## ⚙ Требования

- Raspberry Pi OS (Debian-based)
- Python 3
- Включённый SPI
- TFT SPI дисплей 128×128
- systemd

---

## 📁 Расположение

Проект:
/home/pi/Desktop/raspberry_pi_status_monitor

Виртуальное окружение:
/home/pi/tftenv

---

## 🗂 Структура проекта

raspberry_pi_status_monitor/  
.
├── app  
│   ├── config  
│   │   ├── __init__.py  
│   │   └── settings.py  
│   ├── core  
│   │   └── __init__.py  
│   ├── display  
│   │   ├── device.py  
│   │   ├── fonts.py  
│   │   ├── __init__.py  
│   │   └── splash.py  
│   ├── __init__.py  
│   ├── metrics  
│   │   ├── cpu.py  
│   │   ├── disk.py  
│   │   ├── __init__.py  
│   │   ├── network.py  
│   │   ├── power.py  
│   │   ├── ram.py  
│   │   ├── ssh.py  
│   │   └── uptime.py  
│   └── ui  
│       ├── colors.py  
│       ├── colors.py.save  
│       ├── formatters.py  
│       ├── heartbeat.py  
│       └── __init__.py  
├── README.md  
├── requirements.txt  
├── splash.png  
└── tft_test.py  


---

## 🔌 Включение SPI

sudo raspi-config  
Interface Options → SPI → Enable  
sudo reboot

---

## 🚀 Установка

python3 -m venv /home/pi/tftenv  
source /home/pi/tftenv/bin/activate  
cd /home/pi/Desktop/raspberry_pi_status_monitor  
pip install --upgrade pip  
pip install -r requirements.txt

---

## 📦 requirements.txt

cbor2==5.8.0  
luma.core==2.5.3  
luma.lcd==2.11.0  
pillow==12.1.0  
RPi.GPIO==0.7.1  
smbus2==0.6.0  
spidev==3.8  

---

## ▶ Запуск

source /home/pi/tftenv/bin/activate  
cd /home/pi/Desktop/raspberry_pi_status_monitor  
python3 -m app

---

## 🔁 Автозапуск через systemd

Имя сервиса: tft.service

/etc/systemd/system/tft.service

[Unit]
Description=TFT SPI Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Desktop/raspberry_pi_status_monitor
Environment=PYTHONUNBUFFERED=1
ExecStartPre=/bin/sleep 2
ExecStart=/home/pi/tftenv/bin/python /home/pi/Desktop/raspberry_pi_status_monit>
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.targe

---

## 🧹 Удаление Python-кеша

cd /home/pi/Desktop/raspberry_pi_status_monitor  
find . -type d -name "__pycache__" -prune -exec rm -rf {} +  
find . -type f -name "*.pyc" -delete  

.gitignore:
__pycache__/  
*.pyc  
*.pyo  
*.pyd  

---

## ⚠ Особенности инициализации дисплея ST7735

Файл:  
`/home/pi/Desktop/raspberry_pi_status_monitor/app/display/device.py`

В процессе разработки было обнаружено, что некоторые SPI-дисплеи **ST7735 (128×128)** могут нестабильно инициализироваться при быстром запуске или перезапуске приложения.

### Симптомы

- дисплей включается, но остаётся **чёрный экран**
- иногда дисплей начинает работать только после повторного запуска
- при быстром перезапуске службы `systemd` инициализация может не происходить

### Причина

Контроллер дисплея требует **аппаратного сброса (RST)** и времени для выхода из состояния reset.  
Без задержек контроллер может не принять первые SPI-команды.

### Решение

Для обеспечения стабильной инициализации используется следующая последовательность:

```python
GPIO.cleanup()
time.sleep(1)

hardware_reset()
time.sleep(1)

## 📜 Лицензия

Свободное использование и модификация.  
Берите , модифицируйте кто хотите!
