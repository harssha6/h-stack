"""Offline behavior tests. Run: python3 -m unittest discover -s scripts -v"""
import copy
import os
import unittest
from unittest.mock import patch

import pr_snapshot as s


def comment(login="cursor", state="COMMENTED"):
    return {"author": {"login": login}, "body": "finding",
            "pullRequestReview": {"state": state, "commit": {"oid": "h"}}}


def connection(nodes, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor}}


def thread(identifier, comments, cursor=None):
    return {"id": identifier, "isResolved": False, "isOutdated": True,
            "path": "file.py", "line": 1, "comments": connection(comments, cursor)}


class FakeGitHub:
    def __init__(self):
        self.pr_data = {"number": 1, "headRefOid": "h", "baseRefName": "release/v1",
                        "baseRefOid": "b", "state": "OPEN", "statusCheckRollup": []}
        self.final = copy.deepcopy(self.pr_data)
        self.pr_calls = 0
        self.data = {"user": {"login": "octocat"},
                     "repos/acme/repo/branches/release%2Fv1/protection": {}}
        self.page_data = {
            "repos/acme/repo/commits/h/check-runs?per_page=100&filter=latest": [],
            "repos/acme/repo/commits/h/status?per_page=100": [],
            "repos/acme/repo/pulls/1/reviews?per_page=100": [],
            "repos/acme/repo/issues/1/comments?per_page=100": [],
            "repos/acme/repo/pulls/1/comments?per_page=100": [],
            "repos/acme/repo/rules/branches/release%2Fv1?per_page=100": [],
        }
        self.gql = []

    def api(self, path):
        value = self.data[path]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def pages(self, path, field=None):
        value = self.page_data[path]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def pr(self, repo, target):
        self.pr_calls += 1
        return copy.deepcopy(self.pr_data if self.pr_calls == 1 else self.final)

    def graphql(self, query, **variables):
        if self.gql:
            expected, response = self.gql.pop(0)
            if variables != expected:
                raise AssertionError((variables, expected))
            return copy.deepcopy(response)
        return {"repository": {"pullRequest": {"reviewThreads": connection([])}}}


