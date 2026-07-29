from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

import jieba
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

from .features import compose_analysis_text
from .parser import normalize_text


DEFAULT_STOPWORDS = {
    "的",
    "了",
    "和",
    "是",
    "在",
    "与",
    "及",
    "为",
    "对",
    "将",
    "于",
    "等",
    "及其",
    "以及",
    "有关",
    "进行",
    "通过",
    "根据",
    "关于",
    "其中",
    "一个",
    "一种",
    "我们",
    "你们",
    "他们",
    "本",
    "该",
    "此",
    "其",
    "各",
    "并",
    "或",
    "而",
    "及",
    "等",
    "文件",
    "内容",
    "数据",
    "信息",
    "图片",
    "名称",
    "下载",
    "正文",
    "标题",
    "附件",
    "记录",
    "资料",
    "url",
    "html",
    "http",
    "https",
    "www",
    "cn",
    "com",
    "stats",
    "ndsj",
    "jpg",
    "jpeg",
    "png",
    "pdf",
    "docx",
    "txt",
    "xlsx",
    "gov",
    "sj",
    "the",
    "of",
    "and",
    "to",
    "in",
    "for",
    "on",
    "with",
    "at",
    "from",
    "通知",
    "办法",
    "规定",
    "方案",
    "实施",
    "管理",
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
}


@dataclass(slots=True)
class TopicDiscoveryConfig:
    min_text_length: int = 80
    min_clusters: int = 160
    max_clusters: int = 160
    max_features: int = 4000
    min_df: int = 2
    max_df: float = 0.85
    svd_components: int = 50
    max_text_chars: int = 6000
    kmeans_n_init: int = 8
    silhouette_sample_size: int = 1000
    top_terms: int = 10
    top_documents: int = 3
    random_state: int = 42


def _tokenize(text: str) -> list[str]:
    text = normalize_text(text).lower()
    if not text:
        return []
    tokens: list[str] = []
    for token in jieba.lcut(text):
        token = token.strip().lower()
        if len(token) < 2:
            continue
        if token in DEFAULT_STOPWORDS:
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", token):
            continue
        if token.isdigit():
            continue
        tokens.append(token)
    return tokens


def build_vectorizer(config: TopicDiscoveryConfig) -> TfidfVectorizer:
    return TfidfVectorizer(
        tokenizer=_tokenize,
        preprocessor=None,
        token_pattern=None,
        ngram_range=(1, 1),
        min_df=config.min_df,
        max_df=config.max_df,
        max_features=config.max_features,
        lowercase=False,
    )


def choose_cluster_count(
    embeddings: np.ndarray,
    min_clusters: int,
    max_clusters: int,
    kmeans_n_init: int,
    silhouette_sample_size: int,
    random_state: int,
) -> tuple[int, list[dict[str, float]]]:
    n_samples = embeddings.shape[0]
    if n_samples < 3:
        return 1, []

    upper = min(max_clusters, n_samples - 1)
    lower = min(min_clusters, upper)
    if lower < 2:
        lower = 2
    if upper < lower:
        return lower, []

    evaluations: list[dict[str, float]] = []
    best_k = lower
    best_score = -math.inf

    for k in range(lower, upper + 1):
        model = MiniBatchKMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=kmeans_n_init,
            batch_size=1536,
        )
        labels = model.fit_predict(embeddings)
        if len(set(labels)) < 2:
            continue
        sample_size = min(silhouette_sample_size, n_samples)
        score = float(
            silhouette_score(
                embeddings,
                labels,
                sample_size=sample_size if sample_size < n_samples else None,
                random_state=random_state,
            )
        )
        evaluations.append({"k": float(k), "silhouette": score})
        if score > best_score:
            best_score = score
            best_k = k

    return best_k, evaluations


