"""Route ownership fixtures; no Tailscale executable or network is contacted."""

import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_lifecycle import hum, leases


def route(port=20443, app_port=3000):
    return {"Web": {f"host:{port}": {"Handlers": {"/": {"Proxy": f"http://127.0.0.1:{app_port}"}}}},
            "TCP": {str(port): {"HTTPS": True}}}


class ShareOwnershipTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = {"cmd": "fixture-command", "cwd": str(self.root), "marker": "fixture-run"}
        state_patch = patch.object(hum, "STATE_DIR", self.root / "state")
        state_patch.start()
        self.addCleanup(state_patch.stop)
        hum.save_state("project", "web", self.state)

    def save_owned(self):
        self.state["share"] = hum.share_record("host", 20443, 3000)
        hum.save_state("project", "web", self.state)
        return deepcopy(self.state)

    def create(self, before, after, port=3000):
        with patch.object(hum.shutil, "which", return_value="/fixture/tailscale"), \
                patch.object(hum, "tailscale_json", side_effect=[{"Self": {"DNSName": "host."}}, before, after]), \
                patch.object(hum.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout="", stderr="")) as command:
            url = hum.share("pane", "project", "web", port)
        return url, command

    def test_existing_admin_proxy_is_not_adopted_or_changed(self):
        before = route()
        before["Web"]["host:20443"]["Handlers"] = {"/admin": {"Proxy": "http://127.0.0.1:3000"}}
        after = deepcopy(before)
        added = route(20444)
        after["Web"].update(added["Web"])
        after["TCP"].update(added["TCP"])
        original = deepcopy(before)
        url, command = self.create(before, after)
        self.assertEqual(url, "https://host:20444")
        self.assertEqual(before, original)
        self.assertEqual(command.call_count, 1)
        self.assertIn("--https=20444", command.call_args.args[0])
        saved = hum.load_state("project", "web")["share"]
        self.assertEqual(saved["https_port"], 20444)
        self.assertEqual(saved["ownership"]["kind"], "hum-serve-root")

    def test_unowned_root_proxy_is_not_adopted_either(self):
        before = route()
        after = deepcopy(before)
        added = route(20444)
        after["Web"].update(added["Web"])
        after["TCP"].update(added["TCP"])
        self.assertEqual(self.create(before, after)[0], "https://host:20444")

    def test_legacy_receipt_is_protected_for_both_share_and_unshare(self):
        self.state["share"] = {"url": "https://host:20443", "https_port": 20443, "app_port": 3000}
        hum.save_state("project", "web", self.state)
        with patch.object(hum.shutil, "which", return_value="/fixture/tailscale"), \
                patch.object(hum, "tailscale_json") as status, \
                patch.object(hum.subprocess, "run") as command:
            for action in [lambda: hum.share("pane", "project", "web", 3000),
                           lambda: hum.unshare("project", "web")]:
                with self.assertRaises(leases.PolicyError) as error:
                    action()
                self.assertIn("ownership receipt", str(error.exception))
        status.assert_not_called()
        command.assert_not_called()
        self.assertEqual(hum.load_state("project", "web"), self.state)

    def test_extra_path_same_proxy_is_never_removed(self):
        before = self.save_owned()
        status = route()
        status["Web"]["host:20443"]["Handlers"]["/admin"] = {"Proxy": "http://127.0.0.1:3000"}
        with patch.object(hum, "tailscale_json", return_value=status), \
                patch.object(hum.subprocess, "run") as command:
            with self.assertRaises(leases.PolicyError):
                hum.unshare("project", "web")
        command.assert_not_called()
        self.assertEqual(hum.load_state("project", "web"), before)

    def test_owned_exact_root_can_be_removed_without_touching_other_routes(self):
        before = self.save_owned()
        status = route()
        status["Web"]["other:20444"] = {"Handlers": {"/admin": {"Proxy": "http://127.0.0.1:9000"}}}
        status["TCP"]["20444"] = {"HTTPS": True}
        snapshot = deepcopy(status)
        with patch.object(hum, "tailscale_json", return_value=status), \
                patch.object(hum.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as command:
            hum.unshare("project", "web")
        self.assertEqual(command.call_args.args[0], ["tailscale", "serve", "--https=20443", "off"])
        self.assertEqual(status, snapshot)
        after = hum.load_state("project", "web")
        self.assertNotIn("share", after)
        self.assertEqual(after["cmd"], before["cmd"])

    def test_owned_exact_root_can_be_reused_without_a_provider_write(self):
        before = self.save_owned()
        with patch.object(hum.shutil, "which", return_value="/fixture/tailscale"), \
                patch.object(hum, "tailscale_json", side_effect=[{"Self": {"DNSName": "host"}}, route()]), \
                patch.object(hum.subprocess, "run") as command:
            self.assertEqual(hum.share("pane", "project", "web", 3000), "https://host:20443")
        command.assert_not_called()
        self.assertEqual(hum.load_state("project", "web"), before)

    def test_verified_owned_root_can_follow_app_port_change_on_same_url(self):
        self.save_owned()
        url, command = self.create(route(), route(app_port=3001), port=3001)
        self.assertEqual(url, "https://host:20443")
        self.assertIn("--https=20443", command.call_args.args[0])
        self.assertEqual(hum.load_state("project", "web")["share"]["app_port"], 3001)

    def test_funnel_flag_alone_reserves_the_entire_port(self):
        before = {"AllowFunnel": {"other:20443": True}}
        after = route(20444)
        after.update(before)
        url, command = self.create(before, after)
        self.assertEqual(url, "https://host:20444")
        self.assertIn("--https=20444", command.call_args.args[0])

    def test_funnel_flag_protects_owned_route_from_reuse_and_removal(self):
        before = self.save_owned()
        status = route()
        status["AllowFunnel"] = {"host:20443": True}
        with patch.object(hum.shutil, "which", return_value="/fixture/tailscale"), \
                patch.object(hum, "tailscale_json", side_effect=[{"Self": {"DNSName": "host"}}, status]), \
                patch.object(hum.subprocess, "run") as command:
            with self.assertRaises(leases.PolicyError):
                hum.share("pane", "project", "web", 3000)
        command.assert_not_called()
        with patch.object(hum, "tailscale_json", return_value=status), \
                patch.object(hum.subprocess, "run") as command:
            with self.assertRaises(leases.PolicyError):
                hum.unshare("project", "web")
        command.assert_not_called()
        self.assertEqual(hum.load_state("project", "web"), before)

    def test_funnel_enabled_during_creation_never_gets_an_ownership_receipt(self):
        after = route()
        after["AllowFunnel"] = {"host:20443": True}
        with self.assertRaises(leases.PolicyError):
            self.create({}, after)
        self.assertNotIn("share", hum.load_state("project", "web"))

    def test_failed_creation_never_records_ownership(self):
        with patch.object(hum.shutil, "which", return_value="/fixture/tailscale"), \
                patch.object(hum, "tailscale_json", side_effect=[{"Self": {"DNSName": "host"}}, {}]), \
                patch.object(hum.subprocess, "run", return_value=SimpleNamespace(
                    returncode=1, stdout="", stderr="fixture failure")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                hum.share("pane", "project", "web", 3000)
        self.assertNotIn("share", hum.load_state("project", "web"))

    def test_changed_ownership_fingerprint_prevents_provider_calls(self):
        self.save_owned()
        self.state["share"]["ownership"]["fingerprint"] = "altered"
        hum.save_state("project", "web", self.state)
        with patch.object(hum, "tailscale_json") as status, \
                patch.object(hum.subprocess, "run") as command:
            with self.assertRaises(leases.PolicyError):
                hum.unshare("project", "web")
        status.assert_not_called()
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
