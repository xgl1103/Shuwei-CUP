from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class FileRecord:
    dataset: str
    file_path: str
    file_name: str
    suffix: str
    size_bytes: int


def detect_dataset(path: Path) -> str:
    for part in path.parts:
        if part.startswith("数据集1"):
            return "dataset1"
        if part.startswith("数据集2"):
            return "dataset2"
        if part.startswith("数据集3"):
            return "dataset3"
        if part.startswith("数据集4"):
            return "dataset4"
    return "unknown"


def iter_files(root: Path) -> Iterable[FileRecord]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        yield FileRecord(
            dataset=detect_dataset(path),
            file_path=str(path),
            file_name=path.name,
            suffix=path.suffix.lower(),
            size_bytes=path.stat().st_size,
        )


def to_rows(records: Iterable[FileRecord]) -> list[dict[str, object]]:
    return [asdict(record) for record in records]