def build_analysis_texts(
    records: Sequence[dict[str, object]],
    min_text_length: int,
    max_text_chars: int = 6000,
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for record in records:
        analysis_text = compose_analysis_text(record)
        if len(analysis_text) < min_text_length:
            continue
        item = dict(record)
        item["analysis_text"] = analysis_text[:max_text_chars]
        selected.append(item)
    return selected


def fit_topic_model(
    records: Sequence[dict[str, object]],
    config: TopicDiscoveryConfig | None = None,
) -> dict[str, object]:
    config = config or TopicDiscoveryConfig()
    texts = [str(record.get("analysis_text") or "") for record in records]
    if not texts:
        raise ValueError("no text records available for topic discovery")

    vectorizer = build_vectorizer(config)
    tfidf = vectorizer.fit_transform(texts)

    if tfidf.shape[1] <= 2 or tfidf.shape[0] <= 2:
        embeddings = normalize(tfidf.astype(float), norm="l2", copy=False).toarray()
        svd = None
    else:
        n_components = min(config.svd_components, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        n_components = max(2, n_components)
        svd = TruncatedSVD(n_components=n_components, random_state=config.random_state)
        embeddings = svd.fit_transform(tfidf)
        embeddings = normalize(embeddings, norm="l2")

    best_k, evaluations = choose_cluster_count(
        embeddings=embeddings,
        min_clusters=config.min_clusters,
        max_clusters=config.max_clusters,
        kmeans_n_init=config.kmeans_n_init,
        silhouette_sample_size=config.silhouette_sample_size,
        random_state=config.random_state,
    )

    cluster_model = MiniBatchKMeans(
        n_clusters=best_k,
        random_state=config.random_state,
        n_init=config.kmeans_n_init,
        batch_size=256,
    )
    labels = cluster_model.fit_predict(embeddings)
    centers = cluster_model.cluster_centers_
    distances = np.linalg.norm(embeddings - centers[labels], axis=1)

    cluster_scales: dict[int, float] = {}
    for cluster_id in sorted(set(labels)):
        cluster_distances = distances[labels == cluster_id]
        scale = float(np.median(cluster_distances)) if len(cluster_distances) else 1.0
        cluster_scales[int(cluster_id)] = max(scale, 1e-6)

    confidences = np.array(
        [
            math.exp(-distance / cluster_scales[int(cluster_id)])
            for distance, cluster_id in zip(distances, labels, strict=False)
        ],
        dtype=float,
    )

    feature_names = np.array(vectorizer.get_feature_names_out())
    cluster_summaries: list[dict[str, object]] = []
    assignments: list[dict[str, object]] = []

    for cluster_id in sorted(set(labels)):
        member_indices = np.where(labels == cluster_id)[0]
        cluster_tfidf = tfidf[member_indices]
        centroid_terms = np.asarray(cluster_tfidf.mean(axis=0)).ravel()
        top_term_indices = centroid_terms.argsort()[::-1][: config.top_terms]
        top_terms = [str(feature_names[index]) for index in top_term_indices if centroid_terms[index] > 0]
        if not top_terms:
            top_terms = [f"主题{cluster_id}"]

        member_distances = distances[member_indices]
        ordering = member_indices[np.argsort(member_distances)]
        representatives = []
        for doc_index in ordering[: config.top_documents]:
            record = records[int(doc_index)]
            representatives.append(
                {
                    "doc_id": record.get("doc_id", ""),
                    "title": record.get("title", ""),
                    "distance": float(distances[int(doc_index)]),
                    "confidence": float(confidences[int(doc_index)]),
                }
            )

        cluster_summaries.append(
            {
                "cluster_id": int(cluster_id),
                "size": int(len(member_indices)),
                "share": float(len(member_indices) / len(records)),
                "top_terms": "、".join(top_terms[:3]),
                "topic_name": "、".join(top_terms[:3]) + "类" if top_terms else f"主题{cluster_id}",
                "mean_confidence": float(confidences[member_indices].mean()),
                "median_distance": float(np.median(member_distances)),
                "representatives": representatives,
            }
        )

    for index, record in enumerate(records):
        cluster_id = int(labels[index])
        cluster_summary = next(item for item in cluster_summaries if item["cluster_id"] == cluster_id)
        assignments.append(
            {
                "doc_id": record.get("doc_id", ""),
                "dataset": record.get("dataset", ""),
                "title": record.get("title", ""),
                "cluster_id": cluster_id,
                "topic_name": cluster_summary["topic_name"],
                "distance_to_centroid": float(distances[index]),
                "confidence": float(confidences[index]),
                "text_length": len(str(record.get("analysis_text") or "")),
            }
        )

    return {
        "vectorizer": vectorizer,
        "svd": svd,
        "cluster_model": cluster_model,
        "labels": labels,
        "distances": distances,
        "confidences": confidences,
        "cluster_summaries": cluster_summaries,
        "assignments": assignments,
        "evaluations": evaluations,
        "cluster_count": int(best_k),
        "coverage": float(len(records)),
        "feature_count": int(tfidf.shape[1]),
        "embedding_dim": int(embeddings.shape[1]),
    }
