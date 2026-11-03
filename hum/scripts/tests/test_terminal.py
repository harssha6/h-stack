"""Behavioral tests for empty-only closing, including last-moment changes."""
from contextlib import nullcontext
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_lifecycle import hum, leases, policy

terminals = hum.terminals
sys.modules[hum.__name__] = hum


class TerminalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'project'
        self.root.mkdir()
        self.pane = {'pane_id': 'p1', 'workspace_id': 'w1', 'terminal_id': 'terminal1',
                     'label': 'web', 'cwd': str(self.root), 'focused': False}
        self.state = {'cmd': 'original-server', 'cwd': str(self.root), 'marker': 'hum:start:old',
                      'lifecycle': policy(), 'stopped': 150,
                      'binding': {'version': 1, 'mode': 'adopted', 'pane_id': 'p1',
                                  'marker': 'hum:start:old', 'shell': {'pid': 101, 'birth': 'shell'},
                                  'process': {'pid': 111, 'birth': 'job'}, 'pgid': 111}}
        self.calls = []
        def herdr(*args):
            self.calls.append(args)
            if args[:2] == ('pane', 'get'):
                return {'pane': deepcopy(self.pane)}
            if args[:2] == ('workspace', 'get'):
                return {'workspace': {'pane_count': 1}}
            if args[:2] == ('workspace', 'list'):
                return {'workspaces': []}
            return {}
        patches = [patch.object(hum, 'STATE_DIR', self.root / 'state'),
                   patch.object(hum, 'herdr', side_effect=herdr),
                   patch.object(hum, 'project', return_value=('project', self.root)),
                   patch.object(hum, 'find_workspace', return_value='w1'),
                   patch.object(hum, 'proc_info', return_value={'shell_pid': 101,
                                                                'foreground_process_group_id': 101}),
                   patch.object(leases, 'process_birth', side_effect=lambda pid: 'shell' if pid == 101 else None),
                   patch.object(terminals, 'empty_shell'),
                   patch.object(terminals, 'hold_empty_shell', side_effect=lambda _: nullcontext()),
                   patch.object(hum, 'read', return_value='original log\n'), patch.object(hum, 'emit')]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        hum.save_state('project', 'web', self.state)

    def close(self, dry=False):
        return terminals.close_finished(hum, 'project', 'web', self.state, dry_run=dry)

    def assert_no_close(self):
        self.assertNotIn(('pane', 'close', 'p1'), self.calls)

    def test_close_preserves_command_and_archives_logs_and_only_closes_one_pane(self):
        self.assertEqual(self.close()['result'], 'closed')
        after = hum.load_state('project', 'web')
        self.assertEqual(after['cmd'], 'original-server')
        self.assertEqual(after['lifecycle'], self.state['lifecycle'])
        self.assertEqual(Path(after['archived_log']).read_text(), 'original log\n')
        self.assertIn(('pane', 'close', 'p1'), self.calls)
        self.assertFalse(any(c[:2] in (('tab', 'close'), ('workspace', 'close')) for c in self.calls))

    def test_dry_run_never_suspends_or_mutates(self):
        self.assertEqual(self.close(dry=True)['result'], 'would-close')
        terminals.hold_empty_shell.assert_not_called()
        self.assertEqual(hum.load_state('project', 'web'), self.state)
        self.assert_no_close()

    def test_shared_preview_persistent_unknown_and_active_owners_survive(self):
        values = [policy(now=hum.time.time()), policy(kind='persistent'),
                  leases.claim(policy(), {}, 'manual:other', hum.time.time()),
                  policy('t3:unknown'), policy('t3:active')]
        for value in values:
            self.state['lifecycle'] = value
            with patch.object(hum, 'exact_thread_status', side_effect=lambda owner, cache: 'active' if owner == 'active' else 'unknown'), \
                    self.assertRaises(leases.PolicyError): self.close()
        self.assert_no_close()

    def test_renewal_during_archive_prevents_close(self):
        def renew(*args):
            updated = deepcopy(self.state)
            updated['lifecycle'] = leases.claim(updated['lifecycle'], {}, 'manual:other', hum.time.time())
            hum.save_state('project', 'web', updated)
            return 'log'
        with patch.object(hum, 'read', side_effect=renew), self.assertRaises(leases.PolicyError): self.close()
        self.assert_no_close()

    def test_terminal_replacement_after_archive_prevents_close(self):
        def replace(*args):
            self.pane['terminal_id'] = 'new-terminal'
            return 'log'
        with patch.object(hum, 'read', side_effect=replace), self.assertRaises(leases.PolicyError): self.close()
        self.assert_no_close()

    def test_owner_resuming_at_last_check_prevents_close(self):
        self.state['lifecycle'] = policy('t3:exact')
        with patch.object(hum, 'exact_thread_status', side_effect=['inactive', 'inactive', 'active']), \
                self.assertRaises(leases.PolicyError): self.close()
        self.assert_no_close()

    def test_focused_manual_new_foreground_and_live_run_survive(self):
        self.pane['focused'] = True
        with self.assertRaises(leases.PolicyError): self.close()
        self.pane['focused'] = False
        with patch.object(hum, 'proc_info', return_value={'shell_pid': 101, 'foreground_process_group_id': 222}), \
                self.assertRaises(leases.PolicyError): self.close()
        with patch.object(leases, 'same_process', return_value=True), \
                self.assertRaises(leases.PolicyError): self.close()
        self.state.pop('binding')
        with self.assertRaises(leases.PolicyError): self.close()
        self.assert_no_close()

    def test_parent_worktree_group_never_closes_even_if_herdr_confirmation_disabled(self):
        def grouped(*args):
            if args[:2] == ('pane', 'get'): return {'pane': self.pane}
            if args[:2] == ('workspace', 'get'):
                return {'workspace': {'pane_count': 1, 'worktree': {'repo_key': 'repo', 'is_linked_worktree': False}}}
            return {'workspaces': [{'workspace_id': 'w2', 'worktree': {'repo_key': 'repo'}}]}
        with patch.object(hum, 'herdr', side_effect=grouped), self.assertRaises(leases.PolicyError): self.close()
        self.assert_no_close()

    def test_missing_run_receipt_and_mismatched_generation_never_close(self):
        self.state['binding'].update(mode='wrapper', run_id='a' * 32)
        with self.assertRaises(leases.PolicyError): self.close()
        self.state['marker'] = self.state['binding']['marker'] = 'hum:start:' + 'a' * 32
        with self.assertRaises(FileNotFoundError): self.close()
        self.assert_no_close()

    def test_sweep_preserves_initial_focus_after_herdr_moves_focus(self):
        # Pane is unfocused by the time it is inspected, but was focused when
        # the sweep began. Closing some other workspace must not unprotect it.
        original = hum.herdr.side_effect
        def focus_then_move(*args):
            if args[:2] == ('pane', 'list'):
                return {'panes': [dict(self.pane, focused=True)]}
            return original(*args)
        with patch.object(hum, 'session_running', return_value=True), \
                patch.object(hum, 'herdr', side_effect=focus_then_move), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            hum.cleanup(empty_only=True, as_json=True)
        self.assertEqual(json.loads(output.getvalue())[0]['result'], 'protected')
        self.assert_no_close()

    def test_malformed_binding_is_reported_without_closing(self):
        self.state['binding'] = []
        hum.save_state('project', 'web', self.state)
        with patch.object(hum, 'session_running', return_value=True), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            hum.cleanup(empty_only=True, as_json=True)
        self.assertEqual(json.loads(output.getvalue())[0]['result'], 'protected')
        self.assert_no_close()


