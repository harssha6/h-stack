#!/usr/bin/env python3
"""Create or find a website in Umami, print its tracking tag, and read its stats.

    umami-site.py add <name> <domain>      idempotent: reuses a website with the same domain
    umami-site.py list                     every website the account (or team) can see
    umami-site.py stats <domain> [days]    pageviews, visitors and top pages for the last N days (default 7)

Configuration comes from environment variables (load them from your secret manager,
for example `infisical run -- python3 umami-site.py list`):

    UMAMI_API_URL      API base. Self-hosted: https://<your-umami>/api. Umami Cloud: https://api.umami.is/v1
    UMAMI_SCRIPT_URL   tracker URL for the tag (default: UMAMI_API_URL without /api, plus /script.js)
    UMAMI_API_KEY      Umami Cloud API key (sent as x-umami-api-key), or
    UMAMI_USERNAME + UMAMI_PASSWORD   self-hosted login
    UMAMI_TEAM         optional team name; websites are listed and created in that team

Standard library only. Never prints the password, API key or session token.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request


def need(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"missing environment variable {name} (see the docstring: umami-site.py --help)")
    return value


BASE = None
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read() or b"null")


def rows(payload):
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def connect():
    global BASE
    BASE = need("UMAMI_API_URL").rstrip("/")
    key = os.environ.get("UMAMI_API_KEY", "").strip()
    if key:
        HEADERS["x-umami-api-key"] = key
    else:
        token = call("POST", "/auth/login", {"username": need("UMAMI_USERNAME"), "password": need("UMAMI_PASSWORD")})["token"]
        HEADERS["Authorization"] = "Bearer " + token
    team_name = os.environ.get("UMAMI_TEAM", "").strip()
    if not team_name:
        return None
    teams = [t for t in rows(call("GET", "/teams")) if t.get("name") == team_name]
    if not teams:
        sys.exit(f"team not found: {team_name}")
    return teams[0]


def websites(team):
    path = f"/teams/{team['id']}/websites?pageSize=200" if team else "/websites?pageSize=200"
    return rows(call("GET", path))


def by_domain(team, domain):
    hits = [s for s in websites(team) if s.get("domain") == domain]
    if not hits:
        sys.exit(f"no website with domain {domain}; run: umami-site.py add <name> {domain}")
    return hits[0]


def script_url():
    explicit = os.environ.get("UMAMI_SCRIPT_URL", "").strip()
    if explicit:
        return explicit
    base = BASE[: -len("/api")] if BASE.endswith("/api") else BASE
    return base + "/script.js"


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd not in ("list", "add", "stats"):
        sys.exit(__doc__)
    team = connect()
    if cmd == "list":
        for site in websites(team):
            print(f"{site['id']}  {site.get('name', ''):<28} {site.get('domain', '')}")
    elif cmd == "add":
        if len(argv) < 4:
            sys.exit("usage: umami-site.py add <name> <domain>")
        name, domain = argv[2], argv[3]
        hits = [s for s in websites(team) if s.get("domain") == domain]
        body = {"name": name, "domain": domain}
        if team:
            body["teamId"] = team["id"]
        site = hits[0] if hits else call("POST", "/websites", body)
        print(("existing " if hits else "created ") + site["id"])
        print(f'<script defer src="{script_url()}" data-website-id="{site["id"]}" data-domains="{domain}"></script>')
    else:
        if len(argv) < 3:
            sys.exit("usage: umami-site.py stats <domain> [days]")
        domain = argv[2]
        days = int(argv[3]) if len(argv) > 3 else 7
        site = by_domain(team, domain)
        end = int(time.time() * 1000)
        query = urllib.parse.urlencode({"startAt": end - days * 86_400_000, "endAt": end})
        stats = call("GET", f"/websites/{site['id']}/stats?{query}")
        top = call("GET", f"/websites/{site['id']}/metrics?{query}&type=path&limit=5")
        print(json.dumps({"site": site.get("name"), "days": days, "stats": stats, "top_pages": top}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