class SnapshotTests(unittest.TestCase):
    def test_url_repo_conflict_rejected(self):
        with self.assertRaises(s.EvidenceError):
            s.resolve_target("acme/a", "https://github.com/acme/b/pull/2")

    def test_url_host_and_number_validated(self):
        for target in ["https://github.com.evil.test/acme/a/pull/2",
                       "https://github.com/acme/a/pull/0", "-2"]:
            with self.subTest(target=target), self.assertRaises(s.EvidenceError):
                s.resolve_target("acme/a", target)
        self.assertEqual(s.resolve_target(None, "https://github.com/acme/a/pull/2"), ("acme/a", "2"))

    def test_remote_protocols(self):
        for remote in ["git@github.com:acme/a.git", "https://github.com/acme/a.git",
                       "ssh://git@github.com/acme/a.git"]:
            self.assertEqual(s.repository_from_remote(remote), "acme/a")

    def test_account_mismatch_fails_before_pr_read(self):
        api = FakeGitHub()
        api.data["user"] = {"login": "hubot"}
        with patch.dict(os.environ, {s.EXPECTED_ACCOUNT_ENV: "octocat"}):
            with self.assertRaises(s.EvidenceError):
                s.collect(api, "acme/repo", "1")
        self.assertEqual(api.pr_calls, 0)

    def test_any_active_account_is_accepted_when_none_expected(self):
        api = FakeGitHub()
        api.data["user"] = {"login": "hubot"}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(s.EXPECTED_ACCOUNT_ENV, None)
            result = s.collect(api, "acme/repo", "1")
        self.assertEqual(result["account"], "hubot")

    def test_api_pagination_flattens_all_pages(self):
        with patch.object(s.GitHub, "json", return_value=[{"check_runs": [1]}, {"check_runs": [2]}]):
            self.assertEqual(s.GitHub().pages("path", "check_runs"), [1, 2])

    def test_thread_and_comment_pagination_and_pending_filter(self):
        api = FakeGitHub()
        t1 = thread("T1", [comment(), comment("operator", "PENDING")], "C2")
        api.gql = [
            ({"owner": "acme", "repo": "repo", "number": 1, "cursor": None},
             {"repository": {"pullRequest": {"reviewThreads": connection([t1], "T2")}}}),
            ({"id": "T1", "cursor": "C2"}, {"node": {"comments": connection([comment("human")])}}),
            ({"owner": "acme", "repo": "repo", "number": 1, "cursor": "T2"},
             {"repository": {"pullRequest": {"reviewThreads": connection([thread("T2", [comment("copilot-pull-request-reviewer")])])}}}),
        ]
        result = s.review_threads(api, "acme/repo", 1)
        self.assertEqual([t["id"] for t in result], ["T1", "T2"])
        self.assertEqual([c["author"]["login"] for c in result[0]["comments"]], ["cursor", "human"])
        self.assertTrue(result[0]["isOutdated"])

    def test_pending_only_thread_omitted(self):
        api = FakeGitHub()
        api.gql = [({"owner": "acme", "repo": "repo", "number": 1, "cursor": None},
                    {"repository": {"pullRequest": {"reviewThreads": connection([thread("T", [comment(state="PENDING")])])}}})]
        self.assertEqual(s.review_threads(api, "acme/repo", 1), [])

    def test_stale_head_or_base_or_terminal_change_incomplete(self):
        for key, value in [("headRefOid", "new"), ("baseRefOid", "new"), ("state", "MERGED")]:
            api = FakeGitHub()
            api.final[key] = value
            result = s.collect(api, "acme/repo", "1")
            self.assertFalse(result["stable"])
            self.assertFalse(result["complete"])

    def test_inaccessible_review_surface_not_clean(self):
        api = FakeGitHub()
        api.page_data["repos/acme/repo/pulls/1/reviews?per_page=100"] = s.EvidenceError("HTTP 403")
        result = s.collect(api, "acme/repo", "1")
        self.assertFalse(result["complete"])
        self.assertEqual(result["errors"][0]["surface"], "reviews")

    def test_hidden_classic_protection_is_limitation_not_absent_rule(self):
        api = FakeGitHub()
        api.data["repos/acme/repo/branches/release%2Fv1/protection"] = s.EvidenceError("HTTP 404")
        result = s.collect(api, "acme/repo", "1")
        self.assertIsNone(result["classic_protection"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["limitations"][0]["surface"], "classic_protection")
        self.assertEqual(result["observations"]["readiness"], "requires_agent_triage")

    def test_confirmed_classic_absence_preserves_effective_rules(self):
        api = FakeGitHub()
        api.data["repos/acme/repo/branches/release%2Fv1/protection"] = s.EvidenceError(
            "HTTP 404", payload={"message": "Branch not protected"})
        api.page_data["repos/acme/repo/rules/branches/release%2Fv1?per_page=100"] = [
            {"type": "pull_request", "parameters": {"required_approving_review_count": 1}}]
        result = s.collect(api, "acme/repo", "1")
        self.assertTrue(result["complete"])
        self.assertTrue(result["classic_protection"]["absence_confirmed"])
        self.assertEqual(result["effective_rules"][0]["type"], "pull_request")

    def test_neutral_checks_do_not_hide_missing_rules_or_findings(self):
        rules = [{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "ticket/validate", "integration_id": 5}]}}]
        checks = [{"name": "Cursor Bugbot", "status": "completed", "conclusion": "neutral"},
                  {"name": "lint", "status": "completed", "conclusion": "cancelled"}]
        result = s.observations({"statusCheckRollup": []}, checks, [], [{"id": "T", "isResolved": False}], rules, {})
        self.assertEqual(result["unresolved_thread_ids"], ["T"])
        self.assertEqual(result["missing_required_contexts"], ["ticket/validate"])
        self.assertEqual(result["unsuccessful_checks"], ["lint"])
        self.assertEqual(result["neutral_or_skipped"], ["Cursor Bugbot"])
        self.assertEqual(result["required_contexts"][0]["integration_id"], 5)

    def test_unpublished_inline_comments_omitted(self):
        api = FakeGitHub()
        api.page_data["repos/acme/repo/pulls/1/reviews?per_page=100"] = [
            {"id": 1, "state": "PENDING"}, {"id": 2, "state": "COMMENTED"}]
        api.page_data["repos/acme/repo/pulls/1/comments?per_page=100"] = [
            {"pull_request_review_id": 1, "body": "private draft"},
            {"pull_request_review_id": 2, "body": "published finding"}]
        result = s.collect(api, "acme/repo", "1")
        self.assertEqual([c["body"] for c in result["inline_comments"]], ["published finding"])
        self.assertEqual([r["id"] for r in result["reviews"]], [2])


if __name__ == "__main__":
    unittest.main()
