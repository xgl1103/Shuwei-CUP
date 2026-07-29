# 数维杯 B 题项目交接说明

本文档面向接手本项目的队友，目标是让队友快速理解：项目目录、核心文件作用、运行顺序、最终结果位置、论文材料位置，以及后续继续开发时应该改哪里。

## 1. 项目定位

本项目用于完成数维杯 B 题“多源异构文件智能治理”建模、实验、可视化和论文写作。当前主线不是单纯做黑盒分类，而是：

```text
多源文件解析/OCR增强
    -> 问题一：历史文件主题发现，建立 160 个细粒度主题原型
    -> 问题二：新文件映射到主题原型，并归并为业务大类和子类
    -> 问题三：结合风险、复核必要性、紧急程度进行人工复核优先级和资源分配
    -> 人工核查平台抽查边界样本，支撑论文中的可解释性与合理性说明
```

当前最终固定方案：

| 项目 | 当前结果 |
|---|---:|
| 问题一历史数据集 | dataset1 |
| dataset1 原始文档数 | 3396 |
| 参与主题发现文档数 | 3133 |
| 覆盖率 | 0.9226 |
| 主题原型数 k | 160 |
| 轮廓系数 | 0.2916 |
| 问题二新文件总数 | 4519 |
| 问题二 assigned | 3159 |
| 问题二 multi_class | 1294 |
| 问题二 unclassifiable | 66 |
| 问题三 high / medium / low | 164 / 1932 / 2423 |

最终归档结果优先看：

```text
E:\Code\数维杯\b_solution\outputs\final_results_2026-05-10
```

## 2. 环境说明

推荐使用项目已定义的 Conda 环境。

```powershell
cd E:\Code\数维杯
conda env create -f b_solution\environment.yml
conda activate shuweibei
```

如果环境已经存在：

```powershell
conda activate shuweibei
```

核心依赖在 `environment.yml` 中，包括：

| 依赖 | 作用 |
|---|---|
| pandas / numpy | 表格处理、数值计算 |
| scikit-learn | TF-IDF、SVD、MiniBatchKMeans、轮廓系数 |
| jieba | 中文分词 |
| openpyxl | Excel 读取 |
| python-docx | Word 文档解析 |
| pypdf / pymupdf | PDF 文本解析和页面处理 |
| rapidocr_onnxruntime | 图片 OCR 和扫描件 OCR |
| matplotlib / seaborn | 论文图表生成 |

项目包配置在 `pyproject.toml` 中，包名为 `bdoc`，源码目录为 `src/`。

## 3. 顶层目录说明

项目根目录：

```text
E:\Code\数维杯
```

重要目录如下。

| 路径 | 作用 | 接手建议 |
|---|---|---|
| `b_solution/` | B 题主项目，代码、结果、论文都在这里 | 主要工作目录 |
| `B题数据集/` | 赛题原始数据集 | 不建议改动，只读使用 |
| `2026年第十一届数维杯大学生数学建模挑战赛（春季赛）赛题/` | 赛题说明、格式要求等 | 写论文和检查题意时使用 |
| `论文图片/` | AI 生成或人工整理的论文插图 | 论文插图替换时使用 |
| `B题论文_基于可解释主题原型与风险优先级的多源异构文件智能治理模型.docx` | 根目录下的论文导出版 | 可能不是最新，优先看 `b_solution/paper/` |

## 4. b_solution 顶层文件和目录

| 文件/目录 | 作用 |
|---|---|
| `README.md` | 项目简要入口，记录主链路和当前核心结果 |
| `PROJECT_HANDOFF.md` | 本交接文档，给队友快速上手使用 |
| `environment.yml` | Conda 环境依赖 |
| `pyproject.toml` | Python 包配置，声明 `src/` 为源码包目录 |
| `.gitignore` | Git 忽略规则 |
| `dashboard_server.py` | 本地可视化工作台服务，支持打开原始文件 |
| `src/` | 核心算法模块 |
| `scripts/` | 可直接运行的流程脚本 |
| `data/` | 解析结果、中间特征表、OCR 缓存等 |
| `outputs/` | 问题一二三结果、实验结果、论文图表、最终归档 |
| `notes/` | 建模记录、论文框架、人工核查记录、实验说明 |
| `dashboard/` | 前端人工核查与可视化平台 |
| `paper/` | 论文草稿、导出脚本、docx/pdf 输出 |
| `chapters/` | 论文分章节草稿或中间文本 |
| `plan/` | 论文写作和任务拆解计划 |
| `backups/` | 备份文件 |
| `tmp/` | 临时文件 |
| `__pycache__/` | Python 缓存，可忽略 |

