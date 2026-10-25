"""Pillow layouts shared by hardware and Mac preview; no hardware imports."""
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from .weather import condition, number
from .weather_art import BLUE, weather_icon
from .palette import indexed_image

INK = "#000000"
GREEN = "#00ff00"
RED = "#ff0000"


@lru_cache(maxsize=48)
def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [str(Path(__file__).parent / "data" / name),
                  f"/usr/share/fonts/truetype/dejavu/{name}",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
                  "/System/Library/Fonts/Supplemental/Arial.ttf", name]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def wrap(draw, text, face, width):
    lines = []
    for paragraph in str(text).split("\n"):
        line = ""
        for word in paragraph.split():
            # Split oversized tokens, including long place names, without overflow.
            while draw.textlength(word, font=face) > width:
                if line:
                    lines.append(line)
                    line = ""
                n = max(1, int(len(word) * width / draw.textlength(word, font=face)))
                while n > 1 and draw.textlength(word[:n], font=face) > width:
                    n -= 1
                lines.append(word[:n])
                word = word[n:]
            candidate = f"{line} {word}".strip()
            if line and draw.textlength(candidate, font=face) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line or not paragraph:
            lines.append(line)
    return lines


def text_block(draw, text, box, size=22, minimum=14, bold=False, fill=INK):
    x, y, width, height = box
    for current in range(size, minimum - 1, -1):
        face = font(current, bold)
        lines = wrap(draw, text, face, width)
        line_height = current + 5
        if len(lines) * line_height <= height:
            break
    capacity = max(1, height // line_height)
    if len(lines) > capacity:
        lines = lines[:capacity]
        tail = lines[-1]
        while tail and draw.textlength(tail + "…", font=face) > width:
            tail = tail[:-1]
        lines[-1] = tail + "…"
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height
    return y


def temp(value, units):
    if not number(value):
        return "—"
    if units == "F":
        value = value * 9 / 5 + 32
    return f"{value:.0f}°{units}"


def percent(value):
    return f"{value:.0f}%" if number(value) else "—"


def footer(draw, c, d):
    draw.line((22, 365, 578, 365), fill=INK, width=2)
    draw.text((24, 375), "A Weather  B French", font=font(13, True), fill=INK)
    draw.text((278, 375), f"C {c}   D {d}", font=font(13, True), fill=INK)


def heading(draw, title, right, fill=INK):
    draw.rectangle((0, 0, 600, 46), fill=fill)
    draw.text((24, 12), title, font=font(18, True), fill="white")
    draw.rounded_rectangle((380, 8, 578, 37), radius=4, fill="#ffff00")
    draw.text((390, 15), right, font=font(15, True), fill=INK)


def weather_screen(draw, snapshot):
    settings = snapshot["settings"]
    city = settings["city"]
    weather_timezone = city["timezone"] if city else settings["timezone"]
    now = datetime.fromisoformat(snapshot["now"]).astimezone(ZoneInfo(weather_timezone))
    heading(draw, "THE WEATHER", now.strftime("%a %d %b"))
    city = settings["city"]
    footer(draw, "Today / 3 days", "Update")
    if not city:
        text_block(draw, "A little local weather", (26, 90, 548, 80), 36, bold=True)
        text_block(draw, "Choose your city in the web dashboard.\nOpen small.local:8080 on your phone or laptop.",
                   (26, 190, 540, 130), 24)
        return
    text_block(draw, city["name"], (24, 55, 410, 52), 30, 18, bold=True)
    weather = snapshot["weather"]
    if not weather:
        text_block(draw, "Waiting for the forecast", (24, 132, 550, 70), 30, bold=True)
        message = "Weather is unavailable. Check the Pi's internet connection; it will retry automatically." if snapshot["weather_error"] else "Fetching your local weather. French lessons are available while you wait."
        text_block(draw, message, (24, 215, 550, 106), 23)
        return
    units = settings["units"]
    local_day = now.date().isoformat()
    today = next((day for day in weather["days"] if day["date"] == local_day), {})
    if snapshot["selection"]["weather_view"] == "today":
        text_block(draw, temp(weather.get("temperature"), units), (24, 112, 290, 80), 62, bold=True)
        text_block(draw, condition(weather.get("code")), (25, 202, 292, 63), 25, bold=True)
        weather_icon(draw, weather.get("code"), (438, 54, 140, 78))
        draw.rectangle((340, 149, 345, 193), fill=GREEN)
        draw.rectangle((340, 237, 345, 254), fill=RED)
        draw.rectangle((340, 264, 345, 281), fill=BLUE)
        text_block(draw, "FEELS LIKE\n" + temp(weather.get("feels_like"), units),
                   (354, 145, 220, 70), 23, bold=True)
        text_block(draw, f"HIGH {temp(today.get('high'), units)}\nLOW  {temp(today.get('low'), units)}",
                   (354, 232, 220, 65), 22, bold=True)
        text_block(draw, "Rain chance  " + percent(weather.get("rain")),
                   (25, 282, 300, 35), 23, 17, bold=True)
    else:
        future = [day for day in weather["days"] if day["date"] > local_day][:3]
        if not future:
            text_block(draw, "Cached forecast has expired. Press D to update.", (24, 140, 550, 150), 28)
        for i, day in enumerate(future):
            x = 24 + i * 188
            if i:
                draw.line((x - 10, 123, x - 10, 312), fill=INK, width=2)
            draw.text((x, 127), datetime.fromisoformat(day["date"]).strftime("%a %d"),
                      font=font(22, True), fill=INK)
            weather_icon(draw, day.get("code"), (x + 92, 115, 76, 57))
            draw.rectangle((x, 160, x+72, 163), fill=GREEN)
            draw.rectangle((x, 242, x+48, 245), fill=RED)
            draw.rectangle((x+60, 242, x+108, 245), fill=BLUE)
            text_block(draw, condition(day.get("code")), (x, 179, 170, 60), 21, 16, bold=True)
            text_block(draw, f"{temp(day.get('high'), units)} / {temp(day.get('low'), units)}",
                       (x, 249, 170, 29), 22, 17, bold=True)
            draw.text((x, 291), "Rain " + percent(day.get("rain")), font=font(18, True), fill=INK)
    fetched = datetime.fromisoformat(weather["fetched_at"]).astimezone(ZoneInfo(weather_timezone))
    label = "SAMPLE DATA" if snapshot["sample"] else "STALE · " if snapshot["stale"] else "Updated "
    draw.text((24, 332), label + " " + fetched.strftime("%d %b %H:%M"), font=font(13), fill=RED if snapshot["stale"] else INK)
    draw.text((24, 351), "Weather: Open-Meteo.com · CC BY 4.0", font=font(10), fill=INK)


def french_screen(draw, snapshot):
    card_index = snapshot["selection"]["card"]
    card = snapshot["lesson"]["cards"][card_index]
    heading(draw, "UN PEU DE FRANÇAIS", f"~B1 · {card_index + 1} / 3")
    # French tricolor and a three-step card-position indicator.
    for left, color in ((24, BLUE), (42, "white"), (60, RED)):
        draw.rectangle((left, 77, left+17, 83), fill=color)
    draw.rectangle((24, 77, 78, 83), outline=INK, width=1)
    for step in range(3):
        left = 526 + step * 18
        draw.rectangle((left, 60, left+11, 71),
                       fill=GREEN if step <= card_index else "white", outline=INK, width=2)
    draw.text((24, 58), snapshot["lesson_day"] + "  ·  " + card["kind"].upper(), font=font(14, True), fill=INK)
    text_block(draw, card["title"], (24, 89, 552, 67), 36, 19, bold=True)
    text_block(draw, card["meaning"], (24, 157, 552, 43), 21, 15, bold=True)
    draw.rounded_rectangle((18, 202, 582, 294), radius=8, fill="white", outline=INK, width=2)
    draw.rectangle((18, 215, 23, 281), fill=RED)
    text_block(draw, card["example"], (28, 209, 544, 42), 20, 15, bold=True)
    text_block(draw, card["translation"], (28, 254, 544, 34), 17, 12)
    text_block(draw, card["note"], (24, 300, 552, 45), 17, 12)
    if card.get("credit"):
        draw.text((24, 350), card["credit"], font=font(10, True), fill=INK)
    footer(draw, "Previous", "Next")


SCREENS = {"weather": weather_screen, "french": french_screen}


def render(snapshot):
    image = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # Solid glyph strokes rather than gray antialiasing.
    SCREENS[snapshot["selection"]["app"]](draw, snapshot)
    return indexed_image(image).convert("RGB")
