from __future__ import annotations

import csv
import json
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "paper_figures" / "code_generated"
FINAL_ROOT = ROOT / "outputs" / "final_results_2026-05-10"

BLUE = "#6F86A6"
BLUE_L = "#D9E1EA"
GREEN = "#7F9A8D"
GREEN_L = "#DDE7E1"
ORANGE = "#C9896B"
ORANGE_L = "#EBD6C8"
AMBER = "#D8BFA3"
AMBER_L = "#EFE4D6"
PURPLE = "#9A8FA8"
PURPLE_L = "#E3DEE8"
RED = "#B87C7A"
RED_L = "#E8D4D2"
TEAL = "#758F8A"
SLATE = "#3F4652"
GRAY = "#6E7480"
LINE = "#E8E3DC"
BG = "#FFFFFF"


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
            "figure.dpi": 150,
            "savefig.dpi": 260,
            "font.size": 11,
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "axes.edgecolor": LINE,
            "axes.labelcolor": SLATE,
            "xtick.color": SLATE,
            "ytick.color": SLATE,
            "axes.titlecolor": SLATE,
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def final_path(*parts: str) -> Path:
    return FINAL_ROOT.joinpath(*parts)


def manual_review_combined_path() -> Path:
    return ROOT / "notes" / "manual_review" / "review_logs_2026-05-09_combined_latest_merged.csv"


def validate_latest_sources() -> None:
    class_rows = read_csv(final_path("document_classification", "classification_results.csv"))
    topic_rows = read_csv(final_path("topic_discovery", "topic_summary_refined.csv"))
    priority_rows = read_csv(final_path("review_prioritization", "review_priority_results.csv"))
    resource_rows = read_csv(final_path("review_prioritization", "resource_plan.csv"))
    review_rows = read_csv(manual_review_combined_path())
    meta = read_json(final_path("document_classification", "classification_meta.json"))

    expected_status = {"assigned": 3159, "multi_class": 1294, "unclassifiable": 66}
    checks = [
        (len(class_rows), 4519, "classification_results rows"),
        (len(topic_rows), 160, "topic_summary_refined rows"),
        (len(priority_rows), 4519, "review_priority_results rows"),
        (len(resource_rows), 3, "resource_plan rows"),
        (len(review_rows), 61, "manual review rows"),
        (meta["status_counts"], expected_status, "classification status counts"),
    ]
    for actual, expected, name in checks:
        if actual != expected:
            raise ValueError(f"{name} expected {expected}, got {actual}")

    boundary_rows = read_csv(ROOT / "outputs" / "experiments" / "k160_boundary_optimization_summary.csv")
    after = {r["metric"]: int(float(r["after"])) for r in boundary_rows if r["metric"] in expected_status}
    if after != expected_status:
        raise ValueError(f"boundary optimization after counts expected {expected_status}, got {after}")


def save(fig: plt.Figure, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{stem}.png", bbox_inches="tight", facecolor=BG)
    fig.savefig(OUT_DIR / f"{stem}.svg", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def title(ax: plt.Axes, main: str, sub: str | None = None) -> None:
    ax.set_title(main, loc="left", fontsize=17, fontweight="bold", pad=16)
    if sub:
        ax.text(0, 1.01, sub, transform=ax.transAxes, ha="left", va="bottom", color=GRAY, fontsize=10)


def clean_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LINE)
    ax.spines["bottom"].set_color(LINE)
    ax.grid(axis=grid_axis, color=LINE, linewidth=0.75, alpha=0.65)
    ax.set_axisbelow(True)


def wrap_label(text: str, width: int = 12) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def add_note(ax: plt.Axes, text: str, x: float = 0.98, y: float = 0.04, align: str = "right") -> None:
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=align,
        va="bottom",
        fontsize=9.2,
        color=GRAY,
        bbox=dict(boxstyle="round,pad=0.35", facecolor=BG, edgecolor=LINE, linewidth=0.8),
    )


def segment_label(ax: plt.Axes, x: float, y: float, text: str, fontsize: float = 10) -> None:
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        color=SLATE,
        fontweight="bold",
        fontsize=fontsize,
        bbox=dict(boxstyle="round,pad=0.18", facecolor="#F6F2EC", edgecolor="none", alpha=0.72),
        clip_on=False,
    )