## 5. 主流程运行顺序

当前完整流程分为 0 到 6。通常不需要全部重跑。若只复现最终结果，重点是 03、05、04、06。

### 5.1 完整重跑顺序

```powershell
cd E:\Code\数维杯
conda activate shuweibei

python b_solution\scripts\00_build_manifest.py
python b_solution\scripts\01_parse_documents.py
python b_solution\scripts\02_build_feature_table.py
python b_solution\scripts\03_discover_topics.py
python b_solution\scripts\05_refine_topic_families.py
python b_solution\scripts\04_classify_documents.py
python b_solution\scripts\06_review_prioritization.py
```

### 5.2 通常只需要重跑的顺序

如果没有改解析逻辑，只是修改主题、分类、风险策略，使用：

```powershell
cd E:\Code\数维杯
conda activate shuweibei

python b_solution\scripts\03_discover_topics.py
python b_solution\scripts\05_refine_topic_families.py
python b_solution\scripts\04_classify_documents.py
python b_solution\scripts\06_review_prioritization.py
```

原因：

| 步骤 | 是否经常重跑 | 说明 |
|---|---|---|
| 00 | 否 | 只有原始数据路径或文件清单变了才重跑 |
| 01 | 否 | 解析/OCR耗时，只有解析策略变了才重跑 |
| 02 | 否 | 特征表来自解析结果，通常不频繁改 |
| 03 | 是 | 问题一主题发现，k 值和主题体系变化会影响后续 |
| 05 | 是 | 主题族归并和业务命名修正 |
| 04 | 是 | 问题二新文件分类，依赖问题一和 05 |
| 06 | 是 | 问题三风险复核和资源分配，依赖问题二 |

## 6. scripts 目录文件说明

路径：

```text
E:\Code\数维杯\b_solution\scripts
```

| 脚本 | 作用 | 主要输入 | 主要输出 |
|---|---|---|---|
| `00_build_manifest.py` | 扫描原始数据集，生成统一文件清单 | `B题数据集/` | `data/file_manifest.csv` |
| `01_parse_documents.py` | 解析 Word、PDF、Excel、图片等多源文件，必要时 OCR | `data/file_manifest.csv` | `data/parsed_documents.jsonl`、`data/parsed_documents_index.csv` |
| `02_build_feature_table.py` | 从解析文本中构造文档级特征表 | `data/parsed_documents.jsonl` | `data/document_features.csv` |
| `03_discover_topics.py` | 问题一：对 dataset1 做主题发现，生成主题原型 | `data/parsed_documents.jsonl` | `outputs/topic_discovery/*` |
| `05_refine_topic_families.py` | 对问题一主题做主题族归并、业务命名和细分修正 | `outputs/topic_discovery/topic_assignments.csv`、`topic_summary.csv` | `topic_summary_refined.csv`、`topic_family_map.csv`、`topic_family_summary.csv` |
| `04_classify_documents.py` | 问题二：对 dataset2、dataset3 新文件归类 | 解析结果、问题一主题、05 的精修主题 | `outputs/document_classification/*` |
| `06_review_prioritization.py` | 问题三：AHP 风险复核优先级和资源约束分配 | `classification_results.csv`、资源约束数据 | `outputs/review_prioritization/*` |
| `generate_paper_figures.py` | 生成部分论文图表或图表素材 | 输出结果 CSV/JSON | `outputs/paper_figures/*` |
| `generate_numeric_paper_figures.py` | 生成准确数据驱动的论文图表 | 输出结果 CSV/JSON | `outputs/paper_figures/code_generated/*` |
| `postprocess_image2_figures.py` | 后处理 AI 生成图片，统一风格/尺寸/边距 | `outputs/paper_figures_image2/` 或论文图片目录 | 后处理图片 |
| `fix_overall_route_figure.py` | 修正或替换总体技术路线图 | 论文图片 | 修正后的路线图 |

