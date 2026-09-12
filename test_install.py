"""Installer contract tests, using isolated XDG directories and a mock shell."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class InstallerTests(unittest.TestCase):
    def test_install_positions_and_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            log = base / "calls"
            for name in ("omarchy", "omarchy-shell"):
                command = bin_dir / name
                command.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$VERSEWORK_TEST_LOG"\n')
                command.chmod(0o755)
            env = dict(os.environ, XDG_DATA_HOME=str(base / "data"),
                       XDG_CONFIG_HOME=str(base / "config"),
                       PATH=str(bin_dir) + ":" + os.environ["PATH"],
                       VERSEWORK_TEST_LOG=str(log))
            def install(*args):
                return subprocess.run(["bash", str(ROOT / "install.sh"), *args],
                                      env=env, capture_output=True, text=True)
            for position, expected in (("left", "left"), ("middle", "center"), ("right", "right")):
                result = install("--bar-position", position)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("plugin enable versework.launcher --section " + expected, log.read_text())
            desktop = base / "data/applications/io.versework.Studio.desktop"
            self.assertTrue(desktop.exists())
            self.assertTrue((base / "config/omarchy/plugins/versework.launcher/BarWidget.qml").exists())
            before = log.read_text()
            self.assertEqual(install().returncode, 0)
            self.assertEqual(log.read_text(), before)
            self.assertEqual(install("--bar-position", "none").returncode, 0)
            self.assertIn("plugin disable versework.launcher", log.read_text())
            before = log.read_text()
            self.assertEqual(install("--bar-position", "invalid").returncode, 2)
            self.assertEqual(log.read_text(), before)


if __name__ == "__main__":
    unittest.main()
