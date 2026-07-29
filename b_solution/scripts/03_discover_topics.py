from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "6")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover document topics from parsed files")
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
        "--output-dir",
        type=Path,
        default=Path("b_solution/outputs/topic_discovery"),
        help="topic discovery output directory",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset1",
        help="dataset to use for topic discovery",
    )
    parser.add_argument("--min-text-length", type=int, default=80)
    parser.add_argument("--min-clusters", type=int, default=160)
    parser.add_argument("--max-clusters", type=int, default=160)
    parser.add_argument("--max-features", type=int, default=4000)
    parser.add_argument("--svd-components", type=int, default=50)
    parser.add_argument("--max-text-chars", type=int, default=6000)
    parser.add_argument("--kmeans-n-init", type=int, default=8)
    parser.add_argument("--silhouette-sample-size", type=int, default=1000)
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

    from bdoc.features import sanitize_feature_value
    from bdoc.topic_discovery import TopicDiscoveryConfig, build_analysis_texts, fit_topic_model

    args = build_parser().parse_args()
    input_jsonl = (
        args.input_jsonl if args.input_jsonl.is_absolute() else (project_root.parent / args.input_jsonl)
    )
    input_features = (
        args.input_features if args.input_features.is_absolute() else (project_root.parent / args.input_features)
    )
    output_dir = args.output_dir if args.output_dir.is_absolute() else (project_root.parent / args.output_dir)

    if not input_jsonl.exists():
        raise FileNotFoundError(f"parsed document jsonl not found: {input_jsonl}")

    records = load_jsonl(input_jsonl)
    features = load_csv(input_features) if input_features.exists() else []
    feature_map = {row["doc_id"]: row for row in features if row.get("doc_id")}

    merged_records: list[dict[str, object]] = []
    for record in records:
        if str(record.get("dataset") or "") != args.dataset:
            continue
        feature_row = feature_map.get(str(record.get("doc_id") or ""))
        if feature_row is not None:
            merged = dict(record)
            merged.update(feature_row)
        else:
            merged = dict(record)
        merged_records.append(merged)

    print(f"loaded={len(merged_records)} dataset={args.dataset}", flush=True)
    selected_records = build_analysis_texts(
        merged_records,
        min_text_length=args.min_text_length,
        max_text_chars=args.max_text_chars,
    )
    if not selected_records:
        raise ValueError("no usable texts found for topic discovery")

    print(f"selected={len(selected_records)}; fitting topic model...", flush=True)
    config = TopicDiscoveryConfig(
        min_text_length=args.min_text_length,
        min_clusters=args.min_clusters,
        max_clusters=args.max_clusters,
        max_features=args.max_features,
        svd_components=args.svd_components,
        max_text_chars=args.max_text_chars,
        kmeans_n_init=args.kmeans_n_init,
        silhouette_sample_size=args.silhouette_sample_size,
    )
    result = fit_topic_model(selected_records, config)

    output_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = output_dir / "topic_assignments.csv"
    summary_path = output_dir / "topic_summary.csv"
    meta_path = output_dir / "topic_meta.json"
    unclustered_path = output_dir / "topic_selection.csv"

    with assignments_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["assignments"][0].keys()))
        writer.writeheader()
        writer.writerows(result["assignments"])

    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["cluster_summaries"][0].keys()))
        writer.writeheader()
        writer.writerows(result["cluster_summaries"])

    with meta_path.open("w", encoding="utf-8") as f:
        meta = {
            "dataset": args.dataset,
            "selected_documents": len(selected_records),
            "total_documents_in_dataset": len(merged_records),
            "coverage": len(selected_records) / len(merged_records) if merged_records else 0.0,
            "cluster_count": result["cluster_count"],
            "feature_count": result["feature_count"],
            "embedding_dim": result["embedding_dim"],
            "evaluations": result["evaluations"],
        }
        json.dump(sanitize_feature_value(meta), f, ensure_ascii=False, indent=2)

    with unclustered_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "doc_id",
                "dataset",
                "title",
                "parse_status",
                "clean_len",
                "analysis_text",
            ],
        )
        writer.writeheader()
        selected_ids = {row["doc_id"] for row in result["assignments"]}
        for record in merged_records:
            if str(record.get("doc_id") or "") not in selected_ids:
                writer.writerow(
                    {
                        "doc_id": record.get("doc_id", ""),
                        "dataset": record.get("dataset", ""),
                        "title": record.get("title", ""),
                        "parse_status": record.get("parse_status", ""),
                        "clean_len": record.get("clean_len", ""),
                        "analysis_text": "",
                    }
                )

    print(f"dataset={args.dataset}")
    print(f"selected={len(selected_records)}")
    print(f"clusters={result['cluster_count']}")
    print(f"coverage={len(selected_records) / len(merged_records) if merged_records else 0:.3f}")
    print(f"assignments -> {assignments_path}")
    print(f"summary -> {summary_path}")
    print(f"meta -> {meta_path}")


if __name__ == "__main__":
    main()
