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

## 环境与复现

```powershell
conda env create -f b_solution/environment.yml
conda activate shuweibei
```

原始赛题数据不上传到仓库。取得授权数据后，请在仓库根目录创建如下目录：

```text
B题数据集/数据集/
```

随后按顺序运行：

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

- 原始数据、解析中间数据、运行输出、浏览器缓存和 Office 文档不纳入版本库。
- 前端展示、本地服务和启动脚本中的 AI 辅助工程性片段已在 [AI 辅助代码说明](docs/AI辅助代码说明.md) 中披露；核心建模算法不在该标注范围内。
- 更详细的建模过程与审计记录见 [docs/notes](docs/notes)。
