from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "paper_figures_image2"
ORIG = OUT / "image2_originals"

W, H = 2560, 1440


FIGURES = [
    {
        "final": "01_overall_route_image2.png",
        "orig": "01_overall_route_image2_original.png",
        "title": "图1  总体技术路线图",
        "subtitle": "多源异构文件智能治理模型：解析/OCR增强 · 主题发现 · 新文件归类 · 风险复核 · 资源约束优化",
        "chips": [
            "dataset1=3396",
            "selected=3133",
            "k=160",
            "问题二=4519",
            "3159 / 1294 / 66",
            "high / medium / low = 164 / 1932 / 2423",
        ],
        "note": "主链路：多源输入 → 统一解析/OCR → 主题发现 → 归类判别 → AHP复核 → 资源分配 → 人工核查",
    },
    {
        "final": "02_three_questions_relation_image2.png",
        "orig": "02_three_questions_relation_image2_original.png",
        "title": "图2  三个问题承接关系图",
        "subtitle": "问题一提供主题原型，问题二形成分类与风险输入，问题三完成复核排序与资源分配",
        "chips": [
            "问题一：历史主题体系",
            "输出：主题原型 + 主题词典",
            "问题二：新文件归类",
            "输出：置信度 + 边界状态",
            "问题三：复核优先级",
            "输出：资源分配方案",
        ],
        "note": "逻辑关系：主题原型库 → 可解释归类 → 错分风险/复核必要性/紧急程度 → 人工复核队列",
    },
    {
        "final": "03_preprocessing_flow_image2.png",
        "orig": "03_preprocessing_flow_image2_original.png",
        "title": "图3  数据预处理流程图",
        "subtitle": "多格式文件统一编号、解析、OCR增强、降噪并生成结构化特征",
        "chips": [
            "总记录=7916",
            "ok=7905",
            "empty=11",
            "dataset1=3396",
            "dataset2=1001",
            "dataset3=3518",
            "dataset4=1",
        ],
        "note": "dataset3 按 Excel 行展开为匿名记录；后续分类对象为 dataset2 文件记录 + dataset3 逐行记录",
    },
    {
        "final": "04_multiformat_parsing_image2.png",
        "orig": "04_multiformat_parsing_image2_original.png",
        "title": "图4  多格式文件解析示意图",
        "subtitle": "Word、PDF、Excel、图片经统一解析器转化为同一文档记录结构",
        "chips": [
            "Word / PDF / Excel / 图片",
            "OCR 增强",
            "表格抽取",
            "统一 doc_id",
            "parsed_documents.jsonl",
            "parsed_documents_index.csv",
        ],
        "note": "解析输出保留标题、正文、表格、OCR文本、时间信息、解析状态等字段，供后续建模使用",
    },
    {
        "final": "05_topic_discovery_image2.png",
        "orig": "05_topic_discovery_image2_original.png",
        "title": "图5  问题一主题发现流程图",
        "subtitle": "TF-IDF 表征、SVD 降维、MiniBatchKMeans 聚类与主题族归并",
        "chips": [
            "dataset1=3396",
            "selected=3133",
            "TF-IDF features=4000",
            "SVD=50",
            "MiniBatchKMeans",
            "k=160",
            "coverage=0.9226",
            "silhouette=0.2916",
        ],
        "note": "输出：160 个细粒度主题原型，并通过主题族归并形成可解释内容分类体系",
    },
    {
        "final": "07_topic_family_consolidation_image2.png",
        "orig": "07_topic_family_consolidation_image2_original.png",
        "title": "图7  主题原型与主题族归并示意图",
        "subtitle": "先发现细粒度主题原型，再根据领域词典与代表文档收口为业务主题族",
        "chips": [
            "160 个主题原型",
            "主题族归并",
            "教育科研",
            "政府治理",
            "财政金融",
            "医药卫生",
            "资源环境",
        ],
        "note": "该步骤避免直接把聚类簇等同于业务类别，提高主题体系的可解释性和论文表达稳定性",
    },
    {
        "final": "15_manual_audit_feedback_image2.png",
        "orig": "15_manual_audit_feedback_image2_original.png",
        "title": "图15  人工核查平台与反馈闭环图",
        "subtitle": "对边界样本进行抽样核查，人工反馈用于解释误差并辅助后续规则优化",
        "chips": [
            "61 个独立样本",
            "可评价=45",
            "确认=24",
            "调整=21",
            "噪声/存疑/无法归类=16",
            "抽样来源更均衡",
        ],
        "note": "人工核查不是替代自动分类，而是用于高风险、低置信度和边界模糊样本的复核机制",
    },
]


