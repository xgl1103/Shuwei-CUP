# 人工核查日志合并处理结果（2026-05-09 两批合并）

## 1. 文件来源

原始导出日志：

```text
D:\edge downlodge\review_logs_2026-05-09.json
D:\edge downlodge\review_logs_2026-05-09 (1).json
```

归档副本：

```text
notes/manual_review/review_logs_2026-05-09.raw.json
notes/manual_review/review_logs_2026-05-09_batch2.raw.json
```

合并去重结果：

```text
notes/manual_review/review_logs_2026-05-09_combined_latest_merged.csv
```

## 2. 处理规则

- 两批原始日志共 110 次操作记录。
- 按 `doc_id` 保留最新一次人工结论。
- 合并去重后得到 61 个独立核查样本。
- 第二批日志已经覆盖了第一批的大部分样本，因此合并后的独立样本数与第二批一致。
- `confirmed/changed` 视为可评价分类样本。
- `noise/uncertain/unclassifiable` 不直接计入分类正确率。
- 若可评价样本中 `final_topic != original_topic`，记为 `category_adjusted`；否则记为 `category_confirmed`。

## 3. 人工状态统计

| 人工状态 | 数量 |
|---|---:|
| confirmed | 45 |
| noise | 11 |
| uncertain | 4 |
| unclassifiable | 1 |

## 4. 有效结果统计

| 有效结果 | 数量 |
|---|---:|
| category_confirmed | 24 |
| category_adjusted | 21 |
| noise | 11 |
| uncertain | 4 |
| unclassifiable | 1 |

## 5. 抽样来源分布

| 抽样来源 | 数量 |
|---|---:|
| unclassifiable_all | 26 |
| education_dataset3_assigned | 13 |
| government_dataset2_assigned | 9 |
| government_dataset3_multiclass | 8 |
| fallback_comprehensive_nonempty | 5 |

## 6. 数据集分布

| 数据集 | 数量 |
|---|---:|
| dataset3 | 34 |
| dataset2 | 27 |

## 7. 人工最终类别 Top

| 人工最终类别 | 数量 |
|---|---:|
| 院校概况类 | 15 |
| 噪声无效 | 11 |
| 党政会议类 | 10 |
| 暂不确定 | 4 |
| 校园活动类 | 3 |
| 网站门户类 | 3 |
| 行政审批类 | 2 |
| 招考录用类 | 2 |
| 文化活动类 | 2 |
| 价格指数类 | 1 |
| 生态环境类 | 1 |
| 科研创新类 | 1 |
| 统计调查类 | 1 |
| 无法归类 | 1 |
| 社会保障类 | 1 |

## 8. 关键结论

- 合并后独立核查样本数：61。
- 可评价分类样本数：45。
- 人工认为原类别可接受的样本数：24。
- 人工调整类别的样本数：21。
- 标记为噪声、存疑或无法归类的样本数：16。
- 从抽样来源看，该批样本不再只集中于无法归类样本，也覆盖教育科研、政府治理、多类边界和综合待判别样本，适合用于论文中的人工抽样核查表。
- 45 个可评价样本中，24 个保持原类别、21 个需要调整，说明当前模型具备可用分类基础，但仍应保留人工复核平台处理边界样本和细分类修正。

## 9. 类别调整样例

| doc_id | 模型/原类别 | 人工最终类别 | 抽样来源 |
|---|---|---|---|
| dataset3:N01401 | 综合待判别类 | 网站门户类 | fallback_comprehensive_nonempty |
| dataset3:N02573 | 综合待判别类 | 社会保障类 | fallback_comprehensive_nonempty |
| dataset3:N01512 | 综合待判别类 | 文化活动类 | fallback_comprehensive_nonempty |
| dataset3:N00927 | 综合待判别类 | 文化活动类 | fallback_comprehensive_nonempty |
| dataset3:N03082 | 行政审批类 | 网站门户类 | government_dataset3_multiclass |
| dataset3:N00102 | 党政会议类 | 行政审批类 | government_dataset3_multiclass |
| dataset3:N00307 | 党政会议类 | 行政审批类 | government_dataset3_multiclass |
| dataset3:N02485 | 行政审批类 | 招考录用类 | government_dataset3_multiclass |
| dataset2:F0861 | 党政会议类 | 财政税收类 | government_dataset2_assigned |
| dataset2:F0145 | 行政审批类 | 党政会议类 | government_dataset2_assigned |
| dataset3:N03181 | 院校概况类 | 能源电力类 | education_dataset3_assigned |
| dataset3:N00681 | 综合待判别类 | 院校概况类 | unclassifiable_all |

## 10. 噪声、存疑或无法归类样例

| doc_id | 人工状态 | 模型/原类别 | 抽样来源 |
|---|---|---|---|
| dataset3:N02553 | unclassifiable | 统计调查类 | government_dataset3_multiclass |
| dataset2:F0928 | noise | 综合待判别类 | unclassifiable_all |
| dataset2:F0807 | uncertain | 综合待判别类 | unclassifiable_all |
| dataset2:F0787 | noise | 综合待判别类 | unclassifiable_all |
| dataset2:F0780 | uncertain | 综合待判别类 | unclassifiable_all |
| dataset2:F0737 | uncertain | 综合待判别类 | unclassifiable_all |
| dataset2:F0651 | noise | 综合待判别类 | unclassifiable_all |
| dataset2:F0598 | uncertain | 综合待判别类 | unclassifiable_all |
| dataset2:F0555 | noise | 综合待判别类 | unclassifiable_all |
| dataset2:F0538 | noise | 综合待判别类 | unclassifiable_all |
| dataset2:F0481 | noise | 综合待判别类 | unclassifiable_all |
| dataset2:F0398 | noise | 综合待判别类 | unclassifiable_all |

## 11. 论文可用表述

```text
本文进一步基于人工核查工作台对问题二分类结果进行抽样校验。两批导出日志共包含 110 次人工处理记录，按文档编号保留最新结论后得到 61 个独立核查样本。样本覆盖无法归类、教育科研、政府治理、多类边界和综合待判别等场景。其中，可评价分类样本 45 个，人工确认原类别可接受 24 个，人工调整到更合适类别 21 个；另有 16 个样本被标记为噪声、存疑或无法归类。该结果说明，模型分类结果具有一定可用性和可解释性，但对于边界样本、弱文本样本和细分类样本，仍需要通过人工复核平台进行确认与修正。
```
