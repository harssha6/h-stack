"""Portable-package checks without real services, user state, or network peers."""

import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_lifecycle import hum, leases


SCRIPT = Path(__file__).resolve().parents[1] / "hum"
INSTALLER = SCRIPT.with_name("install.py")


class PackagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.environment = {
            "HOME": str(self.root / "home"),
            "PATH": "",
            "XDG_STATE_HOME": str(self.root / "state"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "HUM_SESSION": "offline-fixture",
            "HUM_NOTIFY": "none",
            "HUM_HERDR_BIN": str(self.root / "not-installed-herdr"),
        }

    def invoke(self, script, *arguments, **environment):
        return subprocess.run([sys.executable, str(script), *arguments],
                              env=dict(self.environment, **environment), capture_output=True,
                              text=True, timeout=15)

    def test_help_and_doctor_work_without_herdr_and_create_no_state(self):
        before = list(self.root.iterdir())
        self.assertEqual(self.invoke(SCRIPT, "--help").returncode, 0)
        doctor = self.invoke(SCRIPT, "doctor")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIsNone(json.loads(doctor.stdout)["herdr"])
        self.assertEqual(list(self.root.iterdir()), before)

    def test_missing_dependency_is_clear_without_starting_or_writing_state(self):
        result = self.invoke(SCRIPT, "cleanup", "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HUM_HERDR_BIN is not an executable", result.stderr)
        self.assertFalse((self.root / "state").exists())

    def test_invalid_session_is_rejected_without_state(self):
        for session in ["../escape", "a/b", "control\ncharacter"]:
            with self.subTest(session=session):
                result = self.invoke(SCRIPT, "doctor", HUM_SESSION=session)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.root / "state").exists())

    def test_installer_dry_run_writes_nothing(self):
        target = self.root / "new" / "hum-bin"
        before = list(self.root.iterdir())
        result = self.invoke(INSTALLER, "--directory", str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.root.iterdir()), before)

    def test_install_is_self_contained_and_refuses_replacement(self):
        target = self.root / "hum-bin"
        result = self.invoke(INSTALLER, "--directory", str(target), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({entry.name for entry in target.iterdir()},
                         {"hum", "hum_lifecycle.py", "hum_terminal.py", "LICENSE"})
        self.assertEqual((target / "LICENSE").read_text(), SCRIPT.parents[1].joinpath("LICENSE").read_text())
        self.assertTrue(os.access(target / "hum", os.X_OK))
        self.assertEqual(self.invoke(target / "hum", "--help").returncode, 0)
        before = (target / "hum").read_bytes()
        self.assertNotEqual(self.invoke(INSTALLER, "--directory", str(target), "--apply").returncode, 0)
        self.assertEqual((target / "hum").read_bytes(), before)

    def test_installer_never_follows_existing_destination_symlinks(self):
        outside = self.root / "outside"
        outside.mkdir()
        target = self.root / "symlink"
        target.symlink_to(outside)
        result = self.invoke(INSTALLER, "--directory", str(target), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_fake_herdr_offline_cleanup_never_launches_a_server(self):
        trace = self.root / "calls.jsonl"
        fake = self.root / "fake-herdr"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "with Path(os.environ['FAKE_TRACE']).open('a') as stream:\n"
            " stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:] == ['session', 'list', '--json']:\n"
            " print(json.dumps({'sessions': []}))\n"
            "else:\n"
            " sys.exit(99)\n", encoding="utf-8")
        fake.chmod(0o700)
        result = self.invoke(SCRIPT, "cleanup", "--dry-run", "--json",
                             HUM_HERDR_BIN=str(fake), FAKE_TRACE=str(trace))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["result"], "session-offline")
        self.assertEqual([json.loads(line) for line in trace.read_text().splitlines()],
                         [["session", "list", "--json"]])
        self.assertFalse((self.root / "state").exists())


