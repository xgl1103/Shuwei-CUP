# 问题二 k=160 边界优化后抽样核查报告

## 1. 当前总览

当前问题二主结果已经使用 `k=160` 主题原型，并完成边界优化。结果不是“强制所有文件唯一归类”，而是保留了 `assigned / multi_class / unclassifiable` 三种状态，便于后续人工复核。

| 指标 | 数量 |
|---|---:|
| assigned | 3159 |
| multi_class | 1294 |
| unclassifiable | 66 |

按数据集拆分：

| 数据集 | assigned | multi_class | unclassifiable |
|---|---:|---:|---:|
| dataset2 | 738 | 218 | 45 |
| dataset3 | 2421 | 1076 | 21 |

## 2. 高频主题分布

| 排名 | 数据集 | 主题 | 数量 |
|---:|---|---|---:|
| 1 | dataset3 | 教育科研与学术文献类 | 1714 |
| 2 | dataset2 | 政府治理与公共管理类 | 621 |
| 3 | dataset3 | 政府治理与公共管理类 | 546 |
| 4 | dataset3 | 综合内容待判别类 | 301 |
| 5 | dataset3 | 科技专利与标准规范类 | 259 |
| 6 | dataset3 | 资源环境与城市建设类 | 167 |
| 7 | dataset3 | 企业投资与房地产类 | 152 |
| 8 | dataset3 | 文化旅游与居民消费类 | 118 |
| 9 | dataset2 | 财政金融与宏观经济类 | 110 |
| 10 | dataset3 | 工业交通与能源通信类 | 65 |
| 11 | dataset3 | 农业农村与土地资源类 | 62 |
| 12 | dataset2 | 综合内容待判别类 | 53 |

## 3. 剩余 multi_class 分布

| 排名 | 数据集 | 主题 | 数量 |
|---:|---|---|---:|
| 1 | dataset3 | 教育科研与学术文献类 | 443 |
| 2 | dataset3 | 政府治理与公共管理类 | 245 |
| 3 | dataset2 | 政府治理与公共管理类 | 148 |
| 4 | dataset3 | 综合内容待判别类 | 97 |
| 5 | dataset3 | 科技专利与标准规范类 | 78 |
| 6 | dataset3 | 资源环境与城市建设类 | 69 |
| 7 | dataset3 | 文化旅游与居民消费类 | 36 |
| 8 | dataset3 | 企业投资与房地产类 | 27 |
| 9 | dataset2 | 财政金融与宏观经济类 | 21 |
| 10 | dataset3 | 人口就业与社会保障类 | 18 |
| 11 | dataset3 | 农业农村与土地资源类 | 18 |
| 12 | dataset3 | 工业交通与能源通信类 | 17 |

## 4. 抽样清单

已生成可人工填写的 CSV：

```text
notes/manual_review/problem2_k160_boundary_audit_samples.csv
```

该文件已加入 `content_snippet`、`topic_split_reason`、`review_reason`、`manual_decision`、`manual_note` 等字段，可直接作为人工核查平台的导入数据。

抽样桶命中总数为 246；由于部分文档同时属于多个抽样桶，CSV 已按 `doc_id` 去重为 221 行。重叠桶保存在 `audit_bucket` 中，用分号分隔；`primary_audit_bucket` 表示该行的主抽样来源。

| 抽样桶 | 数量 | 用途 |
|---|---:|---|
| unclassifiable_all | 66 | 全量核查无法归类样本 |
| education_dataset3_assigned | 30 | 核查 dataset3 教育科研类是否过度泛化 |
| education_dataset3_multiclass | 30 | 核查教育科研边界样本 |
| government_dataset2_assigned | 25 | 核查 dataset2 政府治理类是否合理 |
| government_dataset3_multiclass | 25 | 核查政府治理边界样本 |
| fallback_comprehensive_nonempty | 35 | 核查综合待判别中非空样本是否还能细分 |
| multiclass_highrisk | 35 | 优先核查高风险多类样本 |

## 5. 初步核查结论

1. `dataset3` 的教育科研类数量确实偏高，但不是完全错误。样本中大量文本来自清华、南大、课程、研究生、学位、校园活动、院校介绍等内容，归为教育科研类总体合理。

2. 教育科研类中存在少量过度泛化样本。例如 `dataset3:N03239` 只是文学叙述中出现“上了大学”，模型仍归入“院校概况类”。这类样本通常同时具有 `low_score / small_margin / low_confidence` 标记，后续应进入人工核查，而不应作为高置信自动归档。

3. `dataset2` 政府治理类总体合理。虽然很多标题只是 `F0145.txt` 这类文件名，但正文片段显示其内容是政府工作报告、人大会议、财政经济运行、政策执行等文本，例如 `dataset2:F0145`、`dataset2:F0861`。因此这里主要是展示字段不足，不是模型方向错误。

4. `dataset3` 的部分 `multi_class` 是真实混合文本，不适合强制唯一归类。例如 `dataset3:N02303` 同时包含国家统计局政府网站检查和镇域公共空间建设内容，`dataset3:N02772` 同时包含鲁迅文学片段和住房政策修改片段。保留为 `multi_class` 更稳妥。

5. `unclassifiable` 共 66 条，其中一部分是空解析、极短文本、表格残片或相似度为 0 的样本。它们更适合进入“无法归类/人工补充”队列，而不是继续放宽阈值硬分。

## 6. 后续优化建议

短期不建议再盲目压低阈值来减少 `multi_class` 或 `unclassifiable`。当前更值得做的是：

- 人工平台优先展示 `content_snippet`，不要只展示标题或文件名。
- 高风险样本优先审核 `education_dataset3_assigned`、`fallback_comprehensive_nonempty`、`multiclass_highrisk`。
- 对人工确认为误分的样本，回填 `manual_decision` 和 `manual_note`，再统计误分类型。
- 若教育科研类误分率明显偏高，再新增“弱教育触发规则”：只有单个弱词如“大学”且缺少学校、课程、科研、学位、教师、学生等支持词时，不自动归入教育科研类。

## 7. 论文可用表述

在固定 `k=160` 后，本文进一步对问题二的边界样本进行分层抽样核查。核查结果表明，无法归类样本占比较低，主要由空解析、极短文本或低相似度文本导致；剩余多类样本集中在教育科研、政府治理、综合待判别等语义边界较近的领域。对于混合内容和低置信样本，本文保留 `multi_class` 与 `unclassifiable` 状态作为人工复核入口，而不是强制唯一归类，从而保证分类体系的稳健性和可解释性。
