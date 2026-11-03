#!/usr/bin/env python3
"""Export selected working files and notes; receive into a fresh isolated checkout.

Python 3.10+, Git 2.29+, macOS or Linux. No network access or automatic credential
harvesting. Artifacts omit Git history; selected content still needs review.
All locations and the expected base are explicit.
"""

import argparse
import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import secrets
import selectors
import signal
import time
import unicodedata


class HandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Limits:
    file_bytes: int = 16 * 1024 * 1024
    total_bytes: int = 128 * 1024 * 1024
    package_bytes: int = 192 * 1024 * 1024
    notes_bytes: int = 1024 * 1024
    entries: int = 10000


DEFAULT_LIMITS = Limits()
FORMAT = "h-stack-selected-files"
VERSION = 1
GIT_TIMEOUT_SECONDS = 60


def require(condition, message):
    if not condition:
        raise HandoffError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hex_value(value, length, label):
    require(isinstance(value, str) and len(value) == length
            and all(char in "0123456789abcdef" for char in value),
            f"invalid {label}")
    return value


def exact_keys(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys),
            f"invalid {label} fields")


def path_parts(value):
    require(isinstance(value, str) and 0 < len(value.encode("utf-8")) <= 1024,
            "invalid file path")
    require(not any(unicodedata.category(char) in ("Cc", "Cf", "Cs") for char in value),
            "control or invisible formatting character in file path")
    require("\\" not in value and ":" not in value, "non-portable file path")
    parts = value.split("/")
    require(all(part and part not in (".", "..") for part in parts),
            "file path must be a canonical relative path")
    require(all(part.casefold() != ".git" for part in parts),
            "Git administrative paths are forbidden")
    require(unicodedata.normalize("NFC", value) == value,
            "file paths must use NFC Unicode normalization")
    require(all(not part.endswith((".", " ")) for part in parts),
            "non-portable trailing character in file path")
    return parts


def sensitive_path(value):
    """A narrow filename precaution, not a content or secret detector."""
    names = [part.casefold() for part in path_parts(value)]
    return any(name in {".ssh", ".aws", ".gnupg", "credentials", "credentials.json",
                        "auth.json", "id_rsa", "id_ed25519", ".netrc", ".npmrc"}
               or name == ".env" or name.startswith(".env.")
               or name.endswith((".pem", ".key", ".p12", ".pfx")) for name in names)


def validate_paths(paths):
    """Reject file/directory conflicts and case aliases on macOS as well as Linux."""
    files = set(paths)
    spellings = {}
    for path in paths:
        parts = path_parts(path)
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            folded = prefix.casefold()
            require(folded not in spellings or spellings[folded] == prefix,
                    "case-colliding file paths")
            spellings[folded] = prefix
            require(length == len(parts) or prefix not in files,
                    "file/directory path conflict")


def git_env():
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_ATTR_NOSYSTEM="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_TERMINAL_PROMPT="0")
    return environment


