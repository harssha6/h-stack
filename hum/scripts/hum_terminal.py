"""Fail-closed, Linux-only closing of finished hum terminals.

Called under hum's existing per-environment lock. Never stops a server. A pidfd
pins the empty shell while SIGSTOP prevents a check/close race with a new job.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import signal
import sys
import time

import hum_lifecycle as leases


def linux_process(pid):
    path = Path('/proc') / str(pid)
    try:
        raw = (path / 'stat').read_text()
        fields = raw[raw.rindex(')') + 2:].split()
        return {'pid': pid, 'state': fields[0], 'ppid': int(fields[1]),
                'sid': int(fields[3]), 'tty': int(fields[4]),
                'birth_ticks': fields[19]}
    except FileNotFoundError:
        return None


def empty_shell(shell, *, frozen=False):
    """Check descendants, disowned jobs and other processes on the same PTY/session.

    Unlike capture_tree, an empty proof must fail if a process cannot be read.
    An orphan with no terminal/session association cannot be killed by pane close.
    """
    if not sys.platform.startswith('linux'):
        raise leases.PolicyError('empty-terminal closing requires Linux /proc and pidfds')
    if not leases.same_process(shell):
        raise leases.PolicyError('recorded shell birth changed')
    root = linux_process(shell['pid'])
    if (not root or root['state'] not in (('T',) if frozen else ('S',))
            or not root['tty'] or root['sid'] != shell['pid']):
        raise leases.PolicyError('shell state or controlling terminal is uncertain')
    if not frozen and (Path('/proc') / str(shell['pid']) / 'wchan').read_text().strip() not in ('wait_woken', 'n_tty_read', 'do_select'):
        raise leases.PolicyError('shell is not waiting for terminal input')
    executable = (Path('/proc') / str(shell['pid']) / 'exe').resolve(strict=True)
    # A process can exec another binary without changing its PID or birth.
    allowed = {Path(p).resolve() for p in ('/bin/bash', '/bin/sh', '/bin/zsh', '/bin/fish')
               if Path(p).is_file()}
    if executable not in allowed:
        raise leases.PolicyError('recorded shell has execed another program')
    for path in Path('/proc').iterdir():
        if not path.name.isascii() or not path.name.isdecimal():
            continue
        item = linux_process(int(path.name))
        if not item or item['pid'] == shell['pid'] or item['state'] in ('Z', 'X'):
            continue
        if (item['ppid'] == shell['pid'] or item['sid'] == root['sid']
                or item['tty'] == root['tty']):
            raise leases.PolicyError(f"terminal still has work (PID {item['pid']})")
    if not leases.same_process(shell) or linux_process(shell['pid']) != root:
        raise leases.PolicyError('shell changed during process scan')


@contextmanager
def hold_empty_shell(shell):
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise leases.PolicyError('empty-terminal closing needs pidfd support')
    empty_shell(shell)
    fd = os.pidfd_open(shell['pid'])
    suspended = False
    previous_handler = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        raise leases.PolicyError('terminal close interrupted; resuming shell')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if not leases.same_process(shell):
            raise leases.PolicyError('shell changed before suspension')
        signal.pidfd_send_signal(fd, signal.SIGSTOP)
        suspended = True
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            item = linux_process(shell['pid'])
            if not item:
                raise leases.PolicyError('shell exited before close')
            if item['state'] == 'T':
                break
            time.sleep(.01)
        empty_shell(shell, frozen=True)
        yield
    finally:
        if suspended:
            try:
                signal.pidfd_send_signal(fd, signal.SIGCONT)
            except ProcessLookupError:
                pass
        os.close(fd)
        signal.signal(signal.SIGTERM, previous_handler)


def finished_run(hum, label, name, state):
    binding = state.get('binding')
    if (not isinstance(binding, dict) or binding.get('version') != 1
            or not binding.get('pane_id') or not state.get('marker')
            or binding.get('marker') != state['marker']):
        raise leases.PolicyError('no exact hum pane/run binding')
    if binding.get('mode') == 'wrapper':
        import json
        run_id = binding.get('run_id')
        if state['marker'] != 'hum:start:' + str(run_id):
            raise leases.PolicyError('run generation differs from marker')
        job = json.loads(hum.run_file(label, name, run_id).read_text())
        if not isinstance(job, dict) or job.get('marker') != state['marker']:
            raise leases.PolicyError('missing matching run receipt')
    elif binding.get('mode') == 'adopted':
        job = binding
    else:
        raise leases.PolicyError('unknown run binding')
    process = job.get('process')
    if (not isinstance(process, dict) or not isinstance(process.get('pid'), int)
            or isinstance(process.get('pid'), bool) or process['pid'] <= 0
            or not isinstance(process.get('birth'), str) or not process['birth']):
        raise leases.PolicyError('missing recorded run process birth')
    if leases.same_process(process):
        raise leases.PolicyError('recorded run is still alive')
    return binding


def candidate(hum, label, name, state, *, frozen=False):
    eligible, reason = leases.due(state.get('lifecycle'), time.time(),
                                  lambda owner: hum.exact_thread_status(owner, {}))
    if not eligible:
        raise leases.PolicyError(reason)
    cwd = state.get('cwd')
    if not isinstance(cwd, str) or not Path(cwd).is_dir() or hum.project(cwd)[0] != label:
        raise leases.PolicyError('recorded checkout cannot be verified')
    binding = finished_run(hum, label, name, state)
    pane = hum.herdr('pane', 'get', binding['pane_id'])['pane']
    if pane.get('label') != name or pane.get('cwd') != cwd or not pane.get('terminal_id'):
        raise leases.PolicyError('pane label, checkout or terminal identity changed')
    if pane.get('focused'):
        raise leases.PolicyError('focused terminal is protected')
    if hum.find_workspace(label) != pane.get('workspace_id'):
        raise leases.PolicyError('workspace identity changed')
    workspace = hum.herdr('workspace', 'get', pane['workspace_id'])['workspace']
    worktree = workspace.get('worktree')
    if (workspace.get('pane_count') == 1 and worktree
            and not worktree.get('is_linked_worktree')):
        # With Herdr's confirmation disabled, closing a parent's last pane can
        # also close linked workspaces. Never delegate that decision to config.
        siblings = hum.herdr('workspace', 'list')['workspaces']
        if any(ws['workspace_id'] != pane['workspace_id']
               and ws.get('worktree', {}).get('repo_key') == worktree.get('repo_key')
               for ws in siblings):
            raise leases.PolicyError('last pane belongs to a parent worktree group')
    info = hum.proc_info(binding['pane_id'])
    shell = binding.get('shell')
    if (not isinstance(shell, dict) or info.get('shell_pid') != shell.get('pid')
            or info.get('foreground_process_group_id') != shell.get('pid')):
        raise leases.PolicyError('foreground job or shell identity changed')
    empty_shell(shell, frozen=frozen)
    return pane, reason


def close_finished(hum, label, name, state, *, dry_run=False):
    """Archive scrollback; recheck owners, generation, PTY and jobs; close one pane.

    Closing a last pane removes its workspace in Herdr. Never close a whole tab
    (it may have other splits), nor force a parent worktree group confirmation.
    """
    pane, reason = candidate(hum, label, name, state)
    if dry_run:
        return {'result': 'would-close', 'reason': reason, 'pane': pane['pane_id']}
    with hold_empty_shell(state['binding']['shell']):
        current, _ = candidate(hum, label, name, state, frozen=True)
        if current['terminal_id'] != pane['terminal_id']:
            raise leases.PolicyError('terminal replaced before close')
        scroll = current.get('scroll', {})
        lines = scroll.get('max_offset_from_bottom', 0) + scroll.get('viewport_rows', 100) + 100
        archive = hum.run_archive(label, name, state)
        # Keep the complete retained scrollback before Herdr destroys its PTY.
        output = hum.read(pane['pane_id'], lines)
        fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
        if hum.load_state(label, name) != state:
            raise leases.PolicyError('run or ownership changed before close')
        current, _ = candidate(hum, label, name, state, frozen=True)
        if current['terminal_id'] != pane['terminal_id']:
            raise leases.PolicyError('terminal replaced before close')
        # No unshare or server signals: empty-only cleanup cannot stop live work.
        # A retained share is reviewed separately, preserving its mapping metadata.
        hum.herdr('pane', 'close', pane['pane_id'])
        state = dict(state, stopped=state.get('stopped') or time.time(),
                     terminal_closed=time.time(), archived_log=str(archive))
        hum.save_state(label, name, state)
    hum.emit('closed', label, name, state['cwd'])
    return {'result': 'closed', 'reason': reason, 'pane': pane['pane_id'], 'log': str(archive)}
