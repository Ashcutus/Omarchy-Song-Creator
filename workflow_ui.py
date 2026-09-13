"""Revision review, library management and recovery dialogs."""
import copy
import json
from pathlib import Path
from gi.repository import Gtk
from core import FIELDS, LABELS
from i18n import t, set_language


class WorkflowMixin:
    def review_proposal(self, original, proposed, accept, discard, allow_unchanged=False):
        from app import box, label, button, text_input
        window, content = self.dialog(t('Review proposed changes'), 900, 750)
        content.append(label(t('Choose the changes to keep. Unchecked fields retain your saved version.')))
        choices = {}
        for field in FIELDS:
            if original[field] == proposed[field]:
                continue
            check = Gtk.CheckButton(label=t(LABELS[field]), active=True)
            choices[field] = check
            content.append(check)
            comparison = box(False, 16)
            comparison.set_homogeneous(True)
            for caption, value in [('Saved', original[field]), ('Proposed', proposed[field])]:
                column = box()
                column.append(label(t(caption), 'heading'))
                editor, wrap = text_input(str(value), 260 if field == 'lyrics' else 110)
                editor.set_editable(False)
                column.append(wrap)
                comparison.append(column)
            content.append(comparison)
        error = label('', 'error')
        content.append(error)
        resolved = [False]
        def save():
            if not allow_unchanged and not any(w.get_active() for w in choices.values()):
                error.set_text(t('Select at least one change, or discard this proposal.'))
                return
            merged = copy.deepcopy(original)
            for field, control in choices.items():
                if control.get_active():
                    merged[field] = proposed[field]
            merged['notes'] = proposed.get('notes', '')
            resolved[0] = True
            window.close()
            accept(merged)
        def closed(*_):
            if not resolved[0]:
                resolved[0] = True
                discard()
        window.connect('close-request', closed)
        window.actions.append(button(t('Accept selected changes'), save, True))
        window.actions.append(button(t('Discard proposal'), window.close))
        window.actions.set_visible(True)
        window.present()
        return window

    def manage_song_dialog(self):
        from app import button, label, text_input, text_of
        if self.busy or not self.flush():
            return
        track = self.project['tracks'][self.track_index]
        window, content = self.dialog(t('Song tools'), 600, 620)
        content.append(label(t('Suno result link')))
        link = Gtk.Entry(text=track.get('suno_url', ''), placeholder_text='https://suno.com/song/…')
        content.append(link)
        content.append(label(t('Listening notes — drums, vocals, arrangement and duration')))
        notes, wrap = text_input(track.get('listening_notes', ''), 180)
        content.append(wrap)
        error = label('', 'error')
        content.append(error)
        def save():
            try:
                candidate = copy.deepcopy(self.project)
                updated = candidate['tracks'][self.track_index]
                updated['suno_url'] = link.get_text().strip()
                updated['listening_notes'] = text_of(notes)
                updated['listening_version'] = len(track['versions'])
                self.store.save(candidate)
                self.project = candidate
                window.close()
            except Exception as exc:
                error.set_text(str(exc))
        def state(value):
            try:
                self.store.set_song_state(track['id'], value)
                window.close()
                self.editors = {}
                self.show_library()
            except Exception as exc:
                error.set_text(str(exc))
        def duplicate():
            try:
                project = self.store.duplicate_song(track['id'])
                window.close()
                self.load_project(project['id'])
            except Exception as exc:
                error.set_text(str(exc))
        content.append(button(t('Duplicate song'), duplicate))
        content.append(button(t('Restore to active songs'), lambda: state('active')))
        content.append(button(t('Archive song'), lambda: state('archive')))
        content.append(button(t('Move to trash'), lambda: state('trash')))
        window.actions.append(button(t('Save listening notes'), save, True))
        window.actions.set_visible(True)
        window.present()

    def recovery_controls(self, content):
        from app import button, label
        content.append(label(t('Backups and recovery'), 'heading'))
        status = label(t('Backups include your songs, history, collections and settings.'), 'caption')
        content.append(status)
        def backup():
            if self.busy or not self.flush():
                return
            try:
                status.set_text(t('Backup saved: {path}', path=self.store.backup()))
            except Exception as exc:
                status.set_text(str(exc))
        content.append(button(t('Create backup'), backup))
        def choose(restore=False):
            if self.busy or not self.flush():
                return
            picker = Gtk.FileChooserNative(title=t('Choose backup') if restore else t('Import history.json'), transient_for=self.settings_window, action=Gtk.FileChooserAction.OPEN)
            def response(dialog, code):
                if code == Gtk.ResponseType.ACCEPT:
                    try:
                        path = Path(dialog.get_file().get_path())
                        if restore:
                            confirm, body = self.dialog(t('Restore backup'), 560, 330)
                            body.append(label(t('Replace the current library with this backup? A safety backup of the current library will be kept.')))
                            restore_error = label('', 'error')
                            body.append(restore_error)
                            def perform():
                                try:
                                    self.store.restore_backup(path)
                                    self.settings = self.store.settings()
                                    set_language(self.settings.get('ui_language', 'system'))
                                    self.editors = {}
                                    self.project = None
                                    self.settings_window.close()
                                    self.refresh_projects()
                                    self.show_library()
                                    self.refresh_theme()
                                    confirm.close()
                                except Exception as exc:
                                    restore_error.set_text(str(exc))
                            confirm.actions.append(button(t('Restore backup'), perform, True))
                            confirm.actions.set_visible(True)
                            confirm.present()
                        else:
                            ids = self.store.import_history(json.loads(path.read_text()))
                            self.refresh_projects()
                            status.set_text(t('Imported {count} songs.', count=len(ids)))
                    except Exception as exc:
                        status.set_text(str(exc))
                dialog.destroy()
            picker.connect('response', response)
            picker.show()
        content.append(button(t('Import exported history'), choose))
        content.append(button(t('Restore backup…'), lambda: choose(True)))
