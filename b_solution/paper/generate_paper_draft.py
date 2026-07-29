from __future__ import annotations

import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


ROOT = Path(r"E:\Code\数维杯")
SOLUTION = ROOT / "b_solution"
PAPER_DIR = SOLUTION / "paper"
IMAGE_DIR = ROOT / "论文图片"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def group_count(rows: list[dict[str, str]], *keys: str) -> list[tuple[tuple[str, ...], int]]:
    buckets: dict[tuple[str, ...], int] = {}
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        buckets[key] = buckets.get(key, 0) + 1
    return sorted(buckets.items(), key=lambda item: item[1], reverse=True)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: object) -> None:
    cell.text = str(text)
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.name = "宋体"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
            run.font.size = Pt(9)


def add_table_docx(doc: Document, headers: list[str], rows: list[list[object]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, header in enumerate(headers):
        set_cell_text(hdr[i], header)
        set_cell_shading(hdr[i], "D9EAF7")
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_text(cells[i], value)
    doc.add_paragraph()


def add_md_table(lines: list[str], headers: list[str], rows: list[list[object]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    lines.append("")


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = "黑体"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")


def add_paragraph(doc: Document, text: str = "", first_line: bool = True) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    if first_line:
        p.paragraph_format.first_line_indent = Pt(24)
    run = p.add_run(text)
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(10.5)


def add_center(doc: Document, text: str, size: int = 10, bold: bool = False) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)


def add_figure_docx(doc: Document, path: Path, caption: str, width_cm: float = 14.5) -> None:
    if path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(path), width=Cm(width_cm))
        add_center(doc, caption, size=9)


def build_context() -> dict[str, object]:
    parsed_index = read_csv(SOLUTION / "data" / "parsed_documents_index.csv")
    classification = read_csv(SOLUTION / "outputs" / "document_classification" / "classification_results.csv")
    priority_summary = read_csv(SOLUTION / "outputs" / "review_prioritization" / "review_priority_summary.csv")
    resource_plan = read_csv(SOLUTION / "outputs" / "review_prioritization" / "resource_plan.csv")
    k_ablation = read_csv(SOLUTION / "outputs" / "experiments" / "k_ablation_summary.csv")
    boundary_summary_path = SOLUTION / "outputs" / "experiments" / "k160_boundary_optimization_summary.csv"
    boundary_summary = read_csv(boundary_summary_path) if boundary_summary_path.exists() else []
    family_map = read_csv(SOLUTION / "outputs" / "topic_discovery" / "topic_family_map.csv")
    topic_meta = json.loads((SOLUTION / "outputs" / "topic_discovery" / "topic_meta.json").read_text(encoding="utf-8"))

    dataset_counts = [(key[0], count) for key, count in sorted(group_count(parsed_index, "dataset"), key=lambda x: x[0][0])]
    parse_status = [list(key) + [count] for key, count in sorted(group_count(parsed_index, "dataset", "parse_status"), key=lambda x: x[0])]
    class_status = [list(key) + [count] for key, count in sorted(group_count(classification, "dataset", "classification_status"), key=lambda x: x[0])]
    top_topics = [list(key) + [count] for key, count in group_count(classification, "dataset", "topic_parent_name")[:12]]
    topic_family_counts = [[key[0], count] for key, count in group_count(family_map, "topic_name")[:12]]

    k_rows = [
        [
            row["k"],
            row["silhouette"],
            row["refined_topics"],
            row["assigned"],
            row["multi_class"],
            row["unclassifiable"],
            row["priority_high"],
        ]
        for row in k_ablation
    ]
    boundary_rows = [
        [
            row["metric"],
            row["before"],
            row["after"],
            row["delta"],
        ]
        for row in boundary_summary
    ]
    priority_rows = [
        [
            row["dataset"],
            row["priority_level"],
            row["count"],
            row["mean_priority_score"],
            row["mean_misclassification_risk"],
            row["mean_urgency_score"],
            row["mean_review_necessity_score"],
        ]
        for row in priority_summary
    ]
    resource_rows = [
        [
            row["scenario_id"],
            row["manual_hours"],
            row["manual_review_limit"],
            row["auto_archive_limit"],
            row["manual_review_selected"],
            row["high_priority_selected"],
            row["medium_priority_selected"],
        ]
        for row in resource_plan
    ]
    status_total = sum(int(row[2]) for row in class_status)
    assigned = sum(int(row[2]) for row in class_status if row[1] == "assigned")
    multi_class = sum(int(row[2]) for row in class_status if row[1] == "multi_class")
    unclassifiable = sum(int(row[2]) for row in class_status if row[1] == "unclassifiable")
    high_total = sum(int(row[2]) for row in priority_rows if row[1] == "high")
    medium_total = sum(int(row[2]) for row in priority_rows if row[1] == "medium")
    low_total = sum(int(row[2]) for row in priority_rows if row[1] == "low")

    return {
        "dataset_counts": dataset_counts,
        "parse_status": parse_status,
        "class_status": class_status,
        "top_topics": top_topics,
        "topic_family_counts": topic_family_counts,
        "k_rows": k_rows,
        "boundary_rows": boundary_rows,
        "priority_rows": priority_rows,
        "resource_rows": resource_rows,
        "topic_meta": topic_meta,
        "status_total": status_total,
        "assigned": assigned,
        "multi_class": multi_class,
        "unclassifiable": unclassifiable,
        "high_total": high_total,
        "medium_total": medium_total,
        "low_total": low_total,
    }


def build_md(ctx: dict[str, object]) -> str:
    lines: list[str] = []
    add = lines.append
    topic_meta = ctx["topic_meta"]

    add("# 基于可解释主题原型与风险优先级的多源异构文件智能治理模型")
    add("")
    add("## 摘要")
    add("")
    add(
        "针对智能办公场景下多源异构文件格式复杂、历史类别未知、新数据字段不完整及人工复核资源有限等问题，本文构建“统一解析—主题发现—归类判别—风险复核—资源分配”的智能文件治理模型。首先对 Word、PDF、Excel、图片等文件统一解析，并用 OCR 补全文本不足样本，构造融合标题、正文、表格和 OCR 的分析文本。"
    )
    add(
        "针对问题一，采用 TF-IDF 表征关键词分布，利用 TruncatedSVD 降维，并通过 MiniBatchKMeans 发现历史文件主题原型。比较 k=90、120、160、200、240、288 六组粒度后，综合轮廓系数、主题碎片化和复核成本，选取 k=160；数据集1共3396条记录，3133条参与主题发现，覆盖率0.923，轮廓系数0.2916。"
    )
    add(
        f"针对问题二，以主题原型和主题词典为基础，建立字段加权相似度归类模型，综合余弦相似度、关键词覆盖率、字段完整度和规则证据对数据集2、3归类。共处理{ctx['status_total']}条新记录，其中唯一归类{ctx['assigned']}条，多类待判别{ctx['multi_class']}条，无法归类{ctx['unclassifiable']}条；边界样本进入复核队列。"
    )
    add(
        f"针对问题三，将置信度、类别间隔、解析状态、紧急词、金额和审批等信号转化为错分风险、紧急程度和复核必要性三类指标，并采用 AHP 构建复核优先级模型。结果显示，高优先级{ctx['high_total']}条，中优先级{ctx['medium_total']}条，低优先级{ctx['low_total']}条。结合数据集4资源约束，按单位复核时间收益贪心分配，得到人工复核和自动归档建议。"
    )
    add("")
    add("**关键词：** 多源异构文件；TF-IDF；MiniBatchKMeans；主题原型；AHP；人工复核")
    add("")
    add("## 目录")
    add("")
    for item in [
        "一、问题重述",
        "二、问题分析",
        "三、模型假设",
        "四、定义与符号说明",
        "五、模型的建立与求解",
        "六、模型的评价及优化",
        "参考文献",
        "附录",
    ]:
        add(item)
    add("")
    add("## 一、问题重述")
    add("")
    add(
        "随着数字化办公的持续推进，企事业单位在日常运行中积累了大量格式多样、结构复杂、内容来源不一的文件数据。这些文件既包括 Word、PDF、Excel、图片等真实原始文件，也包括在流转、汇总和调用过程中形成的半结构化记录。不同文件在文本长度、表达方式、结构层次、业务属性和完整程度上差异明显，传统依赖人工阅读、判断和归档的处理方式容易出现效率低、标准不统一、误分类风险高和后续检索困难等问题。"
    )
    add(
        "题目要求基于附件数据建立智能文件治理模型。数据集1为历史真实文件数据，需要从中挖掘能反映文件内容与属性的关键信息，并形成具有解释性的主题分类体系；数据集2和数据集3为后续流入的新数据，其中既有半结构化记录，也有匿名原始文件，需要根据问题一形成的主题体系进行归类，并设计评价指标衡量归类结果的合理性、可解释性和迁移适用性；数据集4给出业务规则和资源约束，需要在考虑紧急程度、错分风险和复核必要性的基础上，对待处理文件进行高、中、低等级划分，并确定是否需要人工复核及复核优先顺序。"
    )
    add(
        "因此，本文需要解决的核心并非单一文本分类问题，而是一个从异构文件解析、历史主题发现、新数据迁移归类到人机协同复核和资源约束优化的完整文件治理问题。"
    )
    add("")
    add("## 二、问题分析")
    add("")
    add("### 2.1 数据特点分析")
    add("")
    add(
        "附件数据呈现出明显的多源异构特征。首先，文件格式不统一，既包含可直接抽取文本的 Office 文档，也包含需要 OCR 处理的图片或扫描类材料；其次，结构完整程度不一，数据集1主要为历史真实文件，数据集2包含标题、正文片段、来源等半结构化字段，数据集3则需要按匿名记录逐条处理；最后，文件内容存在交叉主题，同一文档可能同时具有政府治理、财政金融、教育科研、资源环境等多个领域特征，因此模型不宜对边界样本进行过度自信的唯一判定。"
    )
    add("")
    add_figure_md(lines, "图1  B题算法流程学术框架图", IMAGE_DIR / "B题算法流程学术框架图.png")
    add("")
    add("### 2.2 三个问题之间的逻辑关系")
    add("")
    add(
        "问题一是基础层，目标是在无人工标签的历史文件中形成稳定主题原型和主题词典；问题二是迁移层，利用问题一的主题原型对新流入数据进行归类，并输出置信度、候选类别和边界状态；问题三是治理层，进一步把问题二的不确定性和业务敏感信号转化为复核优先级，在资源约束下给出处理策略。三问之间存在明显的承上启下关系，问题一的主题体系决定问题二的类别空间，问题二的置信度和边界状态又是问题三风险排序的重要输入。"
    )
    add("")
    add("## 三、模型假设")
    add("")
    assumptions = [
        "题目提供的数据能够反映智能办公场景下待治理文件的主要类型和主题结构。",
        "同一主题下的文档在关键词分布和低维语义空间中具有相似性，可用向量相似度刻画主题接近程度。",
        "标题、正文、表格字段与 OCR 文本均可能包含有效主题信息，但不同字段的信息量和可靠性不同。",
        "对于类别边界模糊或最高类别优势不足的样本，不强制唯一归类，而是标记为多类待判别或无法归类。",
        "金额、审批、合同、采购、药品、专利、截止时间等信号能够反映文件复核必要性和紧急程度。",
        "数据集4给出的资源约束在一个处理周期内固定，人工复核耗时可由文本长度、风险等级和文件复杂度近似估计。",
        "OCR 结果可能存在误识别，但作为补充字段总体有助于降低图片型文件的信息缺失。",
    ]
    for i, text in enumerate(assumptions, start=1):
        add(f"假设{i}：{text}")
    add("")
    add("## 四、定义与符号说明")
    add("")
    add_md_table(
        lines,
        ["符号", "含义"],
        [
            ["d_i", "第 i 个文档或记录"],
            ["T_i", "文档 d_i 的综合分析文本"],
            ["x_i", "文档 d_i 的 TF-IDF 向量"],
            ["z_i", "降维后的文档向量"],
            ["K", "主题原型数量"],
            ["C_k", "第 k 个主题簇"],
            ["μ_k", "第 k 个主题原型中心"],
            ["s_ik", "文档 d_i 与主题 C_k 的综合相似度"],
            ["p_i", "文档 d_i 的分类置信度"],
            ["Δ_i", "最高相似度与次高相似度的间隔"],
            ["R_i", "错分风险得分"],
            ["U_i", "紧急程度得分"],
            ["N_i", "复核必要性得分"],
            ["P_i", "综合复核优先级得分"],
        ],
    )
    add("## 五、模型的建立与求解")
    add("")
    add("### 5.1 数据预处理与特征构建")
    add("")
    add(
        "本文首先建立文件清单，对每个文件分配统一编号 doc_id，并记录其所属数据集、文件路径、扩展名和文件名。随后根据文件格式分别调用解析模块：对 Word 文档提取正文、表格和内嵌结构文本；对 PDF 文档优先抽取文本，若正文不足则触发 OCR；对 Excel 文档提取工作表、表头和单元格文本，其中数据集3按行展开为独立匿名记录；对图片文件直接进行 OCR 识别。解析完成后统一输出 JSONL 文本库和索引表。"
    )
    add("")
    add_figure_md(lines, "图2  多源文件统一解析与特征构建流程", IMAGE_DIR / "图2_多源文件统一解析与特征构建流程.png")
    add("")
    add("当前解析后的记录规模如下表所示。")
    add("")
    add_md_table(lines, ["数据集", "记录数"], ctx["dataset_counts"])
    add("不同数据集的解析状态如下表所示。")
    add("")
    add_md_table(lines, ["数据集", "解析状态", "数量"], ctx["parse_status"])
    add(
        "从结果看，数据集1包含3396条历史记录，数据集2包含1001条半结构化记录，数据集3展开为3518条匿名记录，数据集4为1条资源约束表记录。除数据集2中11条记录为空外，其余记录均完成有效解析。"
    )
    add("")
    add_figure_md(lines, "图3  数据集样本规模与文件类型分布", IMAGE_DIR / "图3_数据集样本规模与文件类型分布.png")
    add("")
    add(
        "在特征构建阶段，本文将标题、正文、表格文本和 OCR 文本融合为综合分析文本，同时过滤网页导航、版权声明、URL、联系方式、重复行等噪声文本，并提取文本长度、金额、日期、政策、审批、合同、药品、专利等结构信号，为后续主题发现、分类判别和复核排序提供统一输入。"
    )
    add("")
    add("### 5.2 问题一的模型建立与求解")
    add("")
    add("#### 5.2.1 文本表示模型")
    add("")
    add(
        "问题一的目标是在缺乏人工类别标签的条件下，从历史真实文件中发现稳定主题结构。本文采用 TF-IDF 方法表示文档关键词分布，其基本形式为："
    )
    add("")
    add("tfidf(t,d)=tf(t,d)·log(N/(1+n_t))")
    add("")
    add(
        "其中，t 为词项，d 为文档，N 为文档总数，n_t 为包含词项 t 的文档数。TF-IDF 能够降低普遍出现的通用词权重，突出对主题区分更有价值的关键词。由于 TF-IDF 向量维度较高且稀疏，进一步采用 TruncatedSVD 将其压缩到低维语义空间，从而减少噪声并提高聚类稳定性。"
    )
    add("")
    add("#### 5.2.2 主题原型发现模型")
    add("")
    add(
        "在低维语义空间中，本文采用 MiniBatchKMeans 进行主题原型发现。设 z_i 为文档 d_i 的低维向量，μ_k 为第 k 个簇中心，则聚类目标为："
    )
    add("")
    add("min Σ_k Σ_{z_i∈C_k} ||z_i-μ_k||²")
    add("")
    add(
        "MiniBatchKMeans 每次使用小批量样本更新聚类中心，适合处理本题中规模较大的文档集合。聚类后，每个簇被视为一个细粒度主题原型，簇内 TF-IDF 平均权重最高的词作为主题关键词，距离簇中心最近的样本作为代表文档。"
    )
    add("")
    add("#### 5.2.3 k 值消融实验")
    add("")
    add(
        "主题原型数量 K 直接影响主题体系的细粒度和下游分类稳定性。若 K 过小，主题表达过粗，难以刻画业务差异；若 K 过大，主题碎片化严重，会增加多类待判别样本和人工复核压力。本文比较 k=90、120、160、200、240、288 六组方案，结果如下。"
    )
    add("")
    add("需要说明的是，下表用于选择主题原型数，采用的是固定 k 方案下的基础边界判别策略；在确定 k=160 后，本文又对问题二边界样本进行了单独优化，最终分类结果见 5.3 节。")
    add("")
    add_md_table(
        lines,
        ["k", "轮廓系数", "主题数", "基础唯一归类", "基础多类待判别", "基础无法归类", "基础高优先级"],
        ctx["k_rows"],
    )
    add(
        "从表中可见，k=288 的轮廓系数最高，但多类待判别样本和高优先级复核样本明显增加，说明主题体系过于碎片化；k=90 下游较稳定，但主题细分不足。综合轮廓系数、主题粒度、下游分类可判别性和人工复核成本，本文选择 k=160 作为主题原型数。当前数据集1共3396条记录，其中3133条参与主题发现，覆盖率为0.923，特征数为4000，嵌入维度为50，轮廓系数为0.2916。"
    )
    add("")
    add("#### 5.2.4 主题族归并")
    add("")
    add(
        "聚类得到的是细粒度主题原型，不直接等同于最终业务主题类别。为避免将“表格、报告、论文”等文体形式误作为主题内容，本文进一步依据主题关键词、代表文档标题和领域规则进行主题族归并，将细粒度主题映射到教育科研与学术文献、财政金融与宏观经济、政府治理与公共管理、企业投资与房地产、科技专利与标准规范、医药卫生与药品、资源环境与城市建设等内容主题族。当前主题原型的主要归并结果如下。"
    )
    add("")
    add_md_table(lines, ["主题族", "细粒度主题原型数"], ctx["topic_family_counts"])
    add_figure_md(lines, "图4  数据集1主题发现结果分布", IMAGE_DIR / "图4_数据集1主题发现结果分布.png")
    add("")
    add("### 5.3 问题二的模型建立与求解")
    add("")
    add("#### 5.3.1 主题原型归类模型")
    add("")
    add(
        "问题二需要将数据集2和数据集3的新流入数据归入问题一建立的主题体系。本文构建基于主题原型的字段加权相似度模型。对于新文档 d_i，分别计算其与各主题原型 C_k 的余弦相似度，并结合关键词覆盖率得到综合得分："
    )
    add("")
    add("s_ik = α·cos(z_i, μ_k) + β·q_ik")
    add("")
    add(
        "其中 q_ik 表示文档关键词与主题词典的重合得分，α 和 β 分别控制语义相似度与关键词解释证据的权重。对于数据集2这类字段残缺的半结构化记录，模型对标题、正文片段、表格文本和 OCR 文本分别打分，再按字段信息量进行加权融合；缺失字段不参与加权，避免因字段缺失直接造成样本丢弃。"
    )
    add("")
    add("#### 5.3.2 置信度和边界样本识别")
    add("")
    add("为避免模型对模糊样本过度自信，本文设置最高得分阈值和类别间隔阈值。置信度定义为：")
    add("")
    add("p_i = exp(s_i1) / Σ_k exp(s_ik)")
    add("")
    add("类别间隔定义为最高得分与次高得分的差：")
    add("")
    add("Δ_i = s_i1 - s_i2")
    add("")
    add(
        "若最高得分低于阈值，则标记为无法归类；若最高得分与次高得分差距过小，且无法通过同主题族证据或领域规则消歧，则标记为多类待判别；若规则证据明确或竞争主题属于同一主题族，则输出唯一归类并保留复核原因。该策略使模型能够主动识别不确定样本，并将其交由问题三的复核模型进一步处理。"
    )
    add("")
    if ctx.get("boundary_rows"):
        add("在固定 k=160 后，本文进一步检查多类待判别样本来源。结果显示，基础方案中的多类样本主要由 `score_margin < 0.06` 触发，其中一部分属于同一主题原型家族内部的细碎原型竞争，另一部分虽跨原型家族但具有明确内容规则证据。因此，本文加入同原型家族消歧和规则证据消歧：同一主题原型家族内部竞争不再直接判为多类；对于得分较高、间隔不极小且规则证据充分的轻微跨类竞争，输出唯一类别并保留 `resolved_small_margin` 等复核原因。优化前后对比如下。")
        add("")
        add_md_table(lines, ["指标", "优化前", "优化后", "变化"], ctx["boundary_rows"])
        add("")
    add("")
    add("#### 5.3.3 分类结果")
    add("")
    add(f"当前共对数据集2和数据集3的{ctx['status_total']}条新流入记录进行归类，结果如下。")
    add("")
    add_md_table(lines, ["数据集", "分类状态", "数量"], ctx["class_status"])
    add(f"合计来看，唯一归类{ctx['assigned']}条，多类待判别{ctx['multi_class']}条，无法归类{ctx['unclassifiable']}条。主要主题分布如下。")
    add("")
    add_md_table(lines, ["数据集", "主题族", "数量"], ctx["top_topics"])
    add("")
    add_figure_md(lines, "图5  新流入数据分类结果与风险等级分布", IMAGE_DIR / "图5_新流入数据分类结果与风险等级分布.png")
    add("")
    add(
        "结果显示，数据集3中教育科研与学术文献类占比较高，这与匿名记录中存在大量高校、课程、论文、研究、模型、项目、教务和院校相关文本有关；数据集2中政府治理与公共管理类占比较高，主要来自政府报告、会议程序、年度工作总结和政策部署类文本。对于综合内容待判别类和多类待判别样本，模型不强行归档，而是保留候选类别、置信度、证据关键词和边界原因，进入后续人工复核环节。"
    )
    add("")
    add("#### 5.3.4 评价指标")
    add("")
    add(
        "本文从可分性、置信度、可解释性和迁移适用性四个维度评价归类结果。可分性由唯一归类、多类待判别和无法归类比例衡量；置信度由最高类别概率 p_i 衡量；可解释性由关键词覆盖率和证据词数量衡量；迁移适用性由新数据主题分布与历史主题体系之间的差异衡量。综合评价指标可写为："
    )
    add("")
    add("E_i = λ1 p_i + λ2 Q_i + λ3(1-B_i) + λ4 M_i")
    add("")
    add("其中 Q_i 为关键词覆盖率，B_i 为边界风险，M_i 为字段完整度，λ_j 为评价权重。")
    add("")
    add("### 5.4 问题三的模型建立与求解")
    add("")
    add("#### 5.4.1 复核优先级指标构建")
    add("")
    add(
        "问题三要求从紧急程度、错分风险和复核必要性三个方面对文件进行等级划分。本文将问题二输出的分类状态、置信度、类别间隔、字段覆盖率和解析状态转化为错分风险 R_i；将紧急、截止、限期、立即、时限等关键词及日期表达转化为紧急程度 U_i；将金额、预算、合同、采购、审批、审计、药品、专利等敏感信号转化为复核必要性 N_i。"
    )
    add("")
    add("#### 5.4.2 AHP 权重确定")
    add("")
    add("构造三指标判断矩阵：")
    add("")
    add("A = [[1, a12, a13], [1/a12, 1, a23], [1/a13, 1/a23, 1]]")
    add("")
    add("通过最大特征值对应的归一化特征向量得到权重，并进行一致性检验：")
    add("")
    add("CI=(λmax-n)/(n-1),  CR=CI/RI")
    add("")
    add("当 CR<0.1 时，认为判断矩阵一致性可接受。综合复核优先级得分为：")
    add("")
    add("P_i = w_R R_i + w_U U_i + w_N N_i")
    add("")
    add("#### 5.4.3 复核等级划分结果")
    add("")
    add("根据综合优先级得分，将文件划分为 high、medium、low 三个等级。当前结果如下。")
    add("")
    add_md_table(
        lines,
        ["数据集", "优先级", "数量", "平均优先级", "平均错分风险", "平均紧急程度", "平均复核必要性"],
        ctx["priority_rows"],
    )
    add(
        f"合计来看，高优先级文件{ctx['high_total']}条，中优先级{ctx['medium_total']}条，低优先级{ctx['low_total']}条。高优先级文件主要由低置信度、边界模糊、字段缺失或含有资金、审批等强敏感信号的样本构成，应优先纳入人工复核。"
    )
    add("")
    add("#### 5.4.4 资源约束下的处理策略")
    add("")
    add("设 h_i 为文件 i 的预计复核耗时，H_s 为场景 s 可用人工小时，L_s 为场景 s 可复核文件数量上限，x_i∈{0,1} 表示是否人工复核，则资源分配问题可表示为：")
    add("")
    add("max Σ_i P_i x_i")
    add("")
    add("s.t.  Σ_i h_i x_i ≤ H_s,  Σ_i x_i ≤ L_s")
    add("")
    add(
        "本文采用贪心策略求解：首先选择 high 和 medium 文件作为候选复核集，再按单位复核时间优先级得分排序，在人工小时和数量约束内依次分配；低优先级文件在自动归档容量允许时进入自动归档队列。三种资源场景下结果如下。"
    )
    add("")
    add_md_table(
        lines,
        ["场景", "人工小时", "人工上限", "自动归档上限", "人工复核数", "高优先级复核数", "中优先级复核数"],
        ctx["resource_rows"],
    )
    add("")
    add_figure_md(lines, "图6  复核优先级划分与资源约束场景比较", IMAGE_DIR / "图6_复核优先级划分与资源约束场景比较.png")
    add("")
    add(
        "可以看出，随着人工小时和人工复核上限从 S1 增加到 S3，被纳入人工复核的文件数量逐步增加。S1 资源较紧，应优先覆盖最高风险样本；S2 在保证大多数高优先级文件复核的同时，可少量处理中优先级样本；S3 资源最充足，能够覆盖全部高优先级文件并进一步处理部分中优先级样本。因此，在实际治理中可根据复核人力资源选择相应策略。"
    )
    add("")
    add("## 六、模型的评价及优化")
    add("")
    add("### 6.1 模型优点")
    add("")
    pros = [
        "模型能够处理 Word、PDF、Excel、图片等多种文件格式，并通过 OCR 补充图片型和扫描型文件的信息。",
        "主题发现不依赖人工标签，适合题目给出的历史真实文件无标注场景。",
        "模型输出主题关键词、代表文档、置信度、边界状态和证据词，具有较强可解释性。",
        "问题一、二、三形成闭环，问题二的不确定性能够自然进入问题三的复核优先级模型。",
        "资源约束模型能够给出不同人工能力场景下的处理建议，具有实际办公场景落地价值。",
    ]
    for i, text in enumerate(pros, start=1):
        add(f"（{i}）{text}")
    add("")
    add("### 6.2 模型不足")
    add("")
    cons = [
        "本文主模型基于 TF-IDF 和线性降维表示，对深层语义、长距离依赖和隐含语义关系的刻画有限。",
        "OCR 结果受图片清晰度、版面结构和识别模型影响，可能引入少量噪声。",
        "主题族归并仍包含规则设计和少量人工审计经验，后续可通过更多人工反馈持续校准。",
        "多类待判别样本仍占一定比例，说明部分文件确实存在主题交叉或文本信息不足，需要人机协同处理。",
    ]
    for i, text in enumerate(cons, start=1):
        add(f"（{i}）{text}")
    add("")
    add("### 6.3 模型优化与推广")
    add("")
    add(
        "后续可在现有主题原型框架上引入中文预训练语言模型生成语义嵌入，以增强深层语义识别能力；在人机协同复核过程中积累人工确认、改类和驳回记录，进一步训练有监督分类器；同时，可引入 RAG 检索增强机制，为复核人员自动提供相似历史文件、主题词典和分类依据。本文已经设计了可视化复核工作台，能够读取分类结果、复核优先级和资源分配表，支持人工确认、改类、无法归类和操作留痕，可作为模型落地应用的基础。"
    )
    add("")
    add("## 参考文献")
    add("")
    refs = [
        "Kadhim A. I. Survey on supervised machine learning techniques for automatic text classification[J]. Artificial Intelligence Review, 2019, 52(3): 273-292.",
        "Abdallah A., Eberharter D., Pfister Z., et al. A survey of recent approaches to form understanding in scanned documents[J]. Artificial Intelligence Review, 2024, 57: 342.",
        "Wu X., Xiao L., Sun Y., et al. A survey of human-in-the-loop for machine learning[J]. Future Generation Computer Systems, 2022, 135: 364-381.",
        "Mosqueira-Rey E., Hernández-Pereira E., Alonso-Ríos D., et al. Human-in-the-loop machine learning: a state of the art[J]. Artificial Intelligence Review, 2023, 56: 3005-3054.",
        "Salton G., Buckley C. Term-weighting approaches in automatic text retrieval[J]. Information Processing & Management, 1988, 24(5): 513-523.",
        "Deerwester S., Dumais S. T., Furnas G. W., et al. Indexing by latent semantic analysis[J]. Journal of the American Society for Information Science, 1990, 41(6): 391-407.",
        "MacQueen J. Some methods for classification and analysis of multivariate observations[C]. Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability, 1967.",
        "Saaty T. L. The Analytic Hierarchy Process[M]. New York: McGraw-Hill, 1980.",
        "Pedregosa F., Varoquaux G., Gramfort A., et al. Scikit-learn: Machine Learning in Python[J]. Journal of Machine Learning Research, 2011, 12: 2825-2830.",
    ]
    for i, ref in enumerate(refs, start=1):
        add(f"[{i}] {ref}")
    add("")
    add("## 附录")
    add("")
    add("### 附录A 核心程序说明")
    add("")
    add_md_table(
        lines,
        ["脚本", "作用"],
        [
            ["00_build_manifest.py", "构建文件清单"],
            ["01_parse_documents.py", "多格式解析与 OCR"],
            ["02_build_feature_table.py", "构建文档特征表"],
            ["03_discover_topics.py", "历史文档主题发现"],
            ["05_refine_topic_families.py", "主题族归并"],
            ["04_classify_documents.py", "数据集2/3归类"],
            ["06_review_prioritization.py", "复核优先级与资源分配"],
        ],
    )
    add("### 附录B 主要输出文件")
    add("")
    add_md_table(
        lines,
        ["文件", "含义"],
        [
            ["data/parsed_documents.jsonl", "解析后的文档文本"],
            ["data/document_features.csv", "文档特征表"],
            ["outputs/topic_discovery/topic_summary_refined.csv", "问题一主题体系"],
            ["outputs/document_classification/classification_results.csv", "问题二分类结果"],
            ["outputs/document_classification/review_queue.csv", "待复核样本"],
            ["outputs/review_prioritization/review_priority_results.csv", "问题三优先级结果"],
            ["outputs/review_prioritization/resource_plan.csv", "资源场景汇总"],
        ],
    )
    return "\n".join(lines)


def add_figure_md(lines: list[str], caption: str, path: Path) -> None:
    if path.exists():
        lines.append(f"![{caption}]({path.as_posix()})")
        lines.append("")


def build_docx(ctx: dict[str, object], md: str, out_path: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)

    styles = doc.styles
    styles["Normal"].font.name = "宋体"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    styles["Normal"].font.size = Pt(10.5)

    title = "基于可解释主题原型与风险优先级的多源异构文件智能治理模型"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.bold = True
    run.font.name = "黑体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
    run.font.size = Pt(16)

    add_heading(doc, "摘  要", level=1)
    for para in md.split("## 摘要\n\n", 1)[1].split("\n\n**关键词：**", 1)[0].split("\n"):
        if para.strip():
            add_paragraph(doc, para.strip())
    add_paragraph(doc, "关键词：多源异构文件；TF-IDF；MiniBatchKMeans；主题原型；AHP；人工复核", first_line=False)
    doc.add_page_break()

    add_heading(doc, "目  录", level=1)
    for item in ["一、问题重述", "二、问题分析", "三、模型假设", "四、定义与符号说明", "五、模型的建立与求解", "六、模型的评价及优化", "参考文献", "附录"]:
        add_paragraph(doc, item, first_line=False)
    doc.add_page_break()

    add_heading(doc, "一、问题重述", level=1)
    for text in [
        "随着数字化办公的持续推进，企事业单位在日常运行中积累了大量格式多样、结构复杂、内容来源不一的文件数据。这些文件既包括 Word、PDF、Excel、图片等真实原始文件，也包括在流转、汇总和调用过程中形成的半结构化记录。不同文件在文本长度、表达方式、结构层次、业务属性和完整程度上差异明显，传统依赖人工阅读、判断和归档的处理方式容易出现效率低、标准不统一、误分类风险高和后续检索困难等问题。",
        "题目要求基于附件数据建立智能文件治理模型。数据集1为历史真实文件数据，需要从中挖掘能反映文件内容与属性的关键信息，并形成具有解释性的主题分类体系；数据集2和数据集3为后续流入的新数据，其中既有半结构化记录，也有匿名原始文件，需要根据问题一形成的主题体系进行归类，并设计评价指标衡量归类结果的合理性、可解释性和迁移适用性；数据集4给出业务规则和资源约束，需要在考虑紧急程度、错分风险和复核必要性的基础上，对待处理文件进行高、中、低等级划分，并确定是否需要人工复核及复核优先顺序。",
        "因此，本文需要解决的核心并非单一文本分类问题，而是一个从异构文件解析、历史主题发现、新数据迁移归类到人机协同复核和资源约束优化的完整文件治理问题。",
    ]:
        add_paragraph(doc, text)

    add_heading(doc, "二、问题分析", level=1)
    add_heading(doc, "2.1 数据特点分析", level=2)
    add_paragraph(doc, "附件数据呈现出明显的多源异构特征。首先，文件格式不统一，既包含可直接抽取文本的 Office 文档，也包含需要 OCR 处理的图片或扫描类材料；其次，结构完整程度不一，数据集1主要为历史真实文件，数据集2包含标题、正文片段、来源等半结构化字段，数据集3则需要按匿名记录逐条处理；最后，文件内容存在交叉主题，同一文档可能同时具有政府治理、财政金融、教育科研、资源环境等多个领域特征，因此模型不宜对边界样本进行过度自信的唯一判定。")
    add_figure_docx(doc, IMAGE_DIR / "B题算法流程学术框架图.png", "图1  B题算法流程学术框架图")
    add_heading(doc, "2.2 三个问题之间的逻辑关系", level=2)
    add_paragraph(doc, "问题一是基础层，目标是在无人工标签的历史文件中形成稳定主题原型和主题词典；问题二是迁移层，利用问题一的主题原型对新流入数据进行归类，并输出置信度、候选类别和边界状态；问题三是治理层，进一步把问题二的不确定性和业务敏感信号转化为复核优先级，在资源约束下给出处理策略。")

    add_heading(doc, "三、模型假设", level=1)
    for text in [
        "假设1：题目提供的数据能够反映智能办公场景下待治理文件的主要类型和主题结构。",
        "假设2：同一主题下的文档在关键词分布和低维语义空间中具有相似性，可用向量相似度刻画主题接近程度。",
        "假设3：标题、正文、表格字段与 OCR 文本均可能包含有效主题信息，但不同字段的信息量和可靠性不同。",
        "假设4：对于类别边界模糊或最高类别优势不足的样本，不强制唯一归类，而是标记为多类待判别或无法归类。",
        "假设5：金额、审批、合同、采购、药品、专利、截止时间等信号能够反映文件复核必要性和紧急程度。",
        "假设6：数据集4给出的资源约束在一个处理周期内固定，人工复核耗时可由文本长度、风险等级和文件复杂度近似估计。",
        "假设7：OCR 结果可能存在误识别，但作为补充字段总体有助于降低图片型文件的信息缺失。",
    ]:
        add_paragraph(doc, text, first_line=False)

    add_heading(doc, "四、定义与符号说明", level=1)
    add_table_docx(
        doc,
        ["符号", "含义"],
        [
            ["d_i", "第 i 个文档或记录"],
            ["T_i", "文档 d_i 的综合分析文本"],
            ["x_i", "文档 d_i 的 TF-IDF 向量"],
            ["z_i", "降维后的文档向量"],
            ["K", "主题原型数量"],
            ["C_k", "第 k 个主题簇"],
            ["μ_k", "第 k 个主题原型中心"],
            ["s_ik", "文档 d_i 与主题 C_k 的综合相似度"],
            ["p_i", "文档 d_i 的分类置信度"],
            ["Δ_i", "最高相似度与次高相似度的间隔"],
            ["P_i", "综合复核优先级得分"],
        ],
    )

    add_heading(doc, "五、模型的建立与求解", level=1)
    add_heading(doc, "5.1 数据预处理与特征构建", level=2)
    add_paragraph(doc, "本文首先建立文件清单，对每个文件分配统一编号 doc_id，并记录其所属数据集、文件路径、扩展名和文件名。随后根据文件格式分别调用解析模块：对 Word 文档提取正文、表格和内嵌结构文本；对 PDF 文档优先抽取文本，若正文不足则触发 OCR；对 Excel 文档提取工作表、表头和单元格文本，其中数据集3按行展开为独立匿名记录；对图片文件直接进行 OCR 识别。解析完成后统一输出 JSONL 文本库和索引表。")
    add_figure_docx(doc, IMAGE_DIR / "图2_多源文件统一解析与特征构建流程.png", "图2  多源文件统一解析与特征构建流程")
    add_table_docx(doc, ["数据集", "记录数"], ctx["dataset_counts"])
    add_table_docx(doc, ["数据集", "解析状态", "数量"], ctx["parse_status"])
    add_paragraph(doc, "在特征构建阶段，本文将标题、正文、表格文本和 OCR 文本融合为综合分析文本，同时过滤网页导航、版权声明、URL、联系方式、重复行等噪声文本，并提取文本长度、金额、日期、政策、审批、合同、药品、专利等结构信号。")
    add_figure_docx(doc, IMAGE_DIR / "图3_数据集样本规模与文件类型分布.png", "图3  数据集样本规模与文件类型分布")

    add_heading(doc, "5.2 问题一的模型建立与求解", level=2)
    for text in [
        "问题一的目标是在缺乏人工类别标签的条件下，从历史真实文件中发现稳定主题结构。本文采用 TF-IDF 方法表示文档关键词分布，其基本形式为：tfidf(t,d)=tf(t,d)·log(N/(1+n_t))。其中 t 为词项，d 为文档，N 为文档总数，n_t 为包含词项 t 的文档数。",
        "由于 TF-IDF 向量维度较高且稀疏，进一步采用 TruncatedSVD 将其压缩到低维语义空间，从而减少噪声并提高聚类稳定性。在低维语义空间中，本文采用 MiniBatchKMeans 进行主题原型发现，其目标函数为 min Σ_k Σ_{z_i∈C_k} ||z_i-μ_k||²。",
        "主题原型数量 K 直接影响主题体系的细粒度和下游分类稳定性。若 K 过小，主题表达过粗；若 K 过大，主题碎片化严重，会增加多类待判别样本和人工复核压力。",
    ]:
        add_paragraph(doc, text)
    add_paragraph(doc, "下表用于选择主题原型数，采用的是固定 k 方案下的基础边界判别策略；在确定 k=160 后，本文又对问题二边界样本进行了单独优化，最终分类结果见后文。")
    add_table_docx(doc, ["k", "轮廓系数", "主题数", "基础唯一归类", "基础多类待判别", "基础无法归类", "基础高优先级"], ctx["k_rows"])
    add_paragraph(doc, "综合轮廓系数、主题粒度、下游分类可判别性和人工复核成本，本文选择 k=160 作为主题原型数。当前数据集1共3396条记录，其中3133条参与主题发现，覆盖率为0.923，特征数为4000，嵌入维度为50，轮廓系数为0.2916。")
    add_table_docx(doc, ["主题族", "细粒度主题原型数"], ctx["topic_family_counts"])
    add_figure_docx(doc, IMAGE_DIR / "图4_数据集1主题发现结果分布.png", "图4  数据集1主题发现结果分布")

    add_heading(doc, "5.3 问题二的模型建立与求解", level=2)
    for text in [
        "问题二需要将数据集2和数据集3的新流入数据归入问题一建立的主题体系。本文构建基于主题原型的字段加权相似度模型。对于新文档 d_i，分别计算其与各主题原型 C_k 的余弦相似度，并结合关键词覆盖率得到综合得分：s_ik = α·cos(z_i, μ_k) + β·q_ik。",
        "对于数据集2这类字段残缺的半结构化记录，模型对标题、正文片段、表格文本和 OCR 文本分别打分，再按字段信息量进行加权融合；缺失字段不参与加权，避免因字段缺失直接造成样本丢弃。",
        "为避免模型对模糊样本过度自信，本文设置最高得分阈值和类别间隔阈值。若最高得分低于阈值，则标记为无法归类；若最高得分与次高得分差距过小，且无法通过同主题族证据或领域规则消歧，则标记为多类待判别；若规则证据明确或竞争主题属于同一主题族，则输出唯一归类并保留复核原因。",
    ]:
        add_paragraph(doc, text)
    if ctx.get("boundary_rows"):
        add_paragraph(doc, "在固定 k=160 后，本文进一步检查多类待判别样本来源。基础方案中的多类样本主要由 score_margin<0.06 触发，其中一部分属于同一主题原型家族内部的细碎原型竞争，另一部分虽跨原型家族但具有明确内容规则证据。因此，本文加入同原型家族消歧和规则证据消歧：同一主题原型家族内部竞争不再直接判为多类；对于得分较高、间隔不极小且规则证据充分的轻微跨类竞争，输出唯一类别并保留 resolved_small_margin 等复核原因。")
        add_table_docx(doc, ["指标", "优化前", "优化后", "变化"], ctx["boundary_rows"])
    add_table_docx(doc, ["数据集", "分类状态", "数量"], ctx["class_status"])
    add_table_docx(doc, ["数据集", "主题族", "数量"], ctx["top_topics"])
    add_figure_docx(doc, IMAGE_DIR / "图5_新流入数据分类结果与风险等级分布.png", "图5  新流入数据分类结果与风险等级分布")
    add_paragraph(doc, f"合计来看，唯一归类{ctx['assigned']}条，多类待判别{ctx['multi_class']}条，无法归类{ctx['unclassifiable']}条。模型保留候选类别、置信度、证据关键词和边界原因，便于进入后续人工复核环节。")

    add_heading(doc, "5.4 问题三的模型建立与求解", level=2)
    for text in [
        "问题三要求从紧急程度、错分风险和复核必要性三个方面对文件进行等级划分。本文将问题二输出的分类状态、置信度、类别间隔、字段覆盖率和解析状态转化为错分风险 R_i；将紧急、截止、限期、立即、时限等关键词及日期表达转化为紧急程度 U_i；将金额、预算、合同、采购、审批、审计、药品、专利等敏感信号转化为复核必要性 N_i。",
        "本文采用 AHP 构建三指标判断矩阵，通过最大特征值对应的归一化特征向量得到权重，并进行一致性检验。当 CR<0.1 时，认为判断矩阵一致性可接受。综合复核优先级得分为 P_i = w_R R_i + w_U U_i + w_N N_i。",
    ]:
        add_paragraph(doc, text)
    add_table_docx(doc, ["数据集", "优先级", "数量", "平均优先级", "平均错分风险", "平均紧急程度", "平均复核必要性"], ctx["priority_rows"])
    add_paragraph(doc, f"合计来看，高优先级文件{ctx['high_total']}条，中优先级{ctx['medium_total']}条，低优先级{ctx['low_total']}条。高优先级文件主要由低置信度、边界模糊、字段缺失或含有资金、审批等强敏感信号的样本构成。")
    add_paragraph(doc, "在资源约束下，本文首先选择 high 和 medium 文件作为候选复核集，再按单位复核时间优先级得分排序，在人工小时和数量约束内依次分配；低优先级文件在自动归档容量允许时进入自动归档队列。")
    add_table_docx(doc, ["场景", "人工小时", "人工上限", "自动归档上限", "人工复核数", "高优先级复核数", "中优先级复核数"], ctx["resource_rows"])
    add_figure_docx(doc, IMAGE_DIR / "图6_复核优先级划分与资源约束场景比较.png", "图6  复核优先级划分与资源约束场景比较")

    add_heading(doc, "六、模型的评价及优化", level=1)
    add_heading(doc, "6.1 模型优点", level=2)
    for text in [
        "模型能够处理 Word、PDF、Excel、图片等多种文件格式，并通过 OCR 补充图片型和扫描型文件的信息。",
        "主题发现不依赖人工标签，适合题目给出的历史真实文件无标注场景。",
        "模型输出主题关键词、代表文档、置信度、边界状态和证据词，具有较强可解释性。",
        "问题一、二、三形成闭环，问题二的不确定性能够自然进入问题三的复核优先级模型。",
        "资源约束模型能够给出不同人工能力场景下的处理建议，具有实际办公场景落地价值。",
    ]:
        add_paragraph(doc, text, first_line=False)
    add_heading(doc, "6.2 模型不足与推广", level=2)
    add_paragraph(doc, "本文主模型基于 TF-IDF 和线性降维表示，对深层语义、长距离依赖和隐含语义关系的刻画有限；OCR 结果受图片清晰度、版面结构和识别模型影响，可能引入少量噪声；主题族归并仍包含规则设计和少量人工审计经验，后续可通过更多人工反馈持续校准。后续可引入中文预训练语言模型生成语义嵌入，或在人机协同复核过程中积累人工修正标签，进一步训练有监督分类器。")
    add_paragraph(doc, "为验证模型在实际文件治理流程中的可用性，本文进一步设计了可视化复核工作台。该工作台读取模型输出的分类结果、复核优先级和资源分配表，提供总览统计、分类结果筛选、待复核队列、文件详情抽屉和人工改类操作。前端界面不改变模型结果，而是作为人机协同复核机制的落地载体。")

    add_heading(doc, "参考文献", level=1)
    refs = [
        "Kadhim A. I. Survey on supervised machine learning techniques for automatic text classification[J]. Artificial Intelligence Review, 2019, 52(3): 273-292.",
        "Abdallah A., Eberharter D., Pfister Z., et al. A survey of recent approaches to form understanding in scanned documents[J]. Artificial Intelligence Review, 2024, 57: 342.",
        "Wu X., Xiao L., Sun Y., et al. A survey of human-in-the-loop for machine learning[J]. Future Generation Computer Systems, 2022, 135: 364-381.",
        "Salton G., Buckley C. Term-weighting approaches in automatic text retrieval[J]. Information Processing & Management, 1988, 24(5): 513-523.",
        "Deerwester S., Dumais S. T., Furnas G. W., et al. Indexing by latent semantic analysis[J]. Journal of the American Society for Information Science, 1990, 41(6): 391-407.",
        "MacQueen J. Some methods for classification and analysis of multivariate observations[C]. Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability, 1967.",
        "Saaty T. L. The Analytic Hierarchy Process[M]. New York: McGraw-Hill, 1980.",
        "Pedregosa F., Varoquaux G., Gramfort A., et al. Scikit-learn: Machine Learning in Python[J]. Journal of Machine Learning Research, 2011, 12: 2825-2830.",
    ]
    for i, ref in enumerate(refs, start=1):
        add_paragraph(doc, f"[{i}] {ref}", first_line=False)

    add_heading(doc, "附录", level=1)
    add_heading(doc, "附录A 核心程序说明", level=2)
    add_table_docx(
        doc,
        ["脚本", "作用"],
        [
            ["00_build_manifest.py", "构建文件清单"],
            ["01_parse_documents.py", "多格式解析与 OCR"],
            ["02_build_feature_table.py", "构建文档特征表"],
            ["03_discover_topics.py", "历史文档主题发现"],
            ["05_refine_topic_families.py", "主题族归并"],
            ["04_classify_documents.py", "数据集2/3归类"],
            ["06_review_prioritization.py", "复核优先级与资源分配"],
        ],
    )

    doc.save(out_path)


def main() -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    ctx = build_context()
    md = build_md(ctx)
    md_path = PAPER_DIR / "数维杯B题论文初稿.md"
    docx_path = PAPER_DIR / "数维杯B题论文初稿.docx"
    md_path.write_text(md, encoding="utf-8")
    build_docx(ctx, md, docx_path)
    print(f"markdown -> {md_path}")
    print(f"docx -> {docx_path}")


if __name__ == "__main__":
    main()
