from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(iterable, **kwargs):  # type: ignore
        return iterable


def load_manifest(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sanitize_value(value):
    if isinstance(value, str):
        return "".join(ch for ch in value if not 0xD800 <= ord(ch) <= 0xDFFF)
    if isinstance(value, dict):
        return {key: sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    return value


def cache_key_for_path(path: Path, backend_name: str) -> str:
    resolved = path.resolve()
    stat = resolved.stat()
    raw = f"{backend_name}|{resolved}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()


def with_path_ocr_cache(ocr_backend, backend_name: str, cache_dir: Path | None):
    if ocr_backend is None or cache_dir is None:
        return ocr_backend

    cache_dir.mkdir(parents=True, exist_ok=True)

    def cached_backend(source):
        if not isinstance(source, Path):
            return ocr_backend(source)

        cache_path = cache_dir / f"{cache_key_for_path(source, backend_name)}.txt"
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8", errors="ignore")

        text = ocr_backend(source)
        cache_path.write_text(text or "", encoding="utf-8")
        return text

    return cached_backend


def replace_or_keep_new(tmp_path: Path, target_path: Path) -> Path:
    try:
        tmp_path.replace(target_path)
        return target_path
    except PermissionError:
        fallback = target_path.with_name(f"{target_path.stem}_new{target_path.suffix}")
        if fallback.exists():
            fallback.unlink()
        tmp_path.replace(fallback)
        print(f"warning: target locked, wrote fallback -> {fallback}")
        return fallback


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse B-question documents")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("b_solution/data/file_manifest.csv"),
        help="path to the file manifest csv",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("b_solution/data/parsed_documents.jsonl"),
        help="full parsed document output",
    )
    parser.add_argument(
        "--output-index",
        type=Path,
        default=Path("b_solution/data/parsed_documents_index.csv"),
        help="compact index csv output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="parse only the first N files for sampling; 0 means all files",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="disable OCR loading for image files",
    )
    parser.add_argument(
        "--ocr-cache-dir",
        type=Path,
        default=Path("b_solution/data/ocr_cache"),
        help="cache OCR text for image files; only Path-based image OCR is cached",
    )
    parser.add_argument(
        "--no-ocr-cache",
        action="store_true",
        help="disable OCR cache",
    )
    parser.add_argument("--max-pdf-pages", type=int, default=25)
    parser.add_argument("--max-xlsx-rows", type=int, default=40)
    parser.add_argument("--max-xlsx-cols", type=int, default=15)
    parser.add_argument("--max-chars", type=int, default=20_000)
    parser.add_argument("--ocr-language", type=str, default="chi_sim+eng")
    parser.add_argument(
        "--docx-ocr-min-text-chars",
        type=int,
        default=0,
        help="run embedded-image OCR for docx when extracted text+tables are at or below this size; 0 preserves conservative behavior",
    )
    parser.add_argument(
        "--pdf-ocr-min-text-chars",
        type=int,
        default=0,
        help="run page OCR for pdf when extracted text is at or below this size; 0 preserves conservative behavior",
    )
    return parser


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from bdoc.parser import ParseConfig, build_ocr_backend, parse_manifest_rows, to_dict

    args = build_parser().parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else (project_root.parent / args.manifest)
    output_jsonl = (
        args.output_jsonl if args.output_jsonl.is_absolute() else (project_root.parent / args.output_jsonl)
    )
    output_index = (
        args.output_index if args.output_index.is_absolute() else (project_root.parent / args.output_index)
    )

    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")

    config = ParseConfig(
        max_pdf_pages=args.max_pdf_pages,
        max_xlsx_rows=args.max_xlsx_rows,
        max_xlsx_cols=args.max_xlsx_cols,
        max_chars=args.max_chars,
        include_ocr=not args.no_ocr,
        ocr_language=args.ocr_language,
        docx_ocr_min_text_chars=args.docx_ocr_min_text_chars,
        pdf_ocr_min_text_chars=args.pdf_ocr_min_text_chars,
    )

    ocr_backend = None
    ocr_name = "disabled"
    if config.include_ocr:
        ocr_backend, ocr_name = build_ocr_backend(config.ocr_language)
        if ocr_backend is not None and not args.no_ocr_cache:
            ocr_cache_dir = (
                args.ocr_cache_dir
                if args.ocr_cache_dir.is_absolute()
                else (project_root.parent / args.ocr_cache_dir)
            )
            ocr_backend = with_path_ocr_cache(ocr_backend, ocr_name, ocr_cache_dir)

    rows = load_manifest(manifest_path)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_index.parent.mkdir(parents=True, exist_ok=True)

    index_fields = [
        "doc_id",
        "dataset",
        "file_path",
        "file_name",
        "suffix",
        "size_bytes",
        "title",
        "time_info",
        "page_count",
        "sheet_count",
        "parse_status",
        "content_truncated",
        "char_count",
        "parse_notes",
    ]

    output_jsonl_tmp = output_jsonl.with_suffix(output_jsonl.suffix + ".tmp")
    output_index_tmp = output_index.with_suffix(output_index.suffix + ".tmp")
    if output_jsonl_tmp.exists():
        output_jsonl_tmp.unlink()
    if output_index_tmp.exists():
        output_index_tmp.unlink()

    status_counter: Counter[str] = Counter()
    with output_jsonl_tmp.open("w", encoding="utf-8") as jsonl_f, output_index_tmp.open(
        "w", encoding="utf-8-sig", newline=""
    ) as index_f:
        writer = csv.DictWriter(index_f, fieldnames=index_fields)
        writer.writeheader()

        for row in tqdm(rows, total=len(rows), desc="Parsing"):
            for record in parse_manifest_rows(row, config, ocr_backend):
                data = sanitize_value(to_dict(record))
                jsonl_f.write(json.dumps(data, ensure_ascii=False) + "\n")

                writer.writerow({key: data.get(key, "") for key in index_fields})
                status_counter[record.parse_status] += 1

    final_jsonl = replace_or_keep_new(output_jsonl_tmp, output_jsonl)
    final_index = replace_or_keep_new(output_index_tmp, output_index)

    print(f"parsed={sum(status_counter.values())}")
    print(f"ocr_backend={ocr_name}")
    for key, value in sorted(status_counter.items()):
        print(f"{key}: {value}")
    print(f"jsonl -> {final_jsonl}")
    print(f"index -> {final_index}")


if __name__ == "__main__":
    main()
