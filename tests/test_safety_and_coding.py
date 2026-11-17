from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import actions, assistant, coding, download_guard, security


class CodingWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"JARVIS_WORKSPACE": self.temp.name})
        self.env.start()
        self.project = Path(coding.workspace_root()) / "demo"
        self.project.mkdir()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_rejects_workspace_escape(self):
        with self.assertRaises(ValueError):
            coding._file_path("demo", "../../outside.txt")

    def test_rejects_git_and_environment_secrets(self):
        with self.assertRaises(ValueError):
            coding._file_path("demo", ".git/config")
        with self.assertRaises(ValueError):
            coding._file_path("demo", ".env")
        with self.assertRaises(ValueError):
            coding._file_path("demo", "private.pem")

    def test_atomic_write_and_backup_on_replace(self):
        coding.write_file("demo", "src/main.py", "print('first')\n")
        coding.write_file("demo", "src/main.py", "print('second')\n")
        self.assertEqual((self.project / "src/main.py").read_text(encoding="utf-8"), "print('second')\n")
        backups = list((self.project / ".jarvis-backups").glob("*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "print('first')\n")

    def test_rejects_symlinked_file(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        link = self.project / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is not available in this environment.")
        with self.assertRaises(ValueError):
            coding._file_path("demo", "linked.txt")

    def test_project_inspection_does_not_follow_manifest_symlink(self):
        outside = Path(self.temp.name) / "outside-readme.md"
        outside.write_text("PRIVATE OUTSIDE CONTENT", encoding="utf-8")
        link = self.project / "README.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is not available in this environment.")
        result = coding.inspect_project("demo")
        self.assertNotIn("PRIVATE OUTSIDE CONTENT", result)

    def test_python_check_falls_back_when_pytest_is_missing(self):
        from types import SimpleNamespace
        with patch("importlib.util.find_spec", return_value=None), \
             patch("jarvis.coding.subprocess.run", return_value=SimpleNamespace(
                 stdout="Ran 0 tests in 0.000s", stderr="", returncode=0
             )) as run:
            result = coding.run_check("demo", "python_tests")
        self.assertIn("NO TESTS FOUND", result)
        self.assertIn("unittest", run.call_args.args[0])

    def test_diff_preview_does_not_modify_file(self):
        source = self.project / "main.py"
        source.write_text("print('old')\n", encoding="utf-8")
        preview = coding.preview_file_change("demo", "main.py", "print('new')\n")
        self.assertIn("-print('old')", preview)
        self.assertIn("+print('new')", preview)
        self.assertEqual(source.read_text(encoding="utf-8"), "print('old')\n")


class ProcessAndLaunchSafetyTests(unittest.TestCase):
    def test_direct_executable_launch_requires_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "unknown.exe"
            executable.write_bytes(b"not executed")
            with patch("jarvis.actions.os.startfile") as startfile:
                result = actions.open_target(str(executable), confirm=lambda prompt: False)
            self.assertIn("cancelled", result.lower())
            startfile.assert_not_called()

    def test_direct_executable_launch_runs_only_after_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "trusted.exe"
            executable.write_bytes(b"placeholder")
            with patch("jarvis.actions.os.startfile") as startfile:
                result = actions.open_target(str(executable), confirm=lambda prompt: True)
            self.assertIn("Opening", result)
            startfile.assert_called_once()

    def test_critical_windows_process_cannot_be_terminated(self):
        class FakeProcess:
            def name(self):
                return "lsass.exe"
            def terminate(self):
                raise AssertionError("Critical process must not be terminated")
        with patch("jarvis.actions.psutil.Process", return_value=FakeProcess()):
            with self.assertRaises(ValueError):
                actions.terminate_process("4321")


class ConfirmationSafetyTests(unittest.TestCase):
    def test_offline_router_fails_closed_without_confirmation_callback(self):
        with patch("jarvis.assistant.ai.is_ready", return_value=False), \
             patch("jarvis.assistant.actions.schedule_power_action") as schedule:
            result = assistant.respond("restart my PC", confirm=None)
        self.assertIn("cancelled", result.lower())
        schedule.assert_not_called()


class FileTrustReportTests(unittest.TestCase):
    def test_non_windows_report_uses_real_line_breaks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.bin"
            path.write_bytes(b"sample")
            with patch("jarvis.security.platform.system", return_value="Linux"):
                report = security.inspect_file_trust(str(path))
        self.assertIn("\nSHA-256:", report)
        self.assertNotIn("\\nSHA-256:", report)


class DownloadMonitorTests(unittest.TestCase):
    def test_waits_for_file_size_to_stabilize(self):
        with tempfile.TemporaryDirectory() as folder:
            monitor = download_guard.DownloadMonitor()
            monitor.folder = Path(folder)
            with patch("jarvis.download_guard.platform.system", return_value="Windows"):
                self.assertEqual(monitor.poll(), [])  # Establish baseline.
                file = Path(folder) / "installer.exe"
                file.write_bytes(b"first")
                self.assertEqual(monitor.poll(), [])  # First sighting.
                self.assertEqual(monitor.poll(), [])  # First stable interval.
                self.assertEqual(monitor.poll(), ["installer.exe (5 bytes)"])
                self.assertEqual(monitor.poll(), [])  # Never alerts twice.

    def test_realerts_when_a_download_is_replaced_with_same_name(self):
        with tempfile.TemporaryDirectory() as folder:
            monitor = download_guard.DownloadMonitor()
            monitor.folder = Path(folder)
            file = Path(folder) / "installer.exe"
            with patch("jarvis.download_guard.platform.system", return_value="Windows"):
                file.write_bytes(b"old")
                self.assertEqual(monitor.poll(), [])  # Existing file baseline.
                file.unlink()
                self.assertEqual(monitor.poll(), [])  # Forget removed file.
                file.write_bytes(b"new payload")
                self.assertEqual(monitor.poll(), [])  # New file sighting.
                self.assertEqual(monitor.poll(), [])  # First stable poll.
                self.assertEqual(monitor.poll(), ["installer.exe (11 bytes)"])

    def test_realerts_when_existing_download_changes_in_place(self):
        with tempfile.TemporaryDirectory() as folder:
            monitor = download_guard.DownloadMonitor()
            monitor.folder = Path(folder)
            file = Path(folder) / "installer.exe"
            with patch("jarvis.download_guard.platform.system", return_value="Windows"):
                monitor.poll()
                file.write_bytes(b"first")
                self.assertEqual(monitor.poll(), [])
                self.assertEqual(monitor.poll(), [])
                self.assertEqual(monitor.poll(), ["installer.exe (5 bytes)"])
                previous = file.stat()
                file.write_bytes(b"other")
                os.utime(file, ns=(previous.st_atime_ns, previous.st_mtime_ns + 2_000_000_000))
                self.assertEqual(monitor.poll(), [])  # Changed content, new stability window.
                self.assertEqual(monitor.poll(), [])
                self.assertEqual(monitor.poll(), ["installer.exe (5 bytes)"])

    def test_does_not_alert_for_file_that_keeps_growing(self):
        with tempfile.TemporaryDirectory() as folder:
            monitor = download_guard.DownloadMonitor()
            monitor.folder = Path(folder)
            with patch("jarvis.download_guard.platform.system", return_value="Windows"):
                monitor.poll()
                file = Path(folder) / "payload.msi"
                file.write_bytes(b"a")
                self.assertEqual(monitor.poll(), [])
                file.write_bytes(b"ab")
                self.assertEqual(monitor.poll(), [])
                file.write_bytes(b"abc")
                self.assertEqual(monitor.poll(), [])
                self.assertEqual(monitor.poll(), [])
                self.assertEqual(monitor.poll(), ["payload.msi (3 bytes)"])


if __name__ == "__main__":
    unittest.main()
