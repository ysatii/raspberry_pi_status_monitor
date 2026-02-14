# Инициализация шрифта

from PIL import ImageFont

def load_font():
    font = ImageFont.load_default()
    line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    return font, line_h