## 7. src/bdoc 核心模块说明

路径：

```text
E:\Code\数维杯\b_solution\src\bdoc
```

| 模块 | 作用 |
|---|---|
| `__init__.py` | Python 包初始化 |
| `manifest.py` | 构造文件清单，统一记录数据集、文件名、路径、后缀等元信息 |
| `parser.py` | 多源文件解析核心，包括 Word、PDF、Excel、图片、OCR、dataset3 按行展开 |
| `features.py` | 从解析结果构造基础特征，例如标题、正文、时间、长度、解析状态等 |
| `topic_discovery.py` | 问题一核心算法：中文分词、TF-IDF、SVD、MiniBatchKMeans、轮廓系数评估 |
| `topic_families.py` | 主题族规则、业务大类映射、领域关键词组织 |
| `topic_refinement.py` | 主题名称精修、原型主题到业务表达的转换 |
| `topic_splitting.py` | 对过大的业务类继续细分，例如教育科研类的子类拆分 |
| `classification.py` | 问题二分类核心：新文件到主题原型/业务类的匹配、置信度、边界状态 |
| `review_prioritization.py` | 问题三核心：复核必要性、错分风险、紧急程度、AHP 权重和资源分配 |

## 8. data 目录说明

路径：

```text
E:\Code\数维杯\b_solution\data
```

| 文件/目录 | 作用 | 是否可重建 |
|---|---|---|
| `file_manifest.csv` | 原始文件清单，由 00 生成 | 可重建 |
| `parsed_documents.jsonl` | 当前主解析结果，每行一个文档记录 | 可重建，但重跑 01 成本较高 |
| `parsed_documents_index.csv` | 解析结果索引，便于快速查看解析状态 | 可重建 |
| `document_features.csv` | 文档特征表，由 02 生成 | 可重建 |
| `parsed_documents_new.jsonl` | 解析结果的备用/新版本 | 谨慎使用，需确认时间 |
| `parsed_documents_ocr_full*` | OCR 完整版本解析备份 | 备用材料 |
| `parsed_documents_ocr_sample*` | OCR 抽样测试结果 | 实验材料 |
| `parsed_documents_restored_noocr.jsonl` | 无 OCR 版本或恢复版本 | 备份材料 |
| `ocr_cache/` | OCR 缓存，避免重复识别图片 | 可重建但耗时 |

注意：dataset3 是 Excel 记录表形式，解析时已经按行展开为独立文档，例如 `dataset3:N00001`。因此问题二的 4519 条新文件不是简单的原始文件个数，而是解析展开后的文档记录数。

## 9. outputs 目录说明

路径：

```text
E:\Code\数维杯\b_solution\outputs
```

### 9.1 问题一：topic_discovery

```text
outputs/topic_discovery
```

| 文件 | 作用 |
|---|---|
| `topic_meta.json` | 问题一元信息，包含 dataset、selected、coverage、k、silhouette 等 |
| `topic_assignments.csv` | dataset1 每篇文档对应的主题原型编号 |
| `topic_summary.csv` | 原始主题摘要和关键词 |
| `topic_summary_refined.csv` | 经 05 精修后的主题摘要，论文和问题二优先使用 |
| `topic_family_map.csv` | 主题原型到主题族/业务大类的映射 |
| `topic_family_summary.csv` | 主题族汇总 |
| `topic_selection.csv` | 参与主题发现的文档选择信息 |
| `topic_model_selection_extended.csv` | k 值选择或扩展实验结果 |

### 9.2 问题二：document_classification

```text
outputs/document_classification
```

