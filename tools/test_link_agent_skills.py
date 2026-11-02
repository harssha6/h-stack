"""Offline CLI checks; every filesystem mutation stays in a temporary directory."""

import os
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


LINKER = Path(__file__).with_name("link-agent-skills.py")
SPEC = importlib.util.spec_from_file_location("skill_linker", LINKER)
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class LinkSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.target = self.root / "tool" / "skills"
        self.add_skill("example")

    def add_skill(self, name):
        folder = self.source / name
        folder.mkdir()
        (folder / "SKILL.md").write_text("Example skill\n", encoding="utf-8")
        return folder

    def run_linker(self, *arguments, source=None, targets=None):
        command = [sys.executable, str(LINKER), "--source", str(source or self.source)]
        for target in targets if targets is not None else [self.target]:
            command.extend(["--target", str(target)])
        return subprocess.run([*command, *arguments], capture_output=True, text=True)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dry_run_does_not_create_target_or_links(self):
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        self.assert_success(self.run_linker())
        after = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse(self.target.exists())

    def test_apply_creates_relative_links_in_each_target(self):
        other = self.root / "another tool" / "skills"
        self.add_skill("second")
        self.assert_success(self.run_linker("--apply", targets=[self.target, other]))
        for target in [self.target, other]:
            for name in ["example", "second"]:
                link = target / name
                self.assertTrue(link.is_symlink())
                self.assertFalse(Path(os.readlink(link)).is_absolute())
                self.assertEqual(link.resolve(), (self.source / name).resolve())
                self.assertEqual((link / "SKILL.md").read_text(), "Example skill\n")

    def test_keeps_existing_file_directory_symlink_and_dangling_symlink(self):
        for name in ["directory", "linked", "broken"]:
            self.add_skill(name)
        self.target.mkdir(parents=True)
        existing_file = self.target / "example"
        existing_file.write_text("User content\n", encoding="utf-8")
        existing_directory = self.target / "directory"
        existing_directory.mkdir()
        (existing_directory / "keep").write_text("Keep me\n", encoding="utf-8")
        live = self.root / "user-skill"
        live.mkdir()
        (self.target / "linked").symlink_to(live)
        (self.target / "broken").symlink_to("missing-user-skill")
        links_before = {name: os.readlink(self.target / name) for name in ["linked", "broken"]}
        self.assert_success(self.run_linker("--apply"))
        self.assertEqual(existing_file.read_text(), "User content\n")
        self.assertEqual((existing_directory / "keep").read_text(), "Keep me\n")
        for name, previous in links_before.items():
            self.assertEqual(os.readlink(self.target / name), previous)
        self.assertFalse((self.target / "broken").exists())
        self.assertTrue((self.target / "broken").is_symlink())

    def test_repeated_application_keeps_link_identity(self):
        self.assert_success(self.run_linker("--apply"))
        link = self.target / "example"
        inode = link.lstat().st_ino
        value = os.readlink(link)
        self.assert_success(self.run_linker("--apply"))
        self.assertEqual(link.lstat().st_ino, inode)
        self.assertEqual(os.readlink(link), value)

    def test_only_immediate_skill_directories_are_linked(self):
        nested = self.source / "non-skill" / "nested"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("Nested\n", encoding="utf-8")
        (self.source / "file").write_text("Not a directory\n", encoding="utf-8")
        self.assert_success(self.run_linker("--apply"))
        self.assertEqual([entry.name for entry in self.target.iterdir()], ["example"])

    def test_invalid_source_does_not_create_target(self):
        for source in [self.root / "missing", self.source / "example" / "SKILL.md"]:
            with self.subTest(source=source):
                self.assertNotEqual(self.run_linker("--apply", source=source).returncode, 0)
                self.assertFalse(self.target.exists())

    def test_source_self_and_ancestor_overlap_do_not_mutate(self):
        for target in [self.source, self.source / "nested", self.root]:
            with self.subTest(target=target):
                before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
                result = self.run_linker("--apply", targets=[self.target, target])
                self.assertNotEqual(result.returncode, 0)
                after = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
                self.assertEqual(before, after)

    def test_overlapping_or_repeated_targets_do_not_mutate(self):
        for other in [self.target, self.target / "nested"]:
            with self.subTest(other=other):
                self.assertNotEqual(self.run_linker("--apply", targets=[self.target, other]).returncode, 0)
                self.assertFalse(self.target.exists())

    def test_invalid_target_after_valid_target_does_not_mutate(self):
        bad = self.root / "file"
        bad.write_text("Keep\n", encoding="utf-8")
        broken = self.root / "dangling"
        broken.symlink_to("missing")
        for target in [bad, bad / "child", broken, broken / "child"]:
            with self.subTest(target=target):
                self.assertNotEqual(self.run_linker("--apply", targets=[self.target, target]).returncode, 0)
                self.assertFalse(self.target.exists())
                self.assertEqual(bad.read_text(), "Keep\n")
                self.assertEqual(os.readlink(broken), "missing")

    def test_target_alias_of_source_is_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.source)
        self.assertNotEqual(self.run_linker("--apply", targets=[self.target, alias]).returncode, 0)
        self.assertFalse(self.target.exists())
        self.assertTrue(alias.is_symlink())

    def test_missing_required_arguments_do_not_mutate(self):
        result = subprocess.run([sys.executable, str(LINKER), "--apply"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_replaced_existing_root_cannot_redirect_apply(self):
        self.target.mkdir(parents=True)
        skills, targets = API.prepare(self.source, [self.target])
        original = self.root / "original"
        outside = self.root / "unselected"
        outside.mkdir()
        self.target.rename(original)
        self.target.symlink_to(outside)
        with self.assertRaises((OSError, ValueError)):
            API.link_skills(skills, targets, apply=True)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list(original.iterdir()), [])

    def test_replacement_directory_identity_is_rejected(self):
        self.target.mkdir(parents=True)
        skills, targets = API.prepare(self.source, [self.target])
        self.target.rename(self.root / "original")
        self.target.mkdir()
        with self.assertRaises(ValueError):
            API.link_skills(skills, targets, apply=True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_root_replaced_with_symlink_cannot_redirect_apply(self):
        skills, targets = API.prepare(self.source, [self.target])
        outside = self.root / "unselected"
        outside.mkdir()
        self.target.parent.mkdir()
        self.target.symlink_to(outside)
        with self.assertRaises((OSError, ValueError)):
            API.link_skills(skills, targets, apply=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_swap_during_symlink_creation_stays_anchored_and_reports_change(self):
        self.target.mkdir(parents=True)
        skills, targets = API.prepare(self.source, [self.target])
        original = self.root / "original"
        outside = self.root / "unselected"
        outside.mkdir()
        symlink = os.symlink

        def replace_root_then_link(source, destination, **kwargs):
            self.target.rename(original)
            symlink(outside, self.target)
            return symlink(source, destination, **kwargs)

        with mock.patch.object(API.os, "symlink", side_effect=replace_root_then_link):
            with self.assertRaises(ValueError):
                API.link_skills(skills, targets, apply=True)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue((original / "example").is_symlink())

    def test_racing_existing_entry_is_kept(self):
        skills, targets = API.prepare(self.source, [self.target])
        symlink = os.symlink

        def create_user_file_then_link(source, destination, **kwargs):
            (self.target / destination).write_text("User race\n", encoding="utf-8")
            return symlink(source, destination, **kwargs)

        with mock.patch.object(API.os, "symlink", side_effect=create_user_file_then_link):
            API.link_skills(skills, targets, apply=True)
        self.assertEqual((self.target / "example").read_text(), "User race\n")


if __name__ == "__main__":
    unittest.main()
