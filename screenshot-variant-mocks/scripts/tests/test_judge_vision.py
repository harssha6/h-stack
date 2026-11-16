"""Offline contract checks with a local OpenAI-compatible HTTP fixture."""
import contextlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image

spec = importlib.util.spec_from_file_location("judge", Path(__file__).resolve().parents[1] / "judge_vision.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)


class JudgeTests(unittest.TestCase):
    def test_score_contract(self):
        good = {"legibility": 7, "verdict": "Readable", "biggest_risk": "Dense"}
        self.assertEqual(judge.parse(json.dumps(good), {"legibility": "Readable"}), good)
        for bad in (True, 11, 0, float("nan"), "7"):
            with self.assertRaises(ValueError):
                judge.parse(json.dumps({**good, "legibility": bad}), {"legibility": "Readable"})

    def run_fixture(self, status=200, redirect=False):
        requests = []
        secret = 'fixture-secret-with-"quote'

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                requests.append((self.path, self.headers["Authorization"],
                                 json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(302 if redirect else status)
                if redirect:
                    self.send_header("Location", "/should-not-follow")
                self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": {"content": json.dumps({
                    "legibility": 8, "verdict": secret, "biggest_risk": "Fixture"})}}]}).encode())

        with tempfile.TemporaryDirectory() as tmp, HTTPServer(("127.0.0.1", 0), Handler) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                folder = Path(tmp)
                Image.new("RGB", (20, 30)).save(folder / "a.png")
                rubric = folder / "rubric.json"
                rubric.write_text(json.dumps({"context": "{desc}", "criteria": {"legibility": "Readable"},
                    "items": {"a": {"image": "a.png", "desc": "Control"}}}))
                output = io.StringIO()
                with patch.dict(os.environ, {"VISION_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
                    "VISION_API_KEY_ENV": "FIXTURE_VISION_KEY", "FIXTURE_VISION_KEY": secret,
                    "VISION_MODELS": '["model-a", "model-b"]'}), patch("sys.argv", ["judge", str(rubric)]), contextlib.redirect_stdout(output):
                    result = judge.main()
                scores = (folder / "scores.json").read_text()
                self.assertNotIn(secret, output.getvalue())
                self.assertNotIn(secret, scores)
                self.assertNotIn(json.dumps(secret)[1:-1], scores)
                self.assertEqual(len(requests), 2, "Exactly one request per judge; no retries or redirects")
                for path, auth, body in requests:
                    self.assertEqual(path, "/v1/chat/completions")
                    self.assertEqual(auth, "Bearer " + secret)
                    self.assertTrue(body["messages"][0]["content"][0]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
                return result, json.loads(scores)
            finally:
                server.shutdown()
                worker.join()

    def test_two_judges_and_response_redaction(self):
        result, scores = self.run_fixture()
        self.assertEqual(result, 0)
        self.assertEqual(set(scores["a"]), {"model-a", "model-b"})
        self.assertEqual(scores["a"]["model-a"]["verdict"], "[REDACTED]")

    def test_provider_error_is_recorded_without_body(self):
        result, scores = self.run_fixture(status=401)
        self.assertEqual(result, 1)
        self.assertEqual(scores["a"]["model-a"], {"error": "HTTP 401"})

    def test_redirect_is_not_followed(self):
        result, scores = self.run_fixture(redirect=True)
        self.assertEqual(result, 1)
        self.assertEqual(scores["a"]["model-b"], {"error": "HTTP 302"})


if __name__ == "__main__":
    unittest.main()
