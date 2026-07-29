from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from .parser import normalize_text, strip_surrogates


POLICY_KEYWORDS = (
    "通知",
    "办法",
    "细则",
    "方案",
    "意见",
    "规定",
    "条例",
    "公告",
    "要求",
    "实施",
    "管理",
    "文件",
)

MONEY_KEYWORDS = (
    "资金",
    "财政",
    "经费",
    "预算",
    "补贴",
    "拨付",
    "结算",
    "报销",
    "奖补",
    "资助",
    "贷款",
    "支付",
    "扶持",
    "分配",
)

TIME_KEYWORDS = (
    "紧急",
    "立即",
    "尽快",
    "及时",
    "期限",
    "截止",
    "月底",
    "今日",
    "明日",
    "本周",
    "本月",
    "近日",
    "时限",
)

REVIEW_KEYWORDS = (
    "复核",
    "审核",
    "审查",
    "复审",
    "核验",
    "校验",
    "检查",
    "核对",
    "人工",
    "质检",
)

APPROVAL_KEYWORDS = (
    "审批",
    "核准",
    "批准",
    "报批",
    "备案",
    "签批",
    "发文",
    "批复",
    "审定",
)

BUSINESS_KEYWORDS = (
    "项目",
    "合同",
    "会议",
    "培训",
    "考核",
    "统计",
    "报表",
    "台账",
    "清单",
    "名单",
    "汇总",
    "记录",
    "采购",
    "申报",
    "申請",
)

WEB_TEMPLATE_KEYWORDS = (
    "首页",
    "登录",
    "注册",
    "搜索",
    "导航",
    "菜单",
    "栏目",
    "专题",
    "互动",
    "服务",
    "公开",
    "知识",
    "网页",
    "网站",
    "版权",
    "版权所有",
    "联系",
    "联系方式",
    "地址",
    "电话",
    "邮箱",
    "传真",
    "邮编",
    "微信",
    "微博",
    "手机版",
    "扫一扫",
    "分享",
    "打印",
    "查看",
    "点击",
    "阅读",
    "更多",
    "详情",
    "返回",
    "上一页",
    "下一页",
    "来源",
    "作者",
    "记者",
    "通讯员",
    "发布者",
    "发布时间",
    "原文链接",
    "站内搜索",
    "信息公开",
    "友情链接",
    "网站地图",
)

WEB_TEMPLATE_HINTS = (
    "首页",
    "登录",
    "注册",
    "搜索",
    "栏目",
    "专题",
    "互动",
    "服务",
    "公开",
    "版权所有",
    "联系方式",
    "站内搜索",
    "信息公开",
    "友情链接",
    "网站地图",
)