def pick_font(candidates: list[str]) -> str | None:
    for item in candidates:
        if Path(item).exists():
            return item
    return None


BOLD_FONT = pick_font(
    [
        r"C:\Windows\Fonts\Noto Sans SC Bold (TrueType).otf",
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ]
)
REG_FONT = pick_font(
    [
        r"C:\Windows\Fonts\Noto Sans SC (TrueType).otf",
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ]
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = BOLD_FONT if bold else REG_FONT
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, min_size: int, bold: bool = False):
    size = start
    while size >= min_size:
        candidate = font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=candidate)
        if bbox[2] - bbox[0] <= max_width:
            return candidate
        size -= 2
    return font(min_size, bold)


def rounded(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width: int = 2) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def make_one(meta: dict[str, object]) -> None:
    src = ORIG / str(meta["orig"])
    image = Image.open(src).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)

    rounded(draw, (70, 60, W - 70, 205), 34, (255, 255, 255, 236), (203, 213, 225, 220), 3)
    rounded(draw, (90, H - 260, W - 90, H - 78), 34, (255, 255, 255, 238), (203, 213, 225, 220), 3)

    draw.text((115, 88), str(meta["title"]), fill=(15, 23, 42, 255), font=font(48, True))
    subtitle_font = fit_text(draw, str(meta["subtitle"]), W - 260, 34, 26)
    draw.text((118, 154), str(meta["subtitle"]), fill=(71, 85, 105, 255), font=subtitle_font)

    colors = [
        (37, 99, 235),
        (8, 145, 178),
        (15, 118, 110),
        (249, 115, 22),
        (245, 158, 11),
        (220, 38, 38),
        (22, 163, 74),
        (51, 65, 85),
    ]
    x, y = 120, H - 230
    for i, chip in enumerate(meta["chips"]):
        chip = str(chip)
        chip_font = fit_text(draw, chip, 470, 29, 22, True)
        bbox = draw.textbbox((0, 0), chip, font=chip_font)
        chip_w = min(max(bbox[2] - bbox[0] + 48, 190), 520)
        if x + chip_w > W - 130:
            x = 120
            y += 62
        color = colors[i % len(colors)]
        rounded(draw, (x, y, x + chip_w, y + 48), 20, (*color, 28), (*color, 220), 2)
        draw.text((x + 24, y + 9), chip, fill=(*color, 255), font=chip_font)
        x += chip_w + 18

    note_font = fit_text(draw, str(meta["note"]), W - 240, 28, 22)
    draw.text((120, H - 118), str(meta["note"]), fill=(51, 65, 85, 255), font=note_font)

    final = Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
    final.save(OUT / str(meta["final"]), quality=96)


def make_contact_sheet() -> None:
    tiles = []
    for meta in FIGURES:
        path = OUT / str(meta["final"])
        img = Image.open(path).convert("RGB")
        img.thumbnail((640, 360))
        tile = Image.new("RGB", (680, 440), "white")
        tile.paste(img, ((680 - img.width) // 2, 25))
        draw = ImageDraw.Draw(tile)
        draw.text((24, 400), str(meta["final"]), fill=(51, 65, 85), font=font(22))
        tiles.append(tile)

    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 680, rows * 440), (248, 250, 252))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * 680, (i // cols) * 440))
    sheet.save(OUT / "paper_figures_image2_contact_sheet.jpg", quality=92)


def write_readme() -> None:
    lines = [
        "# image2 风格化论文插图输出清单",
        "",
        "| 文件 | 图名 | 数据/文字叠加口径 |",
        "|---|---|---|",
    ]
    for meta in FIGURES:
        lines.append(f"| `{meta['final']}` | {meta['title']} | {'；'.join(meta['chips'])} |")
    lines += [
        "",
        "## 原图",
        "",
        "image2 原图已复制到 `image2_originals/`，最终论文建议使用根目录下已叠加准确中文和数字的版本。",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for meta in FIGURES:
        make_one(meta)
    make_contact_sheet()
    write_readme()
    print(OUT)


if __name__ == "__main__":
    main()
