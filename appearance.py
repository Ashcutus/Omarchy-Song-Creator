"""Read Omarchy's current palette; never write desktop theme configuration."""
from pathlib import Path
import os
import re
import tomllib

COLOUR_KEYS = ('background', 'surface', 'foreground', 'accent')
LAYOUT_CSS = '''
.title { font-size: 26px; font-weight: 700; }
.heading { font-size: 16px; font-weight: 650; }
.caption { opacity: 0.72; font-size: 12px; }
.sidebar { padding: 14px; }
.card { border-radius: 12px; padding: 16px; }
button { padding: 7px 12px; border-radius: 8px; }
entry { padding: 6px; }
textview { padding: 12px; }
.library-row { padding: 16px; border-radius: 10px; margin-bottom: 6px; }
.editor-title { font-size: 22px; font-weight: 650; }
'''


def valid_colour(value):
    return isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value) is not None


def read_palette(home=None):
    root = Path(home) if home else Path.home()
    state = Path(os.environ.get('XDG_STATE_HOME', str(root / '.local/state'))) if home is None else root / '.local/state'
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(root / '.config'))) if home is None else root / '.config'
    for path in [state / 'omarchy/current/theme/colors.toml', config / 'omarchy/current/theme/colors.toml']:
        try:
            data = tomllib.loads(path.read_text())
            palette = {'background': data['background'], 'foreground': data['foreground'],
                       'accent': data.get('accent', data.get('blue')), 'surface': data.get('lighter_background', data['background'])}
            if all(valid_colour(v) for v in palette.values()):
                return palette
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {}


def text_on(colour):
    rgb = [int(colour[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    lum = sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    return '#000000' if lum > 0.179 else '#ffffff'


def colour_css(palette):
    if not palette:
        return ''  # Genuine GTK theme fallback: no app colour overrides.
    if not all(valid_colour(palette.get(k)) for k in COLOUR_KEYS):
        raise ValueError('Use a six-digit hex colour such as #A855F7.')
    bg, surface, fg, accent = [palette[k] for k in COLOUR_KEYS]
    on_accent = text_on(accent)
    return f'''
@define-color theme_bg_color {bg};
@define-color theme_fg_color {fg};
@define-color theme_base_color {bg};
@define-color theme_text_color {fg};
@define-color theme_selected_bg_color {accent};
@define-color theme_selected_fg_color {on_accent};
@define-color accent_bg_color {accent};
@define-color accent_fg_color {on_accent};
@define-color accent_color {accent};
window, popover > contents {{ background-color: {bg}; color: {fg}; }}
headerbar, .sidebar, .card, .library-row {{ background: {surface}; color: {fg}; }}
button, dropdown > button {{ background: {surface}; color: {fg}; border-color: alpha({fg}, 0.18); }}
button:hover {{ background: mix({surface}, {fg}, 0.12); }}
button.suggested-action, list row:selected {{ background: {accent}; color: {on_accent}; }}
entry, textview, textview text {{ background: {bg}; color: {fg}; caret-color: {accent}; }}
list, scrolledwindow {{ background-color: transparent; }}
separator {{ background: alpha({fg}, 0.15); }}
.accent {{ color: {accent}; }}
selection {{ background: {accent}; color: {on_accent}; }}
'''


def resolved_palette(settings, system=None):
    system = read_palette() if system is None else system
    if settings.get('colour_mode', 'system') == 'system':
        return system
    return {**system, **settings.get('colours', {})}
