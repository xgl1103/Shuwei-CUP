from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build document feature table")
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=Path("b_solution/data/parsed_documents.jsonl"),
        help="parsed document jsonl input",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("b_solution/data/document_features.csv"),
        help="feature table output csv",
    )
    return parser


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from bdoc.features import FeatureConfig, build_feature_row, sanitize_feature_value

    args = build_parser().parse_args()
    input_jsonl = (
        args.input_jsonl if args.input_jsonl.is_absolute() else (project_root.parent / args.input_jsonl)
    )
    output_csv = args.output_csv if args.output_csv.is_absolute() else (project_root.parent / args.output_csv)

    if not input_jsonl.exists():
        raise FileNotFoundError(f"parsed document jsonl not found: {input_jsonl}")

    rows: list[dict[str, object]] = []
    with input_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            feature_row = build_feature_row(record, FeatureConfig())
            feature_row = {
                key: sanitize_feature_value(value)
                for key, value in feature_row.items()
                if key != "analysis_text"
            }
            rows.append(feature_row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"features={len(rows)}")
    print(f"output -> {output_csv}")


if __name__ == "__main__":
    main()
