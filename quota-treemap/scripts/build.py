#!/usr/bin/env python3
"""Group collected sessions by project and write a treemap of where subscription quota goes.

    build.py --data ~/sub-usage --rules ~/sub-usage/rules.json [--accounts personal] [--windows 30,90] [--tz Europe/Berlin]

Reads every DATA/sessions-*.tsv written by collect.py. Writes DATA/projects.txt, DATA/treemap.html
and a dated snapshot DATA/history/<YYYY-MM-DD>.json so later runs can say what moved.

rules.json (see rules.example.json):
    {"groups": {"work": "#3987e5", "personal": "#199e70", "setup": "#d95926"},
     "fallback": "personal",
     "projects": [{"name": "Docs site", "group": "personal", "match": ["docs-site"]}, ...]}

A session belongs to the first project whose `match` substring appears in its Git remote or working
directory, then (second pass) in its first prompt. Unmatched sessions go to "Other <fallback>".
"""
import argparse
import collections
import csv
import datetime
import glob
import html
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "treemap_template.html")
MIXED = "#5f5e59"


REQUIRED = ("machine", "account", "kind", "ts", "cwd", "remote", "weight", "first")


def load_sessions(data, accounts):
    rows = []
    for path in sorted(glob.glob(os.path.join(data, "sessions-*.tsv"))):
        with open(path, newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                sys.exit(f"{path}: missing columns {', '.join(missing)} (re-run collect.py)")
            for line, r in enumerate(reader, start=2):
                if accounts and r["account"] not in accounts:
                    continue
                try:
                    r["weight"] = float(r["weight"] or 0)
                except ValueError:
                    sys.exit(f"{path}:{line}: weight is not a number: {r['weight']!r}")
                rows.append(r)
    return rows


def load_rules(path):
    with open(path) as handle:
        rules = json.load(handle)
    if not isinstance(rules, dict) or not isinstance(rules.get("projects"), list):
        sys.exit(f"{path}: needs an object with a \"projects\" list (see rules.example.json)")
    for i, p in enumerate(rules["projects"]):
        where = f"{path}: projects[{i}]"
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not isinstance(p.get("group"), str):
            sys.exit(f"{where}: needs string \"name\" and \"group\"")
        match = p.get("match")
        if not isinstance(match, list) or not match or not all(isinstance(m, str) and m.strip() for m in match):
            sys.exit(f"{where}: \"match\" must be a non-empty list of non-empty strings")
    if not isinstance(rules.get("groups", {}), dict):
        sys.exit(f"{path}: \"groups\" must map group names to colors")
    return rules


def classify(row, rules):
    hay = (row.get("remote", "") + " " + row.get("cwd", "")).lower()
    first = row.get("first", "").lower()
    for field in (hay, first):
        for p in rules["projects"]:
            if any(m.lower() in field for m in p["match"]):
                return p["name"], p["group"]
    fallback = rules.get("fallback", "personal")
    return f"Other {fallback}", fallback


def age_days(ts, now):
    """Days since a session start. Timestamps without an offset are read as UTC; unreadable ones are skipped."""
    try:
        start = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return 10**6
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    return (now - start).days


def summarize(rows, rules, window, now):
    share, by_kind, group = collections.Counter(), collections.defaultdict(collections.Counter), {}
    for r in rows:
        if age_days(r["ts"], now) > window:
            continue
        name, g = classify(r, rules)
        share[name] += r["weight"]
        by_kind[name][r["kind"]] += r["weight"]
        group[name] = g
    total = sum(share.values())
    tiles, small = [], 0.0
    for name, value in share.most_common():
        pct = value / total * 100 if total else 0
        if pct < 0.5:
            small += pct
            continue
        tiles.append({"name": name, "pct": pct, "g": group[name],
                      "claude": round(by_kind[name]["claude"] / 1e6), "codex": round(by_kind[name]["codex"] / 1e6)})
    if small >= 0.05:
        tiles.append({"name": "Smaller projects", "pct": small, "g": "mixed", "claude": 0, "codex": 0})
    return tiles, total


def script_json(value):
    """JSON that is safe inside an inline <script>: no tag, comment or line-separator breakouts."""
    text = json.dumps(value)
    for raw, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        text = text.replace(raw, escaped)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--accounts", default="", help="comma-separated account labels to include (default: all)")
    ap.add_argument("--windows", default="30,90")
    ap.add_argument("--tz", default="UTC", help="time zone for the date stamp, an IANA zone such as Europe/Berlin")
    ap.add_argument("--title", default="Where my subscription quota goes")
    args = ap.parse_args(argv)

    data = os.path.expanduser(args.data)
    rules = load_rules(os.path.expanduser(args.rules))
    accounts = {a for a in args.accounts.split(",") if a}
    rows = load_sessions(data, accounts)
    if not rows:
        sys.exit(f"no sessions found in {data}/sessions-*.tsv (run collect.py first)")
    machines = sorted({r["machine"] for r in rows})
    windows = [int(w) for w in args.windows.split(",") if w]
    now = datetime.datetime.now(datetime.timezone.utc)
    local = now.astimezone(ZoneInfo(args.tz))

    out, totals, text = {}, {}, []
    for w in windows:
        tiles, total = summarize(rows, rules, w, now)
        out[str(w)], totals[str(w)] = tiles, round(total / 1e6)
        text.append(f"== last {w} d, total {total / 1e6:.0f}M units")
        text += [f"{t['pct']:5.1f}%  {t['g']:9} {t['name']}" for t in tiles]

    with open(os.path.join(data, "projects.txt"), "w") as handle:
        handle.write("\n".join(text) + "\n")
    os.makedirs(os.path.join(data, "history"), exist_ok=True)
    with open(os.path.join(data, "history", local.strftime("%Y-%m-%d") + ".json"), "w") as handle:
        json.dump({"at": local.isoformat(), "machines": machines, "totals": totals, "data": out}, handle)

    groups = dict(rules.get("groups", {}))
    groups.setdefault("mixed", MIXED)
    with open(TEMPLATE) as handle:
        page = handle.read()
    values = {
        "DATA": script_json(out),
        "TOTALS": script_json(totals),
        "GROUPS": script_json(groups),
        "TITLE": html.escape(args.title),
        "DATE": html.escape(f"{local.strftime('%d %b %Y, %H:%M')} {args.tz} · machines: {', '.join(machines)}"),
    }
    # One pass over the template's own markers, so inserted values are never rescanned.
    page = re.sub(r"__(DATA|TOTALS|GROUPS|TITLE|DATE)__", lambda m: values[m.group(1)], page)
    with open(os.path.join(data, "treemap.html"), "w") as handle:
        handle.write(page)
    print("\n".join(text))
    print(f"wrote {os.path.join(data, 'treemap.html')} and history/{local.strftime('%Y-%m-%d')}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
