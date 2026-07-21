from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


OUT = Path("studyhard-images/20260721")
BASE = OUT / "b6692e61-b1b1-40ff-8795-62ca43516f5b.png"
FONT = "C:/Windows/Fonts/msyh.ttc"
BOLD = "C:/Windows/Fonts/msyhbd.ttc"
W, H = 1080, 1440


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(draw, text, fnt, max_width):
    lines, line = [], ""
    for char in text:
        candidate = line + char
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = char
    if line:
        lines.append(line)
    return lines


def rounded(draw, box, fill, radius=28, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def save_cover():
    img = Image.open(BASE).convert("RGB").resize((W, H))
    overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((72, 90, 1008, 510), radius=42, fill=(255, 255, 255, 218))
    od.text((112, 128), "减脂期", font=font(92, True), fill=(31, 79, 63))
    od.text((112, 238), "便利店早餐", font=font(92, True), fill=(31, 79, 63))
    od.text((116, 370), "照这个公式买不踩雷", font=font(42, True), fill=(219, 102, 56))
    od.rounded_rectangle((112, 435, 424, 492), radius=28, fill=(31, 79, 63))
    od.text((142, 444), "蛋白质 + 主食 + 饮品", font=font(26, True), fill=(255, 255, 255))
    Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB").save(OUT / "xhs_breakfast_cover.png", quality=95)


def page_bg():
    img = Image.new("RGB", (W, H), "#fbfaf5")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 170), fill="#dceadf")
    d.ellipse((820, 54, 1010, 244), fill="#f3d2a8")
    d.ellipse((-80, 1080, 210, 1370), fill="#b8d8c1")
    return img


def draw_header(d, title, page):
    d.text((72, 58), title, font=font(56, True), fill="#244d3f")
    d.text((900, 64), f"0{page}/05", font=font(30, True), fill="#6e786f")


def draw_card(d, y, title, body, accent="#db6638"):
    rounded(d, (72, y, 1008, y + 210), "#ffffff", 26, "#e7e1d7", 2)
    d.ellipse((112, y + 56, 172, y + 116), fill=accent)
    d.text((194, y + 44), title, font=font(38, True), fill="#244d3f")
    for i, line in enumerate(wrap(d, body, font(30), 680)[:3]):
        d.text((194, y + 100 + i * 42), line, font=font(30), fill="#59645d")


def save_text_page(name, page, title, cards, footer=None):
    img = page_bg()
    d = ImageDraw.Draw(img)
    draw_header(d, title, page)
    y = 235
    accents = ["#db6638", "#2f7359", "#d99f42", "#6f8fbd"]
    for idx, (head, body) in enumerate(cards):
        draw_card(d, y, head, body, accents[idx % len(accents)])
        y += 250
    if footer:
        d.text((78, 1304), footer, font=font(34, True), fill="#244d3f")
    img.save(OUT / name, quality=95)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    save_cover()
    save_text_page(
        "xhs_breakfast_page2_formula.png",
        2,
        "万能搭配公式",
        [
            ("先选蛋白质", "茶叶蛋、低脂牛奶、无糖豆浆、无糖酸奶"),
            ("再选主食", "玉米、红薯、全麦三明治、小饭团半个"),
            ("最后配饮品", "无糖茶、美式、无糖豆浆，少碰甜饮"),
        ],
        "记住：别只吃碳水，蛋白质要补上",
    )
    save_text_page(
        "xhs_breakfast_page3_combo.png",
        3,
        "4 套直接照买",
        [
            ("最省事", "无糖豆浆 + 茶叶蛋 2 个 + 玉米"),
            ("想吃面包", "全麦三明治 + 无糖咖啡/无糖豆浆"),
            ("想吃热乎", "关东煮鸡蛋 + 豆腐 + 海带 + 魔芋"),
            ("很饿的时候", "小红薯 + 茶叶蛋 + 无糖酸奶"),
        ],
    )
    save_text_page(
        "xhs_breakfast_page4_avoid.png",
        4,
        "这些别天天当早餐",
        [
            ("高糖饮品", "奶茶、甜豆浆、含糖咖啡、甜酸奶"),
            ("高油面包", "肉松面包、可颂、蛋黄酥、奶油夹心"),
            ("酱料太多", "沙拉酱厚、芝士培根很多的三明治"),
        ],
        "不是不能吃，是别把它当减脂日常",
    )
    save_text_page(
        "xhs_breakfast_page5_summary.png",
        5,
        "减脂早餐小原则",
        [
            ("吃得饱", "别只喝咖啡，上午容易饿到乱加餐"),
            ("搭得稳", "蛋白质 + 主食 + 无糖饮品最省心"),
            ("看包装", "热量、糖、钠含量以商品标签为准"),
        ],
        "便利店也能吃得清爽、有饱腹感",
    )


if __name__ == "__main__":
    main()
