# B 题文档治理复核工作台

这是一个零依赖静态前端，直接读取 `b_solution/data` 和 `b_solution/outputs` 下的真实 CSV 结果。

## 本地运行

在 `b_solution` 目录启动工作台服务：

```powershell
python dashboard_server.py
```

然后访问：

```text
http://127.0.0.1:5178/dashboard/index.html
```

注意：如果只用 `python -m http.server 5178` 启动，只能查看页面和数据，不能点击打开本机原始文件。`dashboard_server.py` 额外提供了打开原文件和打开所在目录的本地接口。

## 功能

- 总览 KPI 与流程状态
- 解析监控表
- 主题发现页
- 分类结果页
- 待复核队列页
- 问题二人工核查页
- S1/S2/S3 资源场景对比
- 详情抽屉
- 人工确认、改类、无法归类、驳回与 localStorage 留痕

## 人工核查页

直接访问：

```text
http://127.0.0.1:5178/dashboard/index.html?view=audit
```

数据来源：

```text
b_solution/notes/manual_review/problem2_k160_boundary_audit_samples.csv
```

当前实现：

- 展示 221 条按 `doc_id` 去重后的问题二抽样核查样本。
- 支持按抽样来源、数据集、分类状态、风险等级、人工状态筛选。
- 表格展示 `content_snippet`、当前分类、归类依据、置信度和风险。
- 详情抽屉展示原始 `file_path`，支持打开原文件、打开所在目录、复制路径。
- 支持快速处理：确认、存疑、噪声、无法归类。
- 详情抽屉支持填写最终类别、备注和操作员，并写入 localStorage 复核日志。

## 使用建议

该页面是模型质量抽查工具，不是问题一、二、三主程序运行的必要步骤。

建议用法：

- 程序跑通和论文结果展示：不需要人工核查全部 221 条。
- 论文模型检验：抽查 30-50 条即可，记录典型正确、边界模糊、误分、噪声样本。
- 继续优化分类规则：先人工标一小批，再根据误分类型修改规则。

建议回填状态：

```text
confirmed       分类合理
changed         需要修改类别
noise           解析噪声或无效文本
uncertain       人工也无法稳定判断
unclassifiable  确认无法归类
```