| 文件 | 作用 |
|---|---|
| `classification_results.csv` | 问题二主结果，每条新文档的分类、置信度、候选主题、证据词、边界状态 |
| `classification_summary.csv` | 分类结果汇总 |
| `classification_meta.json` | 分类参数和总体统计 |
| `review_queue.csv` | 建议人工复核队列 |
| `topic_dictionary.csv` | 问题二使用的主题词典/分类词典 |

关键字段：

| 字段 | 含义 |
|---|---|
| `doc_id` | 文档唯一编号 |
| `dataset` | 来源数据集 |
| `topic_cluster_id` | 问题一主题原型编号 |
| `topic_prototype_name` | 问题一原型主题名称 |
| `raw_topic_name` | 原始聚类主题名称 |
| `topic_broad_name` / `topic_parent_name` | 业务大类 |
| `topic_name` | 业务子类 |
| `classification_status` | `assigned`、`multi_class`、`unclassifiable` |
| `confidence_score` | 分类置信度 |
| `score_margin` | 第一候选和第二候选之间的分差 |
| `candidate_topics` | 候选类别和得分 |
| `evidence_terms` | 分类证据词 |

论文叙事中要强调：问题一的 160 个主题是“原型层”，问题二的业务大类和子类是“应用层”。问题二不是脱离问题一重新分类，而是先映射到主题原型，再做主题族归并和业务命名扩展。

### 9.3 问题三：review_prioritization

```text
outputs/review_prioritization
```

| 文件 | 作用 |
|---|---|
| `review_priority_results.csv` | 每条文档的风险、复核必要性、紧急程度、综合优先级 |
| `review_priority_summary.csv` | high / medium / low 汇总 |
| `resource_plan.csv` | S1/S2/S3 资源场景约束 |
| `resource_allocations.csv` | 各资源场景下的文档分配方案 |
| `review_priority_meta.json` | AHP 权重、一致性检验、参数记录 |

当前 AHP 权重：

| 指标 | 权重 |
|---|---:|
| 错分风险 `misclassification_risk` | 0.5396 |
| 复核必要性 `review_necessity` | 0.2970 |
| 紧急程度 `urgency` | 0.1634 |

一致性比例：

```text
CR = 0.0079
```

### 9.4 最终归档：final_results_2026-05-10

```text
outputs/final_results_2026-05-10
```

这是当前论文、答辩、队友复现时应优先引用的最终结果目录。它把问题一、二、三和人工核查材料复制归档，避免后续中间实验覆盖主结果。

| 文件/目录 | 作用 |
|---|---|
| `final_result_manifest.json` | 最终结果机器可读清单，包含核心指标和文件列表 |
| `README.md` | 最终结果说明 |
| `topic_discovery/` | 问题一最终结果 |
| `document_classification/` | 问题二最终结果 |
| `review_prioritization/` | 问题三最终结果 |
| `manual_review/` | 人工核查抽样和日志归档 |

### 9.5 实验与图表目录

| 路径 | 作用 |
|---|---|
| `outputs/experiments/` | k 值消融、噪声规避、分类策略实验等 |
| `outputs/topic_discovery_k4_12/` | k=4 到 k=12 的早期主题数实验 |
| `outputs/paper_figures/` | 论文图表输出 |
| `outputs/paper_figures/code_generated/` | 代码生成的准确数据图，论文中优先使用 |
| `outputs/paper_figures_image2/` | AI 生成或后处理的风格化图 |

代码生成的主要论文图：

| 文件 | 作用 |
|---|---|
| `06_k_ablation_sensitivity.png/svg` | k 值敏感性/消融实验图 |
| `08_problem2_classification_structure.png/svg` | 问题二分类结果结构图 |
| `09_high_frequency_topics.png/svg` | 高频主题分布图 |
| `12_ahp_weights_consistency.png/svg` | AHP 权重和一致性检验图 |
| `13_review_priority_distribution.png/svg` | 复核优先级分布图 |
| `14_resource_constraint_allocation.png/svg` | 资源约束分配结果图 |

## 10. notes 目录说明

路径：

```text
E:\Code\数维杯\b_solution\notes
```

