#!/usr/bin/env python3
"""Native GTK 4 songwriting workspace for Omarchy."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib
from core import (FIELDS, LABELS, VARIETIES, VOCALS, Store, Ollama, Cancelled, create_project,
                  commit_version, restore_version, prompt_for, generate_song, track_status, song_text, export_text)

APP_ID = 'io.versework.Studio'
DATA = Path(os.environ.get('VERSEWORK_DATA', str(Path.home() / '.local/share/versework/data')))
CSS = b'''
window { background: #171b20; color: #e6e5df; }
headerbar { background: #20262c; border-bottom: 1px solid #343c43; }
.sidebar { background: #11161b; padding: 16px; }
.title { font-size: 28px; font-weight: 700; }
.heading { font-size: 17px; font-weight: 700; }
.caption { color: #a9b4bd; font-size: 12px; }
.accent { color: #a9d8ca; }
.card { background: #20262c; border-radius: 12px; padding: 18px; }
button { background: #2b343c; color: #e6e5df; border: 1px solid #424c54; border-radius: 8px; padding: 8px 12px; }
button:hover { background: #37434c; }
button.suggested-action { background: #a9d8ca; color: #102c25; font-weight: 700; }
entry, textview, textview text { background: #141a20; color: #e6e5df; }
entry { padding: 7px; border-radius: 7px; }
textview { padding: 10px; border-radius: 8px; }
textview text { line-height: 1.4; }
list { background: transparent; }
list row { padding: 9px; border-radius: 8px; margin-bottom: 4px; }
list row:selected { background: #2e4843; }
separator { background: #333c44; }
.error { color: #ffb4a9; }
.success { color: #a9d8ca; }
'''


def box(vertical=True, spacing=10):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)


def label(text, css=None):
    w = Gtk.Label(label=text, xalign=0, wrap=True)
    if css:
        w.add_css_class(css)
    return w


def button(text, callback, primary=False):
    w = Gtk.Button(label=text)
    w.connect('clicked', lambda *_: callback())
    if primary:
        w.add_css_class('suggested-action')
    return w


def margins(widget, amount=20):
    for side in ('top', 'bottom', 'start', 'end'):
        getattr(widget, 'set_margin_' + side)(amount)
    return widget


def scrolled(child, height=None):
    w = Gtk.ScrolledWindow(hexpand=True, vexpand=height is None)
    w.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    w.set_child(child)
    if height:
        w.set_min_content_height(height)
    return w


def text_input(text='', height=120):
    w = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
    w.get_buffer().set_text(text)
    return w, scrolled(w, height)


def text_of(widget):
    if isinstance(widget, Gtk.TextView):
        b = widget.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter(), True)
    if isinstance(widget, Gtk.SpinButton):
        return widget.get_value_as_int()
    if isinstance(widget, Gtk.DropDown):
        item = widget.get_selected_item()
        return item.get_string() if item else ''
    return widget.get_text()


def spin(value, low, high, step=1):
    w = Gtk.SpinButton.new_with_range(low, high, step)
    w.set_value(value)
    return w


class Studio(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE if '--smoke' in sys.argv else Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.store = Store(DATA)
        self.settings = self.store.settings()
        self.ollama = Ollama()
        self.project = None
        self.track_index = None
        self.editors = {}
        self.lockers = {}
        self.feedback_editor = None
        self.busy = False
        self.cancel_event = threading.Event()
        self.connect('activate', self.activate)

    def activate(self, *_):
        if hasattr(self, 'win'):
            self.win.present()
            return
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme', True)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win = Gtk.ApplicationWindow(application=self, title='Versework')
        self.win.set_default_size(1280, 900)
        self.win.connect('close-request', self.close)
        header = Gtk.HeaderBar()
        header.set_title_widget(label('VERSEWORK  /  LOCAL SONG STUDIO', 'heading'))
        header.pack_start(button('New project', self.new_dialog, True))
        header.pack_end(button('Settings', self.settings_dialog))
        self.win.set_titlebar(header)
        root = box()
        root.set_spacing(0)
        self.win.set_child(root)
        body = box(False, 0)
        body.set_vexpand(True)
        root.append(body)
        self.sidebar = box()
        self.sidebar.add_css_class('sidebar')
        self.sidebar.set_size_request(225, -1)
        self.sidebar.append(label('YOUR PROJECTS', 'caption'))
        self.projects_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.sidebar.append(scrolled(self.projects_list))
        self.sidebar.append(label('Private by design\nWrites with local Ollama.\nCopy finished drafts to Suno.', 'caption'))
        body.append(self.sidebar)
        self.content = box()
        self.content.set_hexpand(True)
        body.append(self.content)
        footer = box(False)
        margins(footer, 12)
        self.spinner = Gtk.Spinner()
        footer.append(self.spinner)
        self.status = label('Ready · all projects are saved on this computer', 'caption')
        self.status.set_hexpand(True)
        footer.append(self.status)
        self.stop_button = button('Stop writing', self.stop)
        self.stop_button.set_visible(False)
        footer.append(self.stop_button)
        root.append(footer)
        self.refresh_projects()
        self.welcome()
        self.win.present()
        if '--smoke' in sys.argv:
            GLib.timeout_add(400, self.smoke)

    def notify(self, text, error=False):
        self.status.set_text(text)
        self.status.remove_css_class('error')
        if error:
            self.status.add_css_class('error')

    def clear(self, container):
        while container.get_first_child():
            container.remove(container.get_first_child())

    def refresh_projects(self):
        self.clear(self.projects_list)
        for p in self.store.list():
            title = p['name']
            approved = sum(t['approved'] for t in p['tracks'])
            item = box(spacing=4)
            item.append(label(title, 'heading'))
            item.append(label(f"{p['count']} tracks · {approved} approved", 'caption'))
            b = Gtk.Button(child=item)
            b.connect('clicked', lambda _, ident=p['id']: self.load_project(ident))
            self.projects_list.append(b)

    def welcome(self):
        self.clear(self.content)
        c = margins(box(spacing=20), 42)
        c.set_valign(Gtk.Align.CENTER)
        self.content.append(c)
        c.append(label('From a sound in your head\nto a collection of songs.', 'title'))
        c.append(label('Build an EP, shape each song, and keep every version.', 'heading'))
        for n, title, desc in [('01', 'Set the direction', 'Choose a sound, song count, duration range and rewrite limit.'),
                                ('02', 'Write and review', 'Ollama drafts lyrics and all eight Suno fields. Give feedback and lock fields you love.'),
                                ('03', 'Make it yours', 'Approve your favourites, copy them into Suno, and bring listening notes back here.')]:
            row = box(False, 16)
            row.add_css_class('card')
            row.append(label(n, 'accent'))
            col = box(spacing=5)
            col.append(label(title, 'heading'))
            col.append(label(desc, 'caption'))
            row.append(col)
            c.append(row)
        c.append(button('Create your first project', self.new_dialog, True))
        c.append(button('Set up local writing', self.settings_dialog))

    def load_project(self, ident):
        if self.busy:
            self.notify('Finish or stop writing before switching projects.')
            return
        if not self.flush():
            return
        self.project = next(p for p in self.store.list() if p['id'] == ident)
        self.track_index = None
        self.render_project()

    def render_project(self):
        self.editors, self.lockers, self.feedback_editor = {}, {}, None
        self.clear(self.content)
        outer = margins(box(spacing=16), 24)
        self.content.append(outer)
        top = box(False)
        titles = box(spacing=4)
        titles.set_hexpand(True)
        titles.append(label(self.project['name'], 'title'))
        p = self.project
        titles.append(label(f"{p['count']} songs · {p['minimum']}–{p['maximum']} sec · {p['limit']} rewrites per song", 'caption'))
        top.append(titles)
        top.append(button('Export EP', self.export_dialog))
        outer.append(top)
        brief = label(p['style'], 'caption')
        brief.set_max_width_chars(100)
        brief.set_lines(3)
        outer.append(brief)
        actions = box(False)
        self.generate_button = button('Write remaining drafts', self.generate_missing, True)
        actions.append(self.generate_button)
        actions.append(button('Feedback for EP', self.ep_feedback))
        outer.append(actions)
        lower = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, wide_handle=True)
        lower.set_vexpand(True)
        lower.set_position(245)
        outer.append(lower)
        self.track_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.track_list.connect('row-selected', self.select_track)
        left = scrolled(self.track_list)
        left.set_size_request(225, -1)
        lower.set_start_child(left)
        self.editor_holder = box()
        self.editor_holder.set_hexpand(True)
        lower.set_end_child(scrolled(self.editor_holder))
        self.refresh_tracks()
        i = self.track_index if self.track_index is not None else 0
        self.track_list.select_row(self.track_list.get_row_at_index(i))

    def refresh_tracks(self):
        self.rebuilding = True
        self.clear(self.track_list)
        for t in self.project['tracks']:
            b = box(spacing=5)
            b.append(label(f"{t['number']:02d}   {t['current']['title'] if t['current'] else 'Untitled track'}", 'heading'))
            b.append(label(track_status(self.project, t), 'caption'))
            b.append(label(f"Rewrites {t['rewrites']} / {self.project['limit']}", 'caption'))
            self.track_list.append(b)
        self.rebuilding = False

    def select_track(self, _, row):
        if getattr(self, 'rebuilding', False) or row is None:
            return
        if not self.flush():
            return
        self.track_index = row.get_index()
        self.render_track()

    def render_track(self):
        self.clear(self.editor_holder)
        self.editors, self.lockers, self.feedback_editor = {}, {}, None
        c = margins(box(spacing=16), 16)
        self.editor_holder.append(c)
        track = self.project['tracks'][self.track_index]
        if not track['current']:
            c.append(label(f"Track {track['number']:02d}", 'title'))
            c.append(label('A new chapter, waiting to be written.', 'heading'))
            c.append(label('Your local model will use the project brief and the other tracks to create a distinct song.', 'caption'))
            c.append(button('Write this song', lambda: self.start_jobs([self.track_index]), True))
            return
        song = track['current']
        title_row = box(False)
        title_row.append(label(track_status(self.project, track), 'accent'))
        title_row.append(button('Reopen' if track['approved'] else 'Approve song', self.approve, not track['approved']))
        title_row.append(button('Versions', self.history_dialog))
        title_row.append(button('Copy all', lambda: self.copy_current()))
        c.append(title_row)
        c.append(label('Lock a field to keep it exactly as written during AI revisions.', 'caption'))
        for field in FIELDS:
            field_box = box(spacing=6)
            heading = box(False)
            l = label(LABELS[field], 'heading')
            l.set_hexpand(True)
            heading.append(l)
            lock = Gtk.CheckButton(label='Lock')
            lock.set_active(field in track['locks'])
            lock.set_sensitive(not track['approved'] and not self.busy)
            self.lockers[field] = lock
            heading.append(lock)
            heading.append(button('Copy', lambda f=field: self.copy_field(f)))
            field_box.append(heading)
            if field in ['lyrics', 'style_prompt', 'exclusions']:
                w, wrap = text_input(song[field], 310 if field == 'lyrics' else 92)
                w.set_editable(not track['approved'] and not self.busy)
                field_box.append(wrap)
            elif field in ['weirdness', 'style_influence']:
                w = spin(song[field], 0, 100)
                field_box.append(w)
            elif field in ['variety', 'vocal_gender']:
                choices = VARIETIES if field == 'variety' else VOCALS
                w = Gtk.DropDown.new_from_strings(choices)
                w.set_selected(choices.index(song[field]))
                field_box.append(w)
            else:
                w = Gtk.Entry(text=song[field])
                field_box.append(w)
            w.set_sensitive(not track['approved'] and not self.busy)
            self.editors[field] = w
            c.append(field_box)
        c.append(button('Save edits', self.save_edits))
        if song.get('notes'):
            c.append(label(song['notes'], 'caption'))
        c.append(Gtk.Separator())
        c.append(label('Review & rewrite', 'heading'))
        c.append(label('Describe what to change. You can also paste listening notes after trying the song in Suno.', 'caption'))
        self.feedback_editor, wrap = text_input(track.get('feedback', ''), 110)
        self.feedback_editor.set_sensitive(not self.busy and not track['approved'])
        c.append(wrap)
        r = button(f"Rewrite song · {track['rewrites']}/{self.project['limit']} used", self.rewrite, True)
        r.set_sensitive(not self.busy and not track['approved'] and track['rewrites'] < self.project['limit'])
        c.append(r)
        c.append(label('Duration is an arrangement target. Actual audio length is determined in Suno.', 'caption'))

    def flush(self):
        if not self.project or self.track_index is None or not self.editors:
            return True
        try:
            candidate = copy.deepcopy(self.project)
            t = candidate['tracks'][self.track_index]
            if not t['approved']:
                song = {k: text_of(w) for k, w in self.editors.items()}
                song['notes'] = t['current'].get('notes', '')
                if song != t['current']:
                    commit_version(candidate, self.track_index, song, 'edit')
                t['locks'] = [k for k, w in self.lockers.items() if w.get_active()]
                if self.feedback_editor:
                    t['feedback'] = text_of(self.feedback_editor)
                self.store.save(candidate)
                self.project = candidate
            return True
        except Exception as e:
            self.notify(str(e), True)
            return False

    def save_edits(self):
        if self.flush():
            self.refresh_projects()
            self.render_project()
            self.notify('Edits saved. Manual edits do not use an AI rewrite.')

    def copy_field(self, field):
        self.copy(str(text_of(self.editors[field])))

    def copy_current(self):
        if self.flush():
            self.copy(song_text(self.project['tracks'][self.track_index]['current']))

    def copy(self, value):
        self.win.get_clipboard().set(value)
        self.notify('Copied to clipboard.')

    def dialog(self, title, width=650, height=640):
        w = Gtk.Window(title=title, transient_for=self.win, modal=True)
        w.set_default_size(width, height)
        child = margins(box(spacing=14), 24)
        w.set_child(scrolled(child))
        return w, child

    def new_dialog(self):
        if self.busy:
            self.notify('Finish or stop writing before starting another project.')
            return
        w, c = self.dialog('New project')
        c.append(label('What does this record sound like?', 'title'))
        entries = {}
        for key, title, value in [('name', 'Project name', ''), ('language', 'Lyric language', 'English')]:
            c.append(label(title, 'heading'))
            entries[key] = Gtk.Entry(text=value)
            c.append(entries[key])
        c.append(label('Style prompt', 'heading'))
        style, wrap = text_input('', 130)
        c.append(wrap)
        c.append(label('Theme / lyrical direction (optional)', 'heading'))
        theme, wrap = text_input('', 85)
        c.append(wrap)
        count, minimum, maximum, limit = spin(4, 1, 20), spin(180, 30, 1200, 15), spin(240, 30, 1200, 15), spin(3, 0, 20)
        for title, inp in [('Songs', count), ('Minimum length (seconds)', minimum), ('Maximum length (seconds)', maximum), ('AI rewrites per song', limit)]:
            r = box(False)
            l = label(title)
            l.set_hexpand(True)
            r.append(l)
            r.append(inp)
            c.append(r)
        err = label('', 'error')
        c.append(err)
        def save():
            try:
                p = create_project(text_of(entries['name']), text_of(style), text_of(count), text_of(minimum), text_of(maximum), text_of(limit), text_of(theme), text_of(entries['language']))
                if not self.flush():
                    raise ValueError('Save or correct the current song first.')
                self.store.save(p)
                self.project, self.track_index = p, None
                self.refresh_projects()
                self.render_project()
                w.destroy()
            except Exception as e:
                err.set_text(str(e))
        c.append(button('Create project', save, True))
        w.present()

    def settings_dialog(self):
        w, c = self.dialog('Local writing settings', 630, 570)
        c.append(label('Your writing engine', 'title'))
        c.append(label('Versework connects only to Ollama on this computer (127.0.0.1:11434). It does not use a cloud API.', 'caption'))
        c.append(label('Local model', 'heading'))
        model = Gtk.Entry(text=self.settings.get('model', 'qwen3:8b'))
        c.append(model)
        c.append(label('Choose an installed model below, or enter its exact name. Qwen3 8B is the starter model in the setup script.', 'caption'))
        listing = Gtk.DropDown.new_from_strings([])
        c.append(listing)
        listing.connect('notify::selected', lambda *_: model.set_text(text_of(listing)) if text_of(listing) else None)
        status = label('Click Check connection to discover installed local models.', 'caption')
        c.append(status)
        def check():
            status.set_text('Checking local Ollama…')
            def worker():
                try:
                    names = self.ollama.models()
                    def done():
                        listing.set_model(Gtk.StringList.new(names))
                        if model.get_text() in names:
                            listing.set_selected(names.index(model.get_text()))
                        status.set_text('Connected · ' + ', '.join(names) if names else 'Connected, but no local models are installed. Run the setup script to download one.')
                    GLib.idle_add(done)
                except Exception as e:
                    GLib.idle_add(status.set_text, str(e))
            threading.Thread(target=worker, daemon=True).start()
        c.append(button('Check connection', check))
        def start():
            exe = shutil.which('ollama')
            if not exe:
                status.set_text('Ollama is not installed. Run setup-ollama.sh from the app folder; it installs the Arch packages and downloads the starter model.')
                return
            env = os.environ.copy()
            env.update(OLLAMA_HOST='127.0.0.1:11434', OLLAMA_NO_CLOUD='1', OLLAMA_VULKAN='1')
            log_path = DATA / 'ollama.log'
            with log_path.open('ab') as log:
                subprocess.Popen([exe, 'serve'], env=env, stdout=log, stderr=log, start_new_session=True)
            status.set_text('Ollama start requested. Click Check connection in a moment.')
        c.append(button('Start Ollama', start))
        def save():
            name = model.get_text().strip()
            if not name or 'cloud' in name.lower():
                status.set_text('Enter the name of a local model, not a cloud model.')
                return
            self.settings = {'model': name}
            self.store.save_settings(self.settings)
            self.notify(f'Writing model saved: {name}')
            w.destroy()
        c.append(button('Save settings', save, True))
        c.append(label('Projects and version history: ' + str(DATA), 'caption'))
        w.present()

    def approve(self):
        if self.busy or not self.flush():
            return
        p = copy.deepcopy(self.project)
        t = p['tracks'][self.track_index]
        t['approved'] = not t['approved']
        self.store.save(p)
        self.project = p
        self.refresh_projects()
        self.render_project()
        self.notify('Approval saved.' if t['approved'] else 'Song reopened. Its rewrite counter is unchanged.')

    def generate_missing(self):
        if self.flush():
            self.start_jobs([i for i, t in enumerate(self.project['tracks']) if not t['current']])

    def rewrite(self):
        if not self.flush():
            return
        feedback = self.project['tracks'][self.track_index]['feedback'].strip()
        if not feedback:
            self.notify('Add feedback describing what you want changed.', True)
            return
        self.start_jobs([self.track_index], feedback)

    def ep_feedback(self):
        if self.busy or not self.flush():
            return
        w, c = self.dialog('Feedback for EP', 620, 570)
        c.append(label('Shape the collection', 'title'))
        feedback, wrap = text_input('', 140)
        c.append(wrap)
        c.append(label('Apply to these tracks. Approved songs and songs at their limit are protected.', 'caption'))
        choices = []
        for i, t in enumerate(self.project['tracks']):
            if t['current'] and not t['approved'] and t['rewrites'] < self.project['limit']:
                cb = Gtk.CheckButton(label=f"{i + 1:02d}. {t['current']['title']}", active=True)
                c.append(cb)
                choices.append((i, cb))
        err = label('', 'error')
        c.append(err)
        def run():
            indices = [i for i, cb in choices if cb.get_active()]
            if not text_of(feedback).strip() or not indices:
                err.set_text('Enter feedback and select at least one eligible song.')
                return
            w.destroy()
            self.start_jobs(indices, text_of(feedback))
        c.append(button('Rewrite selected tracks', run, True))
        w.present()

    def start_jobs(self, indices, feedback=''):
        if self.busy or not self.flush():
            return
        if not indices:
            self.notify('All initial drafts are written. Review a track to request changes.')
            return
        self.busy = True
        self.cancel_event = threading.Event()
        self.spinner.start()
        self.stop_button.set_visible(True)
        self.content.set_sensitive(False)
        self.sidebar.set_sensitive(False)
        model = self.settings['model']
        self.notify(f'Connecting to {model}…')
        jobs = list(indices)
        def next_job():
            if self.cancel_event.is_set():
                self.finish('Writing stopped. Completed drafts are saved.')
                return
            if not jobs:
                self.finish('Drafts saved. Ready for your review.')
                return
            index = jobs.pop(0)
            snap = copy.deepcopy(self.project)
            kind = 'rewrite' if snap['tracks'][index]['current'] else 'initial'
            if kind == 'rewrite' and (snap['tracks'][index]['approved'] or snap['tracks'][index]['rewrites'] >= snap['limit']):
                self.finish('A selected track is no longer eligible for rewriting.', True)
                return
            self.notify(f'Writing track {index + 1}/{snap["count"]} with {model}… First load can take a while.')
            def worker():
                try:
                    if model not in self.ollama.models():
                        raise ValueError(f'{model} is not installed locally. Open Settings or run setup-ollama.sh.')
                    last_update = [0.0]
                    def progress(size):
                        if time.monotonic() - last_update[0] > 1:
                            last_update[0] = time.monotonic()
                            GLib.idle_add(self.notify, f'Writing track {index + 1}/{snap["count"]} · {size:,} characters received…')
                    data = generate_song(self.ollama, model, snap, index, feedback, self.cancel_event, progress)
                    GLib.idle_add(accept, index, kind, data)
                except Cancelled:
                    GLib.idle_add(self.finish, 'Writing stopped. Completed drafts are saved.')
                except Exception as e:
                    GLib.idle_add(self.finish, str(e), True)
            threading.Thread(target=worker, daemon=True).start()
        def accept(index, kind, data):
            if self.cancel_event.is_set():
                self.finish('Writing stopped. No rewrite charged for the cancelled draft.')
                return
            try:
                candidate = copy.deepcopy(self.project)
                commit_version(candidate, index, data, kind, feedback, model)
                if feedback:
                    candidate['tracks'][index]['feedback'] = feedback
                self.store.save(candidate)
                self.project = candidate
                self.track_index = index
                self.refresh_projects()
            except Exception as e:
                self.finish(str(e), True)
                return
            next_job()
        next_job()

    def finish(self, message, error=False):
        self.busy = False
        self.spinner.stop()
        self.stop_button.set_visible(False)
        self.content.set_sensitive(True)
        self.sidebar.set_sensitive(True)
        self.editors = {}
        self.render_project()
        self.notify(message, error)

    def stop(self):
        self.cancel_event.set()
        self.notify('Stopping at the next response from Ollama. Completed drafts stay saved.')

    def history_dialog(self):
        if not self.flush():
            return
        w, c = self.dialog('Version history', 720, 720)
        t = self.project['tracks'][self.track_index]
        c.append(label('Every draft, kept.', 'title'))
        c.append(label('Restoring preserves history and never resets the rewrite counter.', 'caption'))
        choices = [f"Version {i+1} · {v['kind']} · {v['at']}" for i, v in enumerate(t['versions'])]
        pick = Gtk.DropDown.new_from_strings(choices)
        pick.set_selected(len(choices) - 1)
        c.append(pick)
        preview, wrap = text_input('', 380)
        preview.set_editable(False)
        c.append(wrap)
        note = label('', 'caption')
        c.append(note)
        def changed(*_):
            v = t['versions'][pick.get_selected()]
            preview.get_buffer().set_text(song_text(v['song']))
            note.set_text(v.get('feedback', '') or v['song'].get('notes', ''))
        pick.connect('notify::selected', changed)
        changed()
        def restore():
            try:
                p = copy.deepcopy(self.project)
                restore_version(p, self.track_index, pick.get_selected())
                self.store.save(p)
                self.project = p
                self.editors = {}
                self.render_project()
                w.destroy()
                self.notify('Version restored. Rewrite counter unchanged.')
            except Exception as e:
                note.set_text(str(e))
        b = button('Restore selected version', restore, True)
        b.set_sensitive(not t['approved'] and not self.busy)
        c.append(b)
        w.present()

    def export_dialog(self):
        if not self.flush():
            return
        w, c = self.dialog('Export project', 680, 650)
        c.append(label('Take your songs with you', 'title'))
        preview, wrap = text_input(export_text(self.project), 400)
        preview.set_editable(False)
        c.append(wrap)
        c.append(button('Copy EP text', lambda: self.copy(export_text(self.project))))
        def save():
            picker = Gtk.FileChooserNative(title='Choose export folder', transient_for=w,
                action=Gtk.FileChooserAction.SELECT_FOLDER, accept_label='Export here', cancel_label='Cancel')
            def response(dialog, code):
                if code == Gtk.ResponseType.ACCEPT:
                    try:
                        folder = Path(dialog.get_file().get_path()) / ('Versework-' + self.project['id'][:8] + '-' + str(time.time_ns()))
                        folder.mkdir()
                        (folder / 'songs.md').write_text(export_text(self.project))
                        (folder / 'project.json').write_text(json.dumps(self.project, ensure_ascii=False, indent=2))
                        self.notify('Exported lyrics, settings and full version history to ' + str(folder))
                        w.destroy()
                    except Exception as e:
                        self.notify('Export failed: ' + str(e), True)
                dialog.destroy()
            picker.connect('response', response)
            picker.show()
        c.append(button('Save text + project backup', save, True))
        w.present()

    def close(self, *_):
        if self.busy:
            self.cancel_event.set()
            return False
        if not self.flush():
            return True
        self.cancel_event.set()
        return False

    def smoke(self):
        try:
            p = create_project('After the streetlights', 'Warm analogue synths, understated indie pop, intimate vocals and late-night city imagery.', 4, 180, 240, 3)
            song = {'title': 'Last Train Home', 'lyrics': '[Verse 1]\nYour coffee rings the timetable\nA small moon on the page\nWe leave the platform quietly\nAnd let the morning wait\n\n[Chorus]\nKeep one light on for me\nPast the end of the line\nThere is still a place to be\nWhere your window meets mine', 'style_prompt': 'Intimate indie synth-pop, 92 BPM, warm analogue pads, soft drum machine, rounded bass, close-miked female vocals, restrained verses opening into a luminous chorus.', 'exclusions': 'harsh distortion, stadium drums, vocal chops', 'vocal_gender': 'female', 'weirdness': 35, 'style_influence': 75, 'variety': 'normal', 'notes': 'Test fixture for interface verification. Not model-generated.'}
            commit_version(p, 0, song, 'initial')
            self.store.save(p)
            self.project = p
            self.render_project()
            self.copy_field('title')
            self.flush()
            self.approve()
            self.approve()
            print('GTK_SMOKE_OK', flush=True)
            GLib.timeout_add(500, self.capture_smoke)
        except Exception:
            import traceback
            traceback.print_exc()
            self.quit()
        return False

    def capture_smoke(self):
        try:
            gi.require_version('Graphene', '1.0')
            from gi.repository import Graphene
            paintable = Gtk.WidgetPaintable.new(self.win)
            snapshot = Gtk.Snapshot.new()
            paintable.snapshot(snapshot, self.win.get_width(), self.win.get_height())
            node = snapshot.to_node()
            rect = Graphene.Rect()
            rect.init(0, 0, self.win.get_width(), self.win.get_height())
            texture = self.win.get_renderer().render_texture(node, rect)
            texture.save_to_png(str(DATA / 'preview.png'))
            print('GTK_RENDER_OK', flush=True)
        except Exception as e:
            print('GTK_RENDER_ERROR', str(e), flush=True)
        self.quit()
        return False


if __name__ == '__main__':
    app = Studio()
    app.run([sys.argv[0]])
