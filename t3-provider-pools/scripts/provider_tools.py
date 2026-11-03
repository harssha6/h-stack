"""Portable account-candidate validation and a bounded native stdio transport.

No credential files are read by this module. Native authentication remains the
responsibility of the explicitly selected executable and account home.
"""

import json
import math
import os
from pathlib import Path
import queue
import selectors
import stat
import subprocess
import threading
import time
import unicodedata

MAX_BYTES = 1024 * 1024


class SafeError(Exception):
    """A fixed message that is safe to return across the adapter boundary."""


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SafeError("Duplicate JSON field")
        result[key] = value
    return result


def parse_json(data):
    try:
        return json.loads(data, object_pairs_hook=object_pairs,
                          parse_constant=lambda _: invalid_constant())
    except (ValueError, UnicodeError, RecursionError):
        raise SafeError("Invalid JSON") from None


def invalid_constant():
    raise SafeError("Non-finite JSON number")


def read_json(path):
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise SafeError("JSON file exceeds size limit")
        return parse_json(raw)
    except OSError:
        raise SafeError("Cannot read selected JSON file") from None


def fields(value, required, optional=()):
    if not isinstance(value, dict):
        raise SafeError("Expected a JSON object")
    keys = set(value)
    if not set(required) <= keys or keys - set(required) - set(optional):
        raise SafeError("Missing or unsupported configuration field")


def text(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise SafeError("Expected a bounded nonempty string")
    if any(ord(char) < 32 for char in value):
        raise SafeError("Control characters are not allowed")
    return value


def absolute_path(value):
    value = text(value)
    path = Path(value)
    if not path.is_absolute():
        raise SafeError("Use an explicit absolute path")
    return path


def bridge_config(value):
    fields(value, ("version", "nativeExecutable", "nativeHome", "allowedTools"),
           ("timeoutSeconds",))
    if type(value["version"]) is not int or value["version"] != 1:
        raise SafeError("Unsupported configuration version")
    executable = absolute_path(value["nativeExecutable"])
    home = absolute_path(value["nativeHome"])
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise SafeError("Selected native executable is unavailable")
    if not home.is_dir():
        raise SafeError("Selected native account directory is unavailable")
    allowed = value["allowedTools"]
    if not isinstance(allowed, dict) or not allowed or len(allowed) > 100:
        raise SafeError("Configure one to 100 explicit tool aliases")
    for alias, original in allowed.items():
        text(alias)
        text(original)
    if len(set(allowed.values())) != len(allowed):
        raise SafeError("Native tools must not have multiple aliases")
    timeout = value.get("timeoutSeconds", 30)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0.1 <= timeout <= 120:
        raise SafeError("Timeout must be between 0.1 and 120 seconds")
    return {"executable": str(executable), "home": str(home),
            "allowed": dict(allowed), "timeout": timeout}


class NativeTransport:
    """Sequential newline-JSON client for Codex's native app-server protocol.

    Native app-server envelopes may omit jsonrpc. This is distinct from the
    MCP interface, which always validates JSON-RPC 2.0.
    """

    def __init__(self, config):
        self.config = config
        self.proc = None
        self.messages = queue.Queue(maxsize=128)
        self.failure = None
        self.sequence = 0

    def start(self):
        if self.proc:
            return
        # Do not inherit inference API keys, bearer tokens, proxy URLs or an
        # unrelated provider home. The native program still has OS-user rights.
        keep = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR",
                "SYSTEMROOT", "WINDIR")
        env = {key: os.environ[key] for key in keep if key in os.environ}
        env["CODEX_HOME"] = self.config["home"]
        try:
            self.proc = subprocess.Popen(
                [self.config["executable"], "app-server", "--stdio"],
                cwd=self.config["home"], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, bufsize=65536,
            )
        except OSError:
            raise SafeError("Native process could not start") from None
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            while True:
                line = self.proc.stdout.readline(MAX_BYTES + 1)
                if not line:
                    self.failure = "Native process disconnected"
                    return
                if len(line) > MAX_BYTES:
                    self.failure = "Native message exceeds size limit"
                    return
                message = parse_json(line)
                if not isinstance(message, dict):
                    self.failure = "Native message is not an object"
                    return
                try:
                    self.messages.put(message, timeout=0.1)
                except queue.Full:
                    self.failure = "Native message queue overflow"
                    return
        except (OSError, ValueError, SafeError):
            self.failure = "Invalid native message"

    def send(self, message):
        try:
            encoded = (json.dumps(message, allow_nan=False) + "\n").encode()
            if len(encoded) > MAX_BYTES:
                raise SafeError("Native request exceeds size limit")
            descriptor = self.proc.stdin.fileno()
            os.set_blocking(descriptor, False)
            deadline = time.monotonic() + self.config["timeout"]
            with selectors.DefaultSelector() as selector:
                selector.register(descriptor, selectors.EVENT_WRITE)
                while encoded:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise SafeError("Native write timed out; outcome may be unknown")
                    try:
                        written = os.write(descriptor, encoded[:4096])
                    except BlockingIOError:
                        continue
                    if written <= 0:
                        raise SafeError("Native write failed")
                    encoded = encoded[written:]
        except (OSError, ValueError):
            raise SafeError("Native write failed") from None

    def rpc(self, method, params):
        self.start()
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.config["timeout"]
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SafeError("Native request timed out; outcome may be unknown")
            try:
                message = self.messages.get(timeout=min(remaining, 0.1))
            except queue.Empty:
                if self.failure:
                    raise SafeError(self.failure)
                continue
            if "jsonrpc" in message and message["jsonrpc"] != "2.0":
                raise SafeError("Unsupported native protocol version")
            if "method" in message:
                if not isinstance(message["method"], str) or not isinstance(message.get("params", {}), dict):
                    raise SafeError("Malformed native request")
                if "id" in message:
                    if not (isinstance(message["id"], str) or type(message["id"]) is int):
                        raise SafeError("Malformed native request ID")
                    # Native approval/login requests cannot be completed by a
                    # headless adapter. Do not grant permission on the user's behalf.
                    self.send({"id": message["id"], "error": {
                        "code": -32000, "message": "Complete interactive work in the native client"}})
                continue
            if type(message.get("id")) is not int or message["id"] != request_id:
                continue
            if ("result" in message) == ("error" in message):
                raise SafeError("Malformed native response")
            if "error" in message:
                # Upstream errors may contain credentials or private payloads.
                raise SafeError("Native request rejected; inspect the native client privately")
            return message["result"]

    def close(self):
        if not self.proc:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
        for stream in (self.proc.stdin, self.proc.stdout):
            if stream:
                stream.close()


