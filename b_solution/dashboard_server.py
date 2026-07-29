from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
PARSED_INDEX = ROOT / "data" / "parsed_documents_index.csv"


def load_doc_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    if not PARSED_INDEX.exists():
        return paths
    with PARSED_INDEX.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            doc_id = row.get("doc_id", "")
            file_path = row.get("file_path", "")
            if doc_id and file_path:
                paths[doc_id] = Path(file_path)
    return paths


DOC_PATHS = load_doc_paths()


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[dashboard] " + (fmt % args) + "\n")

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/doc-path":
            self.handle_doc_path(parsed.query)
            return
        if parsed.path == "/api/open-file":
            self.handle_open(parsed.query, select=False)
            return
        if parsed.path == "/api/show-file":
            self.handle_open(parsed.query, select=True)
            return
        super().do_GET()

    def resolve_doc_path(self, query: str) -> tuple[str, Path | None]:
        params = parse_qs(query)
        doc_id = unquote(params.get("doc_id", [""])[0])
        return doc_id, DOC_PATHS.get(doc_id)

    def handle_doc_path(self, query: str) -> None:
        doc_id, path = self.resolve_doc_path(query)
        if not doc_id:
            self.send_json(400, {"ok": False, "error": "missing doc_id"})
            return
        if path is None:
            self.send_json(404, {"ok": False, "error": "doc_id not found", "doc_id": doc_id})
            return
        self.send_json(200, {"ok": True, "doc_id": doc_id, "path": str(path), "exists": path.exists()})

    def handle_open(self, query: str, select: bool) -> None:
        doc_id, path = self.resolve_doc_path(query)
        if not doc_id:
            self.send_json(400, {"ok": False, "error": "missing doc_id"})
            return
        if path is None:
            self.send_json(404, {"ok": False, "error": "doc_id not found", "doc_id": doc_id})
            return
        if not path.exists():
            self.send_json(404, {"ok": False, "error": "file not found", "doc_id": doc_id, "path": str(path)})
            return

        try:
            if select:
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc), "doc_id": doc_id, "path": str(path)})
            return
        self.send_json(200, {"ok": True, "doc_id": doc_id, "path": str(path), "action": "show" if select else "open"})


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("BDOC_DASHBOARD_PORT", "5178"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Serving B question dashboard at http://{host}:{port}/dashboard/index.html")
    print(f"Manual audit page: http://{host}:{port}/dashboard/index.html?view=audit")
    server.serve_forever()


if __name__ == "__main__":
    main()
