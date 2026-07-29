from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .features import compose_analysis_text
from .parser import normalize_text


@dataclass(slots=True)
class TopicSplitResult:
    topic_parent_name: str
    topic_child_name: str
    split_reason: str


@dataclass(slots=True)
class ContentRule:
    name: str
    title_keywords: tuple[str, ...]
    body_keywords: tuple[str, ...] = ()
    latin_bonus: float = 0.0
    title_weight: float = 2.4
    body_weight: float = 1.0
    prior_weight: float = 0.05


PARENT_NAME = "内容主题分类"
FALLBACK_NAME = "综合内容待判别类"
GOVERNMENT_NAME = "政府治理与公共管理类"
EDUCATION_NAME = "教育科研与学术文献类"
EDUCATION_GENERIC_TERMS = {"研究", "科研", "实验"}

DOMAIN_OVERRIDE_RULES: tuple[tuple[str, tuple[str, ...], int], ...] = (
    (
        "财政金融与宏观经济类",
        (
            "生产总值",
            "国内生产总值",
            "国民经济",
            "财政",
            "预算",
            "决算",
            "金融",
            "税收",
            "贷款",
            "存款",
            "证券",
            "价格",
            "财政收入",
            "财政支出",
            "公共预算",
        ),
        2,
    ),
    (
        "企业投资与房地产类",
        (
            "企业",
            "投资",
            "固定资产",
            "房地产",
            "市场主体",
            "建设项目",
            "开发区",
            "招商",
            "营商",
            "产业链",
            "供应链",
        ),
        2,
    ),
    (
        "工业交通与能源通信类",
        (
            "工业",
            "交通",
            "运输",
            "铁路",
            "公路",
            "港口",
            "物流",
            "邮政",
            "通信",
            "电信",
            "能源",
            "电力",
            "煤炭",
            "石油",
            "燃气",
        ),
        2,
    ),
    (
        "人口就业与社会保障类",
        (
            "人口",
            "就业",
            "失业",
            "民生",
            "社保",
            "养老",
            "居民收入",
            "医疗保障",
            "社会保障",
            "住房保障",
            "脱贫",
            "扶贫",
            "疫情",
            "健康",
        ),
        2,
    ),
    (
        "资源环境与城市建设类",
        (
            "生态",
            "环境",
            "环保",
            "污染",
            "城市",
            "基础设施",
            "水利",
            "供水",
            "排水",
            "绿化",
            "地震",
            "气象",
            "碳达峰",
            "碳中和",
        ),
        2,
    ),
    (
        "农业农村与土地资源类",
        (
            "农业",
            "农村",
            "农民",
            "粮食",
            "耕地",
            "土地",
            "农作物",
            "畜牧",
            "乡村",
            "扶贫",
            "脱贫",
        ),
        2,
    ),
    (
        "科技专利与标准规范类",
        (
            "科技",
            "创新",
            "专利",
            "技术",
            "研发",
            "标准",
            "规范",
            "知识产权",
            "数字技术",
            "人工智能",
        ),
        2,
    ),
    (
        "文化旅游与居民消费类",
        (
            "文化",
            "旅游",
            "游客",
            "景区",
            "消费",
            "零售",
            "餐饮",
            "住宿",
            "体育",
            "娱乐",
            "服务业",
            "休闲",
        ),
        2,
    ),
    (
        "医药卫生与药品类",
        (
            "卫生",
            "医疗",
            "医院",
            "诊疗",
            "药品",
            "医药",
            "药学",
            "疾病",
            "疫情防控",
            "核酸",
        ),
        2,
    ),
    (
        "教育科研与学术文献类",
        (
            "教育",
            "学校",
            "大学",
            "学院",
            "学生",
            "教师",
            "科研",
            "论文",
            "课题",
            "学术",
        ),
        2,
    ),
)


