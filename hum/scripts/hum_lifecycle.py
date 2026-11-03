"""Small, fail-closed lease/state primitives shared by hum and its tests."""

from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import tempfile

KINDS = ("task", "preview", "persistent")
DEFAULT_TTL = 2 * 60 * 60
POLICY_OPTIONS = ("--lifetime", "--owner", "--purpose", "--ttl")


class PolicyError(ValueError):
    pass


def component(value):
    if (not isinstance(value, str) or not value or value in (".", "..")
            or any(c in value for c in ("/", "\\", "\0"))):
        raise PolicyError("project/server names must be single path components")
    return value


def state_path(base, label, name):
    base = Path(base).resolve()
    parent = base / component(label)
    path = parent / (component(name) + ".json")
    if parent.is_symlink() or path.is_symlink() or not parent.resolve().is_relative_to(base):
        raise PolicyError("refusing a state path outside the hum state directory")
    return path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def state_lock(base, label, name):
    path = state_path(base, label, name).with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def text(value, what):
    if (not isinstance(value, str) or not value.strip() or len(value) > 1000
            or any(ord(c) < 32 for c in value)):
        raise PolicyError(f"{what} must be nonempty text without control characters")
    return value


def duration(value):
    if not isinstance(value, str) or not value:
        raise PolicyError("--ttl needs a positive duration such as 30m or 2h")
    unit = value[-1]
    scale = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    digits = value[:-1] if unit in scale else value
    if not digits or not all("0" <= c <= "9" for c in digits):
        raise PolicyError("--ttl needs a positive integer duration such as 30m or 2h")
    seconds = int(digits) * scale.get(unit, 1)
    if not 0 < seconds <= 30 * 86400:
        raise PolicyError("--ttl must be greater than zero and at most 30d")
    return seconds


def validate_options(options):
    kind = options.get("--lifetime")
    if kind is not None and kind not in KINDS:
        raise PolicyError("--lifetime must be task, preview, or persistent")
    for key in ("--owner", "--purpose"):
        if key in options:
            text(options[key], key)
    if "--ttl" in options:
        duration(options["--ttl"])
        if kind == "persistent":
            raise PolicyError("persistent environments do not take --ttl")


def validate(policy):
    if not isinstance(policy, dict) or policy.get("version") != 1 or policy.get("kind") not in KINDS:
        raise PolicyError("unrecognized lifecycle policy")
    text(policy.get("purpose"), "purpose")
    ttl = policy.get("ttl")
    if not finite(ttl) or not 0 < ttl <= 30 * 86400:
        raise PolicyError("invalid lifecycle ttl")
    owners = policy.get("owners")
    if not isinstance(owners, dict) or not owners:
        raise PolicyError("missing lifecycle owners")
    for owner, claim in owners.items():
        text(owner, "owner")
        if not isinstance(claim, dict) or not isinstance(claim.get("released"), bool):
            raise PolicyError("invalid ownership claim")
        text(claim.get("purpose"), "owner purpose")
        if policy["kind"] == "persistent":
            if claim.get("expires_at") is not None:
                raise PolicyError("persistent claim has an expiry")
        elif not finite(claim.get("expires_at")) or claim["expires_at"] < 0:
            raise PolicyError("invalid owner expiry")
    return policy


def claim(previous, options, owner, now, *, new_run=False):
    """Claim an existing policy, or classify an explicitly adopted/new environment."""
    validate_options(options)
    text(owner, "owner")
    explicit = any(key in options for key in POLICY_OPTIONS)
    old = validate(previous) if previous is not None else None
    if old is None and not new_run and not explicit:
        return None
    kind = options.get("--lifetime", old["kind"] if old else "preview")
    if old and old["kind"] != kind:
        others = [key for key, value in old["owners"].items() if key != owner and not value["released"]]
        if old["kind"] == "persistent" or others:
            raise PolicyError("cannot change a persistent or another owner's lifetime; release/recreate it explicitly")
    if kind == "persistent" and "--ttl" in options:
        raise PolicyError("persistent environments do not take --ttl")
    policy = deepcopy(old) if old else {"version": 1, "owners": {}}
    policy.update(kind=kind, purpose=options.get("--purpose", policy.get("purpose", "Development environment")),
                  ttl=duration(options["--ttl"]) if "--ttl" in options else policy.get("ttl", DEFAULT_TTL))
    expires = None if kind == "persistent" else now + policy["ttl"]
    prior = policy["owners"].get(owner)
    if prior and prior.get("expires_at") is not None and expires is not None and not prior["released"]:
        expires = max(expires, prior["expires_at"])
    policy["owners"][owner] = {"expires_at": expires, "released": False,
                                "purpose": options.get("--purpose", policy["purpose"])}
    return validate(policy)


