"""Weather illustrations drawn with shapes in the Spectra 6 ink colors.

No icon fonts, image downloads, or runtime image-generation dependencies.
Coordinates use a 160 × 120 artboard, scaled into the requested box.
"""
import math

BLUE = "#0000ff"
YELLOW = "#ffff00"
BLACK = "#000000"
WHITE = "#ffffff"


def weather_icon(draw, code, box):
    x, y, width, height = box
    scale = min(width / 160, height / 120)
    x += (width - 160 * scale) / 2
    y += (height - 120 * scale) / 2
    stroke = max(2, round(4 * scale))

    def point(px, py):
        return round(x + px * scale), round(y + py * scale)

    def line(points, fill=BLACK, thickness=None):
        draw.line([point(*p) for p in points], fill=fill,
                  width=thickness or stroke, joint="curve")

    def ellipse(bounds, fill, outline=None):
        left, top, right, bottom = bounds
        draw.ellipse((*point(left, top), *point(right, bottom)), fill=fill,
                     outline=outline, width=stroke)

    def sun(cx, cy, radius):
        for i in range(8):
            angle = i * math.pi / 4
            line([(cx + math.cos(angle) * (radius + 8), cy + math.sin(angle) * (radius + 8)),
                  (cx + math.cos(angle) * (radius + 18), cy + math.sin(angle) * (radius + 18))], BLACK)
        ellipse((cx-radius, cy-radius, cx+radius, cy+radius), YELLOW, BLACK)

    def cloud():
        # A continuous outline avoids internal circle seams in the cloud lobes.
        outline = [(37, 82)]
        def curve(a, b, end):
            start = outline[-1]
            for step in range(1, 13):
                t = step / 12
                u = 1 - t
                outline.append((u**3*start[0] + 3*u*u*t*a[0] + 3*u*t*t*b[0] + t**3*end[0],
                                u**3*start[1] + 3*u*u*t*a[1] + 3*u*t*t*b[1] + t**3*end[1]))
        curve((17, 82), (13, 63), (27, 53))
        curve((32, 49), (38, 48), (43, 50))
        curve((41, 28), (59, 20), (74, 27))
        curve((90, 23), (105, 34), (105, 48))
        curve((119, 41), (133, 50), (132, 61))
        curve((151, 68), (142, 82), (126, 82))
        outline.append((37, 82))
        draw.polygon([point(px+3, py+5) for px, py in outline], fill=BLUE)
        draw.polygon([point(*p) for p in outline], fill=WHITE)
        line(outline)

    def drops(light=False):
        for dx, dy in ((51, 101), (80, 108), (109, 101)):
            if light:
                ellipse((dx-2, dy-2, dx+2, dy+2), BLUE)
            else:
                draw.polygon([point(dx, dy-10), point(dx-5, dy-1),
                              point(dx-4, dy+4), point(dx+3, dy+5),
                              point(dx+6, dy), point(dx, dy-10)], fill=BLUE)

    if code == 0:
        sun(80, 56, 27)
        return
    known = (1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
             71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99)
    if code not in known:
        ellipse((49, 23, 111, 85), WHITE, BLUE)
        # Draw the question mark as shapes, so this remains independent of fonts.
        line([(68, 43), (70, 36), (80, 33), (90, 38), (91, 46), (80, 55), (80, 62)], BLUE)
        ellipse((78, 70, 82, 74), BLUE)
        return
    if code in (1, 2):
        sun(49, 34, 16)
    cloud()
    if code in (45, 48):
        for left, right, dy in ((31, 127, 94), (43, 116, 104), (26, 96, 114)):
            line([(left, dy), (right, dy)], BLUE)
    elif code in (51, 53, 55, 56, 57):
        drops(light=True)
    elif code in (61, 63, 65, 66, 67, 80, 81, 82):
        drops()
    elif code in (71, 73, 75, 77, 85, 86):
        for cx, cy in ((49, 101), (80, 109), (111, 101)):
            for angle in (0, math.pi/3, 2*math.pi/3):
                dx, dy = math.cos(angle)*7, math.sin(angle)*7
                line([(cx-dx, cy-dy), (cx+dx, cy+dy)], BLUE)
    elif code in (95, 96, 99):
        bolt = [(78, 84), (63, 104), (79, 103), (72, 119), (100, 94), (84, 95), (92, 84)]
        draw.polygon([point(*p) for p in bolt], fill=YELLOW)
        line(bolt + [bolt[0]], BLACK, max(1, round(scale)))
