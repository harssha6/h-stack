#!/usr/bin/env python3
"""Collect per-session token usage from local Claude Code and Codex logs.

    collect.py --machine laptop --source personal=claude:~/.claude --source personal=codex:~/.codex \
               --source work=claude:~/.claude-work --out ~/sub-usage

Each --source is ACCOUNT=KIND:HOME, where KIND is `claude` (reads HOME/projects/**/*.jsonl) or
`codex` (reads HOME/sessions/**/*.jsonl), and ACCOUNT is your own label for the subscription
behind that home. Writes OUT/sessions-<machine>.tsv. Run it on every machine, point --out at a
folder the machines share (or copy the files), then run build.py.

Read-only over the logs. The TSV holds the first 400 characters of each session's first prompt
(used for project rules), so keep OUT private. No tokens, auth files or account ids are read.
"""
import argparse
import csv
import glob
import json
import os
import subprocess
import sys

FIELDS = ["machine", "account", "kind", "ts", "cwd", "remote", "weight", "output", "first"]


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") in ("text", "input_text"))
    return ""


_remotes = {}


def remote_of(cwd):
    if not cwd or not os.path.isdir(cwd):
        return ""
    if cwd not in _remotes:
        try:
            out = subprocess.run(["git", "-C", cwd, "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5)
            _remotes[cwd] = out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            _remotes[cwd] = ""
    return _remotes[cwd]


def clean(text):
    return " ".join(text.split())[:400]


def lines(path):
    with open(path, errors="ignore") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def claude_sessions(home):
    """Weight = input + 1.25 cache write + 0.1 cache read + 5 output. Deduped by message id + request id."""
    for path in glob.glob(os.path.join(home, "projects", "**", "*.jsonl"), recursive=True):
        seen, cwd, first, ts = set(), "", "", None
        tin = cw = cr = out = 0
        for d in lines(path):
            cwd = cwd or d.get("cwd", "")
            ts = ts or d.get("timestamp")
            if d.get("type") == "user" and not first and not d.get("isSidechain"):
                t = text_of((d.get("message") or {}).get("content"))
                if t and not t.startswith("<"):
                    first = t
            if d.get("type") == "assistant":
                msg = d.get("message") or {}
                usage = msg.get("usage")
                key = (msg.get("id"), d.get("requestId"))
                if not usage or key in seen:
                    continue
                seen.add(key)
                tin += usage.get("input_tokens") or 0
                cw += usage.get("cache_creation_input_tokens") or 0
                cr += usage.get("cache_read_input_tokens") or 0
                out += usage.get("output_tokens") or 0
        weight = tin + 1.25 * cw + 0.1 * cr + 5 * out
        if weight:
            yield ts or "", cwd, round(weight), out, first


def codex_sessions(home):
    """Weight = uncached input + 0.1 cached input + 5 output, from the last token_count event."""
    for path in glob.glob(os.path.join(home, "sessions", "**", "*.jsonl"), recursive=True):
        cwd, first, ts, last = "", "", None, None
        for d in lines(path):
            p = d.get("payload") or {}
            if d.get("type") == "session_meta":
                cwd, ts = p.get("cwd", ""), p.get("timestamp")
            if d.get("type") == "response_item" and p.get("role") == "user" and not first:
                t = text_of(p.get("content"))
                if t and not t.lstrip().startswith("<") and "AGENTS.md instructions" not in t[:80]:
                    first = t
            if p.get("type") == "token_count" and p.get("info"):
                last = p["info"].get("total_token_usage")
        if not last:
            continue
        cached = last.get("cached_input_tokens", 0)
        weight = (last.get("input_tokens", 0) - cached) + 0.1 * cached + 5 * last.get("output_tokens", 0)
        if weight:
            yield ts or "", cwd, round(weight), last.get("output_tokens", 0), first


def parse_source(spec):
    try:
        account, rest = spec.split("=", 1)
        kind, home = rest.split(":", 1)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected ACCOUNT=KIND:HOME, got {spec!r}")
    if kind not in ("claude", "codex"):
        raise argparse.ArgumentTypeError(f"KIND must be claude or codex, got {kind!r}")
    return account, kind, os.path.expanduser(home)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", required=True, help="label for this machine, for example laptop or server")
    ap.add_argument("--source", action="append", type=parse_source, required=True, help="ACCOUNT=KIND:HOME, repeatable")
    ap.add_argument("--out", required=True, help="output folder (keep it private)")
    args = ap.parse_args(argv)
    os.makedirs(os.path.expanduser(args.out), exist_ok=True)
    target = os.path.join(os.path.expanduser(args.out), f"sessions-{args.machine}.tsv")
    count = 0
    with open(target, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(FIELDS)
        for account, kind, home in args.source:
            if not os.path.isdir(home):
                print(f"skip {account}={kind}: {home} not found", file=sys.stderr)
                continue
            reader = claude_sessions if kind == "claude" else codex_sessions
            for ts, cwd, weight, out, first in reader(home):
                writer.writerow([args.machine, account, kind, ts, cwd, remote_of(cwd), weight, out, clean(first)])
                count += 1
    print(f"{count} sessions -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