def git(repo, *arguments, input_data=None, output_limit=8 * 1024 * 1024):
    command = ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
               "-c", "protocol.allow=never", "-c", "protocol.file.allow=always"]
    if repo is not None:
        command.extend(["-C", str(repo)])
    require(type(output_limit) is int and output_limit >= 0, "invalid Git output limit")
    process = None
    try:
        # Discard stderr instead of buffering or echoing private diagnostics.
        # Own the command's group so failure cleanup includes its pack children.
        process = subprocess.Popen([*command, *arguments],
                                   stdin=subprocess.PIPE if input_data else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   start_new_session=True, env=git_env())
        deadline = time.monotonic() + GIT_TIMEOUT_SECONDS
        chunks, total = [], 0
        pending = memoryview(input_data or b"")
        with selectors.DefaultSelector() as selector:
            os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ, "output")
            if pending:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "input")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                require(remaining > 0, "Git unavailable or timed out")
                ready = selector.select(remaining)
                require(bool(ready), "Git unavailable or timed out")
                for key, _ in ready:
                    try:
                        if key.data == "input":
                            count = os.write(key.fd, pending[:65536])
                            require(count > 0, "Git input failed")
                            pending = pending[count:]
                            if not pending:
                                selector.unregister(process.stdin)
                                process.stdin.close()
                        else:
                            data = os.read(key.fd, min(65536, output_limit - total + 1))
                            if not data:
                                selector.unregister(process.stdout)
                                continue
                            total += len(data)
                            require(total <= output_limit, "Git output exceeds the configured limit")
                            chunks.append(data)
                    except BlockingIOError:
                        continue
        remaining = deadline - time.monotonic()
        require(remaining > 0, "Git unavailable or timed out")
        process.wait(timeout=remaining)
        require(process.returncode == 0,
                "Git command failed; check the selected local repository/base")
        return b"".join(chunks)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HandoffError("Git unavailable or timed out") from error
    finally:
        if process is not None:
            # Do not poll/reap before killing on failure: the unreaped command
            # prevents its process-group ID from being recycled during cleanup.
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()


def directory(value):
    path = Path(value).expanduser().absolute()
    for component in (path, *path.parents):
        require(not component.is_symlink(), "directory paths must not cross symlinks")
    require(path.is_dir(), "selected directory does not exist")
    return path.resolve(strict=True)


def repository(value):
    path = directory(value)
    root = git(path, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    require(Path(root).resolve() == path, "select the root of a non-bare Git checkout")
    return path


def open_directory(path):
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def read_file(root, relative, maximum):
    parts = path_parts(relative)
    descriptor = open_directory(root)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                  dir_fd=descriptor)
        with os.fdopen(file_descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode), "only regular files can be transferred")
            require(before.st_size <= maximum, "file exceeds the configured limit")
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        require(len(data) <= maximum, "file exceeds the configured limit")
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns), "file changed while being read")
        return data, "100755" if before.st_mode & 0o111 else "100644"
    finally:
        os.close(descriptor)