def fig04_dataset1_topic_family_distribution() -> None:
    rows = read_csv(final_path("topic_discovery", "topic_summary_refined.csv"))
    counts: Counter = Counter()
    confidence: dict[str, list[float]] = defaultdict(list)
    term_counter: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        family = r["topic_name"] or r["family_group"]
        counts[family] += int(r["size"])
        if r.get("family_confidence"):
            confidence[family].append(float(r["family_confidence"]))
        for term in (r.get("top_terms") or "").replace("，", "、").split("、"):
            term = term.strip()
            if term:
                term_counter[family][term] += int(r["size"])

    top = counts.most_common(8)
    labels = [name for name, _ in top]
    vals = [value for _, value in top]
    palette = [BLUE, PURPLE, ORANGE, AMBER, GREEN, TEAL, "#A9B7C6", "#8EA7A1"]

    fig, ax = plt.subplots(figsize=(14, 7.4))
    title(ax, "图4  数据集1主题发现结果分布")
    y = np.arange(len(vals))
    ax.barh(y, vals, color=palette[: len(vals)], alpha=0.92, edgecolor=SLATE, linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([wrap_label(label, 14) for label in labels], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("数据集1入模文档数量")
    clean_axes(ax, grid_axis="x")
    max_v = max(vals)
    for yi, family, value in zip(y, labels, vals):
        avg_conf = sum(confidence[family]) / len(confidence[family]) if confidence[family] else 0
        terms = "、".join([term for term, _ in term_counter[family].most_common(3)])
        ax.text(value + max_v * 0.018, yi, f"{value} | {terms} | 置信 {avg_conf:.2f}", va="center", fontsize=9.7, color=SLATE)
    ax.set_xlim(0, max_v * 1.42)
    save(fig, "04_dataset1_topic_family_distribution")


def fig05_new_data_classification_risk_distribution() -> None:
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    datasets = ["dataset2", "dataset3"]

    topic_counts: dict[str, Counter] = defaultdict(Counter)
    overall_topics = Counter()
    for r in rows:
        topic = r["topic_name"]
        topic_counts[topic][r["dataset"]] += 1
        overall_topics[topic] += 1
    top_topics = [topic for topic, _ in overall_topics.most_common(8)]
    other_label = "其他主题"
    topic_labels = top_topics + [other_label]
    topic_values = {topic: {dataset: topic_counts[topic][dataset] for dataset in datasets} for topic in top_topics}
    topic_values[other_label] = {
        dataset: sum(1 for r in rows if r["dataset"] == dataset and r["topic_name"] not in top_topics)
        for dataset in datasets
    }

    risk_order = ["high", "medium", "low"]
    risk_labels = {"high": "高风险", "medium": "中风险", "low": "低风险"}
    risk_colors = {"high": ORANGE, "medium": AMBER, "low": GREEN}
    status_order = ["assigned", "multi_class", "unclassifiable"]
    status_labels = {"assigned": "明确归类", "multi_class": "多类边界", "unclassifiable": "无法归类"}
    status_colors = {"assigned": BLUE_L, "multi_class": PURPLE, "unclassifiable": "#A9B7C6"}
    by_risk: dict[str, Counter] = defaultdict(Counter)
    by_status: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_risk[r["dataset"]][r["risk_level"]] += 1
        by_status[r["dataset"]][r["classification_status"]] += 1

    fig = plt.figure(figsize=(15, 7.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.05], wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图5  新流入数据分类结果与风险等级分布", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    y = np.arange(len(topic_labels))
    left = np.zeros(len(topic_labels))
    dataset_colors = {"dataset2": BLUE, "dataset3": TEAL}
    for dataset in datasets:
        vals = np.array([topic_values[topic][dataset] for topic in topic_labels])
        ax0.barh(y, vals, left=left, color=dataset_colors[dataset], edgecolor=SLATE, linewidth=0.45, label=dataset, alpha=0.94)
        left += vals
    ax0.set_yticks(y)
    ax0.set_yticklabels([wrap_label(label, 9) for label in topic_labels], fontsize=10)
    ax0.invert_yaxis()
    ax0.set_xlabel("分类样本数")
    ax0.set_title("主题细分类分布", fontsize=13, fontweight="bold")
    ax0.legend(frameon=False, loc="upper right")
    clean_axes(ax0, grid_axis="x")

    x = np.array([0, 1])
    width = 0.34
    risk_bottom = np.zeros(len(datasets))
    status_bottom = np.zeros(len(datasets))
    for level in risk_order:
        vals = np.array([by_risk[d][level] for d in datasets])
        ax1.bar(x - width / 2, vals, bottom=risk_bottom, width=width, color=risk_colors[level], label=risk_labels[level], edgecolor=SLATE, linewidth=0.45)
        for xi, b, v in zip(x - width / 2, risk_bottom, vals):
            if v >= 45:
                segment_label(ax1, xi, b + v / 2, str(int(v)), fontsize=8.8)
        risk_bottom += vals
    for status in status_order:
        vals = np.array([by_status[d][status] for d in datasets])
        ax1.bar(x + width / 2, vals, bottom=status_bottom, width=width, color=status_colors[status], label=status_labels[status], edgecolor=SLATE, linewidth=0.45, hatch="//" if status == "assigned" else None)
        for xi, b, v in zip(x + width / 2, status_bottom, vals):
            if v >= 45:
                segment_label(ax1, xi, b + v / 2, str(int(v)), fontsize=8.8)
        status_bottom += vals
    ax1.set_xticks(x)
    ax1.set_xticklabels(["数据集2", "数据集3"])
    ax1.set_ylabel("样本数")
    ax1.set_title("风险等级与归类状态", fontsize=13, fontweight="bold")
    ax1.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
    clean_axes(ax1)
    fig.subplots_adjust(top=0.84)
    save(fig, "05_new_data_classification_risk_distribution")


def fig06_k_ablation() -> None:
    ab = read_csv(ROOT / "outputs" / "experiments" / "k_ablation_summary.csv")
    size = {int(r["k"]): r for r in read_csv(ROOT / "outputs" / "experiments" / "k_topic_size_summary.csv")}

    k = np.array([int(r["k"]) for r in ab])
    silhouette = np.array([float(r["silhouette"]) for r in ab])
    multi = np.array([int(r["multi_class"]) for r in ab])
    unclass = np.array([int(r["unclassifiable"]) for r in ab])
    small10 = np.array([int(size[int(r["k"])]["small_le_10"]) for r in ab])

    fig, ax1 = plt.subplots(figsize=(13.5, 7.2))
    title(ax1, "图6  k 值敏感性与消融实验")
    x = np.arange(len(k))
    width = 0.34
    bars = ax1.bar(x - width / 2, multi, width=width, color=BLUE_L, edgecolor=BLUE, linewidth=1.0, label="multi_class")
    small_bars = ax1.bar(x + width / 2, small10 * 18, width=width, color=AMBER_L, edgecolor=AMBER, linewidth=1.0, label="小簇数≤10")
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(v) for v in k])
    ax1.set_xlabel("主题原型数量 k")
    ax1.set_ylabel("数量")
    clean_axes(ax1)

    ax2 = ax1.twinx()
    ax2.plot(x, silhouette, color=PURPLE, marker="o", linewidth=2.4, markersize=6.5, label="轮廓系数")
    ax2.set_ylabel("轮廓系数")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(LINE)
    ax2.tick_params(axis="y", colors=SLATE)

    chosen = list(k).index(160)
    ax1.axvline(chosen, color=TEAL, linestyle=(0, (4, 3)), linewidth=1.8)
    ax1.text(chosen + 0.08, max(multi) * 0.92, "k=160", color=TEAL, fontsize=12, fontweight="bold")

    for rect, m in zip(bars, multi):
        ax1.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 85, f"{m}", ha="center", va="bottom", fontsize=9, color=SLATE)
    for rect, s10 in zip(small_bars, small10):
        ax1.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 85, f"{s10}", ha="center", va="bottom", fontsize=9, color=SLATE)
    for xi, s in zip(x, silhouette):
        ax2.text(xi, s + 0.006, f"{s:.3f}", ha="center", fontsize=9, color=PURPLE)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left", frameon=False, ncol=3)
    save(fig, "06_k_ablation_sensitivity")


def fig08_problem2_structure() -> None:
    meta = read_json(final_path("document_classification", "classification_meta.json"))
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    statuses = ["assigned", "multi_class", "unclassifiable"]
    colors = [GREEN, AMBER, PURPLE]
    labels_cn = {"assigned": "唯一归类", "multi_class": "多类待判别", "unclassifiable": "无法归类"}
    overall = [int(meta["status_counts"][s]) for s in statuses]
    by_ds: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_ds[r["dataset"]][r["classification_status"]] += 1

    fig = plt.figure(figsize=(14, 7.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.35])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图8  问题二分类结果结构", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    wedges, _ = ax0.pie(overall, startangle=90, colors=colors, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
    ax0.text(0, 0.08, f"{meta['total_documents']}", ha="center", va="center", fontsize=22, fontweight="bold", color=SLATE)
    ax0.text(0, -0.12, "分类对象总量", ha="center", va="center", fontsize=10, color=GRAY)
    ax0.set_title("总体结构", fontsize=13, fontweight="bold")
    for i, (w, s, v) in enumerate(zip(wedges, statuses, overall)):
        ang = (w.theta2 + w.theta1) / 2
        x = np.cos(np.deg2rad(ang)) * 1.08
        y = np.sin(np.deg2rad(ang)) * 1.08
        ax0.text(x, y, f"{labels_cn[s]}\n{v}", ha="center", va="center", fontsize=10, color=SLATE)

    ds = ["dataset2", "dataset3"]
    bottom = np.zeros(len(ds))
    x = np.arange(len(ds))
    for s, color in zip(statuses, colors):
        vals = np.array([by_ds[d][s] for d in ds])
        ax1.bar(x, vals, bottom=bottom, color=color, label=f"{labels_cn[s]} {s}", width=0.56)
        for xi, b, v in zip(x, bottom, vals):
            if v > 0:
                segment_label(ax1, xi, b + v / 2, str(int(v)), fontsize=10)
        bottom += vals
    ax1.set_xticks(x)
    ax1.set_xticklabels(ds)
    ax1.set_ylabel("文档/记录数量")
    ax1.set_title("按数据集分布", fontsize=13, fontweight="bold")
    ax1.legend(frameon=False, loc="upper left")
    clean_axes(ax1)
    save(fig, "08_problem2_classification_structure")


