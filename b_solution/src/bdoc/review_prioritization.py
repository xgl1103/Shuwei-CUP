from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .features import compose_analysis_text
from .parser import normalize_text


URGENCY_KEYWORDS = (
    "紧急",
    "立即",
    "尽快",
    "限期",
    "截止",
    "时限",
    "今日",
    "明日",
    "本周",
    "本月",
    "近期",
    "加急",
    "urgent",
    "deadline",
)

REVIEW_NECESSITY_KEYWORDS = (
    "资金",
    "财政",
    "经费",
    "预算",
    "决算",
    "拨付",
    "报销",
    "补贴",
    "资助",
    "审计",
    "审批",
    "核准",
    "备案",
    "合同",
    "招标",
    "采购",
    "质量",
    "标准",
    "药品",
    "专利",
)

MONEY_PATTERN = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>亿元|万元|千元|元|人民币|USD|usd|美元)?"
)


@dataclass(slots=True)
class ReviewPrioritizationConfig:
    high_priority_threshold: float = 0.65
    medium_priority_threshold: float = 0.35
    base_review_hours: float = 0.12
    max_length_hours: float = 0.50
    parse_issue_hours: float = 0.10
    high_risk_bonus_hours: float = 0.10
    random_state: int = 42


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_resource_scenarios(path: Path) -> list[dict[str, object]]:
    frame = pd.read_excel(path)
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "scenario_id": str(row.get("场景编号") or ""),
                "manual_hours": float(row.get("每日可用人工工时（小时）") or 0.0),
                "auto_archive_limit": int(row.get("自动归档能力上限（份/天）") or 0),
                "manual_review_limit": int(row.get("人工复核能力上限（份/天）") or 0),
            }
        )
    return rows


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _keyword_score(text: str, keywords: Sequence[str]) -> tuple[float, list[str]]:
    normalized = normalize_text(text).lower()
    matched: list[str] = []
    for keyword in keywords:
        keyword_normalized = keyword.lower()
        if keyword_normalized and keyword_normalized in normalized and keyword not in matched:
            matched.append(keyword)
    score = min(1.0, len(matched) / 4.0)
    return score, matched[:8]


def _extract_money_values(text: str) -> list[float]:
    values: list[float] = []
    normalized = normalize_text(text)
    for match in MONEY_PATTERN.finditer(normalized):
        number = _safe_float(match.group("num"))
        if number <= 0:
            continue
        unit = match.group("unit") or ""
        if unit == "亿元":
            number *= 100_000_000
        elif unit == "万元":
            number *= 10_000
        elif unit == "千元":
            number *= 1_000
        values.append(number)
    return values


