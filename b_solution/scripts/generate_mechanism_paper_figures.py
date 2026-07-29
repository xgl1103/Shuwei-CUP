from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "paper_figures" / "code_generated"

WHITE = "#FFFFFF"
BLUE = "#6F86A6"
BLUE_L = "#E8EEF5"
GREEN = "#7F9A8D"
GREEN_L = "#E6EEE9"
AMBER = "#D8BFA3"
AMBER_L = "#F3E9DB"
PURPLE = "#9A8FA8"
PURPLE_L = "#ECE7F0"
RED = "#B87C7A"
RED_L = "#F2E2E0"
SLATE = "#3F4652"
GRAY = "#6E7480"
LINE = "#E8E3DC"


def setup_style() -> None:
    font_candidates = [
        r"C:\Windows\Fonts\Noto Sans SC (TrueType).otf",
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ]
    for font_path in font_candidates:
        if Path(font_path).exists():
            font_manager.fontManager.addfont(font_path)
            prop = font_manager.FontProperties(fname=font_path)
            plt.rcParams["font.sans-serif"] = [prop.get_name()]
            break
    plt.rcParams.update(
        {
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "figure.facecolor": WHITE,
            "axes.facecolor": WHITE,
            "font.size": 11,
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{stem}.png", bbox_inches="tight", facecolor=WHITE, dpi=260)
    fig.savefig(OUT_DIR / f"{stem}.svg", bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


def add_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    wh: tuple[float, float],
    text: str,
    face: str,
    edge: str,
    fontsize: float = 12,
    weight: str = "normal",
    radius: float = 0.02,
) -> None:
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=1.25,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        color=SLATE,
        fontsize=fontsize,
        fontweight=weight,
        linespacing=1.35,
    )


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = BLUE) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=1.55,
            color=color,
            shrinkA=4,
            shrinkB=4,
        )
    )


def base_figure(title: str, subtitle: str) -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=(12.8, 6.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.055, 0.93, title, ha="left", va="center", fontsize=23, fontweight="bold", color=SLATE)
    ax.text(0.055, 0.885, subtitle, ha="left", va="center", fontsize=10.5, color=GRAY)
    ax.plot([0.055, 0.945], [0.85, 0.85], color=LINE, linewidth=1.0)
    return fig, ax


def fig10_field_weighted_model() -> None:
    fig, ax = base_figure(
        "字段加权相似度分类模型",
        "按可用字段重分配权重，融合主题相似度、关键词证据与字段覆盖率。",
    )

    fields = [
        ("title", "原始权重 1.6\n归一化 0.291", BLUE_L, BLUE),
        ("clean_text", "原始权重 1.2\n归一化 0.218", BLUE_L, BLUE),
        ("time_info", "原始权重 1.0\n归一化 0.182", GREEN_L, GREEN),
        ("table_text", "原始权重 0.9\n归一化 0.164", GREEN_L, GREEN),
        ("ocr_text", "原始权重 0.8\n归一化 0.145", AMBER_L, AMBER),
    ]
    y_positions = [0.725, 0.61, 0.495, 0.38, 0.265]
    for (name, detail, face, edge), y in zip(fields, y_positions):
        add_box(ax, (0.065, y), (0.22, 0.072), f"{name}\n{detail}", face, edge, fontsize=10.2)
        arrow(ax, (0.285, y + 0.036), (0.39, 0.515), color=BLUE)

    add_box(ax, (0.40, 0.59), (0.22, 0.12), "可用字段筛选\n缺失字段剔除\n剩余权重重归一化", GREEN_L, GREEN, fontsize=12, weight="bold")
    add_box(ax, (0.40, 0.36), (0.22, 0.125), "相似度融合\n$S=\\sum_j \\tilde{w}_j s_j$\n关键词证据校正", PURPLE_L, PURPLE, fontsize=12)
    add_box(ax, (0.70, 0.445), (0.22, 0.145), "输出解释结果\nTop-K 候选主题\n置信度 / 分差 / 边界状态", BLUE_L, BLUE, fontsize=12, weight="bold")

    arrow(ax, (0.51, 0.59), (0.51, 0.485), color=GREEN)
    arrow(ax, (0.62, 0.425), (0.70, 0.50), color=BLUE)

    add_box(
        ax,
        (0.085, 0.105),
        (0.80, 0.072),
        "实现规则：raw_similarity = embedding · centroid；keyword_weight = 0.12；field_coverage 作为整体惩罚项。",
        WHITE,
        LINE,
        fontsize=10.5,
        radius=0.014,
    )
    save(fig, "10_field_weighted_model_formula_fixed")


def fig11_boundary_logic() -> None:
    fig, ax = base_figure(
        "分类置信度与边界状态判别逻辑",
        "不强制唯一归类，保留 assigned / multi_class / unclassifiable 三类边界状态。",
    )

    add_box(ax, (0.07, 0.46), (0.15, 0.18), "输入文档\n字段文本 + OCR\n主题原型映射", BLUE_L, BLUE, fontsize=11.5)
    add_box(ax, (0.31, 0.46), (0.18, 0.18), "计算候选得分\nmax_score\nscore_margin", BLUE_L, BLUE, fontsize=11.5)
    add_box(ax, (0.58, 0.46), (0.17, 0.18), "阈值判别\nmax_score ≥ θ\nmargin ≥ δ", AMBER_L, AMBER, fontsize=11.5, weight="bold")

    arrow(ax, (0.22, 0.55), (0.31, 0.55), color=BLUE)
    arrow(ax, (0.49, 0.55), (0.58, 0.55), color=BLUE)

    outputs = [
        ((0.82, 0.67), "assigned\n类别明确\n可自动归档", GREEN_L, GREEN),
        ((0.82, 0.45), "multi_class\n候选接近\n进入复核队列", AMBER_L, AMBER),
        ((0.82, 0.23), "unclassifiable\n证据不足\n人工判别", RED_L, RED),
    ]
    branch_start = (0.75, 0.55)
    for (xy, text, face, edge), end_y in zip(outputs, [0.76, 0.54, 0.32]):
        add_box(ax, xy, (0.15, 0.13), text, face, edge, fontsize=11.5, weight="bold")
        arrow(ax, branch_start, (0.82, end_y), color=BLUE)

    add_box(
        ax,
        (0.12, 0.12),
        (0.76, 0.09),
        "边界样本继续传递给问题三：错分风险 R_i、复核必要性 N_i、紧急程度 U_i → AHP 复核优先级。",
        WHITE,
        LINE,
        fontsize=12,
        radius=0.014,
    )
    save(fig, "11_boundary_decision_logic")


def main() -> None:
    setup_style()
    fig10_field_weighted_model()
    fig11_boundary_logic()
    print(f"wrote mechanism figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