| 文件/目录 | 作用 |
|---|---|
| `00_总体建模方法.md` | 总体算法思路和三问关系 |
| `01_可视化界面实现说明.md` | 可视化平台需求、框架、字段和页面说明 |
| `02_主题族优化说明.md` | 问题一主题族归并和优化说明 |
| `03_问题三解决方案.md` | 问题三复核优先级、AHP、资源分配方案 |
| `04_模型审计与优化记录.md` | 模型审计、问题修复、阶段性优化记录 |
| `05_k消融实验与推荐方案.md` | k 值实验、k=160 方案依据、消融讨论 |
| `06_论文写作框架.md` | 当前论文框架主文档，写论文优先参考 |
| `manual_review/` | 人工核查样本、人工日志、核查报告 |

人工核查相关文件：

| 文件 | 作用 |
|---|---|
| `manual_review/problem2_k160_boundary_audit_samples.csv` | 问题二边界样本抽查清单 |
| `manual_review/problem2_k160_boundary_audit_report.md` | 边界样本审计报告 |
| `manual_review/review_logs_2026-05-09_combined_latest_merged.csv` | 人工核查日志合并结果 |
| `manual_review/review_logs_2026-05-09_combined_summary.md` | 人工核查日志汇总说明 |

## 11. dashboard 可视化平台

路径：

```text
E:\Code\数维杯\b_solution\dashboard
```

| 文件 | 作用 |
|---|---|
| `index.html` | 前端页面入口 |
| `app.js` | 前端数据读取、页面状态、人工核查交互逻辑 |
| `styles.css` | 页面样式 |
| `README.md` | 仪表盘说明，当前可能存在编码显示问题，优先参考本交接文档 |
| `start-dashboard.ps1` | PowerShell 启动脚本 |

启动方式：

```powershell
cd E:\Code\数维杯\b_solution
conda activate shuweibei
python dashboard_server.py
```

浏览器访问：

```text
http://127.0.0.1:5178/dashboard/index.html
```

人工核查页：

```text
http://127.0.0.1:5178/dashboard/index.html?view=audit
```

注意事项：

1. 如果只是用 `python -m http.server`，页面能看，但无法调用本地接口打开原始文件。
2. 要打开原始文件，必须用 `dashboard_server.py`。
3. 平台中的人工操作默认记录在浏览器 localStorage，不会自动写回后端 CSV。
4. 人工核查完成后需要导出 JSON 日志，再用脚本或人工流程合并到 `notes/manual_review/`。

## 12. paper 论文目录

路径：

```text
E:\Code\数维杯\b_solution\paper
```

| 文件 | 作用 |
|---|---|
| `数维杯B题论文正式草稿_v1.md` | 当前论文 Markdown 主稿 |
| `数维杯B题论文正式草稿_v1.docx` | 当前论文 Word 导出版 |
| `数维杯B题论文正式草稿_v1.preview.pdf` | 当前论文 PDF 预览 |
| `generate_paper_draft.py` | 从框架、结果和图片生成/更新论文草稿的脚本 |
| `数维杯B题论文初稿.md/docx/pdf` | 早期初稿，通常只作备份参考 |

论文写作优先参考：

```text
b_solution\notes\06_论文写作框架.md
b_solution\paper\数维杯B题论文正式草稿_v1.md
b_solution\outputs\final_results_2026-05-10
b_solution\outputs\paper_figures\code_generated
E:\Code\数维杯\论文图片
```

已知论文图位置：

| 图类型 | 推荐路径 |
|---|---|
| 代码生成的真实数据图 | `b_solution\outputs\paper_figures\code_generated` |
| 总体技术路线图 | `E:\Code\数维杯\论文图片\ig_0b7b8a4fbe8888be0169ffb501dd0c819185427a3222141692.png` |
| 人工核查平台截图 | `E:\Code\数维杯\论文图片\人工核查平台界面截图.png` |

## 13. plan 和 chapters 目录

| 目录 | 作用 |
|---|---|
| `plan/project-overview.md` | 项目概览 |
| `plan/outline.md` | 写作提纲 |
| `plan/chapter-architecture.md` | 章节结构规划 |
| `plan/progress.md` | 进度记录 |
| `plan/task-packets/` | 可分配给其他 agent 或队友的任务包 |
| `chapters/` | 论文章节草稿或分块文本 |

