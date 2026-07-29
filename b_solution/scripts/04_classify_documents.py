from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify new documents against discovered topics")
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=Path("b_solution/data/parsed_documents.jsonl"),
        help="parsed document jsonl input",
    )
    parser.add_argument(
        "--input-features",
        type=Path,
        default=Path("b_solution/data/document_features.csv"),
        help="feature table csv input",
    )
    parser.add_argument(
        "--topic-assignments",
        type=Path,
        default=Path("b_solution/outputs/topic_discovery/topic_assignments.csv"),
        help="dataset1 topic assignments csv",
    )
    parser.add_argument(
        "--topic-summary",
        type=Path,
        default=Path("b_solution/outputs/topic_discovery/topic_summary.csv"),
        help="dataset1 topic summary csv",
    )
    parser.add_argument(
        "--refined-topic-summary",
        type=Path,
        default=Path("b_solution/outputs/topic_discovery/topic_summary_refined.csv"),
        help="refined topic family summary csv; used automatically when it exists",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("b_solution/outputs/document_classification"),
        help="classification output directory",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["dataset2", "dataset3"],
        help="datasets to classify",
    )
    parser.add_argument("--min-text-length", type=int, default=40)
    parser.add_argument("--max-text-chars", type=int, default=6000)
    parser.add_argument("--max-features", type=int, default=4000)
    parser.add_argument("--svd-components", type=int, default=50)
    parser.add_argument("--keyword-weight", type=float, default=0.10)
    parser.add_argument("--confidence-threshold", type=float, default=0.45)
    parser.add_argument("--margin-threshold", type=float, default=0.08)
    return parser


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


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from bdoc.classification import (
        TopicPrototypeClassifierConfig,
        build_meta,
        build_topic_dictionary_rows,
        build_topic_classifier,
        classify_documents,
        load_csv,
        load_jsonl,
        summarize_classification,
    )
    from bdoc.features import sanitize_feature_value

    args = build_parser().parse_args()
    input_jsonl = (
        args.input_jsonl if args.input_jsonl.is_absolute() else (project_root.parent / args.input_jsonl)
    )
    input_features = (
        args.input_features if args.input_features.is_absolute() else (project_root.parent / args.input_features)
    )
    topic_assignments = (
        args.topic_assignments
        if args.topic_assignments.is_absolute()
        else (project_root.parent / args.topic_assignments)
    )
    topic_summary = (
        args.topic_summary if args.topic_summary.is_absolute() else (project_root.parent / args.topic_summary)
    )
    refined_topic_summary = (
        args.refined_topic_summary
        if args.refined_topic_summary.is_absolute()
        else (project_root.parent / args.refined_topic_summary)
    )
    output_dir = args.output_dir if args.output_dir.is_absolute() else (project_root.parent / args.output_dir)

    if not input_jsonl.exists():
        raise FileNotFoundError(f"parsed document jsonl not found: {input_jsonl}")
    if not topic_assignments.exists():
        raise FileNotFoundError(f"topic assignments not found: {topic_assignments}")
    if not topic_summary.exists():
        raise FileNotFoundError(f"topic summary not found: {topic_summary}")

    records = load_jsonl(input_jsonl)
    features = load_csv(input_features) if input_features.exists() else []
    assignments = load_csv(topic_assignments)
    summary_source = refined_topic_summary if refined_topic_summary.exists() else topic_summary
    summary = load_csv(summary_source)

    feature_map = {row["doc_id"]: row for row in features if row.get("doc_id")}
    merged_records: list[dict[str, object]] = []
    for record in records:
        merged = dict(record)
        feature_row = feature_map.get(str(record.get("doc_id") or ""))
        if feature_row:
            merged.update(feature_row)
        merged_records.append(merged)

    selected_records = [record for record in merged_records if str(record.get("dataset") or "") in set(args.datasets)]
    if not selected_records:
        raise ValueError("no target documents found for classification")

    config = TopicPrototypeClassifierConfig(
        min_text_length=args.min_text_length,
        max_text_chars=args.max_text_chars,
        max_features=args.max_features,
        svd_components=args.svd_components,
        keyword_weight=args.keyword_weight,
        confidence_threshold=args.confidence_threshold,
        margin_threshold=args.margin_threshold,
    )

    classifier = build_topic_classifier(merged_records, assignments, summary, config)
    print(f"loaded={len(selected_records)} datasets={','.join(args.datasets)}", flush=True)
    print(f"topic_summary={summary_source}", flush=True)
    print("fitting finished; classifying...", flush=True)
    rows = classify_documents(classifier, selected_records, config)
    if not rows:
        raise ValueError("no documents were classified")

    summary_rows = summarize_classification(rows)
    review_rows = sorted(
        [row for row in rows if int(row.get("review_flag") or 0)],
        key=lambda item: (
            int(item.get("review_priority") or 0),
            -float(item.get("risk_score") or 0.0),
            float(item.get("score_margin") or 0.0),
            float(item.get("confidence_score") or 0.0),
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "classification_results.csv"
    summary_path = output_dir / "classification_summary.csv"
    review_path = output_dir / "review_queue.csv"
    dictionary_path = output_dir / "topic_dictionary.csv"
    meta_path = output_dir / "classification_meta.json"

    fieldnames = list(rows[0].keys())
    with results_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if summary_rows:
        with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

    if review_rows:
        with review_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(review_rows[0].keys()))
            writer.writeheader()
            writer.writerows(review_rows)

    dictionary_rows = build_topic_dictionary_rows(classifier)
    if dictionary_rows:
        with dictionary_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(dictionary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(dictionary_rows)

    meta = build_meta(classifier, rows, config)
    meta["datasets"] = list(args.datasets)
    meta["target_documents"] = len(selected_records)
    meta["review_queue_size"] = len(review_rows)
    meta["dictionary_path"] = str(dictionary_path)
    meta["input_jsonl"] = str(input_jsonl)
    meta["topic_assignments"] = str(topic_assignments)
    meta["topic_summary"] = str(summary_source)
    meta = sanitize_feature_value(meta)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"classified={len(rows)}")
    status_counts = {}
    risk_counts = {}
    for row in rows:
        status = str(row.get("classification_status") or "assigned")
        risk = str(row.get("risk_level") or "low")
        status_counts[status] = status_counts.get(status, 0) + 1
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    print("status=" + ", ".join(f"{key}:{value}" for key, value in sorted(status_counts.items())))
    print("risk=" + ", ".join(f"{key}:{value}" for key, value in sorted(risk_counts.items())))
    print(f"review_queue={len(review_rows)}")
    print(f"results -> {results_path}")
    print(f"summary -> {summary_path}")
    print(f"review -> {review_path}")
    print(f"dictionary -> {dictionary_path}")
    print(f"meta -> {meta_path}")


if __name__ == "__main__":
    main()
