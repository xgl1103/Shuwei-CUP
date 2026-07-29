from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"E:\Code\数维杯")
SRC = ROOT / "论文图片" / "已生成图像 1.png"
OUT = ROOT / "论文图片" / "总体技术路线图_校正版.png"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


FONT_HEI = r"C:\Windows\Fonts\simhei.ttf"
FONT_KAI = r"C:\Windows\Fonts\simkai.ttf"

title_font = font(FONT_HEI, 24)
label_font = font(FONT_HEI, 14)
small_font = font(FONT_HEI, 12)
num_font = font(FONT_HEI, 15)
note_font = font(FONT_KAI, 13)


def text_center(draw: ImageDraw.ImageDraw, xy, text, fnt, fill):
    x0, y0, x1, y1 = xy
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2 - 1), text, font=fnt, fill=fill)


def rounded_label(draw, xy, text, border, fill, txt, fnt):
    draw.rounded_rectangle(xy, radius=10, fill=fill, outline=border, width=2)
    text_center(draw, xy, text, fnt, txt)


def main():
    img = Image.open(SRC).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Rebuild panel 9 with exact text and exact data.
    x, y, w, h = 488, 518, 520, 404
    blue = "#133B6D"
    grid = "#D8E1EC"
    panel_fill = "#FBFDFF"
    header_fill = "#EEF5FF"
    text = "#1F2933"
    muted = "#64748B"
    c_blue = "#2F6DB5"
    c_green = "#1B8A5A"
    c_orange = "#E58A21"

    # Cover the previous AI-rendered region and redraw the panel.
    draw.rounded_rectangle((x - 12, y - 12, x + w + 3, y + h + 10), radius=22, fill="white")
    draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=panel_fill, outline=blue, width=3)
    draw.rounded_rectangle((x + 2, y + 2, x + w - 2, y + 48), radius=16, fill=header_fill, outline=None)
    draw.line((x + 10, y + 48, x + w - 10, y + 48), fill="#BFD2EA", width=2)
    draw.text((x + 34, y + 14), "9. 问题三：资源约束分配结果", font=title_font, fill=blue)

    # Legend.
    legend_y = y + 66
    legend = [
        (c_blue, "人工复核数量（篇）"),
        (c_green, "高优先级覆盖（篇）"),
        (c_orange, "中优先级覆盖（篇）"),
    ]
    lx = x + 28
    for color, label in legend:
        draw.rounded_rectangle((lx, legend_y, lx + 22, legend_y + 12), radius=3, fill=color, outline=blue, width=1)
        draw.text((lx + 28, legend_y - 3), label, font=small_font, fill=text)
        lx += 158

    # Chart area.
    cx0, cy0 = x + 54, y + 105
    cx1, cy1 = x + w - 54, y + 252
    max_y = 220
    for tick in [0, 55, 110, 165, 220]:
        ty = cy1 - (tick / max_y) * (cy1 - cy0)
        draw.line((cx0, ty, cx1, ty), fill=grid, width=1)
        draw.text((cx0 - 36, ty - 8), str(tick), font=small_font, fill=muted)
    draw.line((cx0, cy0, cx0, cy1), fill="#334155", width=2)
    draw.line((cx0, cy1, cx1, cy1), fill="#334155", width=2)

    scenarios = ["S1", "S2", "S3"]
    manual = [110, 141, 194]
    high = [107, 139, 164]
    medium = [3, 2, 30]
    series = [(manual, c_blue), (high, c_green), (medium, c_orange)]
    group_w = (cx1 - cx0) / 3
    bar_w = 22
    gap = 4
    for i, scen in enumerate(scenarios):
        center = cx0 + group_w * (i + 0.5)
        starts = [center - bar_w * 1.5 - gap, center - bar_w / 2, center + bar_w / 2 + gap]
        for values, color in series:
            value = values[i]
            sx = starts.pop(0)
            bh = (value / max_y) * (cy1 - cy0)
            by = cy1 - bh
            draw.rounded_rectangle((sx, by, sx + bar_w, cy1), radius=4, fill=color, outline=blue, width=1)
            draw.text((sx - 2, by - 18), str(value), font=num_font, fill=color)
        text_center(draw, (center - 24, cy1 + 12, center + 24, cy1 + 36), scen, label_font, text)

    draw.text((cx0, cy1 + 39), "S1/S2/S3分别表示不同人工工时与复核容量约束下的可处理方案。", font=note_font, fill=muted)

    # Priority total cards.
    card_y = y + 306
    cards = [
        ("高优先级 high", "164", "#FFF5E8", c_orange),
        ("中优先级 medium", "1932", "#EEF5FF", c_blue),
        ("低优先级 low", "2423", "#ECF8F1", c_green),
    ]
    card_w = 138
    for i, (label, value, fill, color) in enumerate(cards):
        cx = x + 34 + i * 158
        draw.rounded_rectangle((cx, card_y, cx + card_w, card_y + 66), radius=11, fill=fill, outline=color, width=2)
        text_center(draw, (cx, card_y + 7, cx + card_w, card_y + 28), label, label_font, color)
        text_center(draw, (cx, card_y + 30, cx + card_w, card_y + 62), value, font(FONT_HEI, 24), color)

    img.save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