这些目录主要用于论文组织和协作，不是主程序运行依赖。

## 14. 核心算法和参数

### 14.1 问题一：主题发现

主要算法：

```text
中文分词 -> TF-IDF -> TruncatedSVD 降维 -> MiniBatchKMeans 聚类 -> 轮廓系数评价
```

当前关键参数位于：

```text
b_solution\scripts\03_discover_topics.py
```

默认参数：

| 参数 | 当前值 | 作用 |
|---|---:|---|
| `--dataset` | `dataset1` | 用历史文件做主题发现 |
| `--min-text-length` | 80 | 文本过短不参与主题发现 |
| `--min-clusters` | 160 | 最小 k |
| `--max-clusters` | 160 | 最大 k，当前固定为 160 |
| `--max-features` | 4000 | TF-IDF 最大特征数 |
| `--svd-components` | 50 | SVD 降维维度 |
| `--max-text-chars` | 6000 | 每篇文档最多参与建模的文本长度 |
| `--kmeans-n-init` | 8 | KMeans 初始化次数 |
| `--silhouette-sample-size` | 1000 | 轮廓系数采样规模 |

如果要重新试 k 值，改运行参数，不一定要改源码。例如：

```powershell
python b_solution\scripts\03_discover_topics.py --min-clusters 120 --max-clusters 200
```

如果 `min-clusters=max-clusters=160`，则表示固定使用 k=160。

### 14.2 问题二：新文件归类

主要逻辑：

```text
新文件文本特征
    -> 映射到问题一主题原型
    -> 结合主题关键词、代表文档、领域词证据
    -> 输出业务大类 topic_broad_name / topic_parent_name
    -> 输出业务子类 topic_name
    -> 根据置信度和分差标记 assigned / multi_class / unclassifiable
```

关键参数位于：

```text
b_solution\scripts\04_classify_documents.py
```

| 参数 | 当前值 | 作用 |
|---|---:|---|
| `--datasets` | `dataset2 dataset3` | 问题二要分类的新数据集 |
| `--min-text-length` | 40 | 文本过短会降低置信度或进入无法归类 |
| `--max-text-chars` | 6000 | 分类时每篇文档最多使用文本长度 |
| `--max-features` | 4000 | TF-IDF 特征数 |
| `--svd-components` | 50 | SVD 维度 |
| `--keyword-weight` | 0.10 | 关键词证据权重 |
| `--confidence-threshold` | 0.45 | 低于该置信度更可能进入边界状态 |
| `--margin-threshold` | 0.08 | 第一和第二候选分差过小会标记为多类边界 |

### 14.3 问题三：复核优先级和资源分配

主要逻辑：

```text
错分风险 + 复核必要性 + 紧急程度
    -> AHP 权重
    -> 综合优先级分数
    -> high / medium / low
    -> S1/S2/S3 资源约束下的复核分配
```

当前权重来自 AHP：

```text
misclassification_risk = 0.5396
review_necessity      = 0.2970
urgency               = 0.1634
CR                    = 0.0079
```

## 15. 后续开发时应该改哪里

| 目标 | 优先修改位置 |
|---|---|
| 改文件解析/OCR策略 | `src/bdoc/parser.py`、`scripts/01_parse_documents.py` |
| 改问题一 k 值或主题发现参数 | `scripts/03_discover_topics.py` 或命令行参数 |
| 改主题大类/领域词规则 | `src/bdoc/topic_families.py` |
| 改主题名称精修 | `src/bdoc/topic_refinement.py` |
| 改教育科研等大类的细分类 | `src/bdoc/topic_splitting.py` |
| 改问题二分类阈值和边界策略 | `src/bdoc/classification.py`、`scripts/04_classify_documents.py` |
| 改问题三风险指标/AHP/资源分配 | `src/bdoc/review_prioritization.py`、`scripts/06_review_prioritization.py` |
| 改可视化页面 | `dashboard/app.js`、`dashboard/styles.css`、`dashboard/index.html` |
| 改论文框架 | `notes/06_论文写作框架.md` |
| 改论文正文 | `paper/数维杯B题论文正式草稿_v1.md` |
| 改论文数据图 | `scripts/generate_numeric_paper_figures.py` |

