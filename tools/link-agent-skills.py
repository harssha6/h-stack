#!/usr/bin/env python3
"""Plan or create add-only relative skill symlinks on macOS and Linux."""

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import stat
from typing import NamedTuple


class TargetRoot(NamedTuple):
    path: Path
    identity: tuple[int, int] | None


def identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def overlaps(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def prepare(source: Path, targets: list[Path]) -> tuple[list[Path], list[TargetRoot]]:
    source = source.expanduser().resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f"source is not a directory: {source}")

    checked = []
    for target in targets:
        target = target.expanduser().absolute()
        # Reject files and dangling symlinks anywhere in the requested directory
        # path before resolving it or creating any of the other target roots.
        for ancestor in (target, *target.parents):
            if os.path.lexists(ancestor) and not ancestor.is_dir():
                raise ValueError(f"target path crosses a non-directory: {ancestor}")
        target = target.resolve()
        if overlaps(source, target):
            raise ValueError(f"source and target must not overlap: {target}")
        if any(overlaps(target, previous.path) for previous in checked):
            raise ValueError(f"target directories must not overlap or repeat: {target}")
        current = target.stat(follow_symlinks=False) if target.exists() else None
        checked.append(TargetRoot(target, identity(current) if current else None))

    skills = sorted(
        (entry for entry in source.iterdir()
         if entry.is_dir() and (entry / "SKILL.md").is_file()),
        key=lambda entry: entry.name,
    )
    return skills, checked


def verify_root(path: Path, expected: tuple[int, int]) -> None:
    current = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(current.st_mode) or identity(current) != expected:
        raise ValueError(f"target directory changed during application: {path}")


def open_target(target: TargetRoot) -> tuple[int, tuple[int, int]]:
    # Ancestor directories must be trusted and stable. Never follow a symlink
    # replacing the selected root, and bind later writes to its directory fd.
    if target.identity is None:
        target.path.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        opened = identity(os.fstat(descriptor))
        if target.identity is not None and opened != target.identity:
            raise ValueError(f"target directory changed since inspection: {target.path}")
        verify_root(target.path, opened)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor, opened


def link_skills(skills: list[Path], targets: list[TargetRoot], apply: bool) -> None:
    if not apply:
        for target in targets:
            for skill in skills:
                destination = target.path / skill.name
                if os.path.lexists(destination):
                    print(f"kept {destination}")
                else:
                    relative_source = os.path.relpath(skill, start=target.path)
                    print(f"planned {destination} -> {relative_source}")
        return
    if not skills:
        return

    with ExitStack() as cleanup:
        roots = []
        for target in targets:
            descriptor, opened = open_target(target)
            cleanup.callback(os.close, descriptor)
            roots.append((target.path, descriptor, opened))
        for path, descriptor, opened in roots:
            for skill in skills:
                verify_root(path, opened)
                destination = path / skill.name
                try:
                    os.stat(skill.name, dir_fd=descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    print(f"kept {destination}")
                    continue
                relative_source = os.path.relpath(skill, start=path)
                try:
                    # dir_fd anchors the write even if the root is renamed
                    # after verification. Never replace a racing new entry.
                    os.symlink(relative_source, skill.name, dir_fd=descriptor)
                except FileExistsError:
                    print(f"kept {destination}")
                else:
                    verify_root(path, opened)
                    print(f"created {destination} -> {relative_source}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="collection of immediate directories containing SKILL.md")
    parser.add_argument("--target", type=Path, action="append", required=True,
                        help="skills directory to link into; repeat for more tools")
    parser.add_argument("--apply", action="store_true",
                        help="create links and missing target directories (default: dry-run)")
    args = parser.parse_args()
    try:
        skills, targets = prepare(args.source, args.target)
        if not skills:
            print("No immediate skill directories containing SKILL.md found.")
        link_skills(skills, targets, args.apply)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