CONTENT_RULES: tuple[ContentRule, ...] = (
    ContentRule(
        name="政府治理与公共管理类",
        title_keywords=(
            "政府",
            "人民政府",
            "人大",
            "政协",
            "国务院",
            "党委",
            "党政",
            "机关",
            "行政",
            "政策",
            "规划",
            "方案",
            "纲要",
            "治理",
            "改革",
            "公告",
            "公务员",
            "考试录用",
            "统计局",
            "国家统计局",
            "市委",
            "省委",
            "党建",
            "党中央",
            "督导组",
            "政绩观",
            "中央八项规定",
            "基层减负",
            "学习教育",
            "督察",
            "习近平",
            "习近平总书记",
            "公共管理",
            "政府工作",
            "工作报告",
            "审议",
            "代表大会",
            "各位代表",
            "请予审议",
            "政府工作报告",
            "工作回顾",
            "本届政府",
        ),
        body_keywords=(
            "政府",
            "人民政府",
            "人大",
            "政协",
            "国务院",
            "党委",
            "党政",
            "机关",
            "行政",
            "政策",
            "规划",
            "方案",
            "纲要",
            "治理",
            "公共管理",
            "公告",
            "公务员",
            "考试录用",
            "统计局",
            "国家统计局",
            "市委",
            "省委",
            "党建",
            "党中央",
            "督导组",
            "政绩观",
            "中央八项规定",
            "基层减负",
            "学习教育",
            "督察",
            "习近平",
            "习近平总书记",
            "政府工作",
            "贯彻落实",
            "依法行政",
            "政务",
            "行政审批",
            "机关效能",
            "公共服务",
            "政府职能",
            "监督管理",
            "各位代表",
            "请予审议",
            "向大会报告",
            "政府工作报告",
            "报告政府工作",
            "本届政府",
            "工作回顾",
            "过去五年",
            "过去一年",
            "一年来",
            "我们主要做了以下工作",
            "人民代表大会",
        ),
        title_weight=2.4,
        body_weight=0.85,
        prior_weight=0.0,
    ),
    ContentRule(
        name="财政金融与宏观经济类",
        title_keywords=(
            "生产总值",
            "国内生产总值",
            "GDP",
            "财政",
            "金融",
            "预算",
            "决算",
            "税收",
            "货币",
            "贷款",
            "存款",
            "外债",
            "证券",
            "股票",
            "债券",
            "保险",
            "价格",
            "指数",
            "收入",
            "支出",
            "消费价格",
            "宏观经济",
            "国民经济",
            "减税降费",
        ),
        body_keywords=(
            "生产总值",
            "国内生产总值",
            "财政",
            "金融",
            "预算",
            "决算",
            "税收",
            "货币",
            "贷款",
            "存款",
            "外债",
            "证券",
            "股票",
            "债券",
            "保险",
            "价格",
            "指数",
            "宏观经济",
            "居民消费价格",
            "财政收入",
            "财政支出",
            "国民经济",
            "减税降费",
        ),
    ),
    ContentRule(
        name="企业投资与房地产类",
        title_keywords=(
            "企业",
            "工业企业",
            "投资",
            "固定资产",
            "房地产",
            "开发",
            "资产",
            "施工",
            "利润",
            "成本",
            "营业",
            "法人单位",
            "电子商务",
            "信息化",
            "建筑业",
            "建设项目",
        ),
        body_keywords=(
            "企业",
            "工业企业",
            "投资",
            "固定资产",
            "房地产",
            "开发",
            "资产",
            "施工",
            "利润",
            "成本",
            "营业",
            "法人单位",
            "电子商务",
            "信息化",
            "建筑业",
            "建设项目",
        ),
    ),
    ContentRule(
        name="教育科研与学术文献类",
        title_keywords=(
            "教育",
            "学校",
            "大学",
            "学院",
            "高校",
            "学生",
            "教师",
            "课程",
            "教学",
            "教务",
            "本科",
            "本科生",
            "研究生",
            "院系",
            "毕业",
            "招生",
            "学位",
            "论文",
            "学报",
            "期刊",
            "科研",
            "研究",
            "课题",
            "实验",
            "abstract",
            "keywords",
            "references",
            "journal",
            "paper",
            "thesis",
        ),
        body_keywords=(
            "教育",
            "学校",
            "大学",
            "学院",
            "高校",
            "学生",
            "教师",
            "课程",
            "教学",
            "教务",
            "本科",
            "本科生",
            "研究生",
            "院系",
            "毕业",
            "招生",
            "学位",
            "论文",
            "学报",
            "期刊",
            "科研",
            "研究",
            "课题",
            "实验",
            "摘要",
            "参考文献",
            "中图分类号",
            "abstract",
            "keywords",
            "references",
            "journal",
            "paper",
            "thesis",
        ),
        latin_bonus=0.18,
    ),
    ContentRule(
        name="科技专利与标准规范类",
        title_keywords=(
            "科技",
            "技术",
            "专利",
            "发明",
            "实用新型",
            "外观设计",
            "知识产权",
            "标准",
            "规范",
            "规程",
            "检验",
            "检测",
            "认证",
            "质量",
            "指南",
            "授权",
            "创新",
        ),
        body_keywords=(
            "科技",
            "技术",
            "专利",
            "发明",
            "实用新型",
            "外观设计",
            "知识产权",
            "标准",
            "规范",
            "规程",
            "检验",
            "检测",
            "认证",
            "质量",
            "指南",
            "授权",
            "创新",
        ),
    ),
    ContentRule(
        name="医药卫生与药品类",
        title_keywords=(
            "卫生",
            "医疗",
            "医院",
            "诊疗",
            "门诊",
            "床位",
            "医药",
            "药品",
            "药学",
            "处方",
            "医学",
            "健康",
            "疾病",
            "药物",
            "总费用",
        ),
        body_keywords=(
            "卫生",
            "医疗",
            "医院",
            "诊疗",
            "门诊",
            "床位",
            "医药",
            "药品",
            "药学",
            "处方",
            "医学",
            "健康",
            "疾病",
            "药物",
            "卫生总费用",
        ),
    ),
    ContentRule(
        name="人口就业与社会保障类",
        title_keywords=(
            "人口",
            "就业",
            "失业",
            "年龄",
            "出生",
            "死亡",
            "抚养比",
            "社保",
            "社会保障",
            "民政",
            "养老",
            "社会事业",
            "居民",
            "生活",
            "收入分配",
        ),
        body_keywords=(
            "人口",
            "就业",
            "失业",
            "年龄",
            "出生",
            "死亡",
            "抚养比",
            "社保",
            "社会保障",
            "民政",
            "养老",
            "社会事业",
            "居民生活",
            "收入分配",
        ),
    ),
    ContentRule(
        name="农业农村与土地资源类",
        title_keywords=(
            "农业",
            "农村",
            "农民",
            "农牧",
            "粮食",
            "耕地",
            "土地",
            "农作物",
            "牲畜",
            "畜牧",
            "水利",
            "林业",
            "渔业",
            "乡村",
            "农机",
            "播种",
        ),
        body_keywords=(
            "农业",
            "农村",
            "农民",
            "农牧",
            "粮食",
            "耕地",
            "土地",
            "农作物",
            "牲畜",
            "畜牧",
            "水利",
            "林业",
            "渔业",
            "乡村",
            "农机",
            "播种",
        ),
    ),
    ContentRule(
        name="工业交通与能源通信类",
        title_keywords=(
            "工业",
            "交通",
            "运输",
            "客运",
            "货运",
            "铁路",
            "公路",
            "港口",
            "邮政",
            "通信",
            "电信",
            "能源",
            "电力",
            "煤炭",
            "石油",
            "天然气",
            "供电",
            "供热",
            "物流",
        ),
        body_keywords=(
            "工业",
            "交通",
            "运输",
            "客运",
            "货运",
            "铁路",
            "公路",
            "港口",
            "邮政",
            "通信",
            "电信",
            "能源",
            "电力",
            "煤炭",
            "石油",
            "天然气",
            "供电",
            "供热",
            "物流",
        ),
    ),
    ContentRule(
        name="文化旅游与居民消费类",
        title_keywords=(
            "文化",
            "旅游",
            "游客",
            "景区",
            "冰雪",
            "消费",
            "零售",
            "商品",
            "服务业",
            "餐饮",
            "住宿",
            "体育",
            "娱乐",
            "休闲",
            "居民消费",
        ),
        body_keywords=(
            "文化",
            "旅游",
            "游客",
            "景区",
            "冰雪",
            "消费",
            "零售",
            "商品",
            "服务业",
            "餐饮",
            "住宿",
            "体育",
            "娱乐",
            "休闲",
            "居民消费",
        ),
    ),
    ContentRule(
        name="资源环境与城市建设类",
        title_keywords=(
            "资源",
            "环境",
            "生态",
            "环保",
            "污染",
            "地震",
            "气象",
            "城市",
            "城区",
            "市政",
            "基础设施",
            "供水",
            "排水",
            "绿化",
            "城市建设",
            "城乡建设",
            "环境监测",
            "监测",
        ),
        body_keywords=(
            "资源",
            "环境",
            "生态",
            "环保",
            "污染",
            "地震",
            "气象",
            "城市",
            "城区",
            "市政",
            "基础设施",
            "供水",
            "排水",
            "绿化",
            "城市建设",
            "城乡建设",
            "环境监测",
            "监测",
        ),
    ),
    ContentRule(
        name="对外贸易与国际经济类",
        title_keywords=(
            "进出口",
            "出口",
            "进口",
            "外贸",
            "外资",
            "外汇",
            "国际旅游",
            "贸易",
            "海关",
            "口岸",
            "利用外资",
            "跨境",
        ),
        body_keywords=(
            "进出口",
            "出口",
            "进口",
            "外贸",
            "外资",
            "外汇",
            "国际旅游",
            "贸易",
            "海关",
            "口岸",
            "利用外资",
            "跨境",
        ),
    ),
)