def fig09_high_frequency_topics() -> None:
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    parent_counts = Counter(r["topic_parent_name"] for r in rows)
    top = parent_counts.most_common(8)
    labels = [topic for topic, _ in top]
    vals = [v for _, v in top]

    education_parent = parent_counts.most_common(1)[0][0]
    education_split = Counter(r["topic_name"] for r in rows if r["topic_parent_name"] == education_parent).most_common()
    split_labels = [name for name, _ in education_split]
    split_vals = [count for _, count in education_split]

    fig = plt.figure(figsize=(15, 7.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.36)
    ax = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图9  高频主题与教育科研细分", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    y = np.arange(len(vals))
    bar_colors = [BLUE if i == 0 else "#A9B7C6" for i in range(len(vals))]
    ax.barh(y, vals, color=bar_colors, alpha=0.95, edgecolor="white", linewidth=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels([wrap_label(s, 18) for s in labels], fontsize=9.6)
    ax.invert_yaxis()
    ax.set_xlabel("数量")
    ax.set_title("主题父类 Top 8", fontsize=13, fontweight="bold")
    clean_axes(ax, grid_axis="x")
    for yi, v in zip(y, vals):
        ax.text(v + max(vals) * 0.018, yi, str(v), va="center", fontsize=10, fontweight="bold", color=SLATE)

    y2 = np.arange(len(split_vals))
    split_palette = [GREEN, BLUE, ORANGE, AMBER, PURPLE, "#B7AAA3", "#8EA7A1"]
    ax2.barh(y2, split_vals, color=split_palette[: len(split_vals)], alpha=0.95, edgecolor="white", linewidth=1.2)
    ax2.set_yticks(y2)
    ax2.set_yticklabels([wrap_label(s, 8) for s in split_labels], fontsize=10)
    ax2.invert_yaxis()
    ax2.set_xlabel("数量")
    ax2.set_title("教育科研类细分", fontsize=13, fontweight="bold")
    clean_axes(ax2, grid_axis="x")
    for yi, v in zip(y2, split_vals):
        ax2.text(v + max(split_vals) * 0.025, yi, str(v), va="center", fontsize=10, fontweight="bold", color=SLATE)
    fig.subplots_adjust(top=0.84)
    save(fig, "09_high_frequency_topics")


def fig12_ahp_weights() -> None:
    meta = read_json(final_path("review_prioritization", "review_priority_meta.json"))
    ahp = meta["ahp"]
    names = ["错分风险", "复核必要性", "紧急程度"]
    keys = ["misclassification_risk", "review_necessity", "urgency"]
    weights = np.array([float(ahp["weights"][k]) for k in keys])
    matrix = np.array(ahp["matrix"], dtype=float)

    fig = plt.figure(figsize=(13.5, 7.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图12  AHP 指标权重与一致性检验", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    bars = ax0.bar(names, weights, color=[BLUE, ORANGE, PURPLE], width=0.55)
    ax0.set_ylim(0, 0.65)
    ax0.set_ylabel("权重")
    ax0.set_title("一级指标权重", fontsize=13, fontweight="bold")
    clean_axes(ax0)
    for rect, w in zip(bars, weights):
        ax0.text(rect.get_x() + rect.get_width() / 2, w + 0.018, f"{w:.4f}", ha="center", fontsize=11, fontweight="bold", color=SLATE)

    im = ax1.imshow(matrix, cmap="PuBu", vmin=0, vmax=3)
    ax1.set_xticks(np.arange(3))
    ax1.set_yticks(np.arange(3))
    ax1.set_xticklabels(names)
    ax1.set_yticklabels(names)
    ax1.set_title("AHP 判断矩阵", fontsize=13, fontweight="bold")
    for i in range(3):
        for j in range(3):
            ax1.text(j, i, f"{matrix[i, j]:.3g}", ha="center", va="center", color=SLATE, fontweight="bold", fontsize=11)
    for spine in ax1.spines.values():
        spine.set_visible(False)
    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    fig.text(0.055, 0.035, f"CR={ahp['consistency_ratio']:.4f}，CI={ahp['consistency_index']:.4f}，lambda_max={ahp['lambda_max']:.4f}", ha="left", color=GRAY, fontsize=10)
    save(fig, "12_ahp_weights_consistency")


def fig13_review_priority_distribution() -> None:
    rows = read_csv(final_path("review_prioritization", "review_priority_summary.csv"))
    levels = ["high", "medium", "low"]
    colors = [PURPLE, AMBER, GREEN]
    by_level = {level: 0 for level in levels}
    by_ds = defaultdict(lambda: {level: 0 for level in levels})
    for r in rows:
        level = r["priority_level"]
        count = int(r["count"])
        by_level[level] += count
        by_ds[r["dataset"]][level] = count

    fig = plt.figure(figsize=(14, 7.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.25])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图13  复核优先级分布", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    vals = [by_level[l] for l in levels]
    wedges, _ = ax0.pie(vals, startangle=90, colors=colors, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
    ax0.text(0, 0.08, str(sum(vals)), ha="center", fontsize=22, fontweight="bold", color=SLATE)
    ax0.text(0, -0.12, "文档总量", ha="center", fontsize=10, color=GRAY)
    ax0.set_title("总体优先级占比", fontsize=13, fontweight="bold")
    for w, level, v in zip(wedges, levels, vals):
        ang = (w.theta1 + w.theta2) / 2
        ax0.text(np.cos(np.deg2rad(ang)) * 1.08, np.sin(np.deg2rad(ang)) * 1.08, f"{level}\n{v}", ha="center", va="center", fontsize=10, color=SLATE)

    ds = ["dataset2", "dataset3"]
    x = np.arange(len(ds))
    bottom = np.zeros(len(ds))
    for level, color in zip(levels, colors):
        values = np.array([by_ds[d][level] for d in ds])
        ax1.bar(x, values, bottom=bottom, color=color, width=0.56, label=level)
        for xi, b, v in zip(x, bottom, values):
            if v > 0:
                segment_label(ax1, xi, b + v / 2, str(int(v)), fontsize=10)
        bottom += values
    ax1.set_xticks(x)
    ax1.set_xticklabels(ds)
    ax1.set_ylabel("数量")
    ax1.set_title("按数据集分布", fontsize=13, fontweight="bold")
    ax1.legend(frameon=False)
    clean_axes(ax1)
    save(fig, "13_review_priority_distribution")


def fig14_resource_allocation() -> None:
    rows = read_csv(final_path("review_prioritization", "resource_plan.csv"))
    scenarios = [r["scenario_id"] for r in rows]
    manual = np.array([int(r["manual_review_selected"]) for r in rows])
    high = np.array([int(r["high_priority_selected"]) for r in rows])
    medium = np.array([int(r["medium_priority_selected"]) for r in rows])
    archive = np.array([int(r["auto_archive_selected"]) for r in rows])
    used_hours = np.array([float(r["used_manual_hours"]) for r in rows])
    limits = np.array([int(r["manual_review_limit"]) for r in rows])

    fig, ax1 = plt.subplots(figsize=(13.5, 7.5))
    title(ax1, "图14  资源约束分配结果")
    x = np.arange(len(scenarios))
    width = 0.22
    ax1.bar(x - width, manual, width, color=BLUE, label="人工复核")
    ax1.bar(x, high, width, color=PURPLE, label="high 覆盖")
    ax1.bar(x + width, medium, width, color=AMBER, label="中优先级覆盖")
    ax1.plot(x, limits, color=GRAY, linestyle="--", marker="o", label="人工复核上限")
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios)
    ax1.set_ylabel("文件数量")
    clean_axes(ax1)
    for xi, vals in zip(x, zip(manual, high, medium, archive)):
        ax1.text(xi - width, vals[0] + 6, str(vals[0]), ha="center", fontsize=9.5, fontweight="bold", color=SLATE)
        ax1.text(xi, vals[1] + 6, str(vals[1]), ha="center", fontsize=9.5, fontweight="bold", color=SLATE)
        ax1.text(xi + width, vals[2] + 6, str(vals[2]), ha="center", fontsize=9.5, fontweight="bold", color=SLATE)

    ax2 = ax1.twinx()
    ax2.plot(x, used_hours, color=TEAL, linewidth=2.6, marker="D", label="使用人工工时")
    ax2.set_ylabel("使用人工工时")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(LINE)
    for xi, h in zip(x, used_hours):
        ax2.text(xi, h + 2.5, f"{h:.1f}h", ha="center", color=TEAL, fontsize=9.5, fontweight="bold")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, ncol=3, loc="upper left")
    save(fig, "14_resource_constraint_allocation")


def fig16_dataset_scale_file_structure() -> None:
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    datasets = ["dataset2", "dataset3"]
    ds_counts = Counter(r["dataset"] for r in rows)
    file_types = ["docx", "txt", "其他格式", "xlsx 行记录"]
    by_type: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        dataset = r["dataset"]
        if dataset == "dataset3":
            file_type = "xlsx 行记录"
        else:
            suffix = Path(r["file_name"]).suffix.lower().lstrip(".") or "无后缀"
            file_type = suffix if suffix in {"docx", "txt"} else "其他格式"
        by_type[dataset][file_type] += 1

    fig = plt.figure(figsize=(14, 7.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[0.92, 1.35], wspace=0.30)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图16  数据集规模与文件来源结构", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    vals = [ds_counts[d] for d in datasets]
    bars = ax0.bar(datasets, vals, color=[BLUE, GREEN], width=0.54)
    ax0.set_ylabel("记录数量")
    ax0.set_title("数据集规模", fontsize=13, fontweight="bold")
    clean_axes(ax0)
    for rect, v in zip(bars, vals):
        ax0.text(rect.get_x() + rect.get_width() / 2, v + max(vals) * 0.025, str(v), ha="center", fontsize=12, fontweight="bold", color=SLATE)

    x = np.arange(len(datasets))
    bottom = np.zeros(len(datasets))
    colors = [BLUE, GREEN, AMBER, "#A9B7C6"]
    for file_type, color in zip(file_types, colors):
        values = np.array([by_type[d][file_type] for d in datasets])
        if values.sum() == 0:
            continue
        ax1.bar(x, values, bottom=bottom, color=color, width=0.56, label=file_type)
        for xi, b, v in zip(x, bottom, values):
            if v > 0:
                segment_label(ax1, xi, b + v / 2, str(int(v)), fontsize=9.5)
        bottom += values
    ax1.set_xticks(x)
    ax1.set_xticklabels(datasets)
    ax1.set_ylabel("记录数量")
    ax1.set_title("文件/记录来源", fontsize=13, fontweight="bold")
    ax1.legend(frameon=False, loc="upper left", ncol=2)
    clean_axes(ax1)
    fig.subplots_adjust(top=0.84)
    save(fig, "16_dataset_scale_file_structure")


def fig17_parse_quality_text_length() -> None:
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    datasets = ["dataset2", "dataset3"]
    status_order = ["ok", "empty"]
    status_labels = {"ok": "正常解析", "empty": "空文本"}
    status_colors = [GREEN, PURPLE]
    length_bins = ["0", "1-79", "80-299", "300+"]
    by_status: dict[str, Counter] = defaultdict(Counter)
    by_length: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        dataset = r["dataset"]
        by_status[dataset][r["parse_status"]] += 1
        char_count = int(float(r.get("char_count") or 0))
        if char_count == 0:
            bucket = "0"
        elif char_count < 80:
            bucket = "1-79"
        elif char_count < 300:
            bucket = "80-299"
        else:
            bucket = "300+"
        by_length[dataset][bucket] += 1

    fig = plt.figure(figsize=(14, 7.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.25], wspace=0.30)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("图17  解析质量与文本长度分布", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    x = np.arange(len(datasets))
    bottom = np.zeros(len(datasets))
    for status, color in zip(status_order, status_colors):
        values = np.array([by_status[d][status] for d in datasets])
        ax0.bar(x, values, bottom=bottom, color=color, width=0.56, label=status_labels[status])
        for xi, b, v in zip(x, bottom, values):
            if v > 0:
                segment_label(ax0, xi, b + v / 2, str(int(v)), fontsize=9.5)
        bottom += values
    ax0.set_xticks(x)
    ax0.set_xticklabels(datasets)
    ax0.set_ylabel("记录数量")
    ax0.set_title("解析状态", fontsize=13, fontweight="bold")
    ax0.legend(frameon=False, loc="upper left")
    clean_axes(ax0)

    width = 0.36
    x2 = np.arange(len(length_bins))
    vals2 = [by_length["dataset2"][b] for b in length_bins]
    vals3 = [by_length["dataset3"][b] for b in length_bins]
    bars2 = ax1.bar(x2 - width / 2, vals2, width=width, color=BLUE, label="dataset2")
    bars3 = ax1.bar(x2 + width / 2, vals3, width=width, color=GREEN, label="dataset3")
    ax1.set_xticks(x2)
    ax1.set_xticklabels(length_bins)
    ax1.set_xlabel("正文字符数分层")
    ax1.set_ylabel("记录数量")
    ax1.set_title("文本长度分层", fontsize=13, fontweight="bold")
    ax1.legend(frameon=False)
    clean_axes(ax1)
    max_len = max(vals2 + vals3)
    for bars in [bars2, bars3]:
        for rect in bars:
            v = int(rect.get_height())
            if v > 0:
                ax1.text(rect.get_x() + rect.get_width() / 2, v + max_len * 0.018, str(v), ha="center", fontsize=9.5, fontweight="bold", color=SLATE)
    fig.subplots_adjust(top=0.84)
    save(fig, "17_parse_quality_text_length")


def fig18_boundary_optimization_effect() -> None:
    rows = read_csv(ROOT / "outputs" / "experiments" / "k160_boundary_optimization_summary.csv")
    metrics = ["assigned", "multi_class", "unclassifiable"]
    labels = ["唯一归类", "多类待判别", "无法归类"]
    data = {r["metric"]: r for r in rows}
    before = np.array([int(float(data[m]["before"])) for m in metrics])
    after = np.array([int(float(data[m]["after"])) for m in metrics])
    delta = after - before

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    title(ax, "图18  边界优化前后分类状态变化")
    x = np.arange(len(metrics))
    width = 0.34
    bars_before = ax.bar(x - width / 2, before, width=width, color=BLUE_L, edgecolor=BLUE, linewidth=1.0, label="优化前")
    bars_after = ax.bar(x + width / 2, after, width=width, color=GREEN, label="优化后")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("记录数量")
    ax.legend(frameon=False, loc="upper right")
    clean_axes(ax)
    max_v = max(before.max(), after.max())
    for bars, values in [(bars_before, before), (bars_after, after)]:
        for rect, v in zip(bars, values):
            ax.text(rect.get_x() + rect.get_width() / 2, v + max_v * 0.025, str(int(v)), ha="center", fontsize=10.5, fontweight="bold", color=SLATE)
    save(fig, "18_boundary_optimization_effect")


def fig19_topic_cluster_size_distribution() -> None:
    rows = read_csv(final_path("topic_discovery", "topic_summary_refined.csv"))
    sizes = np.array(sorted([int(r["size"]) for r in rows], reverse=True))
    ranks = np.arange(1, len(sizes) + 1)
    small5 = int((sizes <= 5).sum())
    small10 = int((sizes <= 10).sum())

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    title(ax, "图19  主题簇规模长尾分布")
    colors = [BLUE if i < 10 else BLUE_L for i in range(len(sizes))]
    ax.bar(ranks, sizes, color=colors, width=0.92, edgecolor="white", linewidth=0.35)
    ax.set_xlabel("主题原型序号（按规模降序）")
    ax.set_ylabel("簇内文档数")
    ax.set_xticks([1, 40, 80, 120, 160])
    clean_axes(ax)
    ax.text(0.985, 0.94, f"主题原型 160 个｜≤5: {small5}｜≤10: {small10}", transform=ax.transAxes, ha="right", va="top", fontsize=11, color=SLATE, fontweight="bold")
    ax.text(1, sizes[0] + sizes[0] * 0.035, str(int(sizes[0])), ha="center", fontsize=10.5, fontweight="bold", color=SLATE)
    save(fig, "19_topic_cluster_size_distribution")


def fig20_manual_review_correction_flow() -> None:
    rows = read_csv(manual_review_combined_path())
    education_topics = {"院校概况类", "科研项目类", "校园活动类", "论文期刊类", "招生学位类", "教务培养类", "国际合作类", "科研创新类"}

    def original_bucket(topic: str) -> str:
        if topic == "综合待判别类":
            return "综合待判别"
        if topic in education_topics:
            return "教育科研原类"
        return "其他原类"

    def final_bucket(row: dict[str, str]) -> str:
        final_topic = row["final_topic"]
        if final_topic == "噪声无效":
            return "噪声无效"
        if final_topic == "暂不确定":
            return "暂不确定"
        if final_topic == "无法归类":
            return "无法归类"
        if final_topic == row["original_topic"]:
            return "保持原类"
        if final_topic in education_topics:
            return "教育科研细类"
        return "其他业务类"

    row_labels = ["综合待判别", "教育科研原类", "其他原类"]
    col_labels = ["噪声无效", "暂不确定", "无法归类", "教育科研细类", "其他业务类", "保持原类"]
    matrix = np.zeros((len(row_labels), len(col_labels)), dtype=int)
    for r in rows:
        if r.get("manual_status") not in {"confirmed", "noise", "uncertain", "unclassifiable"}:
            continue
        matrix[row_labels.index(original_bucket(r["original_topic"])), col_labels.index(final_bucket(r))] += 1

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    title(ax, "图20  人工核查修正矩阵")
    cmap = LinearSegmentedColormap.from_list("morandi_heat", [BG, "#EEE7D9", GREEN_L, "#AFC6BE", "#8EA7A1"])
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=max(1, int(matrix.max())))
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)
    ax.set_xlabel("人工核查后")
    ax.set_ylabel("模型原结果")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = int(matrix[i, j])
            if value:
                ax.text(j, i, str(value), ha="center", va="center", color=SLATE, fontsize=12, fontweight="bold")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.035)
    fig.text(0.055, 0.035, f"人工核查记录：{int(matrix.sum())} 条", ha="left", color=GRAY, fontsize=10)
    save(fig, "20_manual_review_correction_flow")


def fig21_priority_score_distribution() -> None:
    rows = read_csv(final_path("review_prioritization", "review_priority_results.csv"))
    levels = ["low", "medium", "high"]
    colors = [GREEN, AMBER, PURPLE]
    labels = {"low": "low", "medium": "medium", "high": "high"}
    scores_by_level = {level: [float(r["priority_score"]) for r in rows if r["priority_level"] == level] for level in levels}
    all_scores = [float(r["priority_score"]) for r in rows]
    medium_threshold = 0.35
    high_threshold = 0.65
    bins = np.unique(np.r_[np.linspace(0, max(all_scores) + 0.02, 22), medium_threshold, high_threshold])

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    title(ax, "图21  复核优先级得分分布")
    ax.hist([scores_by_level[l] for l in levels], bins=bins, stacked=True, color=colors, label=[labels[l] for l in levels], edgecolor=BG, linewidth=0.8)
    ax.set_xlabel("priority_score")
    ax.set_ylabel("记录数量")
    ax.legend(frameon=False, loc="upper right")
    clean_axes(ax)
    for threshold, label, color, y_frac in [(medium_threshold, "medium", AMBER, 0.86), (high_threshold, "high", PURPLE, 0.78)]:
        ax.axvline(threshold, color=color, linestyle=(0, (4, 3)), linewidth=1.8)
        ax.text(
            threshold - 0.012,
            ax.get_ylim()[1] * y_frac,
            label,
            ha="right",
            va="center",
            color=color,
            fontsize=10.5,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.18", facecolor=BG, edgecolor="none", alpha=0.92),
            clip_on=False,
        )
    save(fig, "21_priority_score_distribution")


def fig22_data_foundation_parse_quality() -> None:
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    datasets = ["dataset2", "dataset3"]
    ds_counts = Counter(r["dataset"] for r in rows)
    file_types = ["docx", "txt", "其他格式", "xlsx 行记录"]
    by_type: dict[str, Counter] = defaultdict(Counter)
    by_status: dict[str, Counter] = defaultdict(Counter)
    length_bins = ["0", "1-79", "80-299", "300+"]
    by_length: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        dataset = r["dataset"]
        if dataset == "dataset3":
            file_type = "xlsx 行记录"
        else:
            suffix = Path(r["file_name"]).suffix.lower().lstrip(".") or "无后缀"
            file_type = suffix if suffix in {"docx", "txt"} else "其他格式"
        by_type[dataset][file_type] += 1
        by_status[dataset][r["parse_status"]] += 1
        char_count = int(float(r.get("char_count") or 0))
        if char_count == 0:
            bucket = "0"
        elif char_count < 80:
            bucket = "1-79"
        elif char_count < 300:
            bucket = "80-299"
        else:
            bucket = "300+"
        by_length[dataset][bucket] += 1

    fig = plt.figure(figsize=(15.2, 8.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[0.92, 1.22], hspace=0.34, wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])
    fig.suptitle("数据基础与解析质量", x=0.055, y=0.98, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    vals = [ds_counts[d] for d in datasets]
    bars = ax0.bar(["数据集2", "数据集3"], vals, color=[BLUE, GREEN], width=0.54)
    ax0.set_title("样本规模", fontsize=13, fontweight="bold")
    ax0.set_ylabel("记录数量")
    clean_axes(ax0)
    for rect, v in zip(bars, vals):
        ax0.text(rect.get_x() + rect.get_width() / 2, v + max(vals) * 0.035, str(v), ha="center", fontsize=11, fontweight="bold", color=SLATE)

    x = np.arange(len(datasets))
    bottom = np.zeros(len(datasets))
    for file_type, color in zip(file_types, [BLUE, GREEN, AMBER, "#A9B7C6"]):
        values = np.array([by_type[d][file_type] for d in datasets])
        if values.sum() == 0:
            continue
        ax1.bar(x, values, bottom=bottom, color=color, width=0.56, label=file_type, edgecolor=SLATE, linewidth=0.35)
        for xi, b, v in zip(x, bottom, values):
            if v >= 80:
                segment_label(ax1, xi, b + v / 2, str(int(v)), fontsize=8.8)
        bottom += values
    ax1.set_xticks(x)
    ax1.set_xticklabels(["数据集2", "数据集3"])
    ax1.set_title("文件/记录来源", fontsize=13, fontweight="bold")
    ax1.set_ylabel("记录数量")
    ax1.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
    clean_axes(ax1)

    bottom = np.zeros(len(datasets))
    for status, color, label in [("ok", GREEN, "正常解析"), ("empty", PURPLE, "空文本")]:
        values = np.array([by_status[d][status] for d in datasets])
        ax2.bar(x, values, bottom=bottom, color=color, width=0.56, label=label, edgecolor=SLATE, linewidth=0.35)
        for xi, b, v in zip(x, bottom, values):
            if v > 0:
                segment_label(ax2, xi, b + v / 2, str(int(v)), fontsize=8.8)
        bottom += values
    ax2.set_xticks(x)
    ax2.set_xticklabels(["数据集2", "数据集3"])
    ax2.set_title("解析状态", fontsize=13, fontweight="bold")
    ax2.set_ylabel("记录数量")
    ax2.legend(frameon=False, loc="upper left", fontsize=9)
    clean_axes(ax2)

    width = 0.36
    x2 = np.arange(len(length_bins))
    vals2 = [by_length["dataset2"][b] for b in length_bins]
    vals3 = [by_length["dataset3"][b] for b in length_bins]
    bars2 = ax3.bar(x2 - width / 2, vals2, width=width, color=BLUE, label="数据集2")
    bars3 = ax3.bar(x2 + width / 2, vals3, width=width, color=GREEN, label="数据集3")
    ax3.set_xticks(x2)
    ax3.set_xticklabels(length_bins)
    ax3.set_xlabel("正文字符数分层")
    ax3.set_title("文本长度", fontsize=13, fontweight="bold")
    ax3.set_ylabel("记录数量")
    ax3.legend(frameon=False, fontsize=9)
    clean_axes(ax3)
    max_len = max(vals2 + vals3)
    for bars_group in [bars2, bars3]:
        for rect in bars_group:
            v = int(rect.get_height())
            if v > 0:
                ax3.text(rect.get_x() + rect.get_width() / 2, v + max_len * 0.02, str(v), ha="center", fontsize=8.8, fontweight="bold", color=SLATE)
    fig.subplots_adjust(top=0.88)
    save(fig, "22_data_foundation_parse_quality")


def fig23_k_selection_topic_longtail() -> None:
    ab = read_csv(ROOT / "outputs" / "experiments" / "k_ablation_summary.csv")
    size_rows = {int(r["k"]): r for r in read_csv(ROOT / "outputs" / "experiments" / "k_topic_size_summary.csv")}
    k = np.array([int(r["k"]) for r in ab])
    silhouette = np.array([float(r["silhouette"]) for r in ab])
    multi = np.array([int(r["multi_class"]) for r in ab])
    small10 = np.array([int(size_rows[int(r["k"])]["small_le_10"]) for r in ab])
    topic_rows = read_csv(final_path("topic_discovery", "topic_summary_refined.csv"))
    sizes = np.array(sorted([int(r["size"]) for r in topic_rows], reverse=True))
    ranks = np.arange(1, len(sizes) + 1)

    fig = plt.figure(figsize=(15.2, 7.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1.0], wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle("k 值选择与主题原型规模分布", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    x = np.arange(len(k))
    bars = ax0.bar(x, multi, width=0.46, color=BLUE_L, edgecolor=BLUE, linewidth=1.0, label="多类待判别")
    ax0.set_xticks(x)
    ax0.set_xticklabels([str(v) for v in k])
    ax0.set_xlabel("主题原型数量 k")
    ax0.set_ylabel("数量")
    ax0.set_title("消融实验", fontsize=13, fontweight="bold")
    clean_axes(ax0)
    ax0b = ax0.twinx()
    ax0b.plot(x, silhouette, color=PURPLE, marker="o", linewidth=2.2, markersize=5.8, label="轮廓系数")
    ax0b.set_ylabel("轮廓系数")
    ax0b.spines["top"].set_visible(False)
    ax0b.spines["right"].set_color(LINE)
    chosen = list(k).index(160)
    ax0.axvline(chosen, color=TEAL, linestyle=(0, (4, 3)), linewidth=1.7)
    ax0.text(chosen + 0.08, max(multi) * 0.92, "k=160", color=TEAL, fontsize=11.5, fontweight="bold")
    for rect, value in zip(bars, multi):
        ax0.text(rect.get_x() + rect.get_width() / 2, value + 90, str(value), ha="center", fontsize=8.5, color=SLATE)
    for xi, value in zip(x, small10):
        ax0.text(xi, 135, f"小簇{value}", ha="center", va="bottom", fontsize=8.3, color=SLATE, fontweight="bold")
    handles0, labels0 = ax0.get_legend_handles_labels()
    handles1, labels1 = ax0b.get_legend_handles_labels()
    ax0.legend(handles0 + handles1, labels0 + labels1, frameon=False, loc="upper left", ncol=2, fontsize=8.8)

    colors = [BLUE if i < 10 else BLUE_L for i in range(len(sizes))]
    ax1.bar(ranks, sizes, color=colors, width=0.92, edgecolor="white", linewidth=0.35)
    ax1.set_title("k=160 主题原型长尾", fontsize=13, fontweight="bold")
    ax1.set_xlabel("主题原型序号（按规模降序）")
    ax1.set_ylabel("簇内文档数")
    ax1.set_xticks([1, 40, 80, 120, 160])
    clean_axes(ax1)
    small5 = int((sizes <= 5).sum())
    small10_final = int((sizes <= 10).sum())
    ax1.text(0.98, 0.94, f"160 个原型｜≤5: {small5}｜≤10: {small10_final}", transform=ax1.transAxes, ha="right", va="top", fontsize=10.5, color=SLATE, fontweight="bold")
    ax1.text(1, sizes[0] + sizes[0] * 0.035, str(int(sizes[0])), ha="center", fontsize=10, fontweight="bold", color=SLATE)
    fig.subplots_adjust(top=0.84)
    save(fig, "23_k_selection_topic_longtail")


def fig24_problem2_integrated_results() -> None:
    rows = read_csv(final_path("document_classification", "classification_results.csv"))
    boundary_rows = read_csv(ROOT / "outputs" / "experiments" / "k160_boundary_optimization_summary.csv")
    datasets = ["dataset2", "dataset3"]
    by_status: dict[str, Counter] = defaultdict(Counter)
    parent_counts = Counter()
    education_parent = "教育科研与学术文献类"
    education_split = Counter()
    for r in rows:
        by_status[r["dataset"]][r["classification_status"]] += 1
        parent_counts[r["topic_parent_name"]] += 1
        if r["topic_parent_name"] == education_parent:
            education_split[r["topic_name"]] += 1

    fig = plt.figure(figsize=(15.6, 9.0))
    gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.34)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])
    fig.suptitle("问题二分类结果、边界状态与高频主题结构", x=0.055, y=0.975, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    status_order = ["assigned", "multi_class", "unclassifiable"]
    status_labels = {"assigned": "明确归类", "multi_class": "多类边界", "unclassifiable": "无法归类"}
    status_colors = {"assigned": GREEN, "multi_class": AMBER, "unclassifiable": PURPLE}
    x = np.arange(len(datasets))
    bottom = np.zeros(len(datasets))
    small_segments: list[tuple[float, float, int, str]] = []
    for status in status_order:
        values = np.array([by_status[d][status] for d in datasets])
        ax0.bar(x, values, bottom=bottom, width=0.56, color=status_colors[status], label=status_labels[status], edgecolor=SLATE, linewidth=0.35)
        for xi, b, v in zip(x, bottom, values):
            if v >= 300:
                segment_label(ax0, xi, b + v / 2, str(int(v)), fontsize=8.8)
            elif v > 0:
                small_segments.append((xi, b + v / 2, int(v), status))
        bottom += values
    for xi, yi, value, status in small_segments:
        label_color = status_colors[status]
        label_y = yi
        if status == "multi_class":
            label_y = yi - 65
        elif status == "unclassifiable":
            label_y = yi + 65
        ax0.annotate(
            str(value),
            xy=(xi + 0.29, yi),
            xytext=(xi + 0.43, label_y),
            ha="left",
            va="center",
            fontsize=8.8,
            fontweight="bold",
            color=SLATE,
            bbox=dict(boxstyle="round,pad=0.16", facecolor="#F6F2EC", edgecolor=label_color, linewidth=0.8, alpha=0.92),
            arrowprops=dict(arrowstyle="-", color=label_color, linewidth=0.8, shrinkA=0, shrinkB=3),
            clip_on=False,
        )
    ax0.set_xticks(x)
    ax0.set_xticklabels(["数据集2", "数据集3"])
    ax0.set_title("最终归类状态", fontsize=13, fontweight="bold")
    ax0.set_ylabel("记录数量")
    ax0.legend(frameon=False, fontsize=9)
    clean_axes(ax0)
    ax0.margins(x=0.16)

    top = parent_counts.most_common(8)
    labels = [name for name, _ in top]
    vals = [value for _, value in top]
    y = np.arange(len(vals))
    ax1.barh(y, vals, color=[BLUE if i == 0 else "#A9B7C6" for i in range(len(vals))], edgecolor="white", linewidth=1.0)
    ax1.set_yticks(y)
    ax1.set_yticklabels([wrap_label(label, 12) for label in labels], fontsize=9)
    ax1.invert_yaxis()
    ax1.set_title("主题父类 Top 8", fontsize=13, fontweight="bold")
    ax1.set_xlabel("记录数量")
    clean_axes(ax1, grid_axis="x")
    for yi, v in zip(y, vals):
        ax1.text(v + max(vals) * 0.018, yi, str(v), va="center", fontsize=9.2, fontweight="bold", color=SLATE)

    edu = education_split.most_common()
    edu_labels = [name for name, _ in edu]
    edu_vals = [value for _, value in edu]
    y2 = np.arange(len(edu_vals))
    ax2.barh(y2, edu_vals, color=[GREEN, BLUE, ORANGE, AMBER, PURPLE, "#B7AAA3", "#8EA7A1"][: len(edu_vals)], edgecolor="white", linewidth=1.0)
    ax2.set_yticks(y2)
    ax2.set_yticklabels([wrap_label(label, 8) for label in edu_labels], fontsize=9.2)
    ax2.invert_yaxis()
    ax2.set_title("教育科研类细分", fontsize=13, fontweight="bold")
    ax2.set_xlabel("记录数量")
    clean_axes(ax2, grid_axis="x")
    for yi, v in zip(y2, edu_vals):
        ax2.text(v + max(edu_vals) * 0.025, yi, str(v), va="center", fontsize=9.2, fontweight="bold", color=SLATE)

    data = {r["metric"]: r for r in boundary_rows}
    metrics = ["assigned", "multi_class"]
    labels_b = ["明确归类", "多类边界"]
    before = np.array([int(float(data[m]["before"])) for m in metrics])
    after = np.array([int(float(data[m]["after"])) for m in metrics])
    xb = np.arange(len(metrics))
    width = 0.34
    ax3.bar(xb - width / 2, before, width=width, color=BLUE_L, edgecolor=BLUE, linewidth=1.0, label="优化前")
    ax3.bar(xb + width / 2, after, width=width, color=GREEN, edgecolor=SLATE, linewidth=0.35, label="优化后")
    ax3.set_xticks(xb)
    ax3.set_xticklabels(labels_b)
    ax3.set_title("边界优化效果", fontsize=13, fontweight="bold")
    ax3.set_ylabel("记录数量")
    ax3.legend(frameon=False, fontsize=9)
    clean_axes(ax3)
    max_v = max(before.max(), after.max())
    for xi, b, a in zip(xb, before, after):
        ax3.text(xi - width / 2, b + max_v * 0.025, str(int(b)), ha="center", fontsize=9.2, fontweight="bold", color=SLATE)
        ax3.text(xi + width / 2, a + max_v * 0.025, str(int(a)), ha="center", fontsize=9.2, fontweight="bold", color=SLATE)
    fig.subplots_adjust(top=0.88)
    save(fig, "24_problem2_integrated_results")


def fig25_priority_resource_integrated() -> None:
    priority_rows = read_csv(final_path("review_prioritization", "review_priority_results.csv"))
    summary_rows = read_csv(final_path("review_prioritization", "review_priority_summary.csv"))
    resource_rows = read_csv(final_path("review_prioritization", "resource_plan.csv"))
    levels = ["low", "medium", "high"]
    colors = {"low": GREEN, "medium": AMBER, "high": PURPLE}
    scores_by_level = {level: [float(r["priority_score"]) for r in priority_rows if r["priority_level"] == level] for level in levels}
    all_scores = [float(r["priority_score"]) for r in priority_rows]
    medium_threshold = 0.35
    high_threshold = 0.65
    bins = np.unique(np.r_[np.linspace(0, max(all_scores) + 0.02, 20), medium_threshold, high_threshold])
    by_level = Counter()
    for r in summary_rows:
        by_level[r["priority_level"]] += int(r["count"])

    fig = plt.figure(figsize=(15.6, 7.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 0.82, 1.35], wspace=0.34)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])
    fig.suptitle("复核优先级划分与资源约束分配", x=0.055, y=0.965, ha="left", fontsize=17, fontweight="bold", color=SLATE)

    ax0.hist([scores_by_level[l] for l in levels], bins=bins, stacked=True, color=[colors[l] for l in levels], label=levels, edgecolor=BG, linewidth=0.8)
    ax0.set_title("优先级得分分布", fontsize=13, fontweight="bold")
    ax0.set_xlabel("priority_score")
    ax0.set_ylabel("记录数量")
    for threshold, label, color, y_frac in [(medium_threshold, "medium", AMBER, 0.86), (high_threshold, "high", PURPLE, 0.78)]:
        ax0.axvline(threshold, color=color, linestyle=(0, (4, 3)), linewidth=1.6)
        ax0.text(
            threshold - 0.012,
            ax0.get_ylim()[1] * y_frac,
            label,
            ha="right",
            va="center",
            fontsize=9.2,
            color=color,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.18", facecolor=BG, edgecolor="none", alpha=0.92),
            clip_on=False,
        )
    ax0.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(0.98, 0.86))
    clean_axes(ax0)

    vals = [by_level[l] for l in ["high", "medium", "low"]]
    labels = ["high", "medium", "low"]
    y = np.arange(len(vals))
    ax1.barh(y, vals, color=[PURPLE, AMBER, GREEN], edgecolor="white", linewidth=1.0)
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels)
    ax1.invert_yaxis()
    ax1.set_title("优先级数量", fontsize=13, fontweight="bold")
    ax1.set_xlabel("记录数量")
    clean_axes(ax1, grid_axis="x")
    for yi, v in zip(y, vals):
        ax1.text(v + max(vals) * 0.03, yi, str(v), va="center", fontsize=10, fontweight="bold", color=SLATE)

    scenarios = [r["scenario_id"] for r in resource_rows]
    manual = np.array([int(r["manual_review_selected"]) for r in resource_rows])
    high = np.array([int(r["high_priority_selected"]) for r in resource_rows])
    medium = np.array([int(r["medium_priority_selected"]) for r in resource_rows])
    limits = np.array([int(r["manual_review_limit"]) for r in resource_rows])
    used_hours = np.array([float(r["used_manual_hours"]) for r in resource_rows])
    x = np.arange(len(scenarios))
    width = 0.22
    ax2.bar(x - width, manual, width, color=BLUE, label="人工复核")
    ax2.bar(x, high, width, color=PURPLE, label="high 覆盖")
    ax2.bar(x + width, medium, width, color=AMBER, label="中优先级覆盖")
    ax2.plot(x, limits, color=GRAY, linestyle="--", marker="o", label="复核上限")
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenarios)
    ax2.set_title("资源约束场景", fontsize=13, fontweight="bold")
    ax2.set_ylabel("文件数量")
    clean_axes(ax2)
    for xi, values in zip(x, zip(manual, high, medium)):
        for offset, v in zip([-width, 0, width], values):
            ax2.text(xi + offset, v + 7, str(int(v)), ha="center", fontsize=8.7, fontweight="bold", color=SLATE)
    ax2b = ax2.twinx()
    ax2b.plot(x, used_hours, color=TEAL, linewidth=2.2, marker="D", label="使用工时")
    ax2b.set_ylabel("使用工时")
    ax2b.spines["top"].set_visible(False)
    ax2b.spines["right"].set_color(LINE)
    handles0, labels0 = ax2.get_legend_handles_labels()
    handles1, labels1 = ax2b.get_legend_handles_labels()
    ax2.legend(handles0 + handles1, labels0 + labels1, frameon=False, loc="upper left", ncol=2, fontsize=8.5)
    fig.subplots_adjust(top=0.84)
    save(fig, "25_priority_resource_integrated")


