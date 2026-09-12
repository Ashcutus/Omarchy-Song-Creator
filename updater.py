"""User-level updates from Versework's official main branch."""
import fcntl
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REPOSITORY = 'https://github.com/Ashcutus/Omarchy-Versework.git'
FILES = ('app.py', 'core.py', 'appearance.py', 'i18n.py', 'updater.py',
         'launch.sh', 'setup-ollama.sh', 'icon.svg', 'README.md')
REVISION_FILE = '.versework-revision'


def git(*args):
    result = subprocess.run(['git', *args], capture_output=True, text=True,
                            timeout=120, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'GitHub update request failed.')
    return result.stdout.strip()


def current_revision(target):
    try:
        return (Path(target) / REVISION_FILE).read_text().strip()
    except OSError:
        return ''


def latest_revision():
    response = git('ls-remote', REPOSITORY, 'refs/heads/main').split()
    revision = response[0] if response else ''
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise RuntimeError('GitHub returned an invalid update revision.')
    return revision


def replace_installation(source, target, revision):
    """Validate a complete staged copy before swapping; roll back a failed swap."""
    source, target = Path(source), Path(target)
    if not (target / REVISION_FILE).is_file() or (target / '.git').exists():
        raise RuntimeError('Run install.sh once, then open the installed Versework to use updates.')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Invalid update revision.')
    with tempfile.TemporaryDirectory(prefix='.versework-update-', dir=target.parent) as temporary:
        stage = Path(temporary) / 'app'
        stage.mkdir()
        for name in FILES:
            source_file = source / name
            if source_file.is_symlink() or not source_file.is_file():
                raise RuntimeError('The update is missing a required app file: ' + name)
            shutil.copy2(source_file, stage / name)
        subprocess.run(['/usr/bin/python3', '-m', 'py_compile',
                        *[str(stage / name) for name in FILES if name.endswith('.py')]],
                       check=True, capture_output=True, timeout=30)
        for name in ('launch.sh', 'setup-ollama.sh'):
            (stage / name).chmod(0o755)
        (stage / REVISION_FILE).write_text(revision + '\n')
        backup = Path(temporary) / 'previous'
        target.rename(backup)
        try:
            stage.rename(target)
        except BaseException:
            backup.rename(target)
            raise


def install_update(target, revision):
    target = Path(target).resolve()
    with (target.parent / '.versework-update.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another Versework update is already running.')
        with tempfile.TemporaryDirectory(prefix='versework-download-') as temporary:
            source = Path(temporary) / 'source'
            git('clone', '--depth', '1', '--branch', 'main', '--single-branch', REPOSITORY, str(source))
            if git('-C', str(source), 'rev-parse', 'HEAD') != revision:
                raise RuntimeError('A newer update was published. Check for updates again.')
            replace_installation(source, target, revision)