def release(policy, owner):
    result = deepcopy(validate(policy))
    if owner not in result["owners"]:
        raise PolicyError("this owner has no claim; refusing to release another owner's environment")
    result["owners"][owner]["released"] = True
    return result


def due(policy, now, owner_status):
    """A lease grants bounded use; unresolved exact T3 ownership fails closed."""
    policy = validate(policy)
    if policy["kind"] == "persistent":
        return False, "persistent"
    owners = [(owner, item) for owner, item in policy["owners"].items() if not item["released"]]
    if any(item["expires_at"] > now for _, item in owners):
        return False, "leased"
    for owner, _ in owners:
        if owner.startswith("t3:"):
            status = owner_status(owner[3:])
            if status == "active":
                return False, "active-owner"
            if status != "inactive":
                return False, "unknown-owner"
    return True, "released" if not owners else "expired"


def process_record(pid):
    """Read birth and parent together, never pairing a stale PPID with a new PID."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    try:
        if Path("/proc").is_dir():
            stat = Path(f"/proc/{pid}/stat").read_text()
            rest = stat[stat.rindex(")") + 2:].split()
            if rest[0] == "Z":
                return None
            boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            return {"pid": pid, "ppid": int(rest[1]), "pgid": int(rest[2]),
                    "birth": f"linux:{boot}:{rest[19]}"}
        # macOS provides a stable process birth timestamp, independent of elapsed CPU.
        import subprocess
        result = subprocess.run(["ps", "-p", str(pid), "-o", "pid=,ppid=,pgid=,lstart="],
                                capture_output=True, text=True, timeout=3)
        fields = result.stdout.strip().split(None, 3)
        if result.returncode == 0 and len(fields) == 4 and int(fields[0]) == pid:
            return {"pid": pid, "ppid": int(fields[1]), "pgid": int(fields[2]), "birth": "ps:" + fields[3]}
        return None
    except (OSError, ValueError, IndexError):
        return None


def process_birth(pid):
    record = process_record(pid)
    return record["birth"] if record else None


def capture_tree(root_pid, candidate_pids=None):
    """Accept a descendant only while its captured parent and child still match.

    A PID list is only a candidate search. Every accepted edge is proved using
    birth and actual PPID from the same process record; a recycled candidate
    belonging to another parent is not part of this environment.
    """
    root = process_record(root_pid)
    if root is None:
        return []
    if candidate_pids is None:
        if Path("/proc").is_dir():
            candidate_pids = [int(path.name) for path in Path("/proc").iterdir() if path.name.isdigit()]
        else:
            import subprocess
            output = subprocess.run(["ps", "-A", "-o", "pid="], capture_output=True, text=True).stdout
            candidate_pids = [int(value) for value in output.split() if value.isascii() and value.isdigit()]
    children = {}
    for pid in candidate_pids:
        child = process_record(pid)
        if child and child["pid"] != root_pid:
            children.setdefault(child["ppid"], []).append(child)
    result, stack, seen = [root], [root], {root_pid}
    while stack:
        parent = stack.pop()
        for child in children.get(parent["pid"], []):
            current_parent = process_record(parent["pid"])
            current_child = process_record(child["pid"])
            if (child["pid"] not in seen and current_parent and current_child
                    and current_parent["birth"] == parent["birth"]
                    and current_child["birth"] == child["birth"]
                    and current_child["ppid"] == parent["pid"]):
                seen.add(child["pid"])
                result.append(child)
                stack.append(child)
    return result


def identity(pid):
    birth = process_birth(pid)
    return {"pid": pid, "birth": birth} if birth else None


def same_process(record):
    return (isinstance(record, dict) and isinstance(record.get("birth"), str)
            and process_birth(record.get("pid")) == record["birth"])


def signal_process(record, sig):
    if not same_process(record):
        return False
    fd = None
    try:
        if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
            fd = os.pidfd_open(record["pid"])
            if not same_process(record):
                return False
            signal.pidfd_send_signal(fd, sig)
        else:
            # macOS has no pidfd API; recheck its birth timestamp immediately.
            if not same_process(record):
                return False
            os.kill(record["pid"], sig)
        return True
    except (OSError, ProcessLookupError):
        return False
    finally:
        if fd is not None:
            os.close(fd)
