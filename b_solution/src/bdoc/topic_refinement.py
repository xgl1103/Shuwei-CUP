from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .features import compose_analysis_text
from .parser import normalize_text


@dataclass(slots=True)
class SubtopicRule:
    name: str
    keywords: tuple[str, ...]
    title_patterns: tuple[str, ...] = ()
    boost: float = 1.0


def _normalize(value: object) -> str:
    return "" if value is None else normalize_text(str(value))


def _count_hits(text: str, keywords: Sequence[str]) -> tuple[float, list[str]]:
    if not text or not keywords:
        return 0.0, []
    text_lower = text.lower()
    matched: list[str] = []
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in text_lower and keyword not in matched:
            matched.append(keyword)
    return float(len(matched)), matched


def _score_rule(title: str, body: str, prior: str, rule: SubtopicRule) -> tuple[float, list[str]]:
    title_hits, title_terms = _count_hits(title, rule.keywords)
    body_hits, body_terms = _count_hits(body, rule.keywords)
    prior_hits, prior_terms = _count_hits(prior, rule.keywords)
    score = title_hits * 2.2 + body_hits * 1.0 + prior_hits * 0.4
    evidence: list[str] = []
    evidence.extend(title_terms[:4])
    evidence.extend(term for term in body_terms[:4] if term not in evidence)
    evidence.extend(term for term in prior_terms[:3] if term not in evidence)
    for pattern in rule.title_patterns:
        if re.search(pattern, title, flags=re.IGNORECASE):
            score += 2.0
            evidence.append(pattern)
    return score * rule.boost, evidence[:8]


def _fallback_name(broad_topic_name: str) -> str:
    fallback_map = {
        "教育科研与学术文献类": "教育综合类",
        "政府治理与公共管理类": "政务综合类",
        "财政金融与宏观经济类": "经济综合类",
        "企业投资与房地产类": "企业综合类",
        "资源环境与城市建设类": "资源综合类",
        "人口就业与社会保障类": "人口综合类",
        "工业交通与能源通信类": "工交综合类",
        "文化旅游与居民消费类": "文旅综合类",
        "农业农村与土地资源类": "农业综合类",
        "科技专利与标准规范类": "科技综合类",
        "医药卫生与药品类": "卫生综合类",
        "对外贸易与国际经济类": "外贸综合类",
        "地区民生与收入消费类": "民生综合类",
        "单位人员与平均指标类": "统计综合类",
        "基础情况与时序记录类": "记录综合类",
        "综合内容待判别类": "综合待判别类",
    }
    return fallback_map.get(broad_topic_name, f"{broad_topic_name}综合类")


