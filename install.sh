#!/usr/bin/env bash
# User-level app install; does not change Omarchy system files.
set -euo pipefail
versework_source="$(cd -- "$(dirname -- "$0")" && pwd)"
versework_target="$HOME/.local/share/versework/app"
versework_desktop="$HOME/.local/share/applications/io.versework.Studio.desktop"
/usr/bin/python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" || {
  echo 'GTK dependencies missing. Install with: omarchy pkg add python-gobject gtk4'
  exit 1
}
mkdir -p -- "$versework_target" "$(dirname -- "$versework_desktop")"
for versework_file in app.py core.py appearance.py i18n.py launch.sh setup-ollama.sh icon.svg README.md; do
  if [[ "$versework_source/$versework_file" != "$versework_target/$versework_file" ]]; then
    install -m 644 -- "$versework_source/$versework_file" "$versework_target/$versework_file"
  fi
done
chmod +x "$versework_target/launch.sh" "$versework_target/setup-ollama.sh"
VERSEWORK_INSTALL_TARGET="$versework_target" VERSEWORK_DESKTOP_PATH="$versework_desktop" /usr/bin/python - <<'PYTHON'
import os
from pathlib import Path
# Desktop-entry quoting, not shell quoting. No shell interprets Exec.
target = os.environ['VERSEWORK_INSTALL_TARGET']
def quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
Path(os.environ['VERSEWORK_DESKTOP_PATH']).write_text('[Desktop Entry]\nType=Application\nName=Versework — Song Creator\nComment=Write songs and organise collections locally with Ollama\nExec=' + quote(target + '/launch.sh') + '\nIcon=' + target + '/icon.svg\nTerminal=false\nCategories=AudioVideo;Audio;\nKeywords=Song;Lyrics;Music;Suno;Ollama;EP;\nStartupNotify=true\nStartupWMClass=io.versework.Studio\n')
PYTHON
if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate "$versework_desktop"
fi
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$HOME/.local/share/applications"
fi
echo 'Installed. Search for Versework in your app launcher.'
echo 'For local AI setup, run ./setup-ollama.sh in a terminal.'
