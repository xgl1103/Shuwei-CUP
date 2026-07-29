from __future__ import annotations

import csv
import json
import math
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "paper_figures"

BLUE = "#2563eb"
CYAN = "#0891b2"
TEAL = "#0f766e"
ORANGE = "#f97316"
AMBER = "#f59e0b"
RED = "#dc2626"
GREEN = "#16a34a"
SLATE = "#334155"
GRAY = "#64748b"
LIGHT = "#f8fafc"
LINE = "#cbd5e1"


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
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["savefig.dpi"] = 220
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.edgecolor"] = LINE
    plt.rcParams["axes.labelcolor"] = SLATE
    plt.rcParams["xtick.color"] = SLATE
    plt.rcParams["ytick.color"] = SLATE


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save(fig: plt.Figure, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def wrap(text: str, width: int = 12) -> str:
    parts: list[str] = []
    for piece in str(text).split("\n"):
        if len(piece) <= width:
            parts.append(piece)
        else:
            parts.extend(textwrap.wrap(piece, width=width, break_long_words=True))
    return "\n".join(parts)


def add_title(ax: plt.Axes, title: str, subtitle: str | None = None) -> None:
    ax.text(0.02, 0.97, title, ha="left", va="top", transform=ax.transAxes, fontsize=18, weight="bold", color="#0f172a")
    if subtitle:
        ax.text(0.02, 0.91, subtitle, ha="left", va="top", transform=ax.transAxes, fontsize=10.5, color=GRAY)


def rounded_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    face: str = LIGHT,
    edge: str = LINE,
    color: str = "#0f172a",
    fontsize: float = 10.5,
    weight: str = "normal",
    radius: float = 0.035,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=1.4,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=color, fontsize=fontsize, weight=weight)
    return patch


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = GRAY, lw: float = 1.5) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=lw, color=color))


def blank_canvas(width: float = 14, height: float = 8) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def fig01_overall_route(topic_meta: dict, class_meta: dict, priority_summary: dict) -> None:
    fig, ax = blank_canvas(16, 8)
    add_title(ax, "图1  总体技术路线图", "解析/OCR -> 主题发现 -> 新文件归类 -> 风险复核 -> 资源分配")
    nodes = [
        ("多源文件输入\nWord/PDF/Excel/图片", BLUE),
        ("统一解析\nOCR增强与降噪", CYAN),
        (f"问题一\n主题发现\nk={topic_meta['cluster_count']}", TEAL),
        ("主题族归并\n主题词典", GREEN),
        (f"问题二\n新文件归类\n总量 {class_meta['total_documents']}", ORANGE),
        ("风险解释\n置信度/边界状态", AMBER),
        ("问题三\nAHP复核优先级", RED),
        ("资源约束分配\n人工核查平台", SLATE),
    ]
    xs = np.linspace(0.04, 0.82, 4)
    y_top, y_bottom = 0.64, 0.35
    positions = [(xs[0], y_top), (xs[1], y_top), (xs[2], y_top), (xs[3], y_top), (xs[3], y_bottom), (xs[2], y_bottom), (xs[1], y_bottom), (xs[0], y_bottom)]
    for (label, color), (x, y) in zip(nodes, positions):
        rounded_box(ax, x, y, 0.16, 0.14, label, face="#eff6ff" if color == BLUE else "#f8fafc", edge=color, color="#0f172a", fontsize=10.2, weight="bold")
    for a, b in zip(positions[:3], positions[1:4]):
        arrow(ax, (a[0] + 0.16, a[1] + 0.07), (b[0], b[1] + 0.07))
    arrow(ax, (positions[3][0] + 0.08, positions[3][1]), (positions[4][0] + 0.08, positions[4][1] + 0.14))
    for a, b in zip(positions[4:7], positions[5:8]):
        arrow(ax, (a[0], a[1] + 0.07), (b[0] + 0.16, b[1] + 0.07))

    stats = [
        ("dataset1", "3396"),
        ("selected", str(topic_meta["selected_documents"])),
        ("coverage", f"{topic_meta['coverage']:.3f}"),
        ("assigned", str(class_meta["status_counts"]["assigned"])),
        ("multi_class", str(class_meta["status_counts"]["multi_class"])),
        ("unclassifiable", str(class_meta["status_counts"]["unclassifiable"])),
        ("high/medium/low", f"{priority_summary['high']}/{priority_summary['medium']}/{priority_summary['low']}"),
    ]
    rounded_box(ax, 0.84, 0.28, 0.13, 0.5, "", face="#f1f5f9", edge=LINE)
    ax.text(0.905, 0.74, "关键结果", ha="center", va="center", fontsize=12, weight="bold", color=SLATE)
    for i, (k, v) in enumerate(stats):
        ax.text(0.86, 0.68 - i * 0.055, k, ha="left", va="center", fontsize=9.4, color=GRAY)
        ax.text(0.96, 0.68 - i * 0.055, v, ha="right", va="center", fontsize=9.4, color="#0f172a", weight="bold")
    save(fig, "01_overall_technical_route.png")


