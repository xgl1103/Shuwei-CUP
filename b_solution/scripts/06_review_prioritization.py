from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build problem-3 review prioritization and resource plan")
    parser.add_argument(
        "--classification-results",
        type=Path,
        default=Path("b_solution/outputs/document_classification/classification_results.csv"),
        help="classification result csv from problem 2",
    )
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
        "--resource-xlsx",
        type=Path,
        default=Path("B题数据集/数据集/数据集4：业务规则与资源约束表.xlsx"),
        help="dataset4 resource constraints xlsx",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("b_solution/outputs/review_prioritization"),
        help="review prioritization output directory",
    )
    return parser


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workspace_root = project_root.parent
    sys.path.insert(0, str(project_root / "src"))

    from bdoc.review_prioritization import (
        ReviewPrioritizationConfig,
        allocate_resources,
        build_priority_rows,
        load_csv,
        load_jsonl,
        load_resource_scenarios,
        summarize_priority,
    )

    args = build_parser().parse_args()
    classification_results = (
        args.classification_results
        if args.classification_results.is_absolute()
        else workspace_root / args.classification_results
    )
    input_jsonl = args.input_jsonl if args.input_jsonl.is_absolute() else workspace_root / args.input_jsonl
    input_features = args.input_features if args.input_features.is_absolute() else workspace_root / args.input_features
    resource_xlsx = args.resource_xlsx if args.resource_xlsx.is_absolute() else workspace_root / args.resource_xlsx
    output_dir = args.output_dir if args.output_dir.is_absolute() else workspace_root / args.output_dir

    if not classification_results.exists():
        raise FileNotFoundError(f"classification results not found: {classification_results}")
    if not input_jsonl.exists():
        raise FileNotFoundError(f"parsed document jsonl not found: {input_jsonl}")
    if not input_features.exists():
        raise FileNotFoundError(f"feature table not found: {input_features}")
    if not resource_xlsx.exists():
        raise FileNotFoundError(f"resource constraints xlsx not found: {resource_xlsx}")

    classification_rows = load_csv(classification_results)
    parsed_records = load_jsonl(input_jsonl)
    feature_rows = load_csv(input_features)
    scenarios = load_resource_scenarios(resource_xlsx)

    config = ReviewPrioritizationConfig()
    priority_rows, meta = build_priority_rows(classification_rows, parsed_records, feature_rows, config)
    summary_rows = summarize_priority(priority_rows)
    plan_rows, allocation_rows = allocate_resources(priority_rows, scenarios)

    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "review_priority_results.csv"
    summary_path = output_dir / "review_priority_summary.csv"
    plan_path = output_dir / "resource_plan.csv"
    allocation_path = output_dir / "resource_allocations.csv"
    meta_path = output_dir / "review_priority_meta.json"

    write_csv(results_path, priority_rows)
    write_csv(summary_path, summary_rows)
    write_csv(plan_path, plan_rows)
    write_csv(allocation_path, allocation_rows)

    meta.update(
        {
            "total_documents": len(priority_rows),
            "classification_results": str(classification_results),
            "input_jsonl": str(input_jsonl),
            "input_features": str(input_features),
            "resource_xlsx": str(resource_xlsx),
            "scenarios": scenarios,
            "outputs": {
                "results": str(results_path),
                "summary": str(summary_path),
                "resource_plan": str(plan_path),
                "allocations": str(allocation_path),
            },
        }
    )
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    level_counts: dict[str, int] = {}
    for row in priority_rows:
        level = str(row.get("priority_level") or "")
        level_counts[level] = level_counts.get(level, 0) + 1

    print(f"prioritized={len(priority_rows)}")
    print("priority=" + ", ".join(f"{key}:{value}" for key, value in sorted(level_counts.items())))
    print(f"scenarios={len(scenarios)}")
    print(f"results -> {results_path}")
    print(f"summary -> {summary_path}")
    print(f"resource_plan -> {plan_path}")
    print(f"allocations -> {allocation_path}")
    print(f"meta -> {meta_path}")


if __name__ == "__main__":
    main()