@unittest.skipUnless(sys.platform.startswith('linux') and hasattr(os, 'pidfd_open')
                     and hasattr(signal, 'pidfd_send_signal'),
                     'Linux /proc and pidfd process guards; no macOS runtime proof')
class ProcessGuardTests(unittest.TestCase):
    def test_shell_executing_a_builtin_is_not_an_empty_prompt(self):
        root = {'pid': 101, 'state': 'R', 'ppid': 1, 'sid': 101, 'tty': 42}
        with patch.object(leases, 'same_process', return_value=True), \
                patch.object(terminals, 'linux_process', return_value=root), self.assertRaises(leases.PolicyError):
            terminals.empty_shell({'pid': 101, 'birth': 'shell'})

    def test_tree_check_rejects_child_same_session_and_disowned_tty_work(self):
        root = {'pid': 101, 'state': 'S', 'ppid': 1, 'sid': 101, 'tty': 42}
        for edge in ({'ppid': 101, 'sid': 999, 'tty': 0},
                     {'ppid': 1, 'sid': 101, 'tty': 0},
                     {'ppid': 1, 'sid': 999, 'tty': 42}):
            child = dict(edge, pid=222, state='S')
            with patch.object(leases, 'same_process', return_value=True), \
                    patch.object(terminals, 'linux_process', side_effect=lambda pid: root if pid == 101 else child), \
                    patch.object(Path, 'resolve', return_value=Path('/usr/bin/bash')), \
                    patch.object(Path, 'is_file', return_value=True), \
                    patch.object(Path, 'read_text', return_value='do_select'), \
                    patch.object(Path, 'iterdir', return_value=[Path('/proc/222')]), \
                    self.assertRaises(leases.PolicyError):
                terminals.empty_shell({'pid': 101, 'birth': 'shell'})

    def test_pidfd_guard_resumes_shell_on_failure(self):
        with patch.object(terminals, 'empty_shell'), patch.object(os, 'pidfd_open', return_value=77), \
                patch.object(os, 'close') as close, patch.object(leases, 'same_process', return_value=True), \
                patch.object(terminals, 'linux_process', return_value={'state': 'T'}), \
                patch.object(signal, 'pidfd_send_signal') as send:
            with self.assertRaises(RuntimeError):
                with terminals.hold_empty_shell({'pid': 101, 'birth': 'shell'}):
                    raise RuntimeError('close failed')
            self.assertEqual([c.args for c in send.call_args_list], [(77, signal.SIGSTOP), (77, signal.SIGCONT)])
            close.assert_called_once_with(77)

    def test_birth_race_before_freeze_does_not_signal_anything(self):
        with patch.object(terminals, 'empty_shell'), patch.object(os, 'pidfd_open', return_value=77), \
                patch.object(os, 'close'), patch.object(leases, 'same_process', return_value=False), \
                patch.object(signal, 'pidfd_send_signal') as send, self.assertRaises(leases.PolicyError):
            with terminals.hold_empty_shell({'pid': 101, 'birth': 'shell'}): pass
        send.assert_not_called()

    def test_sigterm_resumes_shell_and_restores_previous_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        with patch.object(terminals, 'empty_shell'), patch.object(os, 'pidfd_open', return_value=77), \
                patch.object(os, 'close'), patch.object(leases, 'same_process', return_value=True), \
                patch.object(terminals, 'linux_process', return_value={'state': 'T'}), \
                patch.object(signal, 'pidfd_send_signal') as send:
            with self.assertRaises(leases.PolicyError):
                with terminals.hold_empty_shell({'pid': 101, 'birth': 'shell'}):
                    signal.raise_signal(signal.SIGTERM)
            self.assertEqual(send.call_args.args, (77, signal.SIGCONT))
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)


if __name__ == '__main__':
    unittest.main()