def fig02_preprocessing() -> None:
    rows = read_csv(ROOT / "data" / "parsed_documents_index.csv")
    total = len(rows)
    parse_counts = Counter(r["parse_status"] for r in rows)
    dataset_counts = Counter(r["dataset"] for r in rows)
    fig, ax = blank_canvas(15, 8)
    add_title(ax, "图2  数据预处理流程图", "多格式文件统一编号、解析、OCR增强、降噪并生成结构化特征")
    labels = [
        "原始附件\n多格式文件",
        "文件清单\nfile_manifest.csv",
        "统一解析\nparsed_documents.jsonl",
        "解析索引\nparsed_documents_index.csv",
        "文本降噪\n字段融合",
        "特征表\n document_features.csv",
    ]
    xs = np.linspace(0.05, 0.79, len(labels))
    for i, (x, label) in enumerate(zip(xs, labels)):
        rounded_box(ax, x, 0.55, 0.13, 0.16, label, face="#f8fafc", edge=[BLUE, CYAN, TEAL, GREEN, ORANGE, RED][i], fontsize=9.5, weight="bold")
        if i < len(labels) - 1:
            arrow(ax, (x + 0.13, 0.63), (xs[i + 1], 0.63))
    rounded_box(ax, 0.09, 0.21, 0.33, 0.2, f"解析状态\n总记录 {total}\nok {parse_counts['ok']}    empty {parse_counts['empty']}", face="#eff6ff", edge=BLUE, fontsize=11, weight="bold")
    ds_text = "\n".join([f"{k}: {dataset_counts[k]}" for k in ["dataset1", "dataset2", "dataset3", "dataset4"]])
    rounded_box(ax, 0.48, 0.21, 0.33, 0.2, f"数据集展开\n{ds_text}", face="#ecfeff", edge=CYAN, fontsize=11, weight="bold")
    ax.text(0.5, 0.12, "说明：dataset3 按 Excel 行展开为 3518 条匿名记录，是问题二的主要分类对象之一。", ha="center", fontsize=11, color=SLATE)
    save(fig, "02_data_preprocessing_flow.png")


def fig03_topic_discovery(topic_meta: dict) -> None:
    fig, ax = blank_canvas(15, 8)
    add_title(ax, "图3  问题一主题发现流程图", "从历史文件自动发现可解释、可迁移的主题原型")
    labels = [
        f"dataset1\n历史文件 {topic_meta['total_documents_in_dataset']}",
        f"文本筛选\nselected {topic_meta['selected_documents']}",
        f"TF-IDF\nfeatures {topic_meta['feature_count']}",
        f"SVD降维\n维度 {topic_meta['embedding_dim']}",
        f"MiniBatchKMeans\nk={topic_meta['cluster_count']}",
        "主题族归并\n业务主题体系",
    ]
    xs = np.linspace(0.06, 0.78, 6)
    colors = [BLUE, CYAN, TEAL, GREEN, ORANGE, RED]
    for i, (x, label) in enumerate(zip(xs, labels)):
        rounded_box(ax, x, 0.54, 0.13, 0.17, label, face="#f8fafc", edge=colors[i], fontsize=9.8, weight="bold")
        if i < 5:
            arrow(ax, (x + 0.13, 0.625), (xs[i + 1], 0.625))
    rounded_box(ax, 0.23, 0.24, 0.22, 0.14, f"覆盖率\n{topic_meta['coverage']:.4f}", face="#eff6ff", edge=BLUE, fontsize=13, weight="bold")
    rounded_box(ax, 0.55, 0.24, 0.22, 0.14, f"轮廓系数\n{topic_meta['evaluations'][0]['silhouette']:.4f}", face="#fff7ed", edge=ORANGE, fontsize=13, weight="bold")
    ax.text(0.5, 0.13, "输出：topic_summary_refined.csv、topic_family_map.csv、topic_assignments.csv", ha="center", fontsize=10.5, color=SLATE)
    save(fig, "03_problem1_topic_discovery_flow.png")


