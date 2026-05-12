"""Concurrency tests for housekeep.py — exercise the lock guard.

Verifies the documented behaviour for a second `housekeep.py --apply`
invocation while one is already in flight: wait up to LOCK_WAIT_SECONDS,
then exit non-zero with a message that names the holder PID.
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import housekeep as hk


def _make_repo(tmp: pathlib.Path) -> None:
    """Set up a minimal scratch repo with one open task.

    Not a real git repo — the script falls back to os.replace for
    moves when .git is absent, which is fine for these tests since
    we are exercising the lock, not the move logic.
    """
    tasks = tmp / "docs" / "developers" / "tasks"
    for sub in ("open", "active", "closed"):
        (tasks / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "developers" / "ideas" / "open").mkdir(parents=True, exist_ok=True)


class TestLockGuard(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        _make_repo(self.tmp)
        self._cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_second_caller_waits_then_runs_when_first_releases_quickly(self):
        # Hold the lock briefly, then release; second invocation should
        # acquire after the wait and exit 0.
        lock_path = self.tmp / hk.LOCK_FILENAME
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            hk._platform_lock(fd)
            # Release after 0.5s in a child via a tiny helper script —
            # but simpler: spawn the subprocess, sleep, release.
            proc = subprocess.Popen(
                [sys.executable,
                 str(pathlib.Path(hk.__file__)),
                 "--apply"],
                cwd=self.tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.5)
            hk._platform_unlock(fd)
            os.close(fd)
            fd = -1
            stdout, stderr = proc.communicate(timeout=15)
        finally:
            if fd >= 0:
                try:
                    hk._platform_unlock(fd)
                except OSError:
                    pass
                os.close(fd)

        self.assertEqual(
            proc.returncode, 0,
            f"second --apply should have succeeded after lock released; "
            f"stdout={stdout!r} stderr={stderr!r}",
        )
        self.assertIn("housekeep: applied.", stdout)

    def test_second_caller_fails_loud_when_lock_held_past_timeout(self):
        # Hold the lock for the entire duration of the subprocess by
        # passing a very short wait_seconds via env. Easier: monkey-patch
        # is not available across processes, so spawn with a thin wrapper
        # that lowers LOCK_WAIT_SECONDS.
        lock_path = self.tmp / hk.LOCK_FILENAME
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            hk._platform_lock(fd)
            # Identify ourselves in the lockfile so the timeout message
            # has something concrete to report.
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))

            wrapper = textwrap.dedent(f"""
                import sys
                sys.path.insert(0, {str(pathlib.Path(hk.__file__).parent)!r})
                import housekeep
                housekeep.LOCK_WAIT_SECONDS = 1
                raise SystemExit(housekeep.main(["--apply"]))
            """)
            proc = subprocess.run(
                [sys.executable, "-c", wrapper],
                cwd=self.tmp,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            try:
                hk._platform_unlock(fd)
            except OSError:
                pass
            os.close(fd)

        self.assertNotEqual(
            proc.returncode, 0,
            f"second --apply should have failed loud; "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
        )
        self.assertIn("another instance is running", proc.stderr)
        self.assertIn(str(os.getpid()), proc.stderr)

    def test_dry_run_does_not_acquire_lock(self):
        # Hold the lock; a dry-run (no --apply) should still succeed,
        # because dry-run is a pure read.
        lock_path = self.tmp / hk.LOCK_FILENAME
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            hk._platform_lock(fd)
            proc = subprocess.run(
                [sys.executable, str(pathlib.Path(hk.__file__))],
                cwd=self.tmp,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            try:
                hk._platform_unlock(fd)
            except OSError:
                pass
            os.close(fd)

        self.assertEqual(
            proc.returncode, 0,
            f"dry-run should not acquire the lock; "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
        )
        self.assertIn("dry-run", proc.stdout)

    def test_lock_released_when_process_exits_without_release(self):
        # Open + lock the file in a child Python process, then kill it.
        # The OS must release the lock automatically — a fresh
        # housekeep --apply should then succeed without waiting.
        wrapper = textwrap.dedent(f"""
            import os, sys, time
            sys.path.insert(0, {str(pathlib.Path(hk.__file__).parent)!r})
            import housekeep
            fd = os.open(housekeep.LOCK_FILENAME, os.O_RDWR | os.O_CREAT, 0o644)
            housekeep._platform_lock(fd)
            sys.stdout.write('locked\\n')
            sys.stdout.flush()
            time.sleep(60)
        """)
        child = subprocess.Popen(
            [sys.executable, "-c", wrapper],
            cwd=self.tmp,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Wait for "locked" handshake.
            assert child.stdout is not None
            line = child.stdout.readline()
            self.assertEqual(line.strip(), "locked")
            child.kill()
            child.wait(timeout=5)
            # Now run housekeep --apply; the kernel should have
            # released the lock when the child died.
            proc = subprocess.run(
                [sys.executable,
                 str(pathlib.Path(hk.__file__)),
                 "--apply"],
                cwd=self.tmp,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    stream.close()

        self.assertEqual(
            proc.returncode, 0,
            f"--apply should succeed after holder process died; "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
        )


if __name__ == "__main__":
    unittest.main()