class PortableBehaviorTests(unittest.TestCase):
    def test_command_arguments_survive_shell_serialization(self):
        arguments = ["python3", "-c", "print('hello world')", "literal;$(touch nope)", ""]
        _, _, command = hum.parse(["web", "--", *arguments])
        self.assertEqual(shlex.split(command), arguments)

    def test_no_notifications_or_terminal_scan_without_opt_in(self):
        with patch.dict(os.environ, {"HUM_NOTIFY": "none"}), \
                patch.object(hum, "ghostty_tty") as scan, \
                patch.object(hum.subprocess, "run") as run:
            hum.deliver({})
        scan.assert_not_called()
        run.assert_not_called()

    def test_notification_text_is_argv_not_applescript_source(self):
        import platform
        payload = 'quote" & do shell script "unexpected"'
        data = {"event": "started", "project": payload, "server": "web",
                "machine": "test", "by": "fixture", "cmd": payload}
        with patch.dict(os.environ, {"HUM_NOTIFY": "desktop"}), \
                patch.object(platform, "system", return_value="Darwin"), \
                patch.object(hum.shutil, "which", return_value="/fake/osascript"), \
                patch.object(hum.subprocess, "run") as run:
            hum.deliver(data)
        arguments = run.call_args.args[0]
        self.assertNotIn(payload, arguments[2])
        self.assertIn(payload, arguments[3])
        self.assertIn(payload, arguments[4])

    def test_remote_event_path_is_one_quoted_argument_and_never_creates_files(self):
        path = "events/private notes; echo ignored"
        with patch.dict(os.environ, {"HUM_REMOTE_EVENT_PATH": path}):
            command = hum.remote_event_command()
        self.assertEqual(shlex.split(command), ["tail", "-n", "0", "-F", "./" + path])

    def test_missing_process_identity_is_not_an_idle_pane(self):
        for info in [{}, {"shell_pid": None, "foreground_process_group_id": None},
                     {"shell_pid": 123, "foreground_process_group_id": -1}]:
            with self.subTest(info=info), patch.object(hum, "proc_info", return_value=info):
                with self.assertRaises(leases.PolicyError):
                    hum.busy_once("pane")

    def test_empty_terminal_close_is_explicitly_unavailable_on_macos(self):
        with patch.object(hum.terminals.sys, "platform", "darwin"):
            with self.assertRaises(leases.PolicyError):
                hum.terminals.empty_shell({"pid": 123, "birth": "fixture"})

    def test_tailscale_failure_cannot_allocate_or_replace_a_route(self):
        with patch.object(hum.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as run:
            with self.assertRaises(leases.PolicyError):
                hum.tailscale_json("serve", "status")
        self.assertEqual(run.call_count, 1)

    def test_managed_command_artifacts_are_private_and_refuse_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "command.sh"
            hum.private_text(artifact, "private command\n")
            self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
            victim = root / "keep"
            victim.write_text("Keep\n", encoding="utf-8")
            artifact.unlink()
            artifact.symlink_to(victim)
            with self.assertRaises(OSError):
                hum.private_text(artifact, "changed")
            self.assertEqual(victim.read_text(), "Keep\n")

    def test_failed_stop_cannot_remove_terminal_or_share(self):
        with patch.object(hum, "load_state", return_value={}), \
                patch.object(hum, "find_workspace", return_value="workspace"), \
                patch.object(hum, "find_pane", return_value="pane"), \
                patch.object(hum, "stop", return_value=False), \
                patch.object(hum, "unshare") as unshare, \
                patch.object(hum, "herdr") as herdr:
            with self.assertRaises(leases.PolicyError):
                hum.server_action("rm", ["web"], {"--owner": "manual:fixture"},
                                  None, "project", Path("/fixture"), 120)
        unshare.assert_not_called()
        herdr.assert_not_called()

    def test_unsupported_herdr_response_is_a_clear_failure(self):
        with patch.object(hum, "herdr_bin", return_value="/fake/herdr"), \
                patch.object(hum.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout='"unexpected"', stderr="")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                hum.herdr("session", "list", "--json")

    def test_json_formatted_pane_logs_remain_unmodified_plain_text(self):
        output = '{"message":"Ready"}\n'
        with patch.object(hum, "herdr_bin", return_value="/fake/herdr"), \
                patch.object(hum.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout=output, stderr="")):
            self.assertEqual(hum.read("pane", 10), output)

    def test_prior_run_readiness_cannot_pass_without_current_run_marker(self):
        with patch.object(hum, "load_state", return_value={"marker": "hum:start:new"}), \
                patch.object(hum, "read", return_value="Ready from the previous run\n"), \
                patch.object(hum.time, "time", side_effect=[0, .5, .5, 2]), \
                patch.object(hum.time, "sleep"), \
                contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                hum.wait_for("pane", "project", "web", "Ready", 1)

    def test_current_run_marker_allows_readiness(self):
        marker = "hum:start:new"
        with patch.object(hum, "load_state", return_value={"marker": marker}), \
                patch.object(hum, "read", return_value=f"── {marker} ──\nReady\n"), \
                patch.object(hum.time, "sleep"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(hum.wait_for("pane", "project", "web", "Ready", 1), 0)

    def test_event_records_are_private_and_stay_in_selected_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / "state" / "events.jsonl"
            event = {"root": "fixture", "by": "fixture", "event": "started"}
            with patch.object(hum, "EVENTS", events), \
                    patch.object(hum, "t3_thread", return_value=None), \
                    patch.object(hum, "deliver"):
                hum.finish_emit(json.dumps(event))
            self.assertEqual(json.loads(events.read_text())["event"], "started")
            self.assertEqual(events.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