def fig04_k_ablation() -> None:
    ablation = read_csv(ROOT / "outputs" / "experiments" / "k_ablation_summary.csv")
    size_rows = {int(r["k"]): r for r in read_csv(ROOT / "outputs" / "experiments" / "k_topic_size_summary.csv")}
    k = np.array([int(r["k"]) for r in ablation])
    sil = np.array([float(r["silhouette"]) for r in ablation])
    multi = np.array([int(r["multi_class"]) for r in ablation])
    small = np.array([int(size_rows[int(r["k"])]["small_le_10"]) for r in ablation])

    fig, ax1 = plt.subplots(figsize=(13, 7))
    ax1.set_title("图4  k 值敏感性与消融实验", loc="left", fontsize=18, weight="bold", color="#0f172a", pad=18)
    x = np.arange(len(k))
    ax1.bar(x - 0.18, multi, width=0.36, color="#bfdbfe", label="multi_class 数量")
    ax1.set_ylabel("multi_class 数量", color=SLATE)
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(v) for v in k])
    ax1.set_xlabel("主题原型数 k")
    ax1.grid(axis="y", alpha=0.2)
    ax2 = ax1.twinx()
    ax2.plot(x, sil, marker="o", color=ORANGE, linewidth=2.6, label="轮廓系数")
    ax2.plot(x, small / small.max() * sil.max(), marker="s", color=TEAL, linestyle="--", linewidth=2.0, label="小簇数(归一化显示)")
    ax2.set_ylabel("轮廓系数", color=SLATE)
    ax1.axvline(list(k).index(160), color=RED, linestyle=":", linewidth=2)
    ax1.text(list(k).index(160) + 0.08, max(multi) * 0.92, "最终选择 k=160\n兼顾质量与复核成本", color=RED, fontsize=10, weight="bold")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left", frameon=False)
    for i, v in enumerate(small):
        ax1.text(i + 0.16, multi[i] + 70, f"小簇≤10:{v}", ha="center", fontsize=8.5, color=GRAY, rotation=20)
    save(fig, "04_k_ablation_sensitivity.png")


def fig05_problem2_status(class_meta: dict) -> None:
    rows = read_csv(ROOT / "outputs" / "document_classification" / "classification_results.csv")
    statuses = ["assigned", "multi_class", "unclassifiable"]
    dataset_order = ["dataset2", "dataset3"]
    counts = {(d, s): 0 for d in dataset_order for s in statuses}
    for r in rows:
        counts[(r["dataset"], r["classification_status"])] += 1

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1, 1.25]})
    fig.suptitle("图5  问题二分类结果结构", x=0.04, y=0.98, ha="left", fontsize=18, weight="bold", color="#0f172a")
    vals = [class_meta["status_counts"][s] for s in statuses]
    colors = [GREEN, AMBER, RED]
    axes[0].pie(vals, labels=[f"{s}\n{v}" for s, v in zip(statuses, vals)], autopct="%1.1f%%", colors=colors, startangle=90, textprops={"fontsize": 10})
    axes[0].set_title("总体状态占比")
    bottom = np.zeros(len(dataset_order))
    x = np.arange(len(dataset_order))
    for s, color in zip(statuses, colors):
        vals2 = np.array([counts[(d, s)] for d in dataset_order])
        axes[1].bar(x, vals2, bottom=bottom, label=s, color=color, alpha=0.86)
        for xi, b, v in zip(x, bottom, vals2):
            if v > 0:
                axes[1].text(xi, b + v / 2, str(int(v)), ha="center", va="center", fontsize=10, color="white", weight="bold")
        bottom += vals2
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(dataset_order)
    axes[1].set_ylabel("文档/记录数量")
    axes[1].set_title("按数据集分布")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.2)
    save(fig, "05_problem2_classification_structure.png")


