#!/usr/bin/env python3
"""Preview a hum installation into a new, explicitly chosen directory."""

import argparse
import json
import os
from pathlib import Path


FILES = ("hum", "hum_lifecycle.py", "hum_terminal.py", "LICENSE")


def install(directory: Path, apply: bool) -> None:
    directory = directory.expanduser().absolute()
    if os.path.lexists(directory):
        raise ValueError(f"installation directory already exists; choose a new directory: {directory}")
    for ancestor in directory.parents:
        if os.path.lexists(ancestor) and not ancestor.is_dir():
            raise ValueError(f"installation path crosses a non-directory: {ancestor}")
    source = Path(__file__).resolve().parent
    contents = {name: (source.parent / name if name == "LICENSE" else source / name).read_bytes()
                for name in FILES}
    print(json.dumps({"mode": "apply" if apply else "preview",
                      "directory": str(directory), "files": list(FILES),
                      "services_enabled": False}, indent=2))
    if not apply:
        return
    # Chosen parent directories must be trusted and stable. mkdir refuses an
    # existing root; O_EXCL/O_NOFOLLOW never overwrite destination entries.
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir(mode=0o700)
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, content in contents.items():
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o700 if name == "hum" else 0o600, dir_fd=descriptor)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True,
                        help="new directory for the executable and its two sibling helpers")
    parser.add_argument("--apply", action="store_true", help="write files; default only prints the plan")
    args = parser.parse_args()
    try:
        install(args.directory, args.apply)
    except (OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