def home_lineage(path):
    """Existing ancestor identities mapped to portable relative path suffixes.

    Inodes detect real aliases; normalized casefold suffixes conservatively
    protect future homes on filesystems with different case/Unicode behavior.
    """
    identities = {}
    for ancestor in (path, *path.parents):
        try:
            info = ancestor.stat()
        except FileNotFoundError:
            continue
        except OSError:
            raise SafeError("Cannot inspect selected account-home ancestry") from None
        if not stat.S_ISDIR(info.st_mode):
            raise SafeError("Account-home paths must not cross files")
        suffix = tuple(unicodedata.normalize("NFC", part).casefold()
                       for part in path.relative_to(ancestor).parts)
        identities[(info.st_dev, info.st_ino)] = suffix
    return identities


def homes_overlap(left, right):
    for identity in set(left) & set(right):
        a, b = left[identity], right[identity]
        if a[:len(b)] == b or b[:len(a)] == a:
            return True
    return False


def alignment_candidate(settings, spec):
    fields(spec, ("version", "updates"))
    if type(spec["version"]) is not int or spec["version"] != 1:
        raise SafeError("Unsupported alignment version")
    updates = spec["updates"]
    if not isinstance(updates, list) or not updates or len(updates) > 100:
        raise SafeError("Configure one to 100 updates")
    if not isinstance(settings, dict) or not isinstance(settings.get("providerInstances"), dict):
        raise SafeError("Settings have no providerInstances object")
    candidate = parse_json(json.dumps(settings, allow_nan=False))
    instances = candidate["providerInstances"]
    seen = set()
    for update in updates:
        fields(update, ("id", "expectedDriver", "homePath"), ("displayName", "binaryPath"))
        instance_id = text(update["id"])
        if instance_id in seen:
            raise SafeError("Duplicate provider update")
        seen.add(instance_id)
        driver = update["expectedDriver"]
        if driver not in ("codex", "claudeAgent"):
            raise SafeError("Unsupported provider driver")
        current = instances.get(instance_id)
        if not isinstance(current, dict) or current.get("driver") != driver:
            raise SafeError("Existing provider and expected driver must match")
        config = current.get("config")
        if not isinstance(config, dict):
            raise SafeError("Existing provider configuration is not an object")
        home = absolute_path(update["homePath"])
        # No home creation, credential reads/copying or login occurs here.
        config["homePath"] = str(home)
        if "binaryPath" in update:
            config["binaryPath"] = str(absolute_path(update["binaryPath"]))
        if "displayName" in update:
            current["displayName"] = text(update["displayName"])
    # Account-home isolation is a path invariant, not a guess from labels.
    homes = {}
    for instance_id, instance in instances.items():
        if not isinstance(instance, dict) or instance.get("driver") not in ("codex", "claudeAgent"):
            continue
        config = instance.get("config")
        home = config.get("homePath") if isinstance(config, dict) else None
        if not home:
            raise SafeError("All native instances need explicit homes to verify isolation")
        try:
            path = absolute_path(home).resolve()
        except (OSError, RuntimeError):
            raise SafeError("Cannot resolve selected native home") from None
        lineage = home_lineage(path)
        for other_id, other_lineage in homes.items():
            if homes_overlap(lineage, other_lineage) and (instance_id in seen or other_id in seen):
                raise SafeError("Updated provider home overlaps another instance")
        homes[instance_id] = lineage
    return candidate


def write_candidate(candidate, output):
    path = absolute_path(str(output))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError:
        raise SafeError("Candidate path must be new and writable") from None
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(candidate, handle, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except (OSError, ValueError):
        raise SafeError("Candidate write failed; inspect the output privately") from None
