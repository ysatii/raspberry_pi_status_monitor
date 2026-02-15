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
├── app/  
│   ├── config/  
│   ├── core/  
│   ├── display/  
│   ├── metrics/  
│   ├── ui/  
│   └── __init__.py  
├── splash.png  
├── tft_test.py  
├── requirements.txt  
└── README.md  

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
Description=Raspberry Pi TFT Status Monitor
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Desktop/raspberry_pi_status_monitor
ExecStart=/home/pi/tftenv/bin/python3 -m app
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload  
sudo systemctl enable tft.service  
sudo systemctl start tft.service

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

## 📜 Лицензия

Свободное использование и модификация.  
Берите , модифицируйте кто хотите!
