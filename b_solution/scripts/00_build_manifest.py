from __future__ import annotations

import csv
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from bdoc.manifest import iter_files, to_rows

    data_root = project_root.parent / "B题数据集" / "数据集"
    output_path = project_root / "data" / "file_manifest.csv"

    records = to_rows(iter_files(data_root))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["dataset", "file_path", "file_name", "suffix", "size_bytes"],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"saved {len(records)} rows -> {output_path}")


if __name__ == "__main__":
    main()