URL_RE = re.compile(r"(?i)^(?:https?://|www\.)\S+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PURE_SEPARATOR_RE = re.compile(r"^[\s·|/\\\-_=—…\.\dA-Za-z]*$")
META_LINE_RE = re.compile(r"^(?:发布者|发布时间|来源|作者|记者|通讯员|原文链接|网址|URL|地址|电话|邮箱|传真)[:：]")


def _unique_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        key = normalize_text(line).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(line)
    return output


def _looks_like_template_line(line: str) -> bool:
    text = normalize_text(line)
    if not text:
        return True
    if URL_RE.match(text) or EMAIL_RE.match(text):
        return True
    if META_LINE_RE.match(text):
        return True
    if len(text) <= 2 and not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
        return True
    if PURE_SEPARATOR_RE.match(text) and len(text) <= 24:
        return True
    hint_hits = sum(1 for term in WEB_TEMPLATE_HINTS if term in text)
    if hint_hits >= 2:
        return True
    if hint_hits >= 1 and len(text) <= 20 and not re.search(r"[\u4e00-\u9fff]{4,}", text):
        return True
    return False


def _clean_analysis_lines(text: str) -> str:
    if not text:
        return ""
    lines = [normalize_text(line) for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            continue
        if _looks_like_template_line(line):
            continue
        cleaned.append(line)
    cleaned = _unique_lines(cleaned)
    return normalize_text("\n".join(cleaned))


@dataclass(slots=True)
class FeatureConfig:
    min_keyword_length: int = 2


def _get_text(record: Mapping[str, object], field: str) -> str:
    value = record.get(field, "")
    if value is None:
        return ""
    return normalize_text(str(value))


def _count_patterns(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword and keyword in text)


def _count_chars(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text))


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def compose_analysis_text(record: Mapping[str, object]) -> str:
    parts = [
        _get_text(record, "title"),
        _get_text(record, "time_info"),
        _get_text(record, "clean_text"),
        _get_text(record, "table_text"),
        _get_text(record, "ocr_text"),
    ]
    merged = normalize_text("\n\n".join(part for part in parts if part))
    cleaned = _clean_analysis_lines(merged)
    return cleaned or merged


def build_feature_row(record: Mapping[str, object], config: FeatureConfig | None = None) -> dict[str, object]:
    config = config or FeatureConfig()

    title = _get_text(record, "title")
    time_info = _get_text(record, "time_info")
    raw_text = _get_text(record, "raw_text")
    clean_text = _get_text(record, "clean_text")
    table_text = _get_text(record, "table_text")
    ocr_text = _get_text(record, "ocr_text")
    analysis_text = compose_analysis_text(record)
    suffix = str(record.get("suffix") or "").lower()

    combined_text = normalize_text("\n\n".join(part for part in (title, analysis_text) if part))
    chinese_count = _count_chars(combined_text, r"[\u4e00-\u9fff]")
    latin_count = _count_chars(combined_text, r"[A-Za-z]")
    digit_count = _count_chars(combined_text, r"\d")
    punctuation_count = _count_chars(combined_text, r"[，。！？；：,.!?;:\-—()（）\[\]{}<>《》“”\"']")
    whitespace_count = _count_chars(combined_text, r"\s")
    line_count = combined_text.count("\n") + (1 if combined_text else 0)
    sentence_count = _count_chars(combined_text, r"[。！？!?;；]")
    paragraph_count = max(1, combined_text.count("\n\n") + 1) if combined_text else 0

    policy_hits = _count_patterns(combined_text, POLICY_KEYWORDS)
    money_hits = _count_patterns(combined_text, MONEY_KEYWORDS)
    time_hits = _count_patterns(combined_text, TIME_KEYWORDS)
    review_hits = _count_patterns(combined_text, REVIEW_KEYWORDS)
    approval_hits = _count_patterns(combined_text, APPROVAL_KEYWORDS)
    business_hits = _count_patterns(combined_text, BUSINESS_KEYWORDS)

    text_length = len(clean_text)
    analysis_length = len(analysis_text)
    title_length = len(title)
    table_length = len(table_text)
    ocr_length = len(ocr_text)
    raw_length = len(raw_text)

    feature_row: dict[str, object] = {
        "doc_id": str(record.get("doc_id") or ""),
        "dataset": str(record.get("dataset") or ""),
        "suffix": suffix,
        "parse_status": str(record.get("parse_status") or ""),
        "content_truncated": bool(record.get("content_truncated") or False),
        "title_len": title_length,
        "time_info_len": len(time_info),
        "raw_len": raw_length,
        "clean_len": text_length,
        "table_len": table_length,
        "ocr_len": ocr_length,
        "analysis_len": analysis_length,
        "line_count": line_count,
        "paragraph_count": paragraph_count,
        "sentence_count": sentence_count,
        "chinese_count": chinese_count,
        "latin_count": latin_count,
        "digit_count": digit_count,
        "punctuation_count": punctuation_count,
        "whitespace_count": whitespace_count,
        "chinese_ratio": _safe_ratio(chinese_count, len(combined_text)),
        "latin_ratio": _safe_ratio(latin_count, len(combined_text)),
        "digit_ratio": _safe_ratio(digit_count, len(combined_text)),
        "punctuation_ratio": _safe_ratio(punctuation_count, len(combined_text)),
        "has_title": int(bool(title)),
        "has_time_info": int(bool(time_info)),
        "has_table": int(bool(table_text)),
        "has_ocr_text": int(bool(ocr_text)),
        "policy_keyword_hits": policy_hits,
        "money_keyword_hits": money_hits,
        "time_keyword_hits": time_hits,
        "review_keyword_hits": review_hits,
        "approval_keyword_hits": approval_hits,
        "business_keyword_hits": business_hits,
        "policy_signal": int(policy_hits > 0),
        "money_signal": int(money_hits > 0),
        "time_signal": int(time_hits > 0),
        "review_signal": int(review_hits > 0),
        "approval_signal": int(approval_hits > 0),
        "business_signal": int(business_hits > 0),
        "analysis_text": analysis_text,
    }
    return feature_row


def sanitize_feature_value(value: object) -> object:
    if isinstance(value, str):
        return strip_surrogates(value)
    return value
