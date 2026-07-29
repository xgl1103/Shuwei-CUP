from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import jieba
import numpy as np
from sklearn.preprocessing import normalize

from .features import compose_analysis_text
from .parser import normalize_text
from .topic_refinement import refine_topic_label
from .topic_splitting import split_topic_family
from .topic_discovery import TopicDiscoveryConfig, build_vectorizer


FIELD_WEIGHTS: dict[str, float] = {
    "title": 1.6,
    "time_info": 1.0,
    "clean_text": 1.2,
    "table_text": 0.9,
    "ocr_text": 0.8,
}


def _split_terms(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[、,，;；/|\\\s]+", str(value))
    return [normalize_text(part) for part in parts if normalize_text(part)]


def _unique_terms(terms: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for term in terms:
        normalized = normalize_text(term)
        if normalized and normalized not in seen:
            seen.add(normalized)
            output.append(normalized)
    return output


def _tokenize_keywords(text: str) -> set[str]:
    text = normalize_text(text)
    if not text:
        return set()
    tokens: set[str] = set()
    for token in jieba.lcut(text):
        token = normalize_text(token).lower()
        if len(token) < 2:
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", token):
            continue
        if token.isdigit():
            continue
        tokens.add(token)
    return tokens


@dataclass(slots=True)
class TopicPrototypeClassifierConfig:
    min_text_length: int = 40
    max_text_chars: int = 6000
    max_features: int = 4000
    min_df: int = 2
    max_df: float = 0.85
    svd_components: int = 50
    top_k: int = 3
    keyword_weight: float = 0.12
    confidence_threshold: float = 0.45
    margin_threshold: float = 0.08
    unclassifiable_threshold: float = 0.35
    ambiguous_margin_threshold: float = 0.06
    min_field_coverage: float = 0.45
    weak_evidence_threshold: float = 0.30
    high_risk_threshold: float = 0.65
    medium_risk_threshold: float = 0.35
    dictionary_term_limit: int = 12


@dataclass(slots=True)
class TopicPrototype:
    cluster_id: int
    topic_name: str
    raw_topic_name: str
    top_terms: list[str]
    dictionary_terms: list[str]
    support: int
    centroid: np.ndarray


@dataclass(slots=True)
class TopicClassifierModel:
    vectorizer: object
    svd: object | None
    prototypes: list[TopicPrototype]
    feature_count: int
    embedding_dim: int


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


def _analysis_text(record: Mapping[str, object], max_chars: int) -> str:
    text = compose_analysis_text(record)
    return text[:max_chars] if len(text) > max_chars else text


def _field_text(record: Mapping[str, object], field: str, max_chars: int) -> str:
    value = record.get(field, "")
    if value is None:
        return ""
    text = normalize_text(str(value))
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def _fit_embeddings(texts: Sequence[str], config: TopicPrototypeClassifierConfig):
    topic_config = TopicDiscoveryConfig(
        min_text_length=config.min_text_length,
        max_features=config.max_features,
        min_df=config.min_df,
        max_df=config.max_df,
        svd_components=config.svd_components,
        max_text_chars=config.max_text_chars,
    )
    vectorizer = build_vectorizer(topic_config)
    tfidf = vectorizer.fit_transform(texts)

    if tfidf.shape[0] <= 2 or tfidf.shape[1] <= 2:
        embeddings = normalize(tfidf.astype(float), norm="l2", copy=False).toarray()
        svd = None
    else:
        from sklearn.decomposition import TruncatedSVD

        n_components = min(config.svd_components, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        n_components = max(2, n_components)
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        embeddings = svd.fit_transform(tfidf)
        embeddings = normalize(embeddings, norm="l2")

    return vectorizer, svd, tfidf, np.asarray(embeddings, dtype=float)


def _transform_texts(model: TopicClassifierModel, texts: Sequence[str]) -> np.ndarray:
    tfidf = model.vectorizer.transform(texts)
    if model.svd is None:
        embeddings = normalize(tfidf.astype(float), norm="l2", copy=False).toarray()
    else:
        embeddings = model.svd.transform(tfidf)
        embeddings = normalize(embeddings, norm="l2")
    return np.asarray(embeddings, dtype=float)


def _keyword_overlap_score(text: str, terms: Sequence[str]) -> tuple[float, list[str]]:
    if not text or not terms:
        return 0.0, []
    normalized_text = normalize_text(text)
    matched = [term for term in terms if term and term in normalized_text]
    return (len(matched) / len(terms), matched) if terms else (0.0, [])


def _topic_dictionary_terms(topic_name: str, top_terms: Sequence[str], limit: int) -> list[str]:
    candidate_terms = _unique_terms(_split_terms(topic_name) + list(top_terms))
    if len(candidate_terms) < limit:
        candidate_terms = _unique_terms(candidate_terms + list(top_terms))
    return candidate_terms[:limit]


def build_topic_classifier(
    records: Sequence[dict[str, object]],
    assignments: Sequence[dict[str, str]],
    topic_summary: Sequence[dict[str, str]],
    config: TopicPrototypeClassifierConfig | None = None,
) -> TopicClassifierModel:
    config = config or TopicPrototypeClassifierConfig()

    assignment_map = {str(row.get("doc_id") or ""): row for row in assignments if row.get("doc_id")}
    summary_map: dict[int, dict[str, str]] = {}
    for row in topic_summary:
        try:
            cluster_id = int(str(row.get("cluster_id") or ""))
        except ValueError:
            continue
        summary_map[cluster_id] = row

    training_rows: list[dict[str, object]] = []
    for record in records:
        doc_id = str(record.get("doc_id") or "")
        assignment = assignment_map.get(doc_id)
        if not assignment:
            continue
        try:
            cluster_id = int(str(assignment.get("cluster_id") or ""))
        except ValueError:
            continue
        text = _analysis_text(record, config.max_text_chars)
        if not text:
            continue
        item = dict(record)
        item["cluster_id"] = cluster_id
        item["analysis_text"] = text
        training_rows.append(item)

    if not training_rows:
        raise ValueError("no dataset1 assignments available for prototype building")

    texts = [str(row.get("analysis_text") or "") for row in training_rows]
    vectorizer, svd, tfidf, embeddings = _fit_embeddings(texts, config)

    feature_names = np.array(vectorizer.get_feature_names_out())
    prototypes: list[TopicPrototype] = []
    cluster_ids = sorted({int(row["cluster_id"]) for row in training_rows})

    for cluster_id in cluster_ids:
        member_indices = [index for index, row in enumerate(training_rows) if int(row["cluster_id"]) == cluster_id]
        if not member_indices:
            continue

        centroid = embeddings[member_indices].mean(axis=0)
        norm = float(np.linalg.norm(centroid))
        if norm > 0:
            centroid = centroid / norm

        summary_row = summary_map.get(cluster_id, {})
        topic_name = str(summary_row.get("topic_name") or f"主题{cluster_id}")
        raw_topic_name = str(summary_row.get("raw_topic_name") or topic_name)
        top_terms = _split_terms(str(summary_row.get("top_terms") or ""))
        cluster_tfidf = tfidf[member_indices]
        centroid_terms = np.asarray(cluster_tfidf.mean(axis=0)).ravel()
        top_term_indices = centroid_terms.argsort()[::-1][:8]
        centroid_top_terms = [str(feature_names[index]) for index in top_term_indices if centroid_terms[index] > 0]
        if not top_terms:
            top_terms = centroid_top_terms[:3]

        dictionary_terms = _topic_dictionary_terms(
            topic_name,
            list(top_terms) + centroid_top_terms,
            config.dictionary_term_limit,
        )
        if len(dictionary_terms) < 4:
            dictionary_terms = _unique_terms(dictionary_terms + top_terms + centroid_top_terms)[
                : config.dictionary_term_limit
            ]

        prototypes.append(
            TopicPrototype(
                cluster_id=cluster_id,
                topic_name=topic_name,
                raw_topic_name=raw_topic_name,
                top_terms=top_terms[:6],
                dictionary_terms=dictionary_terms,
                support=len(member_indices),
                centroid=np.asarray(centroid, dtype=float),
            )
        )

    return TopicClassifierModel(
        vectorizer=vectorizer,
        svd=svd,
        prototypes=prototypes,
        feature_count=int(tfidf.shape[1]),
        embedding_dim=int(embeddings.shape[1]),
    )


def _score_text_against_topics(
    model: TopicClassifierModel,
    text: str,
    centroids: np.ndarray,
    config: TopicPrototypeClassifierConfig,
) -> tuple[np.ndarray, np.ndarray, dict[int, list[str]]]:
    embedding = _transform_texts(model, [text])[0]
    raw_scores = embedding @ centroids.T

    combined_scores: list[float] = []
    evidence_by_cluster: dict[int, list[str]] = {}
    for prototype_index, prototype in enumerate(model.prototypes):
        overlap_score, matched_terms = _keyword_overlap_score(text, prototype.dictionary_terms)
        if matched_terms:
            evidence_by_cluster[prototype.cluster_id] = matched_terms
        combined_scores.append(float(raw_scores[prototype_index]) + config.keyword_weight * overlap_score)

    return np.asarray(combined_scores, dtype=float), np.asarray(raw_scores, dtype=float), evidence_by_cluster


def _confidence_from_scores(scores: Sequence[float]) -> float:
    if not scores:
        return 0.0
    values = np.asarray(scores, dtype=float)
    values = values - np.max(values)
    exp = np.exp(values)
    total = float(exp.sum())
    if total <= 0:
        return 0.0
    return float(exp[0] / total)


def _status_and_reasons(
    top1_score: float,
    margin: float,
    field_coverage: float,
    confidence: float,
    dictionary_overlap: float,
    parse_status: str,
    text_length: int,
    config: TopicPrototypeClassifierConfig,
    rule_rescue: bool = False,
    ambiguity_resolution_reason: str = "",
) -> tuple[str, list[str], list[str], int, float, str, str]:
    boundary_reasons: list[str] = []
    review_reasons: list[str] = []
    risk_score = 0.0

    if top1_score < config.unclassifiable_threshold and rule_rescue:
        boundary_status = "assigned"
        boundary_reasons.append(f"rule_rescue:{top1_score:.2f}<{config.unclassifiable_threshold:.2f}")
        review_reasons.append("rule_assisted_low_score")
        risk_score += 0.25
    elif top1_score < config.unclassifiable_threshold:
        boundary_status = "unclassifiable"
        boundary_reasons.append(f"max_score<{config.unclassifiable_threshold:.2f}")
        risk_score += 0.55
    elif margin < config.ambiguous_margin_threshold and not ambiguity_resolution_reason:
        boundary_status = "multi_class"
        boundary_reasons.append(f"margin<{config.ambiguous_margin_threshold:.2f}")
        risk_score += 0.35
    else:
        boundary_status = "assigned"
        if margin < config.ambiguous_margin_threshold and ambiguity_resolution_reason:
            boundary_reasons.append(
                f"{ambiguity_resolution_reason}:{margin:.2f}<{config.ambiguous_margin_threshold:.2f}"
            )
            review_reasons.append("resolved_small_margin")

    if field_coverage < config.min_field_coverage:
        review_reasons.append(f"low_field_coverage<{config.min_field_coverage:.2f}")
        risk_score += 0.20 * (config.min_field_coverage - field_coverage) / config.min_field_coverage
    if dictionary_overlap < config.weak_evidence_threshold:
        review_reasons.append(f"weak_dictionary_evidence<{config.weak_evidence_threshold:.2f}")
        risk_score += 0.20 * (config.weak_evidence_threshold - dictionary_overlap) / config.weak_evidence_threshold
    if margin < config.margin_threshold:
        review_reasons.append("small_margin")
        risk_score += 0.25 * (config.margin_threshold - margin) / config.margin_threshold
    if confidence < config.confidence_threshold:
        review_reasons.append("low_confidence")
        risk_score += 0.10 * (config.confidence_threshold - confidence) / config.confidence_threshold
    if text_length < config.min_text_length:
        review_reasons.append("short_text")
        risk_score += 0.20
    if parse_status != "ok":
        review_reasons.append(f"parse_status={parse_status or 'unknown'}")
        risk_score += 0.35

    risk_score = max(0.0, min(1.0, float(risk_score)))
    if risk_score >= config.high_risk_threshold:
        risk_level = "high"
        review_priority = 0
        review_decision = "must_review"
    elif risk_score >= config.medium_risk_threshold:
        risk_level = "medium"
        review_priority = 1
        review_decision = "review_if_capacity"
    else:
        risk_level = "low"
        review_priority = 2
        review_decision = "auto_archive"

    return boundary_status, boundary_reasons, review_reasons, review_priority, risk_score, risk_level, review_decision


def _has_specific_split_evidence(split_reason: str) -> bool:
    if not split_reason or split_reason == "content_fallback":
        return False
    generic_terms = {
        "教育",
        "科研",
        "研究",
        "项目",
        "工作",
        "问题",
        "材料",
        "发展",
        "content_keyword_match",
    }
    terms = [term.strip() for term in split_reason.replace("domain_override:", "").split("、") if term.strip()]
    return any(term not in generic_terms and not term.startswith("latin_ratio") for term in terms)


def classify_documents(
    model: TopicClassifierModel,
    records: Sequence[dict[str, object]],
    config: TopicPrototypeClassifierConfig | None = None,
) -> list[dict[str, object]]:
    config = config or TopicPrototypeClassifierConfig()
    if not model.prototypes:
        return []

    centroids = np.vstack([prototype.centroid for prototype in model.prototypes])
    centroids = normalize(centroids, norm="l2")
    total_field_weight = float(sum(FIELD_WEIGHTS.values()))

    rows: list[dict[str, object]] = []

    for record in records:
        field_texts: list[tuple[str, str, float]] = []
        for field, weight in FIELD_WEIGHTS.items():
            text = _field_text(record, field, config.max_text_chars)
            if text:
                field_texts.append((field, text, weight))

        if not field_texts:
            continue

        combined_scores = np.zeros(len(model.prototypes), dtype=float)
        raw_scores = np.zeros(len(model.prototypes), dtype=float)
        evidence_by_cluster: dict[int, list[str]] = defaultdict(list)
        active_weight = 0.0

        for _, text, weight in field_texts:
            field_combined, field_raw, field_evidence = _score_text_against_topics(model, text, centroids, config)
            combined_scores += weight * field_combined
            raw_scores += weight * field_raw
            active_weight += weight
            for cluster_id, terms in field_evidence.items():
                evidence_by_cluster[cluster_id].extend(terms)

        field_coverage = active_weight / total_field_weight if total_field_weight else 0.0
        if active_weight > 0:
            combined_scores /= active_weight
            raw_scores /= active_weight
        combined_scores *= 0.75 + 0.25 * field_coverage

        ranking = np.argsort(combined_scores)[::-1]
        top_indices = ranking[: max(1, config.top_k)]
        best_index = int(top_indices[0])
        second_index = int(top_indices[1]) if len(top_indices) > 1 else best_index
        third_index = int(top_indices[2]) if len(top_indices) > 2 else second_index

        top_scores = [float(combined_scores[index]) for index in top_indices]
        confidence = _confidence_from_scores(top_scores)
        top1_score = float(combined_scores[best_index])
        top2_score = float(combined_scores[second_index])
        top3_score = float(combined_scores[third_index])
        margin = top1_score - top2_score

        best_prototype = model.prototypes[best_index]
        second_prototype = model.prototypes[second_index]
        third_prototype = model.prototypes[third_index]
        all_text = " ".join(text for _, text, _ in field_texts)
        dictionary_overlap = float(_keyword_overlap_score(all_text, best_prototype.dictionary_terms)[0])

        parse_status = str(record.get("parse_status") or "")
        text_length = sum(len(text) for _, text, _ in field_texts)

        split_result = split_topic_family(
            record=record,
            topic_name=best_prototype.topic_name,
            raw_topic_name=best_prototype.raw_topic_name,
        )
        broad_topic_name = split_result.topic_child_name
        broad_reason = split_result.split_reason
        child_topic_name, fine_reason = refine_topic_label(broad_topic_name, record, broad_reason)
        prototype_topic_name = best_prototype.topic_name
        parent_topic_name = broad_topic_name
        split_reason = broad_reason if not fine_reason else f"{broad_reason}; {fine_reason}"
        rule_rescue = top1_score >= 0.30 and _has_specific_split_evidence(split_reason)
        same_prototype_family = prototype_topic_name == second_prototype.topic_name
        rule_disambiguation = (
            top1_score >= config.confidence_threshold
            and margin >= 0.02
            and dictionary_overlap >= config.weak_evidence_threshold
            and _has_specific_split_evidence(split_reason)
        )
        ambiguity_resolution_reason = ""
        if margin < config.ambiguous_margin_threshold:
            if same_prototype_family:
                ambiguity_resolution_reason = "same_prototype_family"
            elif rule_disambiguation:
                ambiguity_resolution_reason = "rule_disambiguation"

        (
            boundary_status,
            boundary_reasons,
            review_reasons,
            review_priority,
            risk_score,
            risk_level,
            review_decision,
        ) = _status_and_reasons(
            top1_score=top1_score,
            margin=margin,
            field_coverage=field_coverage,
            confidence=confidence,
            dictionary_overlap=dictionary_overlap,
            parse_status=parse_status,
            text_length=text_length,
            config=config,
            rule_rescue=rule_rescue,
            ambiguity_resolution_reason=ambiguity_resolution_reason,
        )

        matched_terms = evidence_by_cluster.get(best_prototype.cluster_id, [])
        if not matched_terms:
            matched_terms = best_prototype.dictionary_terms[:6]

        review_needed = review_priority < 2

        rows.append(
            {
                "doc_id": record.get("doc_id", ""),
                "dataset": record.get("dataset", ""),
                "title": record.get("title", ""),
                "file_name": record.get("file_name", ""),
                "parse_status": parse_status,
                "char_count": record.get("char_count", ""),
                "field_coverage": round(field_coverage, 6),
                "available_fields": ";".join(field for field, _, _ in field_texts),
                "topic_cluster_id": best_prototype.cluster_id,
                "topic_name": child_topic_name,
                "topic_parent_name": parent_topic_name,
                "topic_broad_name": broad_topic_name,
                "topic_prototype_name": prototype_topic_name,
                "raw_topic_name": best_prototype.raw_topic_name,
                "topic_split_reason": split_reason,
                "topic_broad_reason": broad_reason,
                "topic_refinement_reason": fine_reason,
                "topic_support": best_prototype.support,
                "classification_status": boundary_status,
                "boundary_reason": "; ".join(boundary_reasons),
                "top1_score": top1_score,
                "top1_raw_similarity": float(raw_scores[best_index]),
                "top1_dictionary_overlap": dictionary_overlap,
                "top2_cluster_id": second_prototype.cluster_id,
                "top2_topic_name": second_prototype.topic_name,
                "top2_score": top2_score,
                "top3_cluster_id": third_prototype.cluster_id,
                "top3_topic_name": third_prototype.topic_name,
                "top3_score": top3_score,
                "score_margin": margin,
                "confidence_score": confidence,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "review_flag": int(review_needed),
                "review_priority": review_priority,
                "review_decision": review_decision,
                "review_reason": "; ".join(review_reasons),
                "evidence_terms": "、".join(_unique_terms(matched_terms)[:6]),
                "candidate_topics": " | ".join(
                    f"{model.prototypes[index].topic_name}:{combined_scores[index]:.4f}" for index in top_indices
                ),
            }
        )

    return rows


def build_topic_dictionary_rows(model: TopicClassifierModel) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for prototype in model.prototypes:
        rows.append(
            {
                "cluster_id": prototype.cluster_id,
                "topic_name": prototype.topic_name,
                "raw_topic_name": prototype.raw_topic_name,
                "support": prototype.support,
                "dictionary_size": len(prototype.dictionary_terms),
                "top_terms": "、".join(prototype.top_terms),
                "dictionary_terms": "、".join(prototype.dictionary_terms),
            }
        )
    return rows


def summarize_classification(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    summary: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in rows:
        key = (
            str(row.get("dataset") or ""),
            str(row.get("topic_parent_name") or ""),
            str(row.get("topic_name") or ""),
        )
        bucket = summary.setdefault(
            key,
            {
                "dataset": key[0],
                "topic_parent_name": key[1],
                "topic_name": key[2],
                "count": 0,
                "assigned_count": 0,
                "multi_class_count": 0,
                "unclassifiable_count": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "review_count": 0,
                "mean_risk_score": 0.0,
                "mean_confidence": 0.0,
                "mean_margin": 0.0,
                "mean_field_coverage": 0.0,
            },
        )
        bucket["count"] += 1
        status = str(row.get("classification_status") or "assigned")
        if status == "assigned":
            bucket["assigned_count"] += 1
        elif status == "multi_class":
            bucket["multi_class_count"] += 1
        elif status == "unclassifiable":
            bucket["unclassifiable_count"] += 1
        risk_level = str(row.get("risk_level") or "low")
        if risk_level == "high":
            bucket["high_risk_count"] += 1
        elif risk_level == "medium":
            bucket["medium_risk_count"] += 1
        else:
            bucket["low_risk_count"] += 1
        bucket["review_count"] += int(row.get("review_flag") or 0)
        bucket["mean_risk_score"] += float(row.get("risk_score") or 0.0)
        bucket["mean_confidence"] += float(row.get("confidence_score") or 0.0)
        bucket["mean_margin"] += float(row.get("score_margin") or 0.0)
        bucket["mean_field_coverage"] += float(row.get("field_coverage") or 0.0)

    output: list[dict[str, object]] = []
    for bucket in summary.values():
        count = int(bucket["count"]) or 1
        output.append(
            {
                "dataset": bucket["dataset"],
                "topic_parent_name": bucket["topic_parent_name"],
                "topic_name": bucket["topic_name"],
                "count": bucket["count"],
                "assigned_count": bucket["assigned_count"],
                "multi_class_count": bucket["multi_class_count"],
                "unclassifiable_count": bucket["unclassifiable_count"],
                "high_risk_count": bucket["high_risk_count"],
                "medium_risk_count": bucket["medium_risk_count"],
                "low_risk_count": bucket["low_risk_count"],
                "review_count": bucket["review_count"],
                "review_rate": float(bucket["review_count"]) / count,
                "mean_risk_score": float(bucket["mean_risk_score"]) / count,
                "mean_confidence": float(bucket["mean_confidence"]) / count,
                "mean_margin": float(bucket["mean_margin"]) / count,
                "mean_field_coverage": float(bucket["mean_field_coverage"]) / count,
            }
        )
    output.sort(
        key=lambda item: (
            item["dataset"],
            item.get("topic_parent_name", ""),
            -int(item["count"]),
            item["topic_name"],
        )
    )
    return output


def build_meta(
    model: TopicClassifierModel,
    rows: Sequence[dict[str, object]],
    config: TopicPrototypeClassifierConfig,
) -> dict[str, object]:
    total = len(rows)
    review_count = sum(int(row.get("review_flag") or 0) for row in rows)
    by_dataset: dict[str, int] = {}
    status_counts = Counter(str(row.get("classification_status") or "assigned") for row in rows)
    risk_counts = Counter(str(row.get("risk_level") or "low") for row in rows)
    decision_counts = Counter(str(row.get("review_decision") or "auto_archive") for row in rows)
    mean_risk_score = (
        sum(float(row.get("risk_score") or 0.0) for row in rows) / total
        if total
        else 0.0
    )

    for row in rows:
        dataset = str(row.get("dataset") or "")
        by_dataset[dataset] = by_dataset.get(dataset, 0) + 1

    prototypes = [
        {
            "cluster_id": proto.cluster_id,
            "topic_name": proto.topic_name,
            "raw_topic_name": proto.raw_topic_name,
            "support": proto.support,
            "top_terms": proto.top_terms,
            "dictionary_terms": proto.dictionary_terms,
        }
        for proto in model.prototypes
    ]

    return {
        "total_documents": total,
        "review_count": review_count,
        "review_rate": float(review_count / total) if total else 0.0,
        "by_dataset": by_dataset,
        "status_counts": dict(status_counts),
        "risk_counts": dict(risk_counts),
        "decision_counts": dict(decision_counts),
        "mean_risk_score": mean_risk_score,
        "feature_count": model.feature_count,
        "embedding_dim": model.embedding_dim,
        "config": asdict(config),
        "prototypes": prototypes,
    }
