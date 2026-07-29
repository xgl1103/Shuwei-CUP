from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refine discovered topic clusters into concrete content families")
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=Path("b_solution/data/parsed_documents.jsonl"),
        help="parsed document jsonl input",
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
        help="raw dataset1 topic summary csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("b_solution/outputs/topic_discovery"),
        help="topic discovery output directory",
    )
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
    sys.path.insert(0, str(project_root / "src"))

    from bdoc.topic_families import refine_topic_families

    args = build_parser().parse_args()
    input_jsonl = args.input_jsonl if args.input_jsonl.is_absolute() else (project_root.parent / args.input_jsonl)
    topic_assignments = (
        args.topic_assignments
        if args.topic_assignments.is_absolute()
        else (project_root.parent / args.topic_assignments)
    )
    topic_summary = args.topic_summary if args.topic_summary.is_absolute() else (project_root.parent / args.topic_summary)
    output_dir = args.output_dir if args.output_dir.is_absolute() else (project_root.parent / args.output_dir)

    if not input_jsonl.exists():
        raise FileNotFoundError(f"parsed document jsonl not found: {input_jsonl}")
    if not topic_assignments.exists():
        raise FileNotFoundError(f"topic assignments not found: {topic_assignments}")
    if not topic_summary.exists():
        raise FileNotFoundError(f"topic summary not found: {topic_summary}")

    records = load_jsonl(input_jsonl)
    assignments = load_csv(topic_assignments)
    summary = load_csv(topic_summary)
    refined_rows = refine_topic_families(records, assignments, summary)
    if not refined_rows:
        raise ValueError("no topic families were refined")

    output_dir.mkdir(parents=True, exist_ok=True)
    family_summary_path = output_dir / "topic_family_summary.csv"
    refined_summary_path = output_dir / "topic_summary_refined.csv"
    family_map_path = output_dir / "topic_family_map.csv"

    write_csv(family_summary_path, refined_rows)
    write_csv(refined_summary_path, refined_rows)

    map_rows = [
        {
            "cluster_id": row["cluster_id"],
            "raw_topic_name": row["raw_topic_name"],
            "topic_name": row["topic_name"],
            "family_confidence": row["family_confidence"],
            "family_reason": row["family_reason"],
            "family_second": row["family_second"],
        }
        for row in refined_rows
    ]
    write_csv(family_map_path, map_rows)

    print(f"refined_topics={len(refined_rows)}")
    print(f"family_summary -> {family_summary_path}")
    print(f"refined_summary -> {refined_summary_path}")
    print(f"family_map -> {family_map_path}")


if __name__ == "__main__":
    main()