def fig06_topic_distribution() -> None:
    rows = read_csv(ROOT / "outputs" / "document_classification" / "classification_results.csv")
    counter = Counter((r["dataset"], r["topic_parent_name"]) for r in rows)
    top = counter.most_common(8)
    labels = [f"{d}\n{t}" for (d, t), _ in top]
    vals = [v for _, v in top]
    colors = [BLUE if d == "dataset3" else ORANGE for (d, _), _ in top]

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_title("图6  高频主题分布", loc="left", fontsize=18, weight="bold", color="#0f172a", pad=18)
    y = np.arange(len(vals))
    ax.barh(y, vals, color=colors, alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([wrap(label, 16) for label in labels])
    ax.invert_yaxis()
    ax.set_xlabel("数量")
    ax.grid(axis="x", alpha=0.2)
    for yi, v in zip(y, vals):
        ax.text(v + 20, yi, str(v), va="center", fontsize=10, weight="bold", color=SLATE)
    ax.text(0.72, 0.08, "蓝色：dataset3\n橙色：dataset2", transform=ax.transAxes, fontsize=11, color=SLATE, bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8fafc", edgecolor=LINE))
    save(fig, "06_high_frequency_topics.png")


def fig07_field_weighted_model() -> None:
    fig, ax = blank_canvas(15, 8)
    add_title(ax, "图7  字段加权分类模型示意图", "不同字段分别打分，再融合语义相似度、关键词证据和字段覆盖率")
    fields = [("标题", BLUE), ("正文", CYAN), ("表格", TEAL), ("OCR文本", ORANGE), ("时间/元信息", AMBER)]
    for i, (name, color) in enumerate(fields):
        y = 0.72 - i * 0.12
        rounded_box(ax, 0.06, y, 0.16, 0.075, name, face="#f8fafc", edge=color, weight="bold")
        arrow(ax, (0.22, y + 0.038), (0.34, 0.515))
    rounded_box(ax, 0.34, 0.43, 0.18, 0.17, "字段权重融合\nfield_coverage 修正", face="#eff6ff", edge=BLUE, fontsize=11, weight="bold")
    rounded_box(ax, 0.60, 0.57, 0.18, 0.11, "TF-IDF/SVD\n向量表示", face="#ecfeff", edge=CYAN, fontsize=11, weight="bold")
    rounded_box(ax, 0.60, 0.37, 0.18, 0.11, "主题词典\n关键词重合", face="#fff7ed", edge=ORANGE, fontsize=11, weight="bold")
    arrow(ax, (0.52, 0.515), (0.60, 0.62))
    arrow(ax, (0.52, 0.515), (0.60, 0.425))
    rounded_box(ax, 0.84, 0.45, 0.13, 0.18, "输出\nTop1/Top2/Top3\nconfidence\nmargin\nrisk", face="#f1f5f9", edge=SLATE, fontsize=10, weight="bold")
    arrow(ax, (0.78, 0.62), (0.84, 0.56))
    arrow(ax, (0.78, 0.425), (0.84, 0.51))
    params = "top_k=3    keyword_weight=0.10\nconfidence_threshold=0.45    margin_threshold=0.08\nunclassifiable_threshold=0.35    ambiguous_margin=0.06\nmin_field_coverage=0.45    weak_evidence=0.30"
    rounded_box(ax, 0.25, 0.12, 0.55, 0.16, params, face="#f8fafc", edge=LINE, fontsize=10)
    save(fig, "07_field_weighted_classification_model.png")


def fig08_ahp_hierarchy(priority_meta: dict) -> None:
    weights = priority_meta["ahp"]["weights"]
    cr = priority_meta["ahp"]["consistency_ratio"]
    fig, ax = blank_canvas(14, 8)
    add_title(ax, "图8  AHP 复核优先级指标体系", f"一致性检验 CR={cr:.4f} < 0.1")
    rounded_box(ax, 0.37, 0.76, 0.26, 0.11, "目标层\n综合复核优先级 P_i", face="#eff6ff", edge=BLUE, fontsize=12, weight="bold")
    crit = [
        ("错分风险\nmisclassification_risk\nw=0.5396", 0.08, BLUE),
        ("复核必要性\nreview_necessity\nw=0.2970", 0.37, ORANGE),
        ("紧急程度\nurgency\nw=0.1634", 0.66, RED),
    ]
    for text, x, color in crit:
        rounded_box(ax, x, 0.50, 0.25, 0.13, text, face="#f8fafc", edge=color, fontsize=10.5, weight="bold")
        arrow(ax, (0.50, 0.76), (x + 0.125, 0.63))
    leaf_texts = [
        "分类状态\n置信度\n边界间隔\n字段覆盖率\n解析状态",
        "金额\n审批\n合同\n采购\n药品/专利",
        "紧急词\n截止时间\n限期表达\n时效信号",
    ]
    for text, (_, x, color) in zip(leaf_texts, crit):
        rounded_box(ax, x, 0.22, 0.25, 0.18, text, face="#ffffff", edge=LINE, fontsize=10)
        arrow(ax, (x + 0.125, 0.50), (x + 0.125, 0.40), color=color)
    save(fig, "08_ahp_indicator_hierarchy.png")


def fig09_resource_allocation() -> None:
    rows = read_csv(ROOT / "outputs" / "review_prioritization" / "resource_plan.csv")
    scenarios = [r["scenario_id"] for r in rows]
    manual = np.array([float(r["manual_review_selected"]) for r in rows])
    high = np.array([float(r["high_priority_selected"]) for r in rows])
    med = np.array([float(r["medium_priority_selected"]) for r in rows])
    hours = np.array([float(r["used_manual_hours"]) for r in rows])
    x = np.arange(len(scenarios))
    width = 0.24
    fig, ax1 = plt.subplots(figsize=(13, 7))
    ax1.set_title("图9  资源约束分配结果", loc="left", fontsize=18, weight="bold", color="#0f172a", pad=18)
    ax1.bar(x - width, manual, width=width, color=BLUE, label="实际人工复核")
    ax1.bar(x, high, width=width, color=RED, label="高优先级覆盖")
    ax1.bar(x + width, med, width=width, color=AMBER, label="中优先级覆盖")
    for xs, vals in [(x - width, manual), (x, high), (x + width, med)]:
        for xi, v in zip(xs, vals):
            ax1.text(xi, v + 5, str(int(v)), ha="center", fontsize=9, color=SLATE)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios)
    ax1.set_ylabel("文件数量")
    ax1.grid(axis="y", alpha=0.2)
    ax2 = ax1.twinx()
    ax2.plot(x, hours, color=TEAL, marker="o", linewidth=2.4, label="使用人工工时")
    ax2.set_ylabel("使用人工工时")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, frameon=False, loc="upper left")
    save(fig, "09_resource_constraint_allocation.png")


