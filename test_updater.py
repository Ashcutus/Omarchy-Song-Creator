import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import updater

ROOT = Path(__file__).resolve().parent


class UpdaterTests(unittest.TestCase):
    def test_plugin_refresh_only_updates_existing_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / 'omarchy/plugins/versework.launcher'
            with patch.dict('os.environ', {'XDG_CONFIG_HOME': directory}):
                updater.update_bar_plugin(ROOT)
                self.assertFalse(plugin.exists())
                plugin.mkdir(parents=True)
                (plugin / 'custom-setting').write_text('keep')
                updater.update_bar_plugin(ROOT)
                self.assertEqual((plugin / 'custom-setting').read_text(), 'keep')
                self.assertEqual((plugin / 'BarWidget.qml').read_bytes(), (ROOT / 'bar-plugin/BarWidget.qml').read_bytes())

    def test_healthy_startup_retains_previous_version_for_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.installed(Path(directory))
            updater.replace_installation(ROOT, target, 'b' * 40)
            self.assertTrue(updater.has_rollback(target))
            self.assertTrue((target / '.versework-pending').exists())
            updater.confirm_startup(target)
            self.assertFalse((target / '.versework-pending').exists())
            updater.rollback_installation(target)
            self.assertEqual(updater.current_revision(target), 'a' * 40)
            self.assertEqual((target / 'app.py').read_text(), 'old content')

    def installed(self, root):
        target = root / 'app'
        target.mkdir()
        (target / updater.REVISION_FILE).write_text('a' * 40)
        (target / 'app.py').write_text('old content')
        return target

    def test_complete_update_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self.installed(root)
            data = root / 'data'
            data.mkdir()
            (data / 'songs.sqlite3').write_bytes(b'keep')
            updater.replace_installation(ROOT, target, 'b' * 40)
            self.assertEqual(updater.current_revision(target), 'b' * 40)
            self.assertEqual((target / 'app.py').read_bytes(), (ROOT / 'app.py').read_bytes())
            self.assertEqual((data / 'songs.sqlite3').read_bytes(), b'keep')
            self.assertTrue((target / 'launch.sh').stat().st_mode & 0o100)

    def test_missing_source_keeps_current_app(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self.installed(root)
            with self.assertRaises(RuntimeError):
                updater.replace_installation(root, target, 'b' * 40)
            self.assertEqual((target / 'app.py').read_text(), 'old content')
            self.assertEqual(updater.current_revision(target), 'a' * 40)

    def test_failed_swap_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.installed(Path(directory))
            rename = Path.rename
            def fail_stage(path, destination):
                if path.name == 'app' and path.parent.name.startswith('.versework-update-'):
                    raise OSError('simulated failure')
                return rename(path, destination)
            with patch.object(Path, 'rename', fail_stage):
                with self.assertRaises(OSError):
                    updater.replace_installation(ROOT, target, 'b' * 40)
            self.assertEqual((target / 'app.py').read_text(), 'old content')
            self.assertEqual(updater.current_revision(target), 'a' * 40)

    def test_checkout_and_invalid_revision_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.installed(Path(directory))
            with self.assertRaises(ValueError):
                updater.replace_installation(ROOT, target, 'invalid')
            (target / '.git').mkdir()
            with self.assertRaises(RuntimeError):
                updater.replace_installation(ROOT, target, 'b' * 40)

    def test_upstream_change_aborts_before_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.installed(Path(directory))
            with patch.object(updater, 'git', side_effect=['', 'c' * 40]):
                with self.assertRaisesRegex(RuntimeError, 'newer update'):
                    updater.install_update(target, 'b' * 40)
            self.assertEqual(updater.current_revision(target), 'a' * 40)


    def test_download_and_install_from_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            for name in updater.FILES:
                shutil.copy2(ROOT / name, source / name)
            subprocess.run(['git', 'init', '-b', 'main', str(source)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(source), 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Test',
                            '-c', 'user.email=test@example.invalid', 'commit', '-m', 'Fixture'],
                           check=True, capture_output=True)
            target = self.installed(root)
            with patch.object(updater, 'REPOSITORY', str(source)):
                revision = updater.latest_revision()
                updater.install_update(target, revision)
            self.assertEqual(updater.current_revision(target), revision)
            self.assertEqual((target / 'updater.py').read_bytes(), (ROOT / 'updater.py').read_bytes())
