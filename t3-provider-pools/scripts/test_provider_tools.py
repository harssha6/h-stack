"""Offline contracts only: temp directories and a fake native app-server.

No native client, account, connector, external service or model is contacted.
"""

import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from provider_tools import SafeError, alignment_candidate, bridge_config, parse_json, write_candidate

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("apps_bridge", ROOT / "codex-apps-bridge.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Bridge = module.Bridge

FAKE_NATIVE = r'''
import json, os, sys, time
MODE = MODE_VALUE
LOG = LOG_VALUE
HOME = HOME_VALUE
def send(value):
    print(json.dumps(value), flush=True)
def record(value):
    with open(LOG, "a") as handle:
        handle.write(json.dumps(value) + "\n")
record({"argv": sys.argv[1:], "home": os.environ.get("CODEX_HOME"),
        "cwd": os.getcwd(), "forbiddenEnvPresent": any(key in os.environ for key in
        ["OPENAI_API_KEY", "CODEX_ACCESS_TOKEN", "HTTP_PROXY", "PRIVATE_TEST_TOKEN"])})
if MODE == "no_read":
    time.sleep(5)
    sys.exit(0)
for line in sys.stdin:
    message = json.loads(line)
    record(message)
    if "method" not in message or "id" not in message:
        continue
    method, rid = message["method"], message["id"]
    if MODE == "notification_flood":
        for _ in range(500):
            send({"method": "progress", "params": {}})
        continue
    if MODE == "bad_json":
        print("not-json", flush=True)
        continue
    if MODE == "oversized":
        print("x" * (1024 * 1024 + 1), flush=True)
        continue
    if MODE == "native_error":
        send({"id": rid, "error": {"message": "FAKE_BEARER_TOKEN_MUST_NOT_LEAK"}})
        continue
    if MODE == "both_fields":
        send({"id": rid, "result": {}, "error": {}})
        continue
    if MODE == "wrong_version":
        send({"jsonrpc": "1.0", "id": rid, "result": {}})
        continue
    if MODE == "events":
        send({"method": "progress", "params": {"private": "ignored"}})
        send({"id": 999999, "result": {"unrelated": True}})
        send({"id": True, "result": {"wrongIdType": True}})
        send({"id": "approval-request", "method": "requestApproval", "params": {}})
    if method == "initialize":
        result = {"serverInfo": {"version": "fixture"}}
    elif method == "thread/start":
        result = {"thread": {"id": "fixture-thread"}}
    elif method == "mcpServerStatus/list":
        tool = {"name": "fake.search", "description": "Fixture only",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
                "annotations": {"readOnlyHint": True}, "_meta": {"connector_id": "PRIVATE_FIXTURE_ID"}}
        tools = {} if MODE == "missing_tool" else {"fake.search": tool}
        if MODE == "new_protocol":
            tool["outputSchema"] = {"type": "object", "properties": {"found": {"type": "integer"}}}
        result = {"data": [{"name": "codex_apps", "tools": tools}], "nextCursor": None}
        if MODE == "pages":
            if message["params"]["cursor"] is None:
                result = {"data": [], "nextCursor": "next"}
        if MODE == "repeat_cursor":
            result = {"data": [], "nextCursor": "same"}
        if MODE == "tools_error":
            result["data"][0]["toolsError"] = "FAKE_BEARER_TOKEN_MUST_NOT_LEAK"
    elif method == "mcpServer/tool/call":
        if MODE == "call_timeout":
            time.sleep(5)
            continue
        result = {"content": [{"type": "text", "text": "fixture result"}],
                  "structuredContent": {"found": 1}, "isError": MODE == "app_error"}
        if MODE == "app_error":
            result["content"][0]["text"] = "FAKE_BEARER_TOKEN_MUST_NOT_LEAK"
            result["structuredContent"] = {"token": "FAKE_BEARER_TOKEN_MUST_NOT_LEAK"}
        if MODE == "new_protocol":
            result["content"].append({"type": "resource_link", "uri": "https://fixture.invalid/resource", "name": "fixture"})
        if MODE == "bad_content":
            result["content"] = [{"type": "text"}]
    else:
        send({"id": rid, "error": {"message": "unknown"}})
        continue
    send({"id": rid, "result": result})
'''


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "native-home"
        self.home.mkdir()
        self.log = self.root / "native-log.jsonl"
        self.bridge = None

    def tearDown(self):
        if self.bridge:
            self.bridge.close()
        self.temporary.cleanup()

    def config(self, mode="normal", timeout=10):
        executable = self.root / "fixture-native"
        source = FAKE_NATIVE.replace("MODE_VALUE", repr(mode)).replace("LOG_VALUE", repr(str(self.log))).replace("HOME_VALUE", repr(str(self.home)))
        executable.write_text("#!" + sys.executable + "\n" + textwrap.dedent(source))
        executable.chmod(0o700)
        return {"version": 1, "nativeExecutable": str(executable), "nativeHome": str(self.home),
                "allowedTools": {"search": "fake.search"}, "timeoutSeconds": timeout}

    def start_bridge(self, mode="normal", timeout=10):
        self.bridge = Bridge(bridge_config(self.config(mode, timeout)))
        response = self.bridge.message({"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}})
        self.assertIn("result", response)
        self.bridge.message({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self.bridge

    def request(self, method, params=None, rid=7):
        return self.bridge.message({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})

    def records(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_handshake_tool_schema_and_call_routing(self):
        self.start_bridge()
        listed = self.request("tools/list")["result"]["tools"]
        self.assertEqual(listed[0]["name"], "search")
        self.assertEqual(listed[0]["inputSchema"]["type"], "object")
        self.assertNotIn("_meta", listed[0])
        result = self.request("tools/call", {"name": "search", "arguments": {"query": "fixture"}}, rid="call")
        self.assertEqual(result["id"], "call")
        self.assertEqual(result["result"]["structuredContent"], {"found": 1})
        sent = [row for row in self.records() if row.get("method") == "mcpServer/tool/call"]
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["params"], {"threadId": "fixture-thread", "server": "codex_apps",
                         "tool": "fake.search", "arguments": {"query": "fixture"}})
        methods = [row.get("method") for row in self.records()]
        self.assertNotIn("turn/start", methods)
        thread = next(row for row in self.records() if row.get("method") == "thread/start")
        self.assertTrue(thread["params"]["ephemeral"])
        self.assertEqual(thread["params"]["approvalPolicy"], "untrusted")

    def test_selected_home_and_environment_isolation(self):
        prior = {key: os.environ.get(key) for key in ("OPENAI_API_KEY", "CODEX_ACCESS_TOKEN", "HTTP_PROXY", "PRIVATE_TEST_TOKEN")}
        try:
            for key in prior:
                os.environ[key] = "FAKE_BEARER_TOKEN_MUST_NOT_LEAK"
            self.start_bridge()
            self.assertIn("result", self.request("tools/list"))
            startup = self.records()[0]
            self.assertFalse(startup["forbiddenEnvPresent"])
            self.assertEqual(startup["home"], str(self.home))
            self.assertEqual(startup["cwd"], str(self.home))
            self.assertEqual(startup["argv"], ["app-server", "--stdio"])
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_notifications_unrelated_ids_and_interactive_refusal(self):
        self.start_bridge("events")
        self.assertIn("result", self.request("tools/list"))
        # A subsequent request establishes that the native child consumed the refusals.
        self.assertIn("result", self.request("tools/call", {"name": "search"}))
        replies = [row for row in self.records() if row.get("id") == "approval-request" and "error" in row]
        self.assertGreater(len(replies), 0)
        self.assertNotIn("result", replies[0])

    def test_pagination(self):
        self.start_bridge("pages")
        self.assertIn("result", self.request("tools/list"))
        queries = [row for row in self.records() if row.get("method") == "mcpServerStatus/list"]
        self.assertEqual([row["params"]["cursor"] for row in queries], [None, "next"])

    def test_failed_discovery_is_redacted_and_not_restarted(self):
        for mode in ("native_error", "both_fields", "wrong_version", "bad_json", "oversized",
                     "missing_tool", "repeat_cursor", "tools_error", "notification_flood"):
            with self.subTest(mode=mode):
                self.log.unlink(missing_ok=True)
                self.start_bridge(mode)
                result = self.request("tools/list")
                self.assertIn("error", result)
                self.assertNotIn("FAKE_BEARER", json.dumps(result))
                count = len(self.records())
                self.assertIn("error", self.request("tools/list"))
                self.assertEqual(len(self.records()), count)
                self.bridge.close()

    def test_partial_allowlist_discovery_cannot_publish_after_failure(self):
        self.start_bridge()
        self.bridge.config["allowed"]["unavailable"] = "missing.native.tool"
        self.assertIn("error", self.request("tools/list"))
        self.assertEqual(self.bridge.tools, {})
        self.assertIn("error", self.request("tools/list"))

    def test_call_timeout_not_replayed(self):
        self.start_bridge("call_timeout")
        self.assertIn("result", self.request("tools/list"))
        self.bridge.config["timeout"] = 1
        result = self.request("tools/call", {"name": "search"})
        self.assertIn("error", result)
        self.assertIn("outcome may be unknown", result["error"]["message"])
        self.assertIn("error", self.request("tools/call", {"name": "search"}))
        sent = [row for row in self.records() if row.get("method") == "mcpServer/tool/call"]
        self.assertLessEqual(len(sent), 1)
        self.assertTrue(self.bridge.failed)

    def test_app_errors_preserved_not_reported_as_success(self):
        self.start_bridge("app_error")
        result = self.request("tools/call", {"name": "search"})
        self.assertTrue(result["result"]["isError"])
        self.assertNotIn("FAKE_BEARER", json.dumps(result))
        self.assertNotIn("structuredContent", result["result"])
        self.assertFalse(self.bridge.failed)
        sent = [row for row in self.records() if row.get("method") == "mcpServer/tool/call"]
        self.assertEqual(len(sent), 1)

    def test_native_write_timeout_is_bounded(self):
        self.bridge = Bridge(bridge_config(self.config("no_read", timeout=0.1)))
        started = time.monotonic()
        with self.assertRaises(SafeError) as error:
            self.bridge.native.rpc("initialize", {"large": "x" * 500000})
        self.assertIn("timed out", str(error.exception))
        self.assertLess(time.monotonic() - started, 3)

    def test_invalid_call_and_invalid_result(self):
        self.start_bridge("bad_content")
        self.assertIn("error", self.request("tools/call", {"name": "other"}))
        self.assertIn("error", self.request("tools/call", {"name": "search", "arguments": []}))
        self.assertFalse(self.log.exists())
        self.assertIn("error", self.request("tools/call", {"name": "search"}))

    def test_handshake_required_and_bad_envelopes(self):
        self.bridge = Bridge(bridge_config(self.config()))
        self.assertIn("error", self.request("tools/list"))
        self.assertFalse(self.log.exists())
        for request in ([], {"id": 1, "method": "ping"}, {"jsonrpc": "2.0", "id": True, "method": "ping"},
                        {"jsonrpc": "2.0", "id": {}, "method": "ping"}):
            self.assertIn("error", self.bridge.message(request))

    def test_old_protocol_requests_negotiate_only_implemented_2025_version(self):
        self.bridge = Bridge(bridge_config(self.config("new_protocol")))
        response = self.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "fixture", "version": "1"}})
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertFalse(self.log.exists())
        # Only a client that accepts that version should send initialized.
        self.bridge.message({"jsonrpc": "2.0", "method": "notifications/initialized"})
        listed = self.request("tools/list")["result"]["tools"]
        self.assertIn("outputSchema", listed[0])
        result = self.request("tools/call", {"name": "search"})["result"]
        self.assertIn("structuredContent", result)
        self.assertEqual(result["content"][1]["type"], "resource_link")

    def test_strict_config_and_no_secret_errors(self):
        config = self.config()
        for mutation in (
            {"version": True}, {"timeoutSeconds": float("nan")}, {"nativeHome": "relative"},
            {"allowedTools": {}}, {"allowedTools": {"a": "same", "b": "same"}},
            {"apiKey": "FAKE_BEARER_TOKEN_MUST_NOT_LEAK"}, {"nativeExecutable": "/missing/FAKE_BEARER_TOKEN_MUST_NOT_LEAK"},
        ):
            with self.subTest(mutation=tuple(mutation)):
                with self.assertRaises(SafeError) as error:
                    bridge_config({**config, **mutation})
                self.assertNotIn("FAKE_BEARER", str(error.exception))
        for value in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(SafeError):
                parse_json(value)

    def test_stdio_wire_protocol_and_error_redaction(self):
        config_path = self.root / "bridge.json"
        config_path.write_text(json.dumps(self.config("native_error")))
        requests = [
            "invalid json\n",
            json.dumps({"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}}) + "\n",
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n",
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n",
        ]
        result = subprocess.run([sys.executable, str(ROOT / "codex-apps-bridge.py"), "--config", str(config_path)],
                                input="".join(requests), text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["id"], "init")
        self.assertIn("error", replies[2])
        self.assertNotIn("FAKE_BEARER", result.stdout + result.stderr)

    def test_checker_only_discovers_no_app_or_model_calls(self):
        path = self.root / "config.json"
        path.write_text(json.dumps(self.config()))
        result = subprocess.run([sys.executable, str(ROOT / "check-apps-bridge.py"), "--config", str(path)],
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["executedTools"], 0)
        self.assertFalse(evidence["authenticatedAppReadVerified"])
        self.assertFalse(any(row.get("method") in ("mcpServer/tool/call", "turn/start") for row in self.records()))

    def test_validate_only_does_not_launch_native(self):
        path = self.root / "config.json"
        path.write_text(json.dumps(self.config()))
        for script in ("codex-apps-bridge.py", "check-apps-bridge.py"):
            result = subprocess.run([sys.executable, str(ROOT / script), "--config", str(path), "--validate-only"],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())


class Alignment(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.settings = {"unrelated": {"theme": "keep"}, "providerInstances": {
            "a": {"driver": "codex", "displayName": "Account A", "enabled": True,
                  "config": {"homePath": str(self.root / "a"), "binaryPath": "codex", "customModels": [{"slug": "keep"}]}},
            "b": {"driver": "claudeAgent", "config": {"homePath": str(self.root / "b")}},
        }}
        self.spec = {"version": 1, "updates": [{"id": "a", "expectedDriver": "codex", "homePath": str(self.root / "new-a")}]}

    def tearDown(self):
        self.temporary.cleanup()

    def test_preserves_identity_models_and_unrelated_settings(self):
        original = copy.deepcopy(self.settings)
        candidate = alignment_candidate(self.settings, self.spec)
        self.assertEqual(self.settings, original)
        self.assertEqual(candidate["unrelated"], original["unrelated"])
        self.assertEqual(candidate["providerInstances"]["b"], original["providerInstances"]["b"])
        expected = copy.deepcopy(original)
        expected["providerInstances"]["a"]["config"]["homePath"] = str(self.root / "new-a")
        self.assertEqual(candidate, expected)

    def test_rejects_missing_ids_driver_changes_and_secret_fields(self):
        for patch in ({"id": "missing"}, {"expectedDriver": "claudeAgent"}, {"token": "fake"}, {"homePath": "relative"}):
            spec = copy.deepcopy(self.spec)
            spec["updates"][0].update(patch)
            with self.assertRaises(SafeError):
                alignment_candidate(self.settings, spec)

    def test_duplicate_updates_and_overlapping_homes(self):
        spec = copy.deepcopy(self.spec)
        spec["updates"].append(copy.deepcopy(spec["updates"][0]))
        with self.assertRaises(SafeError):
            alignment_candidate(self.settings, spec)
        for home in (self.root / "b", self.root / "b" / "nested", self.root):
            spec = copy.deepcopy(self.spec)
            spec["updates"][0]["homePath"] = str(home)
            with self.assertRaises(SafeError):
                alignment_candidate(self.settings, spec)

    def test_symlink_home_collision(self):
        (self.root / "b").mkdir()
        (self.root / "alias-b").symlink_to(self.root / "b", target_is_directory=True)
        self.spec["updates"][0]["homePath"] = str(self.root / "alias-b")
        with self.assertRaises(SafeError):
            alignment_candidate(self.settings, self.spec)

    def test_existing_case_insensitive_alias(self):
        actual = self.root / "CaseAccount"
        actual.mkdir()
        alias = self.root / "caseaccount"
        if not alias.exists() or not os.path.samefile(actual, alias):
            self.skipTest("Filesystem is case-sensitive")
        self.settings["providerInstances"]["b"]["config"]["homePath"] = str(actual)
        self.spec["updates"][0]["homePath"] = str(alias / "child")
        with self.assertRaises(SafeError):
            alignment_candidate(self.settings, self.spec)

    def test_existing_inode_alias_with_different_path_spelling(self):
        actual = self.root / "native-b"
        alias = self.root / "unrelated-spelling"
        actual.mkdir()
        alias.mkdir()
        actual_stat = actual.stat()
        original_stat = Path.stat
        def alias_stat(path, *args, **kwargs):
            if path == alias:
                return actual_stat
            return original_stat(path, *args, **kwargs)
        self.settings["providerInstances"]["b"]["config"]["homePath"] = str(actual)
        self.spec["updates"][0]["homePath"] = str(alias / "future-child")
        with mock.patch.object(Path, "stat", alias_stat):
            with self.assertRaises(SafeError):
                alignment_candidate(self.settings, self.spec)

    def test_missing_case_and_unicode_aliases_are_conservatively_rejected(self):
        for existing, candidate in (("FutureAccount", "futureaccount/child"),
                                    ("Caf\u00e9", "Cafe\u0301/child")):
            self.settings["providerInstances"]["b"]["config"]["homePath"] = str(self.root / existing)
            self.spec["updates"][0]["homePath"] = str(self.root / candidate)
            with self.subTest(candidate=candidate), self.assertRaises(SafeError):
                alignment_candidate(self.settings, self.spec)

    def test_unknown_native_home_and_symlink_cycle_fail_closed(self):
        settings = copy.deepcopy(self.settings)
        settings["providerInstances"]["b"]["config"].pop("homePath")
        with self.assertRaises(SafeError):
            alignment_candidate(settings, self.spec)
        loop = self.root / "cycle"
        loop.symlink_to(loop)
        self.spec["updates"][0]["homePath"] = str(loop)
        with self.assertRaises(SafeError) as error:
            alignment_candidate(self.settings, self.spec)
        self.assertNotIn(str(self.root), str(error.exception))

    def test_new_protected_candidate_only(self):
        output = self.root / "candidate.json"
        write_candidate(self.settings, output)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(json.loads(output.read_text()), self.settings)
        with self.assertRaises(SafeError):
            write_candidate({}, output)
        self.assertEqual(json.loads(output.read_text()), self.settings)
        link = self.root / "candidate-link"
        link.symlink_to(self.root / "missing")
        with self.assertRaises(SafeError):
            write_candidate({}, link)
        self.assertFalse((self.root / "missing").exists())

    def test_cli_default_read_only_and_output_refusal(self):
        settings = self.root / "settings.json"
        spec = self.root / "updates.json"
        settings.write_text(json.dumps(self.settings))
        spec.write_text(json.dumps(self.spec))
        command = [sys.executable, str(ROOT / "align-t3-providers.py"), "--settings", str(settings), "--spec", str(spec)]
        before = settings.read_bytes()
        result = subprocess.run(command, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["candidateWritten"])
        result = subprocess.run(command + ["--output", str(settings)], text=True, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(settings.read_bytes(), before)
        self.assertEqual(set(self.root.iterdir()), {settings, spec})


if __name__ == "__main__":
    unittest.main()