def _normalize(value: str | object) -> str:
    return normalize_text("" if value is None else str(value))


def _latin_ratio(text: str) -> float:
    if not text:
        return 0.0
    latin = sum(1 for char in text if "A" <= char <= "Z" or "a" <= char <= "z")
    return latin / len(text)


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


def _domain_override(title: str) -> tuple[str, str] | None:
    if not title:
        return None
    for topic_name, keywords, threshold in DOMAIN_OVERRIDE_RULES:
        _, matched = _count_hits(title, keywords)
        if len(matched) >= threshold:
            return topic_name, "domain_override:" + "、".join(matched[:6])
    return None


def _has_education_anchor(title_terms: Sequence[str], body_terms: Sequence[str]) -> bool:
    content_terms = set(title_terms) | set(body_terms)
    return any(term not in EDUCATION_GENERIC_TERMS for term in content_terms)


def split_topic_family(record: Mapping[str, object], topic_name: str, raw_topic_name: str) -> TopicSplitResult:
    title = _normalize(record.get("title"))
    analysis_text = _normalize(compose_analysis_text(record))
    prior_text = _normalize(f"{topic_name} {raw_topic_name}")
    combined_text = " ".join(part for part in (title, analysis_text, prior_text) if part)
    latin_ratio = _latin_ratio(combined_text)

    scores: list[tuple[str, float, str]] = []
    for rule in CONTENT_RULES:
        title_hits, title_terms = _count_hits(title, rule.title_keywords)
        body_hits, body_terms = _count_hits(analysis_text, rule.body_keywords)
        prior_hits, prior_terms = _count_hits(prior_text, rule.title_keywords + rule.body_keywords)
        content_hits = title_hits + body_hits
        if content_hits <= 0 and not (rule.latin_bonus and latin_ratio >= rule.latin_bonus):
            continue
        if rule.name == EDUCATION_NAME and not _has_education_anchor(title_terms, body_terms):
            continue
        score = (
            title_hits * rule.title_weight
            + body_hits * rule.body_weight
            + prior_hits * rule.prior_weight
        )
        evidence: list[str] = []
        evidence.extend(title_terms[:5])
        evidence.extend(term for term in body_terms[:5] if term not in evidence)
        evidence.extend(term for term in prior_terms[:4] if term not in evidence)
        if rule.latin_bonus and latin_ratio >= rule.latin_bonus:
            score += 2.0
            evidence.append(f"latin_ratio>={rule.latin_bonus:.2f}")
        if score > 0:
            scores.append((rule.name, score, "、".join(evidence[:8])))

    if scores:
        scores.sort(key=lambda item: item[1], reverse=True)
        child_name, _, evidence = scores[0]
        if child_name == GOVERNMENT_NAME:
            override = _domain_override(title)
            if override:
                override_name, override_reason = override
                return TopicSplitResult(
                    topic_parent_name=PARENT_NAME,
                    topic_child_name=override_name,
                    split_reason=override_reason,
                )
        return TopicSplitResult(
            topic_parent_name=PARENT_NAME,
            topic_child_name=child_name,
            split_reason=evidence or "content_keyword_match",
        )

    return TopicSplitResult(
        topic_parent_name=PARENT_NAME,
        topic_child_name=FALLBACK_NAME,
        split_reason="content_fallback",
    )
