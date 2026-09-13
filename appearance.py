"""Read Omarchy's current palette; never write desktop theme configuration."""
from pathlib import Path
import os
import re
import tomllib

COLOUR_KEYS = ('background', 'surface', 'foreground', 'accent')
LAYOUT_CSS = '''
window { font-family: monospace; font-size: 13px; }
.title { font-size: 20px; font-weight: 700; }
.heading { font-size: 14px; font-weight: 700; }
.caption { opacity: 0.84; font-size: 12px; }
headerbar { min-height: 40px; padding: 4px 12px; box-shadow: none; }
.sidebar { padding: 12px; border-right: 1px solid alpha(currentColor, 0.15); }
.card { border-radius: 0; padding: 12px; border: 1px solid alpha(currentColor, 0.12); }
button { min-height: 24px; padding: 3px 10px; border-radius: 0; box-shadow: none; }
entry, spinbutton { min-height: 28px; border-radius: 0; }
entry { padding: 4px 8px; }
spinbutton button { min-height: 24px; }
.text-editor { border: 1px solid alpha(currentColor, 0.2); border-radius: 0; }
stackswitcher button { padding: 4px 18px; }
.library-row { padding: 12px; border-radius: 0; margin-bottom: 8px; }
.editor-title { font-size: 18px; font-weight: 700; }
popover > contents { border-radius: 0; }
.status-footer { border-top: 1px solid alpha(currentColor, 0.15); padding: 8px 12px; }
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
headerbar, .sidebar {{ background: {bg}; color: {fg}; }}
.card, .library-row {{ background: mix({bg}, {surface}, 0.55); color: {fg}; }}
headerbar {{ border-bottom: 1px solid alpha({accent}, 0.6); }}
window > box {{ border: 1px solid alpha({accent}, 0.55); }}
button, dropdown > button {{ background: transparent; color: {fg}; border: 1px solid alpha({fg}, 0.35); }}
button:hover {{ background: mix({bg}, {fg}, 0.08); border-color: {accent}; }}
button:disabled {{ opacity: 0.58; }}
button.suggested-action {{ background: alpha({accent}, 0.12); color: {accent}; border-color: {accent}; }}
button.suggested-action:hover {{ background: alpha({accent}, 0.22); }}
stackswitcher button:checked, list row:selected {{ background: alpha({accent}, 0.14); color: {accent}; }}
button:focus-visible, entry:focus-within, .text-editor:focus-within {{ outline: 1px solid {accent}; outline-offset: -1px; }}
entry, textview, textview text {{ background: {bg}; color: {fg}; caret-color: {accent}; }}
list, scrolledwindow {{ background-color: transparent; }}
separator {{ background: alpha({fg}, 0.15); }}
.accent {{ color: {accent}; }}
label.error, .error {{ color: {fg}; opacity: 1; font-weight: 700; }}
selection {{ background: {accent}; color: {on_accent}; }}
'''


def resolved_palette(settings, system=None):
    system = read_palette() if system is None else system
    if settings.get('colour_mode', 'system') == 'system':
        return system
    return {**system, **settings.get('colours', {})}
