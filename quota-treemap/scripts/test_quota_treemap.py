"""Offline tests: fake Claude Code and Codex homes in a temporary directory."""
import csv
import datetime
import glob
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
import collect  # noqa: E402


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        for r in records:
            handle.write(json.dumps(r) + "\n")


class QuotaTreemapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        now = datetime.datetime.now(datetime.timezone.utc)
        self.recent = (now - datetime.timedelta(days=2)).isoformat().replace("+00:00", "Z")
        self.old = (now - datetime.timedelta(days=60)).isoformat().replace("+00:00", "Z")
        usage = {"input_tokens": 100, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1000, "output_tokens": 10}
        assistant = {"type": "assistant", "requestId": "r1", "message": {"id": "m1", "usage": usage}}
        streamed = {"type": "assistant", "requestId": "r1", "message": {"id": "m1", "usage": dict(usage, output_tokens=20)}}
        write_jsonl(os.path.join(self.root, "claude", "projects", "a", "s1.jsonl"), [
            {"type": "user", "timestamp": self.recent, "cwd": "/src/side-project", "message": {"content": "fix the side project"}},
            assistant,
            streamed,  # same message logged again with its final usage: counted once, last record wins
        ])
        write_jsonl(os.path.join(self.root, "codex", "sessions", "2026", "s2.jsonl"), [
            {"type": "session_meta", "payload": {"cwd": "/src/unknown", "timestamp": self.old}},
            {"type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": "work on the portfolio blog"}]}},
            {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 300, "cached_input_tokens": 100, "output_tokens": 20}}}},
        ])
        self.data = os.path.join(self.root, "data")

    def tearDown(self):
        self.tmp.cleanup()

    def collect(self):
        collect.main(["--machine", "test", "--out", self.data,
                      "--source", f"personal=claude:{os.path.join(self.root, 'claude')}",
                      "--source", f"personal=codex:{os.path.join(self.root, 'codex')}"])
        with open(os.path.join(self.data, "sessions-test.tsv"), newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_weights_and_dedupe(self):
        rows = {r["kind"]: r for r in self.collect()}
        self.assertEqual(rows["claude"]["weight"], str(round(100 + 0.1 * 1000 + 5 * 20)))
        self.assertEqual(rows["codex"]["weight"], str(round(200 + 0.1 * 100 + 5 * 20)))
        self.assertEqual(rows["codex"]["first"], "work on the portfolio blog")

    def test_build_windows_rules_and_history(self):
        self.collect()
        rules = os.path.join(self.root, "rules.json")
        with open(os.path.join(HERE, "..", "rules.example.json")) as src, open(rules, "w") as dst:
            dst.write(src.read())
        build.main(["--data", self.data, "--rules", rules, "--tz", "UTC"])
        snaps = glob.glob(os.path.join(self.data, "history", "*.json"))
        self.assertEqual(len(snaps), 1)
        with open(snaps[0]) as handle:
            snap = json.load(handle)
        names30 = {t["name"] for t in snap["data"]["30"]}
        names90 = {t["name"] for t in snap["data"]["90"]}
        self.assertEqual(names30, {"Side project"})
        self.assertEqual(names90, {"Side project", "Portfolio + blog"})  # matched on the first prompt
        with open(os.path.join(self.data, "treemap.html")) as handle:
            page = handle.read()
        self.assertNotIn("__DATA__", page)
        self.assertIn("Side project", page)

    def build_with(self, projects):
        self.collect()
        rules = os.path.join(self.root, "rules.json")
        with open(rules, "w") as handle:
            json.dump({"groups": {"personal": "#199e70"}, "fallback": "personal", "projects": projects}, handle)
        build.main(["--data", self.data, "--rules", rules, "--tz", "UTC"])
        with open(os.path.join(self.data, "treemap.html")) as handle:
            return handle.read()

    def test_labels_cannot_break_the_page(self):
        page = self.build_with([{"name": "x </script><b> __TOTALS__", "group": "personal", "match": ["side-project"]}])
        script = page.split("<script>", 1)[1]
        self.assertEqual(script.count("</script>"), 1)  # only the real closing tag
        self.assertIn("__TOTALS__", script.split("const D=", 1)[1].split(";", 1)[0])  # label kept literally
        self.assertNotIn("__DATA__", page)

    def test_shares_are_not_rounded_for_layout(self):
        tiles, _ = build.summarize([{"ts": self.recent, "weight": 1.0, "kind": "claude", "remote": "", "cwd": f"/p{i}", "first": ""} for i in range(180)],
                                   {"projects": [{"name": f"p{i}", "group": "personal", "match": [f"/p{i}"]} for i in range(180)]},
                                   30, datetime.datetime.now(datetime.timezone.utc))
        self.assertAlmostEqual(sum(t["pct"] for t in tiles), 100.0, places=6)

    def test_rules_are_validated(self):
        bad = os.path.join(self.root, "bad.json")
        with open(bad, "w") as handle:
            json.dump({"projects": [{"name": "x", "group": "personal", "match": "a string"}]}, handle)
        with self.assertRaises(SystemExit):
            build.load_rules(bad)

    def test_offset_free_timestamp_is_utc(self):
        now = datetime.datetime(2026, 1, 10, tzinfo=datetime.timezone.utc)
        self.assertEqual(build.age_days("2026-01-08T00:00:00", now), 2)

    def test_unmatched_goes_to_fallback(self):
        rules = {"groups": {"personal": "#000"}, "fallback": "personal", "projects": []}
        self.assertEqual(build.classify({"remote": "", "cwd": "/x", "first": ""}, rules), ("Other personal", "personal"))


if __name__ == "__main__":
    unittest.main()