def build_readme() -> None:
    lines = [
        "# 代码生成的精确数值论文图",
        "",
        "本目录只放需要严格读取 CSV/JSON 数据生成的论文图。每张图同时提供 PNG 和 SVG。",
        "",
        "本版采用低饱和莫兰迪配色，并将解释性文字移出图内，图中只保留标题、坐标轴、图例和关键数字。论文中建议用图注承担数据来源和解释。",
        "",
        "| 编号 | 图名 | 文件前缀 | 建议位置 | 数据来源 | 图注建议 |",
        "|---|---|---|---|---|---|",
        "| 图4 | 数据集1主题发现结果分布 | `04_dataset1_topic_family_distribution` | 正文 | `outputs/final_results_2026-05-10/topic_discovery/topic_summary_refined.csv` | 按最终 k=160 主题原型归并后的主题族统计数据集1入模文档数量。 |",
        "| 图12 | AHP 指标权重与一致性检验 | `12_ahp_weights_consistency` | 正文 | `outputs/final_results_2026-05-10/review_prioritization/review_priority_meta.json` | AHP 权重显示错分风险最高，CR 小于 0.1，判断矩阵一致性可接受。 |",
        "| 图20 | 人工核查修正矩阵 | `20_manual_review_correction_flow` | 正文/附录 | `notes/manual_review/review_logs_2026-05-09_combined_latest_merged.csv` | 两批人工核查合并去重后形成 61 条记录，展示模型原结果到人工结果的主要修正方向。 |",
        "| 合并图22 | 数据基础与解析质量 | `22_data_foundation_parse_quality` | 正文 | `classification_results.csv` | 合并数据集规模、文件来源、解析状态和文本长度分层，减少第4章图片数量。 |",
        "| 合并图23 | k 值选择与主题原型规模分布 | `23_k_selection_topic_longtail` | 正文/检验 | `k_ablation_summary.csv`, `k_topic_size_summary.csv`, `topic_summary_refined.csv` | 同时展示 k=160 选择依据和主题原型长尾结构。 |",
        "| 合并图24 | 问题二分类结果、边界状态与高频主题结构 | `24_problem2_integrated_results` | 正文 | `classification_results.csv`, `k160_boundary_optimization_summary.csv` | 合并最终归类状态、高频主题、教育科研细分和边界优化效果。 |",
        "| 合并图25 | 复核优先级划分与资源约束分配 | `25_priority_resource_integrated` | 正文 | `review_priority_results.csv`, `review_priority_summary.csv`, `resource_plan.csv` | 合并优先级得分、优先级数量和资源约束场景。 |",
        "",
        "已被合并吸收、根目录不再默认保留的单图：`05`、`06`、`08`、`09`、`13`、`14`、`16`、`17`、`18`、`19`、`21`。",
        "",
        "重新生成命令：",
        "",
        "```powershell",
        "cd E:\\Code\\数维杯",
        "python b_solution\\scripts\\generate_numeric_paper_figures.py",
        "```",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    setup_style()
    validate_latest_sources()
    fig04_dataset1_topic_family_distribution()
    fig12_ahp_weights()
    fig20_manual_review_correction_flow()
    fig22_data_foundation_parse_quality()
    fig23_k_selection_topic_longtail()
    fig24_problem2_integrated_results()
    fig25_priority_resource_integrated()
    build_readme()
    print(f"wrote numeric figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
