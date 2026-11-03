import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import tempfile
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[1] / "hum"
loader = importlib.machinery.SourceFileLoader("hum_under_test", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
hum = importlib.util.module_from_spec(spec)
loader.exec_module(hum)
leases = hum.leases


def policy(owner="manual:alice", kind="preview", now=100, ttl="1m"):
    options = {"--lifetime": kind, "--purpose": "QA preview"}
    if kind != "persistent":
        options["--ttl"] = ttl
    return leases.claim(None, options, owner, now, new_run=True)


class LeaseTests(unittest.TestCase):
    def test_new_preview_has_bounded_owner_and_purpose(self):
        result = leases.claim(None, {}, "manual:alice", 100, new_run=True)
        self.assertEqual(result["kind"], "preview")
        self.assertEqual(result["owners"]["manual:alice"]["expires_at"], 7300)

    def test_unclassified_running_environment_is_not_implicitly_adopted(self):
        self.assertIsNone(leases.claim(None, {}, "manual:alice", 100))

    def test_shared_claim_and_renewal_cannot_shorten_a_lease(self):
        original = policy()
        shared = leases.claim(original, {"--ttl": "2m"}, "manual:bob", 110)
        renewed = leases.claim(shared, {"--ttl": "1s"}, "manual:alice", 111)
        self.assertEqual(renewed["owners"]["manual:alice"]["expires_at"], 160)
        self.assertEqual(renewed["owners"]["manual:bob"]["expires_at"], 230)
        self.assertEqual(original["owners"].keys(), {"manual:alice"})

    def test_any_live_claim_blocks_expiry(self):
        shared = leases.claim(policy(), {"--ttl": "2m"}, "manual:bob", 110)
        self.assertEqual(leases.due(shared, 200, lambda _: "inactive"), (False, "leased"))
        self.assertEqual(leases.due(shared, 231, lambda _: "inactive"), (True, "expired"))

    def test_release_only_own_claim_and_last_release_is_due(self):
        shared = leases.claim(policy(kind="task"), {}, "manual:bob", 100)
        partial = leases.release(shared, "manual:alice")
        self.assertEqual(leases.due(partial, 120, lambda _: "inactive"), (False, "leased"))
        released = leases.release(partial, "manual:bob")
        self.assertEqual(leases.due(released, 120, lambda _: "active"), (True, "released"))
        with self.assertRaises(leases.PolicyError):
            leases.release(shared, "manual:carol")

    def test_persistent_never_expires_or_downgrades(self):
        persistent = policy(kind="persistent")
        self.assertEqual(leases.due(persistent, 10**12, lambda _: "inactive"), (False, "persistent"))
        with self.assertRaises(leases.PolicyError):
            leases.claim(persistent, {"--lifetime": "preview"}, "manual:alice", 100)
        with self.assertRaises(leases.PolicyError):
            leases.claim(persistent, {"--ttl": "2h"}, "manual:alice", 100)

    def test_other_owner_lifetime_cannot_be_changed(self):
        with self.assertRaises(leases.PolicyError):
            leases.claim(policy(), {"--lifetime": "task"}, "manual:bob", 100)

    def test_exact_active_and_unresolved_t3_owners_are_protected(self):
        original = policy("t3:exact-thread-id", kind="task")
        self.assertEqual(leases.due(original, 200, lambda _: "active"), (False, "active-owner"))
        self.assertEqual(leases.due(original, 200, lambda _: "unknown"), (False, "unknown-owner"))
        self.assertEqual(leases.due(original, 200, lambda _: "inactive"), (True, "expired"))

    def test_preview_survives_thread_completion_until_lease_expires(self):
        preview = policy("t3:thread")
        self.assertEqual(leases.due(preview, 110, lambda _: "inactive"), (False, "leased"))

    def test_malformed_lifecycle_never_becomes_a_valid_expired_policy(self):
        for mutate in (
            lambda p: p.update(version=2), lambda p: p.update(kind="old"),
            lambda p: p.update(owners={}), lambda p: p.update(ttl=float("nan")),
            lambda p: p["owners"]["manual:alice"].update(expires_at=float("inf")),
            lambda p: p["owners"]["manual:alice"].update(released="false"),
        ):
            with self.subTest(mutate=mutate):
                value = policy()
                mutate(value)
                with self.assertRaises(leases.PolicyError):
                    leases.due(value, 200, lambda _: "inactive")

    def test_duration_is_explicit_bounded_lexical_input(self):
        self.assertEqual(leases.duration("2h"), 7200)
        self.assertEqual(leases.duration("30m"), 1800)
        for value in ("", "nan", "inf", "1.5h", "-1h", "0h", "31d", "１２h"):
            with self.subTest(value=value), self.assertRaises(leases.PolicyError):
                leases.duration(value)

    def test_pid_birth_mismatch_is_never_signalled(self):
        with patch.object(leases, "process_birth", return_value="new-birth"), \
                patch.object(os, "kill") as kill:
            self.assertFalse(leases.signal_process({"pid": 12345, "birth": "old-birth"}, signal.SIGTERM))
            kill.assert_not_called()

    def test_recycled_candidate_child_does_not_enter_the_captured_tree(self):
        records = {111: {"pid": 111, "ppid": 101, "pgid": 111, "birth": "root"},
                   # PID 222 was a child in an earlier ps snapshot, but now is
                   # an unrelated process. Its actual PPID and birth are read together.
                   222: {"pid": 222, "ppid": 999, "pgid": 999, "birth": "recycled"}}
        with patch.object(leases, "process_record", side_effect=lambda pid: records.get(pid)):
            tree = leases.capture_tree(111, [111, 222])
        self.assertEqual([entry["pid"] for entry in tree], [111])

    def test_child_is_rejected_if_captured_parent_was_recycled(self):
        root = {"pid": 111, "ppid": 101, "pgid": 111, "birth": "old-root"}
        child = {"pid": 222, "ppid": 111, "pgid": 111, "birth": "child"}
        with patch.object(leases, "process_record", side_effect=[root, child, dict(root, birth="new-root"), child]):
            tree = leases.capture_tree(111, [222])
        self.assertEqual([entry["pid"] for entry in tree], [111])

    def test_child_is_rejected_if_reparented_during_capture(self):
        root = {"pid": 111, "ppid": 101, "pgid": 111, "birth": "root"}
        child = {"pid": 222, "ppid": 111, "pgid": 111, "birth": "child"}
        with patch.object(leases, "process_record", side_effect=[root, child, root, dict(child, ppid=999)]):
            tree = leases.capture_tree(111, [222])
        self.assertEqual([entry["pid"] for entry in tree], [111])

    @unittest.skipUnless(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"), "Linux pidfd API")
    def test_pidfd_birth_race_is_rechecked_before_signal(self):
        with patch.object(leases, "process_birth", side_effect=["old", "new"]), \
                patch.object(os, "pidfd_open", return_value=77), \
                patch.object(os, "close") as close, \
                patch.object(signal, "pidfd_send_signal") as send:
            self.assertFalse(leases.signal_process({"pid": 12345, "birth": "old"}, signal.SIGKILL))
            send.assert_not_called()
            close.assert_called_once_with(77)


class ManagedStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.states = self.base / "state"
        self.patches = [
            patch.object(hum, "STATE_DIR", self.states),
            patch.object(hum, "session_running", return_value=True),
            patch.object(hum, "project", return_value=("project", self.root)),
            patch.object(hum, "find_workspace", return_value="workspace"),
            patch.object(hum, "find_pane", return_value="pane"),
            patch.object(hum, "proc_info", return_value={"shell_pid": 101,
                                                         "foreground_process_group_id": 111,
                                                         "foreground_processes": [{"pid": 111}]}),
            patch.object(leases, "process_birth", side_effect=lambda pid: {101: "shell", 111: "job"}.get(pid)),
            patch.object(hum, "emit"),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.addCleanup(self.temp.cleanup)

    def managed(self, value=None):
        state = {"cmd": "test-server", "cwd": str(self.root), "marker": "old-marker",
                 "lifecycle": value or policy()}
        state["binding"] = hum.adopt_binding("pane", state)
        hum.save_state("project", "web", state)
        return state

    def cleanup(self, dry=False):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            hum.cleanup(dry_run=dry, as_json=True)
        return json.loads(output.getvalue())

    def test_expired_environment_stops_only_bound_pane_and_unshares(self):
        self.managed()
        with patch.object(hum, "stop", return_value=True) as stop, \
                patch.object(hum, "unshare") as unshare:
            result = self.cleanup()
        self.assertEqual(result[0]["result"], "stopped")
        self.assertEqual(stop.call_args.args, ("pane",))
        unshare.assert_called_once_with("project", "web")
        self.assertIn("stopped", hum.load_state("project", "web"))

    def test_dry_run_is_read_only(self):
        state = self.managed()
        with patch.object(hum, "stop") as stop, patch.object(hum, "unshare") as unshare:
            result = self.cleanup(dry=True)
        self.assertEqual(result[0]["result"], "would-stop")
        stop.assert_not_called()
        unshare.assert_not_called()
        self.assertEqual(hum.load_state("project", "web"), state)

    def test_unknown_thread_status_never_stops_expired_owned_environment(self):
        self.managed(policy("t3:thread"))
        with patch.object(hum, "exact_thread_status", return_value="unknown"), patch.object(hum, "stop") as stop:
            self.assertEqual(self.cleanup()[0]["result"], "unknown-owner")
        stop.assert_not_called()

    def test_inactive_thread_can_resume_before_another_environment_is_stopped(self):
        state = self.managed(policy("t3:thread"))
        hum.save_state("project", "web2", state)
        executable = self.base / "fake-t3"
        executable.write_text("fake")
        executable.chmod(0o700)
        idle = {"thread": {"threadId": "thread", "status": "idle", "activeRunId": None}}
        active = {"thread": {"threadId": "thread", "status": "running", "activeRunId": "new-run"}}
        with patch.dict(os.environ, {"T3CODE_CLI_PATH": str(executable)}), \
                patch.object(hum.subprocess, "run", side_effect=[SimpleNamespace(returncode=0, stdout=json.dumps(idle)),
                                                               SimpleNamespace(returncode=0, stdout=json.dumps(active))]), \
                patch.object(hum, "stop", return_value=True) as stop, patch.object(hum, "unshare"):
            result = self.cleanup()
        self.assertEqual([row["result"] for row in result], ["stopped", "active-owner"])
        self.assertEqual(stop.call_count, 1)

    def test_owner_is_refreshed_after_identity_checks_before_any_signal(self):
        self.managed(policy("t3:thread"))
        captured = [{"pid": 111, "ppid": 101, "pgid": 111, "birth": "job"}]
        with patch.object(hum, "exact_thread_status", side_effect=["inactive", "active"]) as lookup, \
                patch.object(hum, "busy", return_value=True), \
                patch.object(leases, "capture_tree", return_value=captured), \
                patch.object(leases, "signal_process") as send:
            result = self.cleanup()
        self.assertEqual(result[0]["result"], "protected")
        self.assertEqual(lookup.call_count, 2)
        send.assert_not_called()

    def test_persistent_and_legacy_are_protected(self):
        for state, expected in (({"cmd": "legacy"}, "unmanaged"),
                                (self.managed(policy(kind="persistent")), "persistent")):
            hum.save_state("project", "web", state)
            with patch.object(hum, "stop") as stop:
                self.assertEqual(self.cleanup()[0]["result"], expected)
                stop.assert_not_called()

    def test_malformed_state_is_reported_without_stopping(self):
        self.managed()
        hum.state_file("project", "web").write_text('{"lifecycle": NaN}')
        with patch.object(hum, "stop") as stop:
            self.assertEqual(self.cleanup()[0]["result"], "protected")
            stop.assert_not_called()

    def test_changed_pane_birth_or_generation_is_protected(self):
        for field in ("pane_id", "marker"):
            state = self.managed()
            state["binding"][field] = "another-run"
            hum.save_state("project", "web", state)
            with patch.object(hum, "stop") as stop:
                self.assertEqual(self.cleanup()[0]["result"], "identity-mismatch")
                stop.assert_not_called()
        self.managed()
        with patch.object(leases, "process_birth", return_value="new-job"), patch.object(hum, "stop") as stop:
            self.assertEqual(self.cleanup()[0]["result"], "identity-mismatch")
            stop.assert_not_called()

    def test_generation_specific_run_file_cannot_be_overwritten_by_previous_run(self):
        first = hum.run_file("project", "web", "a" * 32)
        second = hum.run_file("project", "web", "b" * 32)
        leases.atomic_json(first, {"marker": "first"})
        leases.atomic_json(second, {"marker": "second"})
        leases.atomic_json(first, {"marker": "late-first"})
        self.assertEqual(json.loads(second.read_text())["marker"], "second")

    def test_offline_cleanup_does_not_start_herdr(self):
        with patch.object(hum, "session_running", return_value=False), patch.object(hum, "ensure_server") as start:
            self.assertEqual(self.cleanup()[0]["result"], "session-offline")
            start.assert_not_called()

    def test_traversal_and_symlink_state_are_rejected(self):
        for label, name in (("../other", "web"), ("project", "../../web")):
            with self.assertRaises(leases.PolicyError):
                hum.state_file(label, name)
        self.states.mkdir(exist_ok=True)
        (self.states / "escape").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(leases.PolicyError):
            hum.state_file("escape", "web")

    def test_lock_blocks_janitor_until_renewal_is_committed(self):
        self.managed()
        entered, finished = threading.Event(), threading.Event()
        result = []
        def sweep():
            entered.set()
            with contextlib.redirect_stdout(io.StringIO()):
                result.append(hum.cleanup(as_json=True))
            finished.set()
        with leases.state_lock(self.states, "project", "web"):
            worker = threading.Thread(target=sweep)
            worker.start()
            self.assertTrue(entered.wait(2))
            state = hum.load_state("project", "web")
            state["lifecycle"] = leases.claim(state["lifecycle"], {"--ttl": "2h"}, "manual:alice", hum.time.time())
            hum.save_state("project", "web", state)
            self.assertFalse(finished.is_set())
        self.assertTrue(finished.wait(3))
        worker.join()
        self.assertNotIn("stopped", hum.load_state("project", "web"))

    def test_keep_adopts_legacy_metadata_without_restarting(self):
        hum.save_state("project", "web", {"cmd": "test-server", "cwd": str(self.root), "marker": "legacy"})
        with patch.object(hum, "busy", return_value=True), patch.object(hum, "launch") as launch, \
                contextlib.redirect_stdout(io.StringIO()):
            hum.server_action("keep", ["web"], {"--lifetime": "persistent", "--owner": "manual:operator"},
                              None, "project", self.root, 120)
        state = hum.load_state("project", "web")
        self.assertEqual(state["lifecycle"]["kind"], "persistent")
        self.assertEqual(state["binding"]["mode"], "adopted")
        launch.assert_not_called()

    def test_release_does_not_stop_another_owners_claim(self):
        shared = leases.claim(policy(kind="task"), {}, "manual:bob", 100)
        self.managed(shared)
        with patch.object(hum, "stop_registered") as stop, contextlib.redirect_stdout(io.StringIO()):
            hum.server_action("release", ["web"], {"--owner": "manual:alice"},
                              None, "project", self.root, 120)
        stop.assert_not_called()

    def test_invalid_cli_policy_does_not_touch_running_services(self):
        for argv in (["hum", "restart", "web", "--ttl", "nan"],
                     ["hum", "restart", "web", "--lifetime", "permanent"],
                     ["hum", "restart", "web", "--timeout", "NaN"],
                     ["hum", "restart", "web", "--ttl"]):
            with self.subTest(argv=argv), patch.object(hum.sys, "argv", argv), \
                    patch.object(hum, "ensure_server") as ensure, self.assertRaises(leases.PolicyError):
                hum.main()
            ensure.assert_not_called()

    def test_running_reuse_claims_without_launching(self):
        self.managed()
        with patch.object(hum, "ensure_workspace", return_value="workspace"), \
                patch.object(hum, "ensure_pane", return_value=("pane", False)), \
                patch.object(hum, "busy", return_value=True), patch.object(hum, "read", return_value="ready"), \
                patch.object(hum, "launch") as launch, contextlib.redirect_stdout(io.StringIO()):
            hum.server_action("up", ["web"], {"--owner": "manual:bob"}, None, "project", self.root, 120)
        launch.assert_not_called()
        self.assertEqual(set(hum.load_state("project", "web")["lifecycle"]["owners"]),
                         {"manual:alice", "manual:bob"})

    def test_launch_preserves_share_and_binds_new_generation(self):
        state = self.managed()
        state["share"] = {"url": "https://example.test:20443", "https_port": 20443, "app_port": 3000}
        hum.save_state("project", "web", state)
        with patch.object(hum, "favicon_pixels", return_value=None), patch.object(hum, "herdr"), \
                patch.object(hum, "machine_label", return_value="test"):
            hum.launch("pane", "test-server --flag", "project", "web", self.root, policy())
        new = hum.load_state("project", "web")
        self.assertEqual(new["share"], state["share"])
        self.assertNotEqual(new["marker"], state["marker"])
        self.assertEqual(new["binding"]["marker"], new["marker"])
        self.assertIn(" _run project web ", hum.state_file("project", "web").with_suffix(".sh").read_text())

    def test_unshare_checks_current_route_before_disabling_a_port(self):
        state = self.managed()
        state["share"] = hum.share_record("host", 20443, 3000)
        hum.save_state("project", "web", state)
        reassigned = {"Web": {"host:20443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:4000"}}}}}
        with patch.object(hum.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(reassigned))) as run:
            with self.assertRaises(leases.PolicyError):
                hum.unshare("project", "web")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(hum.load_state("project", "web")["share"], state["share"])

    def test_unshare_does_not_remove_another_handler_on_its_port(self):
        state = self.managed()
        state["share"] = hum.share_record("host", 20443, 3000)
        hum.save_state("project", "web", state)
        shared = {"Web": {"host:20443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:3000"},
                                                       "/other": {"Proxy": "http://127.0.0.1:4000"}}}}}
        with patch.object(hum.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(shared))) as run:
            with self.assertRaises(leases.PolicyError):
                hum.unshare("project", "web")
        self.assertEqual(run.call_count, 1)

    def test_verified_unshare_preserves_command_and_logs_metadata(self):
        state = self.managed()
        state["share"] = hum.share_record("host", 20443, 3000)
        hum.save_state("project", "web", state)
        own = {"Web": {"host:20443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:3000"}}}},
               "TCP": {"20443": {"HTTPS": True}}}
        with patch.object(hum.subprocess, "run", side_effect=[SimpleNamespace(returncode=0, stdout=json.dumps(own)),
                                                            SimpleNamespace(returncode=0)]) as run:
            hum.unshare("project", "web")
        self.assertEqual(run.call_count, 2)
        remaining = hum.load_state("project", "web")
        self.assertNotIn("share", remaining)
        self.assertEqual(remaining["cmd"], state["cmd"])
        self.assertEqual(remaining["marker"], state["marker"])


if __name__ == "__main__":
    unittest.main()
