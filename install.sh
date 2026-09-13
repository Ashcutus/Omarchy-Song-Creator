#!/usr/bin/env bash
# User-level app install; does not change Omarchy system files.
set -euo pipefail
versework_source="$(cd -- "$(dirname -- "$0")" && pwd)"
versework_data="${XDG_DATA_HOME:-$HOME/.local/share}"
versework_target="$versework_data/versework/app"
versework_plugin="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/versework.launcher"
versework_desktop="$versework_data/applications/io.versework.Studio.desktop"
versework_position=keep
if (( $# > 0 )); then
  case "$1" in
    --help|-h)
      echo 'Usage: ./install.sh [--bar-position left|middle|right|none|keep]'
      echo 'Without arguments, asks in a terminal; otherwise keeps the current bar layout.'
      exit 0 ;;
    --bar-position)
      if (( $# != 2 )); then
        echo '--bar-position requires left, middle, right, none, or keep.' >&2
        exit 2
      fi
      versework_position="$2" ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
elif [[ -t 0 ]]; then
  echo 'Where would you like the Versework icon on your bar?'
  echo '  1) Left  2) Middle  3) Right  4) No icon  5) Keep current layout'
  while true; do
    read -r -p 'Choose 1–5 [5]: ' versework_position || exit 1
    case "$versework_position" in
      1|left) versework_position=left; break ;;
      2|middle|center) versework_position=center; break ;;
      3|right) versework_position=right; break ;;
      4|none) versework_position=none; break ;;
      5|keep|"") versework_position=keep; break ;;
      *) echo 'Please choose 1, 2, 3, 4, or 5.' ;;
    esac
  done
fi
case "$versework_position" in
  middle) versework_position=center ;;
  left|center|right|none|keep) ;;
  *) echo 'Invalid bar position. Choose left, middle, right, none, or keep.' >&2; exit 2 ;;
esac
if [[ "$versework_position" != keep && "$versework_position" != none ]]; then
  if ! command -v omarchy >/dev/null || ! command -v omarchy-shell >/dev/null; then
    echo 'Bar icons require the Omarchy shell. Use --bar-position none for launcher-only installation.' >&2
    exit 1
  fi
  omarchy plugin validate "$versework_source/bar-plugin"
fi
/usr/bin/python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" || {
  echo 'GTK dependencies missing. Install with: omarchy pkg add python-gobject gtk4'
  exit 1
}
mkdir -p -- "$versework_target" "$(dirname -- "$versework_desktop")"
for versework_file in app.py core.py appearance.py i18n.py updater.py generation_ui.py workflow_ui.py production_ui.py launch.sh setup-ollama.sh icon.svg README.md; do
  if [[ "$versework_source/$versework_file" != "$versework_target/$versework_file" ]]; then
    install -m 644 -- "$versework_source/$versework_file" "$versework_target/$versework_file"
  fi
done
versework_revision="$(git -C "$versework_source" rev-parse HEAD 2>/dev/null || true)"
printf '%s\n' "$versework_revision" > "$versework_target/.versework-revision"
chmod +x "$versework_target/launch.sh" "$versework_target/setup-ollama.sh"
VERSEWORK_INSTALL_TARGET="$versework_target" VERSEWORK_DESKTOP_PATH="$versework_desktop" /usr/bin/python3 - <<'PYTHON'
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
  update-desktop-database "$versework_data/applications"
fi
echo 'Installed. Search for Versework in your app launcher.'
echo 'For local AI setup, run ./setup-ollama.sh in a terminal.'

case "$versework_position" in
  left|center|right)
    mkdir -p -- "$versework_plugin"
    install -m 644 -- "$versework_source/bar-plugin/manifest.json" "$versework_source/bar-plugin/BarWidget.qml" "$versework_plugin/"
    if ! omarchy-shell shell rescanPlugins ||
       ! omarchy plugin enable versework.launcher --section "$versework_position"; then
      echo 'App installed, but the bar icon could not be enabled. From your running Omarchy desktop, rerun this installer with --bar-position left, middle, or right.' >&2
      exit 1
    fi
    echo "Versework icon added to the $versework_position of your bar." ;;
  none)
    if [[ -d "$versework_plugin" ]]; then
      omarchy-shell shell rescanPlugins
      omarchy plugin disable versework.launcher
    fi
    echo 'Versework is available from the app launcher without a bar icon.' ;;
esac