def fig10_manual_audit() -> None:
    rows = read_csv(ROOT / "notes" / "manual_review" / "review_logs_2026-05-09_combined_latest_merged.csv")
    eff = Counter(r["effective_result"] for r in rows)
    bucket = Counter(r["primary_audit_bucket"] for r in rows)
    fig, ax = blank_canvas(15, 8)
    add_title(ax, "图10  人工核查平台与抽样反馈", "人工复核用于检验边界样本，不作为全量监督准确率")
    steps = [
        "待复核样本\n221条候选",
        "查看详情\n正文/候选类别/风险原因",
        "人工标记\n确认/修改/噪声/存疑",
        "导出日志\nJSON",
        "合并统计\n61个独立样本",
    ]
    xs = np.linspace(0.05, 0.77, len(steps))
    for i, x in enumerate(xs):
        rounded_box(ax, x, 0.64, 0.14, 0.12, steps[i], face="#f8fafc", edge=[BLUE, CYAN, TEAL, ORANGE, RED][i], fontsize=9.5, weight="bold")
        if i < len(steps) - 1:
            arrow(ax, (x + 0.14, 0.70), (xs[i + 1], 0.70))
    # Mini dashboard mockup
    rounded_box(ax, 0.06, 0.18, 0.42, 0.32, "", face="#ffffff", edge=LINE)
    ax.text(0.08, 0.46, "人工核查工作台示意", fontsize=12, weight="bold", color=SLATE)
    for i, label in enumerate(["待复核队列", "文档详情", "分类结果", "复核信息"]):
        ax.add_patch(Rectangle((0.08, 0.40 - i * 0.055), 0.16, 0.035, facecolor="#e0f2fe", edgecolor="none"))
        ax.text(0.09, 0.418 - i * 0.055, label, fontsize=8.5, va="center", color=SLATE)
    for i in range(4):
        ax.add_patch(Rectangle((0.27, 0.40 - i * 0.055), 0.17, 0.035, facecolor="#f1f5f9", edgecolor="none"))

    summary = [
        ("可评价样本", eff["category_confirmed"] + eff["category_adjusted"], BLUE),
        ("确认原类别", eff["category_confirmed"], GREEN),
        ("人工调整", eff["category_adjusted"], ORANGE),
        ("噪声/存疑/无法归类", eff["noise"] + eff["uncertain"] + eff["unclassifiable"], RED),
    ]
    for i, (label, value, color) in enumerate(summary):
        rounded_box(ax, 0.55 + (i % 2) * 0.2, 0.38 - (i // 2) * 0.14, 0.17, 0.10, f"{label}\n{value}", face="#f8fafc", edge=color, fontsize=10.5, weight="bold")
    bucket_text = "\n".join(f"{k}: {v}" for k, v in bucket.most_common())
    rounded_box(ax, 0.55, 0.12, 0.38, 0.14, f"抽样来源\n{bucket_text}", face="#f8fafc", edge=LINE, fontsize=9.5)
    save(fig, "10_manual_audit_platform_feedback.png")


def build_index() -> None:
    rows = [
        ("01_overall_technical_route.png", "总体技术路线图", "topic_meta.json, classification_meta.json, review_priority_meta.json, resource_plan.csv"),
        ("02_data_preprocessing_flow.png", "数据预处理流程图", "parsed_documents_index.csv, document_features.csv"),
        ("03_problem1_topic_discovery_flow.png", "问题一主题发现流程图", "topic_meta.json, topic_summary_refined.csv"),
        ("04_k_ablation_sensitivity.png", "k 值敏感性/消融实验图", "outputs/experiments/k_ablation_summary.csv, k_topic_size_summary.csv"),
        ("05_problem2_classification_structure.png", "问题二分类结果结构图", "classification_meta.json, classification_results.csv"),
        ("06_high_frequency_topics.png", "高频主题分布图", "classification_results.csv"),
        ("07_field_weighted_classification_model.png", "字段加权分类模型示意图", "classification_meta.json, classification.py"),
        ("08_ahp_indicator_hierarchy.png", "AHP 指标体系层次图", "review_priority_meta.json"),
        ("09_resource_constraint_allocation.png", "资源约束分配结果图", "resource_plan.csv"),
        ("10_manual_audit_platform_feedback.png", "人工核查平台界面/反馈示意图", "review_logs_2026-05-09_combined_latest_merged.csv"),
    ]
    lines = ["# 论文图表输出清单", "", "| 文件 | 图名 | 主要数据来源 |", "|---|---|---|"]
    for name, title, src in rows:
        lines.append(f"| `{name}` | {title} | {src} |")
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    setup_style()
    topic_meta = read_json(ROOT / "outputs" / "topic_discovery" / "topic_meta.json")
    class_meta = read_json(ROOT / "outputs" / "document_classification" / "classification_meta.json")
    priority_meta = read_json(ROOT / "outputs" / "review_prioritization" / "review_priority_meta.json")
    summary_rows = read_csv(ROOT / "outputs" / "review_prioritization" / "review_priority_summary.csv")
    priority_summary = {r["priority_level"]: int(r["count"]) for r in summary_rows}
    fig01_overall_route(topic_meta, class_meta, priority_summary)
    fig02_preprocessing()
    fig03_topic_discovery(topic_meta)
    fig04_k_ablation()
    fig05_problem2_status(class_meta)
    fig06_topic_distribution()
    fig07_field_weighted_model()
    fig08_ahp_hierarchy(priority_meta)
    fig09_resource_allocation()
    fig10_manual_audit()
    build_index()
    print(f"wrote figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