def _money_score(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    max_value = max(values)
    if max_value <= 0:
        return 0.0
    return min(1.0, math.log10(max_value + 1) / 8.0)


def _review_signal_score(features: Mapping[str, object]) -> float:
    """Convert broad feature flags into a conservative review-necessity signal.

    The generic policy flag is intentionally capped so that ordinary policy wording
    does not make almost every document look equally review-worthy.
    """
    money = _safe_int(features.get("money_signal"))
    review = _safe_int(features.get("review_signal"))
    approval = _safe_int(features.get("approval_signal"))
    business = _safe_int(features.get("business_signal"))
    policy = _safe_int(features.get("policy_signal"))
    score = 0.35 * money + 0.25 * approval + 0.20 * review + 0.10 * business + 0.10 * policy
    if policy and not any((money, approval, review, business)):
        score = min(score, 0.18)
    return min(1.0, score)


def _review_necessity_score(
    keyword_score: float,
    money_score: float,
    signal_score: float,
) -> float:
    if money_score >= 0.8 or keyword_score >= 0.75:
        return max(keyword_score, money_score, signal_score)
    return min(1.0, 0.45 * keyword_score + 0.35 * money_score + 0.20 * signal_score)


def _date_urgency_score(text: str, today: date | None = None) -> float:
    today = today or date.today()
    candidates: list[date] = []
    for year, month, day in re.findall(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?", text):
        try:
            candidates.append(date(int(year), int(month), int(day)))
        except ValueError:
            continue
    if not candidates:
        return 0.0
    future_dates = [item for item in candidates if item >= today]
    if not future_dates:
        return 0.0
    delta = min((item - today).days for item in future_dates)
    if delta <= 1:
        return 1.0
    if delta <= 7:
        return 0.8
    if delta <= 30:
        return 0.5
    return 0.2


def ahp_weights() -> dict[str, object]:
    matrix = np.array(
        [
            [1.0, 2.0, 3.0],
            [0.5, 1.0, 2.0],
            [1.0 / 3.0, 0.5, 1.0],
        ],
        dtype=float,
    )
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    max_index = int(np.argmax(eigenvalues.real))
    max_eigenvalue = float(eigenvalues[max_index].real)
    vector = np.abs(eigenvectors[:, max_index].real)
    weights = vector / vector.sum()
    n = matrix.shape[0]
    consistency_index = (max_eigenvalue - n) / (n - 1)
    random_index = 0.58
    consistency_ratio = consistency_index / random_index if random_index else 0.0
    return {
        "criteria": ["misclassification_risk", "review_necessity", "urgency"],
        "weights": {
            "misclassification_risk": float(weights[0]),
            "review_necessity": float(weights[1]),
            "urgency": float(weights[2]),
        },
        "lambda_max": max_eigenvalue,
        "consistency_index": float(consistency_index),
        "consistency_ratio": float(consistency_ratio),
        "matrix": matrix.tolist(),
    }


def _priority_level(score: float, config: ReviewPrioritizationConfig) -> str:
    if score >= config.high_priority_threshold:
        return "high"
    if score >= config.medium_priority_threshold:
        return "medium"
    return "low"


def _review_hours(row: Mapping[str, object], text_length: int, config: ReviewPrioritizationConfig) -> float:
    hours = config.base_review_hours
    hours += min(config.max_length_hours, text_length / 20000.0)
    if str(row.get("parse_status") or "") != "ok":
        hours += config.parse_issue_hours
    if str(row.get("risk_level") or "") == "high":
        hours += config.high_risk_bonus_hours
    return round(hours, 3)


def build_priority_rows(
    classification_rows: Sequence[Mapping[str, object]],
    parsed_records: Sequence[Mapping[str, object]],
    feature_rows: Sequence[Mapping[str, object]],
    config: ReviewPrioritizationConfig | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    config = config or ReviewPrioritizationConfig()
    parsed_map = {str(row.get("doc_id") or ""): row for row in parsed_records}
    feature_map = {str(row.get("doc_id") or ""): row for row in feature_rows}
    ahp = ahp_weights()
    weights = ahp["weights"]

    rows: list[dict[str, object]] = []
    for row in classification_rows:
        doc_id = str(row.get("doc_id") or "")
        parsed = parsed_map.get(doc_id, {})
        features = feature_map.get(doc_id, {})
        text = compose_analysis_text(parsed) if parsed else str(row.get("title") or "")

        urgency_keyword_score, urgency_terms = _keyword_score(text, URGENCY_KEYWORDS)
        urgency_feature_score = min(1.0, _safe_float(features.get("time_keyword_hits")) / 4.0)
        urgency_date_score = _date_urgency_score(text)
        urgency_score = max(urgency_keyword_score, urgency_feature_score, urgency_date_score)

        necessity_keyword_score, necessity_terms = _keyword_score(text, REVIEW_NECESSITY_KEYWORDS)
        money_values = _extract_money_values(text)
        money_score = _money_score(money_values)
        signal_score = _review_signal_score(features)
        review_necessity_score = _review_necessity_score(necessity_keyword_score, money_score, signal_score)

        misclassification_risk = _safe_float(row.get("risk_score"))
        priority_score = (
            float(weights["misclassification_risk"]) * misclassification_risk
            + float(weights["review_necessity"]) * review_necessity_score
            + float(weights["urgency"]) * urgency_score
        )
        priority_score = max(0.0, min(1.0, priority_score))
        priority_level = _priority_level(priority_score, config)
        text_length = max(
            _safe_int(row.get("char_count")),
            _safe_int(features.get("analysis_len")),
            len(text),
        )
        estimated_hours = _review_hours(row, text_length, config)
        max_money = max(money_values) if money_values else 0.0

        action = "auto_archive"
        if priority_level == "high":
            action = "must_review"
        elif priority_level == "medium":
            action = "review_if_capacity"

        rows.append(
            {
                "doc_id": doc_id,
                "dataset": row.get("dataset", ""),
                "title": row.get("title", ""),
                "file_name": row.get("file_name", ""),
                "topic_name": row.get("topic_name", ""),
                "classification_status": row.get("classification_status", ""),
                "risk_level": row.get("risk_level", ""),
                "misclassification_risk_score": round(misclassification_risk, 6),
                "urgency_score": round(urgency_score, 6),
                "review_necessity_score": round(review_necessity_score, 6),
                "priority_score": round(priority_score, 6),
                "priority_level": priority_level,
                "recommended_action": action,
                "estimated_review_hours": estimated_hours,
                "max_money_value": round(max_money, 2),
                "money_score": round(money_score, 6),
                "urgency_terms": "、".join(urgency_terms),
                "necessity_terms": "、".join(necessity_terms),
                "review_reason": row.get("review_reason", ""),
                "candidate_topics": row.get("candidate_topics", ""),
            }
        )

    rows.sort(
        key=lambda item: (
            -float(item["priority_score"]),
            -float(item["misclassification_risk_score"]),
            -float(item["review_necessity_score"]),
            str(item["doc_id"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["priority_rank"] = index

    return rows, {"ahp": ahp, "config": asdict(config)}


def summarize_priority(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        key = (str(row.get("dataset") or ""), str(row.get("priority_level") or ""))
        bucket = buckets.setdefault(
            key,
            {
                "dataset": key[0],
                "priority_level": key[1],
                "count": 0,
                "mean_priority_score": 0.0,
                "mean_misclassification_risk": 0.0,
                "mean_urgency_score": 0.0,
                "mean_review_necessity_score": 0.0,
                "total_estimated_review_hours": 0.0,
            },
        )
        bucket["count"] += 1
        bucket["mean_priority_score"] += _safe_float(row.get("priority_score"))
        bucket["mean_misclassification_risk"] += _safe_float(row.get("misclassification_risk_score"))
        bucket["mean_urgency_score"] += _safe_float(row.get("urgency_score"))
        bucket["mean_review_necessity_score"] += _safe_float(row.get("review_necessity_score"))
        bucket["total_estimated_review_hours"] += _safe_float(row.get("estimated_review_hours"))

    output: list[dict[str, object]] = []
    for bucket in buckets.values():
        count = int(bucket["count"]) or 1
        output.append(
            {
                "dataset": bucket["dataset"],
                "priority_level": bucket["priority_level"],
                "count": bucket["count"],
                "mean_priority_score": round(float(bucket["mean_priority_score"]) / count, 6),
                "mean_misclassification_risk": round(float(bucket["mean_misclassification_risk"]) / count, 6),
                "mean_urgency_score": round(float(bucket["mean_urgency_score"]) / count, 6),
                "mean_review_necessity_score": round(float(bucket["mean_review_necessity_score"]) / count, 6),
                "total_estimated_review_hours": round(float(bucket["total_estimated_review_hours"]), 3),
            }
        )
    level_order = {"high": 0, "medium": 1, "low": 2}
    output.sort(key=lambda item: (item["dataset"], level_order.get(str(item["priority_level"]), 9)))
    return output


def allocate_resources(
    priority_rows: Sequence[Mapping[str, object]],
    scenarios: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    plan_rows: list[dict[str, object]] = []
    allocation_rows: list[dict[str, object]] = []

    sorted_rows = sorted(priority_rows, key=lambda item: int(item.get("priority_rank") or 999999))
    auto_candidates = sorted(
        [row for row in sorted_rows if str(row.get("priority_level")) == "low"],
        key=lambda item: (
            -_safe_float(item.get("priority_score")),
            int(item.get("priority_rank") or 999999),
        ),
    )
    review_candidates = sorted(
        [row for row in sorted_rows if str(row.get("priority_level")) in {"high", "medium"}],
        key=lambda item: (
            0 if str(item.get("priority_level")) == "high" else 1,
            -(_safe_float(item.get("priority_score")) / max(_safe_float(item.get("estimated_review_hours")), 0.25)),
            -_safe_float(item.get("priority_score")),
            int(item.get("priority_rank") or 999999),
        ),
    )

    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "")
        manual_hours = _safe_float(scenario.get("manual_hours"))
        manual_limit = _safe_int(scenario.get("manual_review_limit"))
        auto_limit = _safe_int(scenario.get("auto_archive_limit"))

        used_hours = 0.0
        selected_count = 0
        high_selected = 0
        medium_selected = 0
        auto_selected = 0

        for row in review_candidates:
            estimated_hours = _safe_float(row.get("estimated_review_hours"))
            if selected_count >= manual_limit or used_hours + estimated_hours > manual_hours:
                continue
            selected_count += 1
            used_hours += estimated_hours
            if str(row.get("priority_level")) == "high":
                high_selected += 1
            else:
                medium_selected += 1
            allocation_rows.append(
                {
                    "scenario_id": scenario_id,
                    "doc_id": row.get("doc_id", ""),
                    "priority_rank": row.get("priority_rank", ""),
                    "priority_level": row.get("priority_level", ""),
                    "priority_score": row.get("priority_score", ""),
                    "allocated_action": "manual_review",
                    "estimated_review_hours": estimated_hours,
                }
            )

        for row in auto_candidates[:auto_limit]:
            allocation_rows.append(
                {
                    "scenario_id": scenario_id,
                    "doc_id": row.get("doc_id", ""),
                    "priority_rank": row.get("priority_rank", ""),
                    "priority_level": row.get("priority_level", ""),
                    "priority_score": row.get("priority_score", ""),
                    "allocated_action": "auto_archive",
                    "estimated_review_hours": 0.0,
                }
            )
            auto_selected += 1

        deferred_review = max(0, len(review_candidates) - selected_count)
        plan_rows.append(
            {
                "scenario_id": scenario_id,
                "manual_hours": manual_hours,
                "manual_review_limit": manual_limit,
                "auto_archive_limit": auto_limit,
                "manual_review_selected": selected_count,
                "high_priority_selected": high_selected,
                "medium_priority_selected": medium_selected,
                "auto_archive_selected": auto_selected,
                "deferred_review_count": deferred_review,
                "used_manual_hours": round(used_hours, 3),
                "remaining_manual_hours": round(max(0.0, manual_hours - used_hours), 3),
                "manual_limit_binding": int(selected_count >= manual_limit),
                "hour_limit_binding": int(used_hours >= manual_hours),
            }
        )

    return plan_rows, allocation_rows