## 16. 常见问题

### 16.1 k=160 是什么意思？

k=160 表示问题一把 dataset1 的历史文档聚成 160 个细粒度主题原型。它不是最终展示给用户的 160 个业务目录，而是后续问题二归类的“原型库”。

### 16.2 问题一和问题二类别名称为什么不完全一样？

因为两者层级不同：

```text
问题一：160 个细粒度主题原型
    -> 主题族归并
问题二：业务大类
    -> 细分类修正
问题二：业务子类
```

因此问题二中的“教育科研与学术文献类”“政府治理与公共管理类”等，是对问题一主题原型的业务化归并表达，不是另起一套分类体系。

### 16.3 人工核查平台会自动改后端结果吗？

不会。平台操作默认写入浏览器 localStorage。需要点击导出日志，得到 JSON 后再合并到 `notes/manual_review/` 或最终归档目录中。

### 16.4 只想看最终答案，应该打开哪里？

优先看：

```text
b_solution\outputs\final_results_2026-05-10\final_result_manifest.json
b_solution\outputs\final_results_2026-05-10\README.md
b_solution\paper\数维杯B题论文正式草稿_v1.md
```

### 16.5 哪些文件可以忽略？

通常可以忽略：

```text
__pycache__/
tmp/
dashboard/browser_profile*/
dashboard/.playwright*/
outputs 中非 final_results_2026-05-10 的旧实验目录
paper 中早期初稿文件
```

但不要删除它们，除非确认不再需要复现旧实验或截图。

## 17. 推荐接手顺序

新队友建议按以下顺序阅读：

1. `PROJECT_HANDOFF.md`：先建立项目地图。
2. `README.md`：看当前固定主方案。
3. `notes/06_论文写作框架.md`：理解论文叙事。
4. `outputs/final_results_2026-05-10/final_result_manifest.json`：核对最终数值。
5. `scripts/03_discover_topics.py`、`04_classify_documents.py`、`06_review_prioritization.py`：理解三问主程序。
6. `src/bdoc/topic_discovery.py`、`classification.py`、`review_prioritization.py`：理解核心算法。
7. `dashboard/index.html` 或启动工作台：查看结果展示和人工核查流程。

## 18. 当前最重要的交付物

| 类型 | 路径 |
|---|---|
| 项目交接文档 | `E:\Code\数维杯\b_solution\PROJECT_HANDOFF.md` |
| 最终结果归档 | `E:\Code\数维杯\b_solution\outputs\final_results_2026-05-10` |
| 论文框架 | `E:\Code\数维杯\b_solution\notes\06_论文写作框架.md` |
| 论文正式草稿 | `E:\Code\数维杯\b_solution\paper\数维杯B题论文正式草稿_v1.md` |
| 论文 Word | `E:\Code\数维杯\b_solution\paper\数维杯B题论文正式草稿_v1.docx` |
| 代码生成图表 | `E:\Code\数维杯\b_solution\outputs\paper_figures\code_generated` |
| 论文补充图片 | `E:\Code\数维杯\论文图片` |
| 可视化平台 | `E:\Code\数维杯\b_solution\dashboard` |

## 19. 交接结论

当前项目已经具备完整链路：

```text
原始数据 -> 文件解析 -> 主题发现 -> 主题族精修 -> 新文件分类 -> 复核优先级 -> 资源分配 -> 可视化核查 -> 论文草稿
```

后续队友接手时，主要工作不应再从零搭建流程，而应集中在：

1. 检查论文表达是否足够清楚，尤其是“问题一原型层”和“问题二应用层”的关系。
2. 补充或美化论文插图。
3. 根据人工核查日志补一段模型合理性和误差分析。
4. 若要继续优化分类，只改 `topic_families.py`、`topic_splitting.py`、`classification.py`，然后重跑 05、04、06。
