"""Production direction controls shared by new songs and existing songs."""
import copy

from core import PRODUCTION_OPTIONS, TEXT_LIMIT, drum_feel, production_direction, production_preview
from i18n import t


class ProductionMixin:
    def production_controls(self, container, value=None, track=None):
        from app import Gtk, label, dropdown, button, text_input, limit_text, text_of
        direction = production_direction(value)
        controls = {}
        container.append(label(t('Production presets'), 'heading'))
        presets = self.settings.get('production_presets', {})
        preset = dropdown([''] + list(presets), '', [t('Choose a preset')] + list(presets))
        container.append(preset)
        for key, title in [('density', 'Production'), ('dynamics', 'Dynamics'), ('vocals', 'Vocal delivery'), ('feel', 'Performance feel')]:
            container.append(label(t(title), 'heading'))
            options = PRODUCTION_OPTIONS[key]
            controls[key] = dropdown(list(options), direction[key], [t(v[0]) for v in options.values()])
            container.append(controls[key])
        container.append(label(t('Drum feel'), 'heading'))
        follow = Gtk.CheckButton(label=t('Follow style'), active=direction['drums'] is None)
        container.append(follow)
        drum_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        drum_scale.set_value(50 if direction['drums'] is None else direction['drums'])
        drum_scale.set_draw_value(False)
        drum_scale.set_hexpand(True)
        container.append(drum_scale)
        container.append(label(t('Machine-perfect → Sunday night in the pub'), 'caption'))
        drum_caption = label('', 'caption')
        container.append(drum_caption)
        container.append(label(t('Arrangement and delivery notes'), 'heading'))
        notes, wrap = text_input(direction['notes'], 100)
        container.append(wrap)
        limit_text(notes, container)
        def collect():
            return production_direction({**{key: text_of(widget) for key, widget in controls.items()},
                                         'notes': text_of(notes),
                                         'drums': None if follow.get_active() else round(drum_scale.get_value())})
        preset_name = Gtk.Entry(placeholder_text=t('Preset name'))
        container.append(preset_name)
        message = label('', 'caption')
        def save_preset():
            name = preset_name.get_text().strip()
            if not name:
                message.set_text(t('Enter a preset name.'))
                return
            try:
                settings = {**self.settings, 'production_presets': {**self.settings.get('production_presets', {}), name: collect()}}
                self.store.save_settings(settings)
                self.settings = settings
                preset.values = [''] + list(settings['production_presets'])
                preset.set_model(Gtk.StringList.new([t('Choose a preset')] + list(settings['production_presets'])))
                message.set_text(t('Preset saved.'))
            except Exception as exc:
                message.set_text(str(exc))
        container.append(button(t('Save production preset'), save_preset))
        container.append(message)
        container.append(label(t('Production preview'), 'heading'))
        container.append(label(t('These directions are added to the next draft. Locked fields are preserved.'), 'caption'))
        previews = {}
        for field, title in [('lyrics', 'Lyrics'), ('style_prompt', 'Style prompt'), ('exclusions', 'Exclusions')]:
            container.append(label(t(title), 'heading'))
            previews[field] = label('', 'caption')
            previews[field].set_selectable(True)
            container.append(previews[field])
        conflicts = label('', 'error')
        container.append(conflicts)
        def update(*_):
            drum_scale.set_sensitive(not follow.get_active())
            drum_caption.set_text(t('Follow style') if follow.get_active() else f'{round(drum_scale.get_value())} — {t(drum_feel(round(drum_scale.get_value()))[0])}')
            preview_track = {**(track or {}), 'production': collect()}
            preview = production_preview(preview_track, (preview_track.get('current') or {}).get('vocal_gender') == 'instrumental')
            for field, widget in previews.items():
                text = ('\n' if field == 'lyrics' else ', ').join(preview['cues'].get(field, []))
                count = f' ({len(text)} / {TEXT_LIMIT})' if field != 'lyrics' else ''
                widget.set_text((text or (t('Preserved') if field not in preview['cues'] else t('Follow style'))) + count)
            conflicts.set_text('\n'.join(t(message) for message in preview['conflicts']))
        def load_preset(*_):
            index = preset.get_selected()
            if index >= len(preset.values):
                return
            selected = preset.values[index]
            if not selected:
                return
            saved = production_direction(self.settings['production_presets'][selected])
            for key, widget in controls.items():
                widget.set_selected(widget.values.index(saved[key]))
            follow.set_active(saved['drums'] is None)
            drum_scale.set_value(50 if saved['drums'] is None else saved['drums'])
            notes.get_buffer().set_text(saved['notes'])
            preset_name.set_text(selected)
            update()
        preset.connect('notify::selected', load_preset)
        for widget in controls.values():
            widget.connect('notify::selected', update)
        drum_scale.connect('value-changed', update)
        follow.connect('toggled', update)
        notes.get_buffer().connect('changed', update)
        update()
        collect.widgets = {'follow_style': follow, 'drums': drum_scale, 'presets': preset, 'preset_name': preset_name}
        return collect

    def production_dialog(self):
        from app import label, button
        if self.busy or not self.flush():
            return
        window, container = self.dialog(t('Production direction'), 640, 700)
        track = self.project['tracks'][self.track_index]
        collect = self.production_controls(container, track.get('production'), track)
        error = label('', 'error')
        container.append(error)
        def save():
            try:
                candidate = copy.deepcopy(self.project)
                candidate['tracks'][self.track_index]['production'] = collect()
                self.store.save(candidate)
                self.project = candidate
                window.close()
                self.notify(t('Production direction saved for the next draft or rewrite.'))
            except Exception as exc:
                error.set_text(str(exc))
        window.production_controls = collect
        window.actions.append(button(t('Save'), save, True))
        window.actions.set_visible(True)
        window.present()
        return window
