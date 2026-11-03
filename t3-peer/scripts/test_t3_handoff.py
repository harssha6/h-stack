"""Offline regression/adversarial tests. All writes and Git repos are temporary."""

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock

import t3_handoff as handoff


SCRIPT = Path(handoff.__file__)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        # macOS commonly returns /var/... through a symlink to /private/var.
        # Test canonical physical roots while retaining all entry protections.
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.shared = self.root / "shared"
        self.shared.mkdir()
        self.output = self.shared / "test.handoff.json"
        self.destination = self.root / "received"
        self.notes = self.root / "notes.md"
        self.notes.write_text("# Handoff\nFinish the selected change.\n", encoding="utf-8")
        self.git("init", "--quiet", "--template=")
        self.git("config", "user.name", "Fixture Author")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "tracked.txt").write_text("base\n")
        (self.repo / "deleted.txt").write_text("remove me\n")
        (self.repo / "untouched.txt").write_text("baseline only\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "fixture base")
        self.commit = self.git("rev-parse", "HEAD").strip()

    def git(self, *args, repo=None, env=None):
        environment = handoff.git_env()
        if env:
            environment.update(env)
        result = subprocess.run(["git", "-C", str(repo or self.repo), *args],
                                capture_output=True, text=True, env=environment, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def package(self, paths=None, branch="handoff/test"):
        return handoff.selected_snapshot(self.repo, self.commit, paths or ["tracked.txt"],
                                        self.notes, branch, handoff.DEFAULT_LIMITS)

    def publish(self, package=None):
        package = package if package is not None else self.package()
        result = handoff.publish(package, self.output, True, handoff.DEFAULT_LIMITS)
        return result["sha256"]

    def receive(self, package=None, **kwargs):
        return handoff.receive(package if package is not None else self.package(),
                               kwargs.get("base_repo", self.repo),
                               kwargs.get("destination", self.destination),
                               kwargs.get("expected_commit", self.commit),
                               kwargs.get("apply", True), kwargs.get("limits", handoff.DEFAULT_LIMITS))

    def rewrite(self, package):
        self.output.write_bytes(handoff.encode_package(package))
        return handoff.digest(self.output.read_bytes())

    def test_dirty_untracked_deleted_executable_roundtrip_and_base_history_policy(self):
        # Ensure history has more than one commit; receiver should retain only
        # the chosen base and materialize selected changes as unstaged content.
        (self.repo / "second.txt").write_text("second commit\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "second fixture commit")
        self.commit = self.git("rev-parse", "HEAD").strip()
        (self.repo / "tracked.txt").write_bytes(b"updated\x00binary\n")
        self.git("add", "tracked.txt")
        (self.repo / "new file.txt").write_text("new\n")
        (self.repo / "run.sh").write_text("#!/bin/sh\nexit 0\n")
        (self.repo / "run.sh").chmod(0o755)
        (self.repo / "deleted.txt").unlink()
        (self.repo / "untouched.txt").write_text("NOT SELECTED\n")
        package = self.package(["tracked.txt", "new file.txt", "run.sh", "deleted.txt"])
        before = self.git("status", "--porcelain=v1")
        index_before = (self.repo / ".git" / "index").read_bytes()
        sha = self.publish(package)
        loaded = handoff.load_package(self.output, sha, handoff.DEFAULT_LIMITS)
        result = self.receive(loaded)
        target = Path(result["repo"])
        self.assertEqual((target / "tracked.txt").read_bytes(), b"updated\x00binary\n")
        self.assertEqual((target / "new file.txt").read_text(), "new\n")
        self.assertTrue((target / "run.sh").stat().st_mode & 0o100)
        self.assertFalse((target / "deleted.txt").exists())
        self.assertEqual((target / "untouched.txt").read_text(), "baseline only\n")
        self.assertEqual(self.git("rev-parse", "HEAD", repo=target).strip(), self.commit)
        self.assertEqual(self.git("branch", "--show-current", repo=target).strip(), "handoff/test")
        self.assertEqual(self.git("rev-list", "--count", "HEAD", repo=target).strip(), "1")
        self.assertEqual(self.git("remote", repo=target), "")
        self.assertEqual(self.git("diff", "--cached", "--name-only", repo=target), "")
        self.assertIn(" M tracked.txt", self.git("status", "--porcelain=v1", repo=target))
        self.assertEqual((self.destination / "HANDOFF.md").read_text(), self.notes.read_text())
        self.assertFalse((self.destination / "INCOMPLETE").exists())
        self.assertEqual(self.git("status", "--porcelain=v1"), before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index_before)
        # Artifact has neither local/private Git metadata nor unchanged files.
        raw = self.output.read_text()
        for unwanted in [str(self.repo), "Fixture Author", "fixture@example.invalid",
                         "second fixture commit", "baseline only", "NOT SELECTED"]:
            self.assertNotIn(unwanted, raw)

    def test_detached_head_is_default_and_invalid_branch_rejected(self):
        self.receive(self.package(branch=None))
        target = self.destination / "repo"
        self.assertEqual(self.git("branch", "--show-current", repo=target), "")
        for branch in ["../escape", "x\nname", "-option", "refs/../escape", 42]:
            with self.subTest(branch=branch), self.assertRaises(handoff.HandoffError):
                self.package(branch=branch)

    def test_export_and_receive_previews_do_not_write(self):
        package = self.package()
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        handoff.publish(package, self.output, False, handoff.DEFAULT_LIMITS)
        self.receive(package, apply=False)
        after = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.output.exists())

    def test_existing_destination_and_broken_symlink_are_never_replaced(self):
        self.destination.mkdir()
        keep = self.destination / "precious"
        keep.write_text("keep")
        with self.assertRaises(handoff.HandoffError):
            self.receive()
        self.assertEqual(keep.read_text(), "keep")
        self.destination = self.root / "dangling"
        self.destination.symlink_to("missing")
        with self.assertRaises(handoff.HandoffError):
            self.receive()
        self.assertEqual(os.readlink(self.destination), "missing")

    def test_atomic_export_does_not_replace_concurrent_file(self):
        original = os.link
        def concurrent(*args, **kwargs):
            self.output.write_text("concurrent content")
            return original(*args, **kwargs)
        with mock.patch.object(handoff.os, "link", side_effect=concurrent):
            with self.assertRaises(FileExistsError):
                self.publish()
        self.assertEqual(self.output.read_text(), "concurrent content")
        self.assertEqual([path.name for path in self.shared.iterdir()], [self.output.name])

    def test_atomic_receive_does_not_replace_concurrent_directory(self):
        original = Path.mkdir
        def concurrent(path, *args, **kwargs):
            if path == self.destination:
                original(path)
                (path / "precious").write_text("concurrent content")
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, "mkdir", concurrent):
            with self.assertRaises(FileExistsError):
                self.receive()
        self.assertEqual((self.destination / "precious").read_text(), "concurrent content")

    def test_invalid_manifest_types_unknown_fields_and_versions(self):
        mutations = [
            lambda p: p.update(version=True), lambda p: p.update(version=2),
            lambda p: p.update(extra="unexpected"), lambda p: p.update(base=[]),
            lambda p: p.update(files={}), lambda p: p.update(files=[]),
            lambda p: p["files"][0].update(size=True),
            lambda p: p["files"][0].update(mode="120000"),
            lambda p: p["files"][0].update(action="symlink"),
            lambda p: p["files"][0].update(target="elsewhere"),
            lambda p: p["base"].update(commit="not-an-object-id"),
            lambda p: p["notes"].update(text=[]),
        ]
        for mutate in mutations:
            package = self.package()
            mutate(package)
            with self.subTest(mutation=mutate), self.assertRaises(handoff.HandoffError):
                handoff.validate_package(package, handoff.DEFAULT_LIMITS)
        self.assertFalse(self.destination.exists())

    def test_duplicate_json_keys_nonfinite_values_and_archives_rejected(self):
        for raw in [b'{"format":"a","format":"b"}', b'{"version":NaN}', b'[]']:
            self.output.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(handoff.HandoffError):
                handoff.load_package(self.output, handoff.digest(raw), handoff.DEFAULT_LIMITS)
        with tarfile.open(self.output, "w") as archive:
            item = tarfile.TarInfo("../escape")
            archive.addfile(item)
        with self.assertRaises(handoff.HandoffError):
            handoff.load_package(self.output, handoff.digest(self.output.read_bytes()), handoff.DEFAULT_LIMITS)
        self.assertFalse((self.root / "escape").exists())

    def test_path_traversal_administrative_paths_and_case_collisions_rejected(self):
        bad_paths = ["../escape", "/absolute", "x/../../escape", "x//file", "./file",
                     "x\\file", "C:/escape", ".git/config", ".GIT/config", "a/.git/hooks/x",
                     "x\x00file", "x\nfile", "trailing.", ".gi\u200ct/config", "x/../y"]
        for path in bad_paths:
            package = self.package()
            package["files"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(handoff.HandoffError):
                handoff.validate_package(package, handoff.DEFAULT_LIMITS)
        for paths in [["Readme", "README"], ["a", "a/b"], ["A/file", "a/other"]]:
            with self.subTest(paths=paths), self.assertRaises(handoff.HandoffError):
                handoff.validate_paths(paths)

    def test_base_tree_symlink_and_submodule_rejected(self):
        (self.repo / "link").symlink_to(self.root / "outside")
        self.git("add", "link")
        self.git("commit", "--quiet", "-m", "symlink fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        with self.assertRaises(handoff.HandoffError):
            self.package()
        self.git("rm", "--quiet", "link")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{self.commit},module")
        self.git("commit", "--quiet", "-m", "submodule fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        with self.assertRaises(handoff.HandoffError):
            self.package()

    def test_source_symlink_and_symlinked_parent_rejected(self):
        external = self.root / "external"
        external.mkdir()
        (external / "file").write_text("private")
        (self.repo / "link").symlink_to(external / "file")
        (self.repo / "alias").symlink_to(external)
        for path in ["link", "alias/file"]:
            with self.subTest(path=path), self.assertRaises((OSError, handoff.HandoffError)):
                self.package([path])
        self.notes.unlink()
        self.notes.symlink_to(external / "file")
        with self.assertRaises((OSError, handoff.HandoffError)):
            self.package()

    def test_credential_filename_precaution_and_no_automatic_untracked_selection(self):
        (self.repo / ".env").write_text("PRIVATE=fixture")
        (self.repo / "secret.key").write_text("fixture")
        for path in [".env", "secret.key", "nested/auth.json"]:
            with self.subTest(path=path), self.assertRaises(handoff.HandoffError):
                self.package([path])
        package = self.package()
        self.assertEqual([entry["path"] for entry in package["files"]], ["tracked.txt"])
        self.assertNotIn("PRIVATE", handoff.encode_package(package).decode())

    def test_stale_commit_missing_base_and_tree_identity_rejected_without_destination(self):
        with self.assertRaises(handoff.HandoffError):
            self.receive(expected_commit="0" * 40)
        package = self.package()
        package["base"]["tree"] = "0" * 40
        with self.assertRaises(handoff.HandoffError):
            self.receive(package)
        other = self.root / "other"
        other.mkdir()
        self.git("init", "--quiet", "--template=", repo=other)
        with self.assertRaises(handoff.HandoffError):
            self.receive(base_repo=other)
        (self.repo / "tracked.txt").write_text("later")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "later fixture")
        with self.assertRaises(handoff.HandoffError):
            self.package()
        self.assertFalse(self.destination.exists())

    def test_bad_hash_size_encoding_and_resource_limits(self):
        package = self.package()
        for field, value in [("sha256", "0" * 64), ("size", 123), ("content", "!invalid!")]:
            malformed = copy.deepcopy(package)
            malformed["files"][0][field] = value
            with self.subTest(field=field), self.assertRaises(handoff.HandoffError):
                handoff.validate_package(malformed, handoff.DEFAULT_LIMITS)
        self.publish(package)
        with self.assertRaises(handoff.HandoffError):
            handoff.load_package(self.output, "0" * 64, handoff.DEFAULT_LIMITS)
        for limits in [handoff.Limits(file_bytes=1), handoff.Limits(total_bytes=1),
                       handoff.Limits(notes_bytes=1), handoff.Limits(entries=0)]:
            with self.subTest(limits=limits), self.assertRaises(handoff.HandoffError):
                handoff.validate_package(package, limits)
        with self.assertRaises(handoff.HandoffError):
            handoff.load_package(self.output, handoff.digest(self.output.read_bytes()),
                                 handoff.Limits(package_bytes=1))
        self.assertFalse(self.destination.exists())

    def test_combined_base_and_delta_limits_fail_before_export_or_destination(self):
        for path in ("tracked.txt", "deleted.txt", "untouched.txt"):
            (self.repo / path).write_bytes(b"b" * 20)
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "base exactly at combined byte cap")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.notes.write_text("")
        for path in ("new-one.txt", "new-two.txt"):
            (self.repo / path).write_bytes(b"n" * 25)
        selected = ["new-one.txt", "new-two.txt"]
        package = self.package(selected)
        for limits, expected in [
            (handoff.Limits(entries=3, total_bytes=1000, file_bytes=30), "file count"),
            (handoff.Limits(entries=10, total_bytes=60, file_bytes=30), "total limit"),
            (handoff.Limits(entries=3, total_bytes=60, file_bytes=30), "file count"),
        ]:
            with self.subTest(limits=limits):
                with self.assertRaisesRegex(handoff.HandoffError, expected):
                    handoff.selected_snapshot(self.repo, self.commit, selected, self.notes,
                                              None, limits)
                with self.assertRaisesRegex(handoff.HandoffError, expected):
                    self.receive(package, limits=limits)
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.output.exists())

    def fake_git(self, mode):
        bin_dir = self.root / "fake-bin"
        bin_dir.mkdir(exist_ok=True)
        executable = bin_dir / "git"
        marker = self.root / "surviving-child"
        child_code = f"import time; from pathlib import Path; time.sleep(0.6); Path({str(marker)!r}).write_text('unexpected')"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import subprocess, sys, time\n"
            f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
            + ("sys.stdout.buffer.write(b'x' * 2000000); sys.stdout.buffer.flush()\n"
               if mode == "flood" else "")
            + "time.sleep(5)\n", encoding="utf-8")
        executable.chmod(0o700)
        return bin_dir, marker

    def test_git_output_is_bounded_while_streaming_and_own_children_stop(self):
        bin_dir, marker = self.fake_git("flood")
        processes = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process
        with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}), \
                mock.patch.object(handoff.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(handoff, "GIT_TIMEOUT_SECONDS", 2):
            started = time.monotonic()
            with self.assertRaisesRegex(handoff.HandoffError, "output exceeds"):
                handoff.git(None, "fixture", output_limit=1024)
            self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0].returncode, -signal.SIGKILL)
        self.assertTrue(processes[0].stdout.closed)
        time.sleep(0.8)
        self.assertFalse(marker.exists(), "failure cleanup must also stop the fake command's child")

    def test_git_timeout_kills_and_reaps_own_command_group(self):
        bin_dir, marker = self.fake_git("timeout")
        processes = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process
        with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}), \
                mock.patch.object(handoff.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(handoff, "GIT_TIMEOUT_SECONDS", 0.15):
            started = time.monotonic()
            with self.assertRaisesRegex(handoff.HandoffError, "timed out"):
                handoff.git(None, "fixture", output_limit=1024)
            self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0].returncode, -signal.SIGKILL)
        self.assertTrue(processes[0].stdout.closed)
        time.sleep(0.8)
        self.assertFalse(marker.exists(), "timeout cleanup must also stop the fake command's child")

    def test_duplicate_paths_missing_delete_and_path_conflicts_rejected(self):
        package = self.package()
        package["files"].append(copy.deepcopy(package["files"][0]))
        with self.assertRaises(handoff.HandoffError):
            handoff.validate_package(package, handoff.DEFAULT_LIMITS)
        package = self.package()
        package["files"] = [{"path": "missing", "action": "delete"}]
        with self.assertRaises(handoff.HandoffError):
            self.receive(package)
        package = self.package()
        package["files"][0]["path"] = "untouched.txt/child"
        with self.assertRaises(handoff.HandoffError):
            self.receive(package)
        self.assertFalse(self.destination.exists())

    def test_filters_hooks_and_inherited_git_configuration_do_not_execute(self):
        marker = self.root / "SHOULD_NOT_EXIST"
        hook_dir = self.root / "hooks"
        hook_dir.mkdir()
        hook = hook_dir / "post-checkout"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        hook.chmod(0o755)
        (self.repo / ".gitattributes").write_text("*.txt filter=fixture\n")
        self.git("add", ".gitattributes")
        self.git("commit", "--quiet", "-m", "attribute fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.git("config", "filter.fixture.smudge", f"touch '{marker}'")
        self.git("config", "filter.fixture.clean", f"touch '{marker}'")
        self.git("config", "core.hooksPath", str(hook_dir))
        global_config = self.root / "global-config"
        global_config.write_text(f'[filter "fixture"]\n smudge = touch {marker}\n'
                                 f'[core]\n hooksPath = {hook_dir}\n')
        overrides = {"GIT_CONFIG_GLOBAL": str(global_config), "GIT_CONFIG_COUNT": "1",
                     "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": str(hook_dir)}
        with mock.patch.dict(os.environ, overrides):
            package = self.package()
            self.receive(package)
        self.assertFalse(marker.exists())
        self.assertEqual((self.destination / "repo" / "tracked.txt").read_text(), "base\n")

    def test_failed_import_keeps_only_new_envelope_for_inspection_no_cleanup(self):
        original = handoff.git
        def fail(repo, *args, **kwargs):
            if args and args[0] == "fetch":
                raise handoff.HandoffError("fixture failure")
            return original(repo, *args, **kwargs)
        with mock.patch.object(handoff, "git", side_effect=fail):
            with self.assertRaises(handoff.HandoffError):
                self.receive()
        self.assertTrue((self.destination / "INCOMPLETE").exists())
        self.assertTrue((self.repo / "tracked.txt").exists())

    def test_cli_help_and_dry_run_need_no_home_or_network_changes(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        result = subprocess.run([sys.executable, str(SCRIPT), "export", "--repo", str(self.repo),
                                 "--expected-commit", self.commit, "--path", "tracked.txt",
                                 "--notes", str(self.notes), "--output", str(self.output)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["state"], "planned")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
