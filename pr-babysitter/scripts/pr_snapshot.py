#!/usr/bin/env python3
"""Read-only GitHub PR evidence collector. Requires Python 3.10+ and gh."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote, unquote, urlparse

# Optional: set PR_SNAPSHOT_EXPECTED_ACCOUNT to the GitHub login that must be active.
# When unset, the collector uses whichever gh account is active and records it.
EXPECTED_ACCOUNT_ENV = "PR_SNAPSHOT_EXPECTED_ACCOUNT"
FIELDS = ("number,url,title,state,isDraft,headRefName,headRefOid,baseRefName,"
          "baseRefOid,mergeable,mergeStateStatus,reviewDecision,reviewRequests,"
          "statusCheckRollup,isCrossRepository,headRepositoryOwner")
THREAD_QUERY = """query($owner:String!,$repo:String!,$number:Int!,$cursor:String){
 repository(owner:$owner,name:$repo){pullRequest(number:$number){
 reviewThreads(first:100,after:$cursor){pageInfo{hasNextPage endCursor}nodes{
 id isResolved isOutdated path line comments(first:100){
 pageInfo{hasNextPage endCursor}nodes{
 id databaseId author{login} body url createdAt updatedAt
 pullRequestReview{state commit{oid}}}}}}}}}"""
COMMENT_QUERY = """query($id:ID!,$cursor:String!){node(id:$id){
 ... on PullRequestReviewThread{comments(first:100,after:$cursor){
 pageInfo{hasNextPage endCursor}nodes{
 id databaseId author{login} body url createdAt updatedAt
 pullRequestReview{state commit{oid}}}}}}}"""


class EvidenceError(RuntimeError):
    def __init__(self, message, payload=None):
        super().__init__(message)
        self.payload = payload


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=90)
    if p.returncode:
        # gh errors identify the failing endpoint without exposing command payloads.
        raise EvidenceError(p.stderr.strip() or "Command failed")
    return p.stdout


class GitHub:
    def json(self, args):
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=90)
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError as exc:
            raise EvidenceError(p.stderr.strip() or "GitHub returned non-JSON evidence") from exc
        if p.returncode:
            raise EvidenceError(p.stderr.strip() or "GitHub request failed", payload=data)
        if isinstance(data, dict) and data.get("errors"):
            raise EvidenceError(json.dumps(data["errors"]))
        return data

    def api(self, path):
        return self.json(["api", path])

    def pages(self, path, field=None):
        pages = self.json(["api", path, "--paginate", "--slurp"])
        return [item for page in pages for item in (page[field] if field else page)]

    def graphql(self, query, **variables):
        args = ["api", "graphql", "-f", "query=" + query]
        for key, value in variables.items():
            if value is not None:
                args += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
        return self.json(args)["data"]

    def pr(self, repo, target):
        args = ["pr", "view"]
        if target != "auto":
            args.append(str(target))
        return self.json([*args, "--repo", repo, "--json", FIELDS])


def repository_from_remote(remote):
    if remote.startswith("git@github.com:"):
        path = remote.split(":", 1)[1]
    else:
        parsed = urlparse(remote)
        if parsed.hostname != "github.com":
            raise EvidenceError("Expected a verified github.com remote")
        path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return validate_repository(path)


def validate_repository(repo):
    parts = repo.split("/")
    if len(parts) != 2 or not all(parts):
        raise EvidenceError("Repository must be OWNER/REPO")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    if any(any(char not in allowed for char in part) for part in parts):
        raise EvidenceError("Invalid GitHub repository identifier")
    if any(part in {".", ".."} for part in parts):
        raise EvidenceError("Invalid GitHub repository identifier")
    return repo


def resolve_target(repo, target):
    if "://" in target:
        parsed = urlparse(target)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/")]
        if (parsed.scheme != "https" or parsed.netloc != "github.com"
                or len(parts) != 4 or parts[2] != "pull" or not parts[3].isdigit()):
            raise EvidenceError("Expected https://github.com/OWNER/REPO/pull/NUMBER")
        url_repo = validate_repository("/".join(parts[:2]))
        if repo and repo.lower() != url_repo.lower():
            raise EvidenceError("PR URL and repository disagree")
        repo, target = url_repo, parts[3]
    if not repo:
        try:
            remote = command(["git", "remote", "get-url", "origin"]).strip()
        except EvidenceError as exc:
            raise EvidenceError("No origin; inspect remotes and supply --repo or a PR URL") from exc
        repo = repository_from_remote(remote)
    validate_repository(repo)
    if target != "auto" and (not target.isdigit() or int(target) < 1):
        raise EvidenceError("PR must be auto, a positive number or a full URL")
    return repo, target


def verify_account(api, repo):
    expected = os.environ.get(EXPECTED_ACCOUNT_ENV, "").strip()
    actual = api.api("user")["login"]
    if expected and actual.lower() != expected.lower():
        raise EvidenceError(f"Active account {actual}; expected {expected}. Route explicitly; collector does not switch.")
    return actual


def review_threads(api, repo, number):
    owner, name = repo.split("/")
    cursor = None
    threads = []
    seen = set()
    while True:
        data = api.graphql(THREAD_QUERY, owner=owner, repo=name, number=number, cursor=cursor)
        connection = data["repository"]["pullRequest"]["reviewThreads"]
        for thread in connection["nodes"]:
            comments = thread.pop("comments")
            comment_nodes = list(comments["nodes"])
            comment_seen = set()
            while comments["pageInfo"]["hasNextPage"]:
                next_cursor = comments["pageInfo"]["endCursor"]
                if not next_cursor or next_cursor in comment_seen:
                    raise EvidenceError("Thread-comment pagination did not advance")
                comment_seen.add(next_cursor)
                comments = api.graphql(COMMENT_QUERY, id=thread["id"], cursor=next_cursor)["node"]["comments"]
                comment_nodes.extend(comments["nodes"])
            thread["comments"] = [c for c in comment_nodes
                                  if (c.get("pullRequestReview") or {}).get("state") != "PENDING"]
            # Retain only published threads; unresolved counts must not expose drafts.
            if thread["comments"]:
                threads.append(thread)
        if not connection["pageInfo"]["hasNextPage"]:
            return threads
        cursor = connection["pageInfo"]["endCursor"]
        if not cursor or cursor in seen:
            raise EvidenceError("Thread pagination did not advance")
        seen.add(cursor)


def observations(pr, checks, statuses, threads, rules, protection):
    acceptable = {"success", "neutral", "skipped"}
    pending = [c["name"] for c in checks if c["status"] != "completed"]
    unsuccessful = [c["name"] for c in checks
                    if c["status"] == "completed" and c.get("conclusion") not in acceptable]
    pending += [s["context"] for s in statuses if s["state"] == "pending"]
    unsuccessful += [s["context"] for s in statuses if s["state"] not in {"success", "pending"}]
    required = []
    for rule in rules or []:
        if rule["type"] == "required_status_checks":
            required.extend(rule.get("parameters", {}).get("required_status_checks", []))
    classic = (protection or {}).get("required_status_checks") or {}
    required.extend(classic.get("checks") or [{"context": c} for c in classic.get("contexts", [])])
    # The rollup may evaluate the test-merge commit. Presence is not success or app proof.
    observed = {c["name"] for c in checks} | {s["context"] for s in statuses}
    observed |= {c.get("name", c.get("context")) for c in pr.get("statusCheckRollup") or []}
    return {"pending_checks": pending, "unsuccessful_checks": unsuccessful,
            "neutral_or_skipped": [c["name"] for c in checks if c.get("conclusion") in {"neutral", "skipped"}],
            "required_contexts": required,
            "missing_required_contexts": [r["context"] for r in required if r["context"] not in observed],
            "unresolved_thread_ids": [t["id"] for t in threads if not t["isResolved"]],
            "readiness": "requires_agent_triage"}


def collect(api, repo, target):
    login = verify_account(api, repo)
    pr = api.pr(repo, target)
    number, head, base = pr["number"], pr["headRefOid"], pr["baseRefName"]
    root = f"repos/{repo}"
    errors, limitations = [], []

    def gather(label, function, default=None, optional=False):
        try:
            return function()
        except (EvidenceError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
            (limitations if optional else errors).append({"surface": label, "error": str(exc)})
            return default

    checks = gather("head_check_runs", lambda: api.pages(
        f"{root}/commits/{head}/check-runs?per_page=100&filter=latest", "check_runs"), [])
    # Combined status includes only the latest status per context.
    statuses = gather("head_statuses", lambda: api.pages(
        f"{root}/commits/{head}/status?per_page=100", "statuses"), [])
    reviews = gather("reviews", lambda: api.pages(f"{root}/pulls/{number}/reviews?per_page=100"), [])
    published_ids = {r["id"] for r in reviews if r["state"] != "PENDING"}
    reviews = [r for r in reviews if r["state"] != "PENDING"]
    comments = gather("issue_comments", lambda: api.pages(f"{root}/issues/{number}/comments?per_page=100"), [])
    inline = gather("inline_comments", lambda: api.pages(f"{root}/pulls/{number}/comments?per_page=100"), [])
    inline = [c for c in inline if c.get("pull_request_review_id") in published_ids]
    threads = gather("review_threads", lambda: review_threads(api, repo, number), [])
    encoded_base = quote(base, safe="")
    rules = gather("effective_rules", lambda: api.pages(f"{root}/rules/branches/{encoded_base}?per_page=100"))
    def classic_protection():
        try:
            return api.api(f"{root}/branches/{encoded_base}/protection")
        except EvidenceError as exc:
            # Structured GitHub response confirms classic absence; generic 404 cannot.
            if isinstance(exc.payload, dict) and exc.payload.get("message") == "Branch not protected":
                return {"absence_confirmed": True, "source": "GitHub protection API"}
            raise

    protection = gather("classic_protection", classic_protection, optional=True)
    final = gather("final_pr_state", lambda: api.pr(repo, str(number)))
    gather("final_account", lambda: verify_account(api, repo))
    stable = final is not None and all(pr.get(key) == final.get(key) for key in
        ("headRefOid", "baseRefOid", "baseRefName", "state"))
    if not stable:
        errors.append({"surface": "snapshot_consistency", "error": "PR head/base/state changed or final reread failed; collect again"})
    # Keep provider IDs/annotations while dropping large API boilerplate.
    selected_checks = [{k: c.get(k) for k in ("id", "name", "head_sha", "status", "conclusion",
        "started_at", "completed_at", "details_url", "app", "output", "check_suite")} for c in checks]
    return {"collected_at": datetime.now(timezone.utc).isoformat(), "repository": repo,
            "account": login, "complete": not errors and not limitations, "stable": stable,
            "errors": errors, "limitations": limitations, "pr": pr, "final_pr": final,
            "head_check_runs": selected_checks, "head_statuses": statuses,
            "reviews": reviews, "issue_comments": comments, "inline_comments": inline,
            "review_threads": threads, "effective_rules": rules, "classic_protection": protection,
            "observations": observations(pr, checks, statuses, threads, rules, protection)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Verified OWNER/REPO (required when origin is absent)")
    parser.add_argument("--pr", default="auto", help="auto, positive number, or github.com PR URL")
    args = parser.parse_args()
    try:
        repo, target = resolve_target(args.repo, args.pr)
        result = collect(GitHub(), repo, target)
    except (EvidenceError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"complete": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    sys.exit(main())
