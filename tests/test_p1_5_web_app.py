from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.providers.mock import MockProvider
from backend.storage.sqlite import CaptureStore


ROOT = Path(__file__).parent.parent


class P15WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "web.sqlite3"
        settings = Settings(
            app_env="test",
            ai_provider="mock",
            database_path=path,
            auth_mode="dev",
            api_auth_token=None,
            allowed_origins=("http://127.0.0.1:8000",),
        )
        self.client = TestClient(
            create_app(
                settings=settings,
                store=CaptureStore(path),
                provider=MockProvider(),
            )
        )

    def test_root_redirects_to_operational_web_app(self) -> None:
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/app/")
        app = self.client.get("/app/")
        self.assertEqual(app.status_code, 200)
        self.assertIn("Today", app.text)
        self.assertIn("Inbox", app.text)
        self.assertIn("Projects", app.text)
        self.assertIn("Pending", app.text)
        self.assertIn("Reports", app.text)

    def test_html_is_mobile_first_accessible_and_has_no_inline_script(self) -> None:
        text = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="viewport"', text)
        self.assertIn("width=device-width", text)
        self.assertIn("Skip to content", text)
        self.assertIn('aria-live="polite"', text)
        self.assertIn('type="password"', text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("onclick=", text)

    def test_manifest_and_service_worker_define_review_only_pwa(self) -> None:
        manifest = json.loads(
            (ROOT / "web" / "manifest.webmanifest").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["start_url"], "/app/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertGreaterEqual(len(manifest["icons"]), 1)
        worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("/app/index.html", worker)
        self.assertNotIn("/api/v1/captures", worker)
        self.assertNotIn("raw_content", worker)

    def test_css_has_touch_targets_and_mobile_breakpoints(self) -> None:
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("min-height: 44px", css)
        self.assertIn("@media (min-width: 48rem)", css)
        self.assertIn("@media (min-width: 64rem)", css)
        self.assertNotIn("linear-gradient", css)

    def test_javascript_covers_pages_states_actions_and_safe_rendering(self) -> None:
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        for label in ("today", "inbox", "projects", "pending", "reports"):
            self.assertIn(label, script.casefold())
        for state in ("Loading", "Nothing to review", "Retry", "Keep raw", "Dismiss processing", "Assign project"):
            self.assertIn(state, script)
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)

    def test_static_assets_are_served_with_security_headers(self) -> None:
        for path in (
            "/app/styles.css",
            "/app/app.js",
            "/app/lib.mjs",
            "/app/manifest.webmanifest",
            "/app/icon.svg",
            "/app/sw.js",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["x-content-type-options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
