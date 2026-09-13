# 数维杯 B 题：多源异构文件智能治理模型

本仓库保存 2026 年第十一届数维杯大学生数学建模挑战赛（春季赛）B 题的可公开复现材料。项目围绕多源异构文件治理，构建“统一解析与 OCR、主题原型发现、新文件归类、人工复核优先级与资源约束分配”的完整建模链路。

## 方法概览

```text
多格式文件解析与 OCR
  -> 文本降噪与特征构建
  -> TF-IDF + TruncatedSVD + MiniBatchKMeans 主题原型发现
  -> 主题族归并与业务命名
  -> 字段加权相似度分类与边界状态判别
  -> 错分风险、复核必要性、紧急程度评分
  -> AHP 优先级与资源约束分配
  -> 人工核查工作台反馈
```

固定主方案的主要结果如下：

- 问题一：dataset1 共 3396 条记录，3133 条参与主题发现，覆盖率 0.9226；采用 `k=160`，轮廓系数为 0.2916。
- 问题二：4519 条新文件中，`assigned=3159`、`multi_class=1294`、`unclassifiable=66`。
- 问题三：高、中、低复核优先级数量分别为 `164 / 1932 / 2423`；AHP 权重为 `0.5396 / 0.2970 / 0.1634`，一致性比例 `CR=0.0079`。

## 目录说明

- `b_solution/src/`：核心模型模块，包括解析、主题发现、分类、风险优先级和资源分配。
- `b_solution/scripts/`：完整运行流程与论文图表生成脚本。
- `b_solution/dashboard/`：本地人工核查与可视化工作台。
- `b_solution/paper/`：论文生成脚本。
- `docs/notes/`：建模过程、实验与人工核查说明。
- `docs/figures/`：正式框架图、数据图和机制图。
- `赛题资料/`：B 题题目、数据集说明与 AI 工具使用规定。
- `论文/`：B 题论文终稿与初稿。

## 赛题数据获取

完整原始数据集（数据集 1~4，约 1.6 GB）体积超出仓库承载范围，已通过 **Release 附件** 分发：

> 前往 [Releases](../../releases) 页面下载 `B题数据集.zip` 及其分卷 `B题数据集.z01` ~ `B题数据集.z03`（共 4 个分卷）。

下载后请把全部分卷放在同一目录，解压 `B题数据集.zip`（分卷压缩包，解压时会自动读取 `.z01`~`.z03`），得到：

```text
B题数据集/数据集/
├── 数据集1：历史真实文件数据/          # 3396 个文件（多格式历史档案）
├── 数据集2：后续流入的半结构化记录数据/  # 1001 个文件（半结构化记录）
├── 数据集3：后续流入的匿名原始文件数据.xlsx
└── 数据集4：业务规则与资源约束表.xlsx
```

将该 `B题数据集/` 目录放到仓库根目录，即可按下方流程复现全部结果。

## 环境与复现

```powershell
conda env create -f b_solution/environment.yml
conda activate shuweibei
```

原始赛题数据体积较大，请先按上文「赛题数据获取」从 Release 下载并解压到仓库根目录，得到 `B题数据集/数据集/` 后，按顺序运行：

```powershell
python b_solution/scripts/00_build_manifest.py
python b_solution/scripts/01_parse_documents.py
python b_solution/scripts/02_build_feature_table.py
python b_solution/scripts/03_discover_topics.py
python b_solution/scripts/05_refine_topic_families.py
python b_solution/scripts/04_classify_documents.py
python b_solution/scripts/06_review_prioritization.py
```

启动本地人工核查工作台：

```powershell
cd b_solution
python dashboard_server.py
```

浏览器访问 `http://127.0.0.1:5178/dashboard/index.html`。该平台读取本地 `b_solution/data/` 与 `b_solution/outputs/` 中的运行结果，因此需要先执行模型流程或恢复相应结果文件。

## 数据与 AI 使用说明

- 原始数据体积较大，通过 Release 附件分发，不进入 Git 版本库；解析中间数据与运行输出亦不纳入版本库。
- 赛题题目、数据集说明、AI 工具使用规定与论文正文已纳入仓库 `赛题资料/` 与 `论文/`。
- 前端展示、本地服务和启动脚本中的 AI 辅助工程性片段已在 [AI 辅助代码说明](docs/AI辅助代码说明.md) 中披露；核心建模算法不在该标注范围内。
- 更详细的建模过程与审计记录见 [docs/notes](docs/notes)。