def base_info(repo, commit, limits):
    object_format = git(repo, "rev-parse", "--show-object-format").decode().strip()
    require(object_format in ("sha1", "sha256"), "unsupported Git object format")
    width = 40 if object_format == "sha1" else 64
    hex_value(commit, width, "base commit")
    require(git(repo, "cat-file", "-t", commit).strip() == b"commit",
            "base object is not a commit")
    tree = git(repo, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    hex_value(tree, width, "base tree")
    entries = {}
    total = 0
    raw = git(repo, "ls-tree", "-r", "-l", "-z", "--full-tree", commit)
    for record in raw.split(b"\0"):
        if not record:
            continue
        fields, raw_path = record.split(b"\t", 1)
        mode, kind, object_id, raw_size = fields.split()
        path = raw_path.decode("utf-8")
        path_parts(path)
        require(mode in (b"100644", b"100755") and kind == b"blob",
                "base tree contains a symlink, submodule or unsupported entry")
        size = int(raw_size)
        require(0 <= size <= limits.file_bytes, "base file exceeds the configured limit")
        total += size
        require(total <= limits.total_bytes, "base tree exceeds the configured total limit")
        require(len(entries) < limits.entries, "too many base files")
        entries[path] = {"mode": mode.decode(), "oid": object_id.decode(), "size": size}
    validate_paths(list(entries))
    return {"commit": commit, "tree": tree, "object_format": object_format}, entries


def check_branch(branch):
    require(branch is None or isinstance(branch, str), "invalid branch")
    if branch is not None:
        require(0 < len(branch) <= 200 and not branch.startswith("-")
                and not any(ord(char) < 32 or ord(char) == 127 for char in branch),
                "invalid branch")
        git(None, "check-ref-format", f"refs/heads/{branch}")


def encode_package(package):
    return (json.dumps(package, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def selected_snapshot(repo, expected_commit, selected, notes_path, branch, limits):
    actual = git(repo, "rev-parse", "HEAD").decode().strip()
    require(actual == expected_commit, "source HEAD differs from the expected commit")
    base, base_files = base_info(repo, actual, limits)
    check_branch(branch)
    require(0 < len(selected) <= limits.entries, "select at least one file, within the entry limit")
    require(len(set(selected)) == len(selected), "duplicate selected file")
    validate_paths(selected)
    notes_path = Path(notes_path).expanduser().absolute()
    notes_parent = directory(notes_path.parent)
    notes, _ = read_file(notes_parent, notes_path.name, limits.notes_bytes)
    text = notes.decode("utf-8")
    operations = []
    total = len(notes)
    for path in sorted(selected):
        require(not sensitive_path(path), "selected path has a credential-like filename; sanitize it first")
        try:
            content, mode = read_file(repo, path, limits.file_bytes)
        except FileNotFoundError:
            require(path in base_files, "selected missing path is not a tracked base file")
            operations.append({"path": path, "action": "delete"})
            continue
        total += len(content)
        require(total <= limits.total_bytes, "selected files exceed the configured total limit")
        operations.append({"path": path, "action": "write", "mode": mode,
                           "size": len(content), "sha256": digest(content),
                           "content": base64.b64encode(content).decode("ascii")})
    require(git(repo, "rev-parse", "HEAD").decode().strip() == actual,
            "source HEAD changed during snapshot")
    package = {"format": FORMAT, "version": VERSION, "base": base, "branch": branch,
               "notes": {"text": text, "sha256": digest(notes)}, "files": operations}
    validate_package(package, limits)
    final_paths(base_files, operations, limits)
    return package


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def validate_package(package, limits):
    exact_keys(package, ("format", "version", "base", "branch", "notes", "files"), "manifest")
    require(package["format"] == FORMAT and type(package["version"]) is int
            and package["version"] == VERSION, "unsupported handoff format/version")
    base = package["base"]
    exact_keys(base, ("commit", "tree", "object_format"), "base")
    require(base["object_format"] in ("sha1", "sha256"), "unsupported object format")
    width = 40 if base["object_format"] == "sha1" else 64
    hex_value(base["commit"], width, "base commit")
    hex_value(base["tree"], width, "base tree")
    check_branch(package["branch"])
    notes = package["notes"]
    exact_keys(notes, ("text", "sha256"), "notes")
    require(isinstance(notes["text"], str), "invalid notes text")
    notes_bytes = notes["text"].encode("utf-8")
    require(len(notes_bytes) <= limits.notes_bytes, "notes exceed the configured limit")
    require(digest(notes_bytes) == notes["sha256"], "notes hash mismatch")
    operations = package["files"]
    require(isinstance(operations, list) and 0 < len(operations) <= limits.entries,
            "invalid selected file count")
    total = len(notes_bytes)
    seen = set()
    for entry in operations:
        require(isinstance(entry, dict), "invalid file entry")
        require(entry.get("action") in ("write", "delete"), "invalid file action")
        keys = ("path", "action") if entry["action"] == "delete" else (
            "path", "action", "mode", "size", "sha256", "content")
        exact_keys(entry, keys, "file entry")
        path_parts(entry["path"])
        require(entry["path"] not in seen, "duplicate selected path")
        seen.add(entry["path"])
        require(not sensitive_path(entry["path"]), "credential-like selected path is forbidden")
        if entry["action"] == "write":
            require(entry["mode"] in ("100644", "100755"), "invalid file mode")
            require(type(entry["size"]) is int and 0 <= entry["size"] <= limits.file_bytes,
                    "file exceeds the configured limit")
            require(isinstance(entry["content"], str)
                    and len(entry["content"]) <= ((entry["size"] + 2) // 3) * 4,
                    "invalid encoded file size")
            try:
                data = base64.b64decode(entry["content"], validate=True)
            except (ValueError, binascii.Error) as error:
                raise HandoffError("invalid file encoding") from error
            require(len(data) == entry["size"] and digest(data) == entry["sha256"],
                    "file size or hash mismatch")
            total += len(data)
            require(total <= limits.total_bytes, "payload exceeds the configured total limit")
    # Deletions can accompany file-to-directory changes; validate the resulting
    # tree against the local base separately rather than just this delta.


def final_paths(base_files, operations, limits):
    paths = set(base_files)
    for entry in operations:
        if entry["action"] == "delete":
            require(entry["path"] in base_files, "deletion is not present in the base tree")
            paths.remove(entry["path"])
    for entry in operations:
        if entry["action"] == "write":
            paths.add(entry["path"])
    validate_paths(list(paths))
    require(len(paths) <= limits.entries, "resulting checkout exceeds the configured file count")
    written = {entry["path"]: entry for entry in operations if entry["action"] == "write"}
    total = sum((written[path] if path in written else base_files[path])["size"] for path in paths)
    require(total <= limits.total_bytes, "resulting checkout exceeds the configured total limit")
    return paths


def load_package(path, expected_sha256, limits):
    hex_value(expected_sha256, 64, "artifact SHA-256")
    path = Path(path).expanduser().absolute()
    raw, _ = read_file(directory(path.parent), path.name, limits.package_bytes)
    require(digest(raw) == expected_sha256, "artifact hash mismatch")
    try:
        package = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 HandoffError("non-finite JSON value")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise HandoffError("invalid JSON handoff; archives are not accepted") from error
    validate_package(package, limits)
    return package


def output_path(value):
    path = Path(value).expanduser().absolute()
    parent = directory(path.parent)
    require(path.name not in ("", ".", ".."), "invalid destination name")
    require(not os.path.lexists(path), "destination already exists; nothing was changed")
    return parent / path.name


def publish(package, output, apply, limits):
    raw = encode_package(package)
    require(len(raw) <= limits.package_bytes, "artifact exceeds the configured package limit")
    output = output_path(output)
    if apply:
        parent_fd = open_directory(output.parent)
        temporary = None
        try:
            temporary = ".handoff-" + secrets.token_hex(16)
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent_fd)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            # Same-directory hard link is atomic and fails if any entry exists.
            os.link(temporary, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd,
                    follow_symlinks=False)
        finally:
            if temporary is not None:
                os.unlink(temporary, dir_fd=parent_fd)
            os.close(parent_fd)
    return {"state": "exported" if apply else "planned", "artifact": str(output),
            "sha256": digest(raw), "base": package["base"], "branch": package["branch"],
            "files": [{key: value for key, value in entry.items() if key != "content"}
                      for entry in package["files"]]}


def write_new(path, content, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o700 if executable else 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)


def receive(package, base_repo, destination, expected_commit, apply, limits):
    validate_package(package, limits)
    require(package["base"]["commit"] == expected_commit,
            "artifact base differs from the independently expected commit")
    base_repo = repository(base_repo)
    actual_base, base_files = base_info(base_repo, expected_commit, limits)
    require(actual_base == package["base"], "local base identity/tree differs from artifact")
    wanted = final_paths(base_files, package["files"], limits)
    destination = output_path(destination)
    if not apply:
        return {"state": "planned", "destination": str(destination),
                "base": actual_base, "files": len(wanted)}

    # Reserve once. Never delete a failed import or reuse an existing directory.
    # Parents must be trusted/stable; this is not a sandbox against the same
    # local user changing ancestors or the newly created checkout concurrently.
    destination.mkdir(mode=0o700)
    write_new(destination / "INCOMPLETE", b"Import has not completed. Inspect before use.\n")
    repo = destination / "repo"
    repo.mkdir(mode=0o700)
    git(repo, "init", "--quiet", "--template=", f"--object-format={actual_base['object_format']}")
    # Only this caller-selected local checkout is read. Depth 1 copies the base
    # commit/tree, not its ancestors. No origin URL or source config is installed.
    git(repo, "fetch", "--quiet", "--depth=1", "--no-tags", "--no-write-fetch-head",
        "--no-recurse-submodules", "--no-auto-maintenance", "--", str(base_repo), expected_commit)
    fetched, _ = base_info(repo, expected_commit, limits)
    require(fetched == actual_base, "local base changed during import")
    if package["branch"] is None:
        git(repo, "update-ref", "--no-deref", "HEAD", expected_commit)
    else:
        reference = f"refs/heads/{package['branch']}"
        git(repo, "update-ref", reference, expected_commit)
        git(repo, "symbolic-ref", "HEAD", reference)
    git(repo, "read-tree", expected_commit)
    changes = {entry["path"]: entry for entry in package["files"]}
    # Read raw Git blobs, not checkout-index/checkout: neither repository
    # attributes nor recipient filters/hooks can execute during materialization.
    for path in sorted(wanted):
        entry = changes.get(path)
        if entry is not None:
            data = base64.b64decode(entry["content"], validate=True)
            mode = entry["mode"]
        else:
            base_entry = base_files[path]
            data = git(repo, "cat-file", "blob", base_entry["oid"],
                       output_limit=limits.file_bytes)
            require(len(data) == base_entry["size"], "base blob size changed")
            mode = base_entry["mode"]
        write_new(repo.joinpath(*path_parts(path)), data, executable=mode == "100755")
    write_new(destination / "HANDOFF.md", package["notes"]["text"].encode("utf-8"))
    write_new(destination / "manifest.json", encode_package({
        key: value for key, value in package.items() if key != "files"} | {
            "files": [{key: value for key, value in entry.items() if key != "content"}
                      for entry in package["files"]]}))
    (destination / "INCOMPLETE").unlink()
    return {"state": "received", "destination": str(destination), "repo": str(repo),
            "base": actual_base, "branch": package["branch"], "files": len(wanted)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="preview/export explicitly selected files and notes")
    export.add_argument("--repo", required=True, type=Path)
    export.add_argument("--expected-commit", required=True)
    export.add_argument("--path", action="append", required=True, dest="paths",
                        help="one exact repo-relative file or tracked deletion; repeat")
    export.add_argument("--notes", required=True, type=Path)
    export.add_argument("--branch", help="explicit destination branch label; default detached HEAD")
    export.add_argument("--output", required=True, type=Path,
                        help="new artifact file in an existing caller-selected shared directory")
    import_parser = sub.add_parser("receive", help="preview/receive using a local known base")
    import_parser.add_argument("--artifact", required=True, type=Path)
    import_parser.add_argument("--expected-sha256", required=True,
                               help="export digest received through a trusted separate channel")
    import_parser.add_argument("--expected-commit", required=True)
    import_parser.add_argument("--base-repo", required=True, type=Path,
                               help="local checkout containing the base commit; no network fetch")
    import_parser.add_argument("--destination", required=True, type=Path,
                               help="new envelope directory; repository will be in its repo/ child")
    for command in (export, import_parser):
        command.add_argument("--apply", action="store_true", help="write (default: read-only preview)")
    args = parser.parse_args()
    try:
        if args.command == "export":
            package = selected_snapshot(repository(args.repo), args.expected_commit,
                                        args.paths, args.notes, args.branch, DEFAULT_LIMITS)
            result = publish(package, args.output, args.apply, DEFAULT_LIMITS)
        else:
            package = load_package(args.artifact, args.expected_sha256, DEFAULT_LIMITS)
            result = receive(package, args.base_repo, args.destination,
                             args.expected_commit, args.apply, DEFAULT_LIMITS)
        print(json.dumps(result, indent=2))
    except (HandoffError, OSError, UnicodeError, RecursionError) as error:
        # OS errors can include private paths, so suppress those details.
        message = str(error) if isinstance(error, HandoffError) else "filesystem or encoding operation failed"
        parser.exit(1, f"handoff: {message}\n")


if __name__ == "__main__":
    main()
