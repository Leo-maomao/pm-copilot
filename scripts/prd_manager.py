#!/usr/bin/env python3
"""Read-only local browser for PM Copilot PRD HTML outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
import re
import socket
import subprocess
import sys
import threading
import webbrowser
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


HOST = "localhost"
LAN_HOST = "0.0.0.0"
PORT = 57391
ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "tools" / "prd-manager"
IGNORED_DIRECTORIES = {
    "node_modules", "vendor", "__pycache__", "dist", "build", ".cache", "Library",
    "venv", ".venv", ".tox", ".next", ".turbo", "Pods", "DerivedData", "target",
}
TITLE_DATE_RE = re.compile(r"^(?P<title>.+?)\s*[-－]\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$")


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.in_h1 = False
        self.ignored_depth = 0
        self.title: list[str] = []
        self.h1: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        self.in_title = self.in_title or tag == "title"
        self.in_h1 = self.in_h1 or tag == "h1"

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag == "h1":
            self.in_h1 = False

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        self.text.append(cleaned)
        if self.in_title:
            self.title.append(cleaned)
        if self.in_h1:
            self.h1.append(cleaned)


@dataclass(frozen=True)
class PrdDocument:
    id: str
    project: str
    title: str
    prd_date: str
    text: str
    modified_at: str
    modified_timestamp: float
    path: str

    def public(self) -> dict[str, object]:
        value = asdict(self)
        value.pop("path")
        value.pop("modified_at")
        value.pop("modified_timestamp")
        return value


def is_candidate_output_root(path: Path) -> bool:
    return path.name == "pm-copilot-outputs" and path.is_dir() and not path.is_symlink()


def parse_prd(path: Path, project: str) -> PrdDocument | None:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        parser = TextExtractor()
        parser.feed(source)
        parser.close()
        text = " ".join(parser.text)
        raw_title = " ".join(parser.title) or " ".join(parser.h1) or path.parent.name
        title_match = TITLE_DATE_RE.match(raw_title)
        title = title_match.group("title") if title_match else raw_title
        prd_date = title_match.group("date") if title_match else ""
        modified = path.stat().st_mtime
    except (OSError, ValueError):
        return None
    if not text:
        return None
    return PrdDocument(
        id=hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:20],
        project=project,
        title=title,
        prd_date=prd_date,
        text=text,
        modified_at=dt.datetime.fromtimestamp(modified).astimezone().isoformat(timespec="seconds"),
        modified_timestamp=modified,
        path=str(path.resolve()),
    )


def discover_documents(scan_root: Path) -> list[PrdDocument]:
    """Find only <project>/pm-copilot-outputs/<run-id>/prd.html documents."""
    documents: list[PrdDocument] = []
    for current, directories, _files in os.walk(scan_root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name for name in directories
            if not name.startswith(".") and name not in IGNORED_DIRECTORIES and not (current_path / name).is_symlink()
        ]
        if not is_candidate_output_root(current_path):
            continue
        project = current_path.parent.name
        for run in sorted(current_path.iterdir()):
            if run.name.startswith(".") or not run.is_dir() or run.is_symlink():
                continue
            document = parse_prd(run / "prd.html", project)
            if document:
                documents.append(document)
        directories[:] = []
    return sorted(documents, key=lambda item: (item.project.casefold(), item.prd_date or "0000-00-00", item.modified_timestamp, item.title.casefold()), reverse=True)


def local_network_address() -> str:
    """Return the local IPv4 address used for outbound LAN traffic."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 80))
        address = probe.getsockname()[0]
        if address and not address.startswith("127."):
            return address
    except OSError:
        pass
    finally:
        probe.close()
    return "<本机局域网IP>"


class Index:
    def __init__(self, scan_root: Path, cache_path: Path) -> None:
        self.scan_root = scan_root.resolve()
        self.cache_path = cache_path
        self.lock = threading.RLock()
        self.documents: dict[str, PrdDocument] = {}
        self.generated_at = ""
        self.scanning = False

    def refresh(self) -> bool:
        with self.lock:
            if self.scanning:
                return False
            self.scanning = True
        try:
            discovered = discover_documents(self.scan_root)
            with self.lock:
                self.documents = {document.id: document for document in discovered}
                self.generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
                self.scanning = False
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(json.dumps(self.payload(), ensure_ascii=False), encoding="utf-8")
        except OSError:
            with self.lock:
                self.scanning = False
            raise
        return True

    def payload(self) -> dict[str, object]:
        with self.lock:
            grouped: dict[str, list[PrdDocument]] = {}
            for document in self.documents.values():
                grouped.setdefault(document.project, []).append(document)
            projects = [
                {
                    "name": name,
                    "documents": [document.public() for document in sorted(items, key=lambda item: (item.prd_date or "0000-00-00", item.modified_timestamp, item.title), reverse=True)],
                }
                for name, items in sorted(
                    grouped.items(),
                    key=lambda item: (max((document.prd_date or "0000-00-00", document.modified_timestamp) for document in item[1]), item[0].casefold()),
                    reverse=True,
                )
            ]
            return {"generatedAt": self.generated_at, "projects": projects, "count": len(self.documents), "scanning": self.scanning}

    def get(self, document_id: str) -> PrdDocument | None:
        with self.lock:
            return self.documents.get(document_id)


class PrdManagerServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], index: Index) -> None:
        super().__init__(server_address, PrdManagerHandler)
        self.index = index


class PrdManagerHandler(BaseHTTPRequestHandler):
    server: PrdManagerServer

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("PRD manager: " + format % args + "\n")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/index":
            return self.send_json(self.server.index.payload())
        if parsed.path == "/":
            return self.send_file(STATIC_ROOT / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path in {"/app.js", "/app.css", "/logo.svg"}:
            return self.send_file(STATIC_ROOT / parsed.path[1:])
        if parsed.path.startswith("/document/"):
            return self.serve_document(parsed.path)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        request_path = urlparse(self.path).path
        if request_path == "/api/refresh":
            try:
                self.server.index.refresh()
            except OSError as error:
                self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self.send_json(self.server.index.payload())
            return
        if request_path.startswith("/api/document/"):
            pieces = [unquote(piece) for piece in request_path.split("/") if piece]
            if len(pieces) == 4 and pieces[3] == "copy":
                return self.copy_document(pieces[2])
            return self.reveal_document(request_path)
        self.send_error(HTTPStatus.NOT_FOUND)

    def reveal_document(self, request_path: str) -> None:
        pieces = [unquote(piece) for piece in request_path.split("/") if piece]
        if len(pieces) != 4 or pieces[0] != "api" or pieces[1] != "document" or pieces[3] != "reveal":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        document = self.server.index.get(pieces[2])
        if not document:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            run_root = Path(document.path).parent.resolve(strict=True)
            run_root.relative_to(self.server.index.scan_root)
        except (OSError, ValueError):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if sys.platform != "darwin":
            self.send_json({"error": "Opening the PRD folder is only supported on macOS."}, HTTPStatus.NOT_IMPLEMENTED)
            return
        try:
            subprocess.run(["open", str(run_root)], check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def copy_document(self, document_id: str) -> None:
        document = self.server.index.get(document_id)
        if not document:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            run_root = Path(document.path).parent.resolve(strict=True)
            run_root.relative_to(self.server.index.scan_root)
        except (OSError, ValueError):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if sys.platform != "darwin":
            self.send_json({"error": "复制目录仅支持 macOS。"}, HTTPStatus.NOT_IMPLEMENTED)
            return
        try:
            subprocess.run(["pbcopy"], input=str(run_root).encode("utf-8"), check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def serve_document(self, request_path: str) -> None:
        pieces = [unquote(piece) for piece in request_path.split("/") if piece]
        if len(pieces) < 2:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        document = self.server.index.get(pieces[1])
        if not document:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        target = Path(document.path)
        if len(pieces) > 2:
            target = target.parent.joinpath(*pieces[2:])
        try:
            target = target.resolve()
            run_root = Path(document.path).parent.resolve()
            target.relative_to(run_root)
        except (OSError, ValueError):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        self.send_file(target)

    def send_file(self, path: Path, content_type: str | None = None) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-root", type=Path, default=Path.home(), help="Directory to scan (defaults to the current user home)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser after startup")
    parser.add_argument("--lan", action="store_true", help="Expose the manager on the local network (default is localhost only)")
    args = parser.parse_args()
    cache_path = Path.home() / ".pm-copilot-prd-manager" / "index.json"
    index = Index(args.scan_root, cache_path)
    try:
        bind_host = LAN_HOST if args.lan else HOST
        server = PrdManagerServer((bind_host, PORT), index)
    except OSError as error:
        display_host = local_network_address() if args.lan else HOST
        print(f"Cannot start PRD manager at http://{display_host}:{PORT}: {error}", file=sys.stderr)
        return 1
    url = f"http://{HOST}:{PORT}"
    share_url = f"http://{local_network_address()}:{PORT}" if args.lan else ""
    threading.Thread(target=index.refresh, daemon=True, name="prd-indexer").start()
    if share_url:
        print(f"PRD manager is running at {url}; LAN URL: {share_url}; the first index is being built in the background.")
    else:
        print(f"PRD manager is running at {url}; the first index is being built in the background.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
