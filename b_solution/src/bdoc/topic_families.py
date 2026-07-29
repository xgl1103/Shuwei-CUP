from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(slots=True)
class ClusterFamilyRule:
    name: str
    keywords: tuple[str, ...]
    title_patterns: tuple[str, ...] = ()
    boost: float = 1.0


CLUSTER_FAMILY_RULES: tuple[ClusterFamilyRule, ...] = (
    ClusterFamilyRule(
        name="企业投资与房地产类",
        keywords=("企业", "投资", "固定资产", "房地产", "开发", "资产", "建筑业", "施工", "利润", "成本", "营业"),
        boost=1.5,
    ),
    ClusterFamilyRule(
        name="地区民生与收入消费类",
        keywords=("地区", "居民", "收入", "消费", "旅游", "零售", "生活", "服务", "客运", "冰雪"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="教育科研与学术文献类",
        keywords=("教育", "学校", "大学", "学院", "高校", "学生", "教师", "科研", "研究", "论文", "学报", "期刊", "课题"),
        title_patterns=(r"\b(Abstract|Keywords|References|Journal|Paper|Thesis)\b",),
        boost=1.5,
    ),
    ClusterFamilyRule(
        name="工业交通与能源通信类",
        keywords=("工业", "交通", "运输", "客运", "货运", "铁路", "公路", "港口", "邮政", "通信", "电信", "能源", "电力", "煤炭", "石油", "物流"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="资源环境与城市建设类",
        keywords=("耕地", "土地", "水利", "生态", "环境", "城市", "地震", "气象", "基础设施", "供水", "排水", "绿化", "监测"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="财政金融与宏观经济类",
        keywords=("生产总值", "国内生产总值", "财政", "金融", "预算", "决算", "税收", "货币", "贷款", "存款", "外债", "证券", "股票", "债券", "价格", "指数", "收入", "支出"),
        boost=1.5,
    ),
    ClusterFamilyRule(
        name="人口就业与社会保障类",
        keywords=("人口", "就业", "失业", "年龄", "出生", "死亡", "抚养比", "社保", "社会保障", "民政", "养老", "社会事业"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="农业农村与土地资源类",
        keywords=("农业", "农村", "农民", "粮食", "耕地", "农作物", "牲畜", "畜牧", "乡村", "水稻", "播种"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="科技专利与标准规范类",
        keywords=("科技", "技术", "专利", "发明", "实用新型", "外观设计", "知识产权", "标准", "规范", "规程", "检验", "检测", "认证", "质量", "指南"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="医药卫生与药品类",
        keywords=("卫生", "医疗", "医院", "诊疗", "门诊", "床位", "医药", "药品", "药学", "处方", "医学", "健康", "疾病", "药物"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="文化旅游与居民消费类",
        keywords=("文化", "旅游", "游客", "景区", "冰雪", "消费", "零售", "商品", "服务业", "餐饮", "住宿", "体育", "娱乐", "休闲"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="综合统计指标类",
        keywords=("单位", "人员", "平均", "情况", "编号", "时间", "指标", "统计", "数据", "合计", "数量", "总计", "表"),
        boost=1.4,
    ),
    ClusterFamilyRule(
        name="对外贸易与国际经济类",
        keywords=("进出口", "出口", "进口", "外贸", "外资", "外汇", "国际旅游", "贸易", "海关", "口岸", "利用外资", "跨境"),
        boost=1.4,
    ),
)

FALLBACK_FAMILY = "综合统计指标类"

RAW_TOPIC_NAME_OVERRIDES: dict[str, tuple[str, str]] = {
    "单位、人员、平均类": ("单位人员与平均指标类", "raw_topic_override:单位/人员/平均"),
    "情况、编号、时间类": ("基础情况与时序记录类", "raw_topic_override:情况/编号/时间"),
    "编号、时间、情况类": ("基础统计表格类", "raw_topic_override:编号/时间/情况"),
    "企业、编号、时间类": ("企业统计与经营情况类", "raw_topic_override:企业/编号/时间"),
}


def _normalize(value: object) -> str:
    return "" if value is None else str(value)


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]{2,}", text)
    return tokens


def _score_rule(text: str, rule: ClusterFamilyRule) -> tuple[float, list[str]]:
    tokens = _tokenize(text)
    matched: list[str] = []
    score = 0.0
    lowered = text.lower()
    for keyword in rule.keywords:
        if keyword.lower() in lowered:
            score += 1.0
            matched.append(keyword)
    for pattern in rule.title_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            score += 2.0
            matched.append(pattern)
    return score * rule.boost, matched[:8]


def _choose_family(summary_row: Mapping[str, object], member_rows: Sequence[Mapping[str, object]]) -> tuple[str, float, str, list[dict[str, object]]]:
    rep_raw = _normalize(summary_row.get("representatives"))
    top_terms = _normalize(summary_row.get("top_terms"))
    raw_topic_name = _normalize(summary_row.get("topic_name"))
    if raw_topic_name in RAW_TOPIC_NAME_OVERRIDES:
        family_name, evidence_text = RAW_TOPIC_NAME_OVERRIDES[raw_topic_name]
        return family_name, 1.0, evidence_text, [
            {
                "family_name": family_name,
                "score": 10.0,
                "evidence": evidence_text,
            }
        ]

    cluster_text = " ".join(part for part in (raw_topic_name, top_terms, rep_raw) if part)

    family_scores: list[dict[str, object]] = []
    for rule in CLUSTER_FAMILY_RULES:
        score, evidence = _score_rule(cluster_text, rule)
        if score > 0:
            family_scores.append(
                {
                    "family_name": rule.name,
                    "score": score,
                    "evidence": evidence,
                }
            )

    if not family_scores:
        return FALLBACK_FAMILY, 0.1, "fallback", []

    family_scores.sort(key=lambda item: float(item["score"]), reverse=True)
    best = family_scores[0]
    second = family_scores[1] if len(family_scores) > 1 else {"family_name": "", "score": 0.0}
    total = sum(float(item["score"]) for item in family_scores)
    confidence = float(best["score"]) / total if total > 0 else 0.0
    evidence_text = "、".join(str(item) for item in best.get("evidence", []))
    return str(best["family_name"]), confidence, evidence_text, family_scores[:4]


def refine_topic_families(
    records: Sequence[Mapping[str, object]],
    assignments: Sequence[Mapping[str, object]],
    topic_summary: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    record_map = {str(record.get("doc_id") or ""): record for record in records if record.get("doc_id")}

    assignment_map: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in assignments:
        doc_id = str(row.get("doc_id") or "")
        if not doc_id:
            continue
        try:
            cluster_id = int(str(row.get("cluster_id") or ""))
        except ValueError:
            continue
        assignment_map[cluster_id].append(dict(row))

    summary_map: dict[int, dict[str, object]] = {}
    for row in topic_summary:
        try:
            cluster_id = int(str(row.get("cluster_id") or ""))
        except ValueError:
            continue
        summary_map[cluster_id] = dict(row)

    refined_rows: list[dict[str, object]] = []
    for cluster_id, summary_row in sorted(summary_map.items()):
        member_rows = assignment_map.get(cluster_id, [])
        family_name, confidence, evidence_text, family_candidates = _choose_family(summary_row, member_rows)
        if not family_candidates:
            family_candidates = [{"family_name": family_name, "score": 0.1, "evidence": evidence_text}]

        representatives = summary_row.get("representatives", "")
        if not isinstance(representatives, str):
            representatives = json.dumps([], ensure_ascii=False)

        refined_rows.append(
            {
                "cluster_id": cluster_id,
                "size": int(summary_row.get("size") or 0),
                "share": float(summary_row.get("share") or 0.0),
                "raw_topic_name": str(summary_row.get("topic_name") or ""),
                "topic_name": family_name,
                "family_group": family_name,
                "family_confidence": round(confidence, 6),
                "family_score": round(float(family_candidates[0]["score"]) if family_candidates else 0.1, 6),
                "family_second": str(family_candidates[1]["family_name"]) if len(family_candidates) > 1 else "",
                "family_second_score": round(float(family_candidates[1]["score"]) if len(family_candidates) > 1 else 0.0, 6),
                "family_candidates": json.dumps(family_candidates, ensure_ascii=False),
                "family_reason": evidence_text,
                "top_terms": str(summary_row.get("top_terms") or ""),
                "mean_confidence": float(summary_row.get("mean_confidence") or 0.0),
                "median_distance": float(summary_row.get("median_distance") or 0.0),
                "representatives": representatives,
            }
        )

    return refined_rows
