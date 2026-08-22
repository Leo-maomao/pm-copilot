#!/usr/bin/env python3
"""Regression coverage for the read-only PRD manager discovery and HTTP surface."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from prd_manager import Index, PrdManagerServer, discover_documents


HTML = "<html><head><title>测试 PRD</title></head><body><h1>测试 PRD</h1><p>支持全局搜索。</p></body></html>"


class PrdManagerTest(unittest.TestCase):
    def create_prd(self, root: Path, project: str, run: str, content: str = HTML) -> Path:
        path = root / project / "pm-copilot-outputs" / run / "prd.html"
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_discovers_only_direct_global_output_prds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_prd(root, "seaart-video-editor", "run-a")
            self.create_prd(root, "seaart-video-editor", "run-b", "<title>第二份</title><h1>第二份</h1>")
            wrong = root / "ignored" / "outputs" / "run" / "prd.html"
            wrong.parent.mkdir(parents=True)
            wrong.write_text(HTML, encoding="utf-8")
            hidden = root / ".hidden" / "project" / "pm-copilot-outputs" / "run" / "prd.html"
            hidden.parent.mkdir(parents=True)
            hidden.write_text(HTML, encoding="utf-8")
            documents = discover_documents(root)
            self.assertEqual(len(documents), 2)
            self.assertEqual({item.project for item in documents}, {"seaart-video-editor"})
            self.assertEqual({item.title for item in documents}, {"测试 PRD", "第二份"})
            self.assertEqual({item.prd_date for item in documents}, {"", ""})

    def test_splits_prd_title_and_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_prd(root, "project", "run", "<title>需求名称 - 2026-08-21</title><h1>需求名称 - 2026-08-21</h1>")
            document = discover_documents(root)[0]
            self.assertEqual(document.title, "需求名称")
            self.assertEqual(document.prd_date, "2026-08-21")

    def test_projects_and_documents_sort_by_prd_title_date_descending(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_prd(root, "older-project", "run-a", "<title>旧需求 - 2026-08-01</title><h1>旧需求</h1>")
            self.create_prd(root, "newer-project", "run-a", "<title>较早需求 - 2026-08-10</title><h1>较早需求</h1>")
            self.create_prd(root, "newer-project", "run-b", "<title>最新需求 - 2026-08-21</title><h1>最新需求</h1>")
            index = Index(root, root / "cache" / "index.json")
            index.refresh()
            projects = index.payload()["projects"]
            self.assertEqual([project["name"] for project in projects], ["newer-project", "older-project"])
            self.assertEqual([document["title"] for document in projects[0]["documents"]], ["最新需求", "较早需求"])

    def test_ignores_missing_or_empty_prd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "project" / "pm-copilot-outputs" / "missing").mkdir(parents=True)
            self.create_prd(root, "project", "empty", "<html><body></body></html>")
            self.assertEqual(discover_documents(root), [])

    def test_excludes_styles_and_scripts_from_search_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_prd(root, "project", "run", "<title>标题</title><style>hidden-rule</style><script>hidden-script</script><h1>正文</h1>")
            document = discover_documents(root)[0]
            self.assertIn("正文", document.text)
            self.assertNotIn("hidden-rule", document.text)
            self.assertNotIn("hidden-script", document.text)

    def test_index_and_document_endpoint_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_prd(root, "project", "run")
            index = Index(root, root / "cache" / "index.json")
            index.refresh()
            self.assertTrue((root / "cache" / "index.json").is_file())
            document = next(iter(index.documents.values()))
            server = PrdManagerServer(("localhost", 0), index)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = HTTPConnection("localhost", server.server_port)
                connection.request("GET", "/api/index")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read())["count"], 1)
                connection.request("GET", f"/document/{document.id}/")
                self.assertEqual(connection.getresponse().status, 200)
                connection.request("GET", f"/document/{document.id}/../outside")
                self.assertEqual(connection.getresponse().status, 403)
                connection.request("GET", "/api/index")
                self.assertEqual(connection.getresponse().status, 200)
            finally:
                server.shutdown()
                server.server_close()

    @patch("prd_manager.subprocess.run")
    def test_reveal_opens_only_the_indexed_prd_run_directory(self, open_directory: object) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document_path = self.create_prd(root, "project", "run")
            index = Index(root, root / "cache" / "index.json")
            index.refresh()
            document = next(iter(index.documents.values()))
            server = PrdManagerServer(("localhost", 0), index)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = HTTPConnection("localhost", server.server_port)
                connection.request("POST", f"/api/document/{document.id}/reveal")
                response = connection.getresponse()
                if sys.platform == "darwin":
                    self.assertEqual(response.status, 204)
                    open_directory.assert_called_once_with(["open", str(document_path.parent.resolve())], check=True)
                else:
                    self.assertEqual(response.status, 501)
                    open_directory.assert_not_called()
                connection.request("POST", "/api/document/not-indexed/reveal")
                self.assertEqual(connection.getresponse().status, 404)
                connection.request("GET", f"/api/document/{document.id}/reveal")
                self.assertEqual(connection.getresponse().status, 404)
            finally:
                server.shutdown()
                server.server_close()


class PrdManagerBrowserTest(unittest.TestCase):
    def test_search_keyboard_flow(self) -> None:
        try:
            from playwright.sync_api import Error, sync_playwright
        except ImportError as error:  # pragma: no cover - CI installs requirements-dev.txt
            self.skipTest(f"Playwright is unavailable: {error}")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "project-a" / "pm-copilot-outputs" / "run-a" / "prd.html"
            second = root / "project-b" / "pm-copilot-outputs" / "run-b" / "prd.html"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("<title>当前 PRD</title><h1>当前 PRD</h1><p>needle-current</p>", encoding="utf-8")
            second.write_text("<title>全局 PRD</title><h1>全局 PRD</h1><p>needle-global</p>", encoding="utf-8")
            index = Index(root, root / "cache" / "index.json")
            index.refresh()
            server = PrdManagerServer(("localhost", 0), index)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as playwright:
                    try:
                        browser = playwright.chromium.launch()
                    except Error:
                        browser = playwright.chromium.launch(channel="chrome")
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.goto(f"http://localhost:{server.server_port}", wait_until="networkidle")
                    page.locator("#document-viewer").wait_for(state="visible")
                    reveal_button = page.get_by_role("button", name="在访达中打开 当前 PRD 所在目录")
                    self.assertEqual(reveal_button.count(), 1)
                    page.locator(".document-item", has_text="当前 PRD").click()
                    page.frame_locator("#document-viewer").get_by_role("heading", name="当前 PRD").wait_for()
                    self.assertEqual(page.locator("#recent").count(), 0)
                    page.locator("#sidebar-toggle").click()
                    page.wait_for_timeout(220)
                    self.assertTrue("sidebar-collapsed" in (page.locator(".app-shell").get_attribute("class") or ""))
                    self.assertTrue(page.locator("#tree").is_hidden())
                    self.assertLessEqual(page.locator(".sidebar").evaluate("node => node.getBoundingClientRect().width"), 56)
                    page.locator("#sidebar-toggle").click()
                    self.assertTrue(page.locator("#tree").is_visible())
                    first_project = page.locator(".project").first
                    first_project.locator(".project-toggle").click()
                    self.assertTrue("collapsed" in (first_project.get_attribute("class") or ""))
                    self.assertTrue(first_project.locator(".document-list").is_hidden())
                    first_project.locator(".project-toggle").click()
                    self.assertFalse("collapsed" in (first_project.get_attribute("class") or ""))
                    self.assertTrue(first_project.locator(".document-list").is_visible())
                    page.keyboard.press("Control+f")
                    self.assertTrue(page.locator("#search-dialog").evaluate("node => node.open"))
                    self.assertEqual(page.locator("#close-search").count(), 0)
                    self.assertTrue(page.locator("#clear-search").is_hidden())
                    page.locator("#search-input").fill("needle-current")
                    self.assertEqual(page.locator(".result").count(), 1)
                    self.assertEqual(page.locator(".result.selected").count(), 0)
                    self.assertTrue(page.locator("#clear-search").is_visible())
                    self.assertIn("needle-current", page.locator(".result-snippet").text_content() or "")
                    page.locator("#clear-search").click()
                    self.assertEqual(page.locator(".result").count(), 0)
                    self.assertTrue(page.locator("#clear-search").is_hidden())
                    page.locator("#search-input").dispatch_event("compositionstart")
                    page.locator("#search-input").fill("needle-global")
                    self.assertEqual(page.locator(".result").count(), 0)
                    page.locator("#search-input").dispatch_event("compositionend")
                    self.assertIn("找到 1 份", page.locator("#search-summary").text_content() or "")
                    page.get_by_role("option", name="全局 PRD project-b").click()
                    page.frame_locator("#document-viewer").get_by_role("heading", name="全局 PRD").wait_for()
                    page.keyboard.press("Control+f")
                    page.locator("#search-input").fill("no-result")
                    page.keyboard.press("Escape")
                    self.assertFalse(page.locator("#search-dialog").evaluate("node => node.open"))
                    page.keyboard.press("Control+f")
                    page.mouse.click(2, 2)
                    self.assertFalse(page.locator("#search-dialog").evaluate("node => node.open"))
                    self.assertEqual(page.locator(".toolbar").count(), 0)
                    self.assertEqual(page.locator(".app-shell").evaluate("node => node.scrollWidth <= window.innerWidth"), True)
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
