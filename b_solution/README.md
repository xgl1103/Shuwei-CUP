# B题代码项目

## 队友接手

完整项目说明、目录结构、核心文件作用、运行顺序和最终结果位置见：

```text
PROJECT_HANDOFF.md
```

本项目用于完成数维杯 B 题的代码实现，优先使用 Python。

## 环境

```powershell
conda activate shuweibei
```

## 目录

- `src/`：核心代码
- `scripts/`：可直接运行的脚本
- `data/`：数据索引或中间文件
- `outputs/`：结果输出
- `notes/`：过程记录与实验说明

当前解析层已支持图片 OCR 和扫描 PDF OCR，前提是环境中已安装 `rapidocr_onnxruntime` 与 `pymupdf`。

数据集 3 的匿名原始文件数据为 Excel 记录表，解析时会按行展开为独立文档，
例如 `dataset3:N00001`、`dataset3:N00002`，而不是把整张 Excel 当成一个文件分类。

## 当前主方案

当前已固定采用 `k=160` 作为问题一的细粒度主题原型数，并已跑通问题一、问题二、问题三主链路：

```text
01_parse_documents.py
02_build_feature_table.py
03_discover_topics.py
05_refine_topic_families.py
04_classify_documents.py
06_review_prioritization.py
```

当前关键结果：

```text
问题一：cluster_count = 160，selected = 3133，coverage = 0.923
问题二：assigned = 3159，multi_class = 1294，unclassifiable = 66
问题三：high = 164，medium = 1932，low = 2423
```

主题数选择说明见：

- `notes/05_k消融实验与推荐方案.md`
- `outputs/experiments/k_ablation_summary.csv`
- `outputs/experiments/k_topic_size_summary.csv`