SUBTOPIC_RULES: dict[str, tuple[SubtopicRule, ...]] = {
    "教育科研与学术文献类": (
        SubtopicRule("教务培养类", ("教学", "教务", "本科", "本科生", "研究生", "课程", "学位", "毕业", "培养", "选课", "成绩")),
        SubtopicRule("招生学位类", ("招生", "录取", "推免", "报名", "复试", "保研", "考试", "推免资格")),
        SubtopicRule("科研项目类", ("科研", "课题", "项目", "基金", "研究", "实验")),
        SubtopicRule("论文期刊类", ("论文", "期刊", "学报", "专著", "著作", "摘要", "参考文献", "journal", "paper", "thesis"), (r"Abstract", r"Keywords", r"References")),
        SubtopicRule("校园活动类", ("讲座", "论坛", "会议", "活动", "交流", "研讨", "支教", "比赛")),
        SubtopicRule("院校概况类", ("大学", "学校", "学院", "高校", "师资", "概况", "校史", "机构", "简介")),
        SubtopicRule("国际合作类", ("国际", "合作", "交换", "联合", "海外", "留学", "访学")),
    ),
    "政府治理与公共管理类": (
        SubtopicRule("党政会议类", ("政府", "人民政府", "市委", "省委", "党委", "党政", "会议", "通知", "方案", "意见", "报告")),
        SubtopicRule("统计调查类", ("统计局", "国家统计局", "统计", "调查", "普查", "督察", "抽样")),
        SubtopicRule("督导整改类", ("督导", "整改", "检查", "反馈", "落实", "问题", "巡察", "审计")),
        SubtopicRule("行政审批类", ("行政", "审批", "政务", "公开", "服务", "办事", "流程", "指南", "窗口")),
        SubtopicRule("招考录用类", ("公务员", "考试录用", "招考", "招聘", "应聘", "录用", "报名")),
        SubtopicRule("网站门户类", ("门户", "网站", "登录", "搜索", "互动", "栏目", "服务平台")),
    ),
    "财政金融与宏观经济类": (
        SubtopicRule("财政税收类", ("财政", "税收", "预算", "决算", "收支", "财政收入", "财政支出")),
        SubtopicRule("金融证券类", ("金融", "贷款", "存款", "证券", "股票", "债券", "保险", "货币")),
        SubtopicRule("宏观核算类", ("生产总值", "国内生产总值", "国民经济", "宏观经济", "核算", "总量")),
        SubtopicRule("价格指数类", ("价格", "指数", "消费价格", "居民消费价格", "物价")),
        SubtopicRule("收支预算类", ("收入", "支出", "预算", "决算", "结余")),
    ),
    "企业投资与房地产类": (
        SubtopicRule("房地产开发类", ("房地产", "住宅", "楼盘", "开发", "商品房", "房屋", "房地产业")),
        SubtopicRule("企业经营类", ("企业", "工业企业", "利润", "成本", "营业", "经营", "法人单位")),
        SubtopicRule("固定资产投资类", ("投资", "固定资产", "建设项目", "项目", "施工", "投资额")),
        SubtopicRule("招商园区类", ("开发区", "招商", "园区", "产业链", "供应链", "营商")),
    ),
    "资源环境与城市建设类": (
        SubtopicRule("生态环境类", ("生态", "环境", "环保", "污染", "监测", "治理")),
        SubtopicRule("城市建设类", ("城市", "城区", "城乡", "市政", "建设", "改造")),
        SubtopicRule("基础设施类", ("基础设施", "供水", "排水", "道路", "桥梁", "绿化")),
        SubtopicRule("气象地震类", ("地震", "气象", "灾害", "预警", "台风", "降水")),
    ),
    "人口就业与社会保障类": (
        SubtopicRule("人口结构类", ("人口", "年龄", "出生", "死亡", "抚养比", "人口数")),
        SubtopicRule("就业失业类", ("就业", "失业", "招聘", "岗位", "劳动", "创业")),
        SubtopicRule("社会保障类", ("社保", "社会保障", "养老", "医保", "民政", "救助")),
        SubtopicRule("民生收入类", ("收入", "居民", "生活", "消费", "家庭", "工资")),
    ),
    "工业交通与能源通信类": (
        SubtopicRule("交通运输类", ("交通", "运输", "客运", "货运", "铁路", "公路", "港口", "物流")),
        SubtopicRule("工业生产类", ("工业", "制造", "产量", "产值", "生产", "工厂")),
        SubtopicRule("能源电力类", ("能源", "电力", "煤炭", "石油", "天然气", "供电", "供热")),
        SubtopicRule("通信邮政类", ("通信", "电信", "邮政", "网络", "宽带")),
    ),
    "文化旅游与居民消费类": (
        SubtopicRule("文化活动类", ("文化", "博物馆", "展览", "艺术", "读书", "讲座")),
        SubtopicRule("旅游景区类", ("旅游", "游客", "景区", "旅行", "景点")),
        SubtopicRule("零售消费类", ("消费", "零售", "商品", "购物", "居民消费")),
        SubtopicRule("餐饮住宿类", ("餐饮", "住宿", "酒店", "宾馆", "饭店")),
        SubtopicRule("体育娱乐类", ("体育", "娱乐", "休闲", "健身", "赛事")),
    ),
    "农业农村与土地资源类": (
        SubtopicRule("农业生产类", ("农业", "粮食", "农作物", "播种", "收获", "种植")),
        SubtopicRule("农村发展类", ("农村", "乡村", "农民", "乡镇", "村庄", "振兴")),
        SubtopicRule("耕地土地类", ("耕地", "土地", "地块", "地类", "用地")),
        SubtopicRule("畜牧渔业类", ("畜牧", "牲畜", "渔业", "养殖", "牧业")),
    ),
    "科技专利与标准规范类": (
        SubtopicRule("专利发明类", ("专利", "发明", "实用新型", "外观设计", "授权")),
        SubtopicRule("标准规范类", ("标准", "规范", "规程", "指南", "技术要求")),
        SubtopicRule("检验认证类", ("检验", "检测", "认证", "质量", "验收")),
        SubtopicRule("科研创新类", ("科技", "技术", "研发", "创新", "知识产权")),
    ),
    "医药卫生与药品类": (
        SubtopicRule("医疗服务类", ("卫生", "医疗", "医院", "诊疗", "门诊", "床位")),
        SubtopicRule("药品药学类", ("药品", "医药", "药学", "药物", "处方")),
        SubtopicRule("疾病防控类", ("疾病", "健康", "疫情", "防控", "核酸")),
    ),
    "对外贸易与国际经济类": (
        SubtopicRule("进出口贸易类", ("进出口", "出口", "进口", "贸易", "海关")),
        SubtopicRule("外资外汇类", ("外资", "外汇", "跨境", "投资", "境外")),
        SubtopicRule("海关口岸类", ("海关", "口岸", "报关", "通关")),
    ),
    "地区民生与收入消费类": (
        SubtopicRule("地区民生类", ("地区", "民生", "生活", "服务", "社会事业")),
        SubtopicRule("收入消费类", ("收入", "消费", "零售", "居民", "支出")),
        SubtopicRule("旅游客运类", ("旅游", "客运", "出行", "景区", "交通")),
        SubtopicRule("冰雪文旅类", ("冰雪", "滑雪", "冰雪旅游", "文旅")),
    ),
    "单位人员与平均指标类": (
        SubtopicRule("单位统计类", ("单位", "法人单位", "从业", "职工", "机构")),
        SubtopicRule("人员统计类", ("人员", "人数", "职工", "员工", "劳动者")),
        SubtopicRule("平均指标类", ("平均", "人均", "均值", "每人", "每户")),
        SubtopicRule("编号时间类", ("编号", "时间", "日期", "年度", "季度", "表")),
    ),
    "基础情况与时序记录类": (
        SubtopicRule("基础概况类", ("基础情况", "概况", "基本情况", "简介", "概述")),
        SubtopicRule("时序记录类", ("时间", "年份", "日期", "月度", "季度", "历年")),
        SubtopicRule("编号档案类", ("编号", "清单", "目录", "档案", "记录")),
        SubtopicRule("表格明细类", ("表", "明细", "附表", "汇总")),
    ),
}


def refine_topic_label(
    broad_topic_name: str,
    record: Mapping[str, object],
    split_reason: str,
) -> tuple[str, str]:
    title = _normalize(record.get("title"))
    analysis_text = _normalize(compose_analysis_text(record))
    prior_text = _normalize(f"{broad_topic_name} {split_reason}")
    search_text = " ".join(part for part in (title, analysis_text, prior_text) if part)

    rules = SUBTOPIC_RULES.get(broad_topic_name, ())
    scored: list[tuple[str, float, str]] = []
    for rule in rules:
        score, evidence = _score_rule(title, analysis_text, prior_text, rule)
        if score > 0:
            scored.append((rule.name, score, "、".join(evidence)))

    if not scored:
        return _fallback_name(broad_topic_name), split_reason or "subtopic_fallback"

    scored.sort(key=lambda item: item[1], reverse=True)
    child_name, _, evidence_text = scored[0]
    if not evidence_text:
        evidence_text = search_text[:60]
    return child_name, evidence_text
