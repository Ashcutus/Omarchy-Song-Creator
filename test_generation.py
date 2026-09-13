"""Regression coverage for revision boundaries and stalled transport."""
import copy
import io
import json
import threading
import time
import unittest
from unittest.mock import Mock

from core import (Cancelled, Ollama, compose_production, create_project,
                  generate_song, missing_production, production_preview)
from test_core import song


class GenerationRegressionTests(unittest.TestCase):
    def project(self):
        return create_project('Working title only', 'Folk', 1, 180, 240, None)

    def generate(self, project, output=None, **kwargs):
        client = Mock()
        client.generate.return_value = output or song('Revised')
        return generate_song(client, 'local', project, 0, 'Improve this', threading.Event(), **kwargs)

    def test_preserve_uses_current_manual_lyrics_on_rewrite(self):
        project = self.project()
        track = project['tracks'][0]
        track.update(lyrics_source='Original supplied words', lyrics_assist='preserve', current=song())
        track['current']['lyrics'] = '[Verse]\nManually improved wording'
        self.assertEqual(self.generate(project)['lyrics'], track['current']['lyrics'])

    def test_title_failure_reports_title_not_peer_repetition(self):
        output = song()
        output['lyrics'] = '[Chorus]\nWorking title only'
        with self.assertRaisesRegex(ValueError, 'working title'):
            self.generate(self.project(), output)

    def test_sound_scope_preserves_title_and_lyrics(self):
        project = self.project()
        project['tracks'][0]['current'] = song('Original')
        output = self.generate(project, scope='sound')
        self.assertEqual(output['title'], 'Original')
        self.assertEqual(output['lyrics'], project['tracks'][0]['current']['lyrics'])

    def test_section_scope_preserves_every_other_section(self):
        project = self.project()
        current = song()
        current['lyrics'] = '[Verse 1]\nOld line\n\n[Chorus]\nKeep this chorus\n'
        project['tracks'][0]['current'] = current
        proposed = song('Changed title')
        proposed['lyrics'] = '[Verse 1]\nNew line\n\n[Chorus]\nUnwanted chorus\n'
        output = self.generate(project, proposed, scope='section', section='[Verse 1]')
        self.assertEqual(output['lyrics'], '[Verse 1]\nNew line\n\n[Chorus]\nKeep this chorus\n')
        self.assertEqual(output['title'], current['title'])

    def test_section_scope_never_normalizes_locked_lyrics(self):
        project = self.project()
        original = song()
        original['lyrics'] = '[Verse 1]\nExact words\n\n\n'
        project['tracks'][0].update(current=original, locks=['lyrics'])
        output = self.generate(project, scope='section', section='[Verse 1]')
        self.assertEqual(output['lyrics'], original['lyrics'])

    def test_full_fields_make_room_for_production(self):
        track = {'production': {'density': 'stripped', 'vocals': 'intimate', 'drums': 100}}
        original = song()
        original['style_prompt'] = 'x' * 1000
        original['exclusions'] = 'y' * 1000
        output = compose_production(original, track)
        self.assertLessEqual(len(output['style_prompt']), 1000)
        self.assertLessEqual(len(output['exclusions']), 1000)
        self.assertEqual(missing_production(output, track), [])

    def test_changed_choices_remove_obsolete_managed_cues(self):
        original = compose_production(song(), {'production': {'density': 'full', 'drums': 0}})
        output = compose_production(original, {'production': {'density': 'stripped', 'drums': 100}})
        self.assertNotIn('full layered arrangement', output['style_prompt'])
        self.assertNotIn('grid-locked drums', output['style_prompt'])
        self.assertNotIn('[Full arrangement]', output['lyrics'])

    def test_trimming_keeps_cues_already_at_end(self):
        track = {'production': {'density': 'stripped', 'vocals': 'intimate'}}
        original = song()
        original['style_prompt'] = 'x' * 982 + 'sparse arrangement'
        output = compose_production(original, track)
        self.assertEqual(missing_production(output, track), [])

    def test_locks_preserve_fields_exactly(self):
        project = self.project()
        track = project['tracks'][0]
        track.update(current=song('Original'), locks=['lyrics', 'style_prompt'], production={'density': 'stripped'})
        output = self.generate(project)
        for field in track['locks']:
            self.assertEqual(output[field], track['current'][field])

    def test_preview_warns_and_qualifies_conflicting_timing(self):
        preview = production_preview({'production': {'feel': 'human', 'drums': 0}})
        self.assertTrue(preview['conflicts'])
        self.assertIn('other instruments: natural timing and phrasing', preview['cues']['style_prompt'])
        self.assertNotIn('hard quantization', preview['cues']['exclusions'])

    def test_follow_style_keeps_model_production_descriptions(self):
        original = song()
        original['style_prompt'] = 'sparse arrangement, natural lead vocal'
        original['lyrics'] = '[Sparse arrangement]\n[Verse]\nWords'
        self.assertEqual(compose_production(original, {}), original)

    def test_one_explicit_choice_keeps_unrelated_production(self):
        original = song()
        original['style_prompt'] = 'sparse arrangement, natural lead vocal'
        output = compose_production(original, {'production': {'drums': 100}})
        self.assertIn('sparse arrangement', output['style_prompt'])
        self.assertIn('natural lead vocal', output['style_prompt'])

    def test_conflict_composition_does_not_duplicate_qualified_cues(self):
        track = {'production': {'feel': 'human', 'drums': 0}}
        once = compose_production(song(), track)
        twice = compose_production(once, track)
        self.assertEqual(twice, once)


class TransportCancellationTests(unittest.TestCase):
    def test_cancels_while_stream_read_is_stalled(self):
        entered, release, cancel = threading.Event(), threading.Event(), threading.Event()
        class StalledStream:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def __iter__(self):
                entered.set()
                release.wait(2)
                return iter(())
        client = Ollama()
        client.request = lambda *args, **kwargs: StalledStream()
        def stop():
            entered.wait(1)
            cancel.set()
        stopper = threading.Thread(target=stop)
        stopper.start()
        start = time.monotonic()
        try:
            with self.assertRaises(Cancelled):
                client.generate('local', 'brief', cancel)
            self.assertLess(time.monotonic() - start, 1)
        finally:
            release.set()
            stopper.join()

    def test_cancels_while_connect_is_stalled(self):
        client = Ollama()
        entered, release, cancel = threading.Event(), threading.Event(), threading.Event()
        def stalled(*args, **kwargs):
            entered.set()
            release.wait(2)
            return io.BytesIO()
        client.request = stalled
        def stop():
            entered.wait(1)
            cancel.set()
        stopper = threading.Thread(target=stop)
        stopper.start()
        start = time.monotonic()
        try:
            with self.assertRaises(Cancelled):
                client.generate('local', 'brief', cancel)
            self.assertLess(time.monotonic() - start, 1)
        finally:
            release.set()
            stopper.join()

    def test_chunked_stream_keeps_unicode_and_final_output(self):
        client = Ollama()
        expected = song('Café')
        raw = json.dumps(expected, ensure_ascii=False)
        parts = [{'response': char} for char in raw]
        parts[-1]['done'] = True
        client.request = lambda *args, **kwargs: io.BytesIO(b'\n'.join(json.dumps(p).encode() for p in parts))
        progress = []
        self.assertEqual(client.generate('local', 'brief', threading.Event(), progress.append), expected)
        self.assertEqual(progress[-1], len(raw))
