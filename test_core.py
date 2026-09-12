import copy
import io
import json
import tempfile
import threading
import unittest
from core import *


def song(title='Paper Moons'):
    return {'title': title, 'lyrics': '[Verse]\nA paper moon above the door\n[Chorus]\nLeave a little light for me', 'style_prompt': 'Quiet folk, brushed drums, warm guitar', 'exclusions': 'distortion', 'vocal_gender': 'female', 'weirdness': 25, 'style_influence': 80, 'variety': 'normal', 'notes': ''}


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.p = create_project('Test EP', 'Dream pop', 4, 180, 240, 1)
    def test_initial_does_not_use_rewrite_and_limit_enforced(self):
        commit_version(self.p, 0, song(), 'initial')
        self.assertEqual(self.p['tracks'][0]['rewrites'], 0)
        commit_version(self.p, 0, song('Second'), 'rewrite', 'Darker')
        with self.assertRaises(ValueError):
            commit_version(self.p, 0, song('Third'), 'rewrite')
        self.assertEqual(self.p['tracks'][0]['current']['title'], 'Second')
    def test_locked_fields_survive_rewrite(self):
        commit_version(self.p, 0, song(), 'initial')
        self.p['tracks'][0]['locks'] = ['lyrics', 'title']
        revision = song('New name')
        revision.update(lyrics='Changed', style_prompt='New sound')
        commit_version(self.p, 0, revision, 'rewrite')
        self.assertEqual(self.p['tracks'][0]['current']['lyrics'], song()['lyrics'])
        self.assertEqual(self.p['tracks'][0]['current']['title'], song()['title'])
        self.assertEqual(self.p['tracks'][0]['current']['style_prompt'], 'New sound')
    def test_approved_tracks_are_immutable(self):
        commit_version(self.p, 0, song(), 'initial')
        self.p['tracks'][0]['approved'] = True
        for kind in ['rewrite', 'edit']:
            with self.assertRaises(ValueError):
                commit_version(self.p, 0, song('Changed'), kind)
        with self.assertRaises(ValueError):
            restore_version(self.p, 0, 0)
    def test_restore_preserves_count_and_old_version(self):
        commit_version(self.p, 0, song(), 'initial')
        commit_version(self.p, 0, song('Second'), 'rewrite')
        restore_version(self.p, 0, 0)
        t = self.p['tracks'][0]
        self.assertEqual(t['rewrites'], 1)
        self.assertEqual(len(t['versions']), 3)
        self.assertEqual(t['versions'][1]['song']['title'], 'Second')
        self.assertEqual(t['current']['title'], song()['title'])
    def test_invalid_output_does_not_consume_rewrite(self):
        commit_version(self.p, 0, song(), 'initial')
        bad = song()
        bad['weirdness'] = 101
        previous = copy.deepcopy(self.p)
        with self.assertRaises(ValueError):
            commit_version(self.p, 0, bad, 'rewrite')
        self.assertEqual(previous, self.p)
    def test_no_op_revision_does_not_use_allowance(self):
        commit_version(self.p, 0, song(), 'initial')
        revised = song()
        revised['notes'] = 'Changed the chorus'
        with self.assertRaisesRegex(ValueError, 'did not change'):
            commit_version(self.p, 0, revised, 'rewrite')
        self.assertEqual(self.p['tracks'][0]['rewrites'], 0)
        self.assertEqual(len(self.p['tracks'][0]['versions']), 1)

    def test_zero_rewrites_can_still_approve(self):
        self.p['limit'] = 0
        commit_version(self.p, 0, song(), 'initial')
        self.assertIn('Limit reached', track_status(self.p, self.p['tracks'][0]))
        self.p['tracks'][0]['approved'] = True
        self.assertEqual(track_status(self.p, self.p['tracks'][0]), 'Approved')
    def test_partial_ep_persists_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            commit_version(self.p, 0, song(), 'initial')
            store.save(self.p)
            store.db.close()
            second = Store(tmp)
            restored = second.list()[0]
            self.assertEqual(restored, self.p)
            self.assertEqual(sum(t['current'] is None for t in restored['tracks']), 3)
            second.db.close()
    def add_collection_context(self):
        self.p['_collection_context'] = {'name': 'Test', 'kind': 'collection', 'theme': 'Shared', 'position': 1, 'total': 4,
            'other_songs': [{'title': t['current']['title'], 'do_not_repeat_these_lyrics': t['current']['lyrics']} for t in self.p['tracks'] if t['current']]}

    def test_revision_prompt_includes_context_feedback_locks(self):
        commit_version(self.p, 0, song(), 'initial')
        commit_version(self.p, 1, song('Neighbour'), 'initial')
        self.add_collection_context()
        self.p['tracks'][0]['locks'] = ['lyrics']
        prompt = prompt_for(self.p, 0, 'More hopeful')
        for text in ['Neighbour', 'More hopeful', 'locked_fields', 'target_seconds', '180', 'track_role', 'do_not_repeat_these_lyrics']:
            self.assertIn(text, prompt)
    def test_export_labels_approval_honestly(self):
        commit_version(self.p, 0, song(), 'initial')
        result = export_text(self.p)
        self.assertIn('Ready for review', result)
        self.assertIn('Not drafted', result)
        for field in LABELS.values():
            self.assertIn(field, result)
    def test_duplicate_draft_gets_one_retry(self):
        commit_version(self.p, 0, song(), 'initial')
        self.add_collection_context()
        unique = song('A new song')
        unique['lyrics'] = 'I count the windows on the hill\nYour boots are drying by the door'
        class Fake:
            calls = 0
            def generate(inner, *args):
                inner.calls += 1
                return song() if inner.calls == 1 else unique
        fake = Fake()
        self.assertEqual(generate_song(fake, 'test', self.p, 1, '', threading.Event()), unique)
        self.assertEqual(fake.calls, 2)

    def test_repeated_duplicate_draft_is_rejected(self):
        commit_version(self.p, 0, song(), 'initial')
        self.add_collection_context()
        class Fake:
            calls = 0
            def generate(inner, *args):
                inner.calls += 1
                return song()
        fake = Fake()
        with self.assertRaisesRegex(ValueError, 'repeating lyrics'):
            generate_song(fake, 'test', self.p, 1, '', threading.Event())
        self.assertEqual(fake.calls, 2)
        self.assertIsNone(self.p['tracks'][1]['current'])

    def test_invalid_brief(self):
        with self.assertRaises(ValueError):
            create_project('EP', 'Folk', 4, 300, 180, 3)


class TransportTests(unittest.TestCase):
    def response(self, parts):
        return io.BytesIO(b'\n'.join(json.dumps(p).encode() for p in parts))
    def test_streamed_json_validates(self):
        client = Ollama()
        raw = json.dumps(song())
        recorded = []
        def request(path, data, timeout):
            recorded.append(data)
            return self.response([{'response': raw[:40]}, {'response': raw[40:], 'done': True, 'done_reason': 'stop'}])
        client.request = request
        result = client.generate('qwen3:8b', 'Brief', threading.Event())
        self.assertEqual(result, song())
        self.assertEqual(recorded[0]['format'], SCHEMA)
    def test_truncated_stream_rejected(self):
        c = Ollama()
        c.request = lambda *a, **kw: self.response([{'response': json.dumps(song())}])
        with self.assertRaises(RuntimeError):
            c.generate('qwen3:8b', 'Brief', threading.Event())
    def test_cancelled_does_not_contact_server(self):
        c = Ollama()
        c.request = lambda *a, **kw: self.fail('Should not contact Ollama')
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(Cancelled):
            c.generate('qwen3:8b', 'Brief', cancelled)
    def test_cloud_models_filtered(self):
        c = Ollama()
        c.request = lambda *a, **kw: io.BytesIO(json.dumps({'models': [{'name': 'qwen3:8b'}, {'name': 'large:cloud'}, {'name': 'remote', 'remote_host': 'https://ollama.com'}]}).encode())
        self.assertEqual(c.models(), ['qwen3:8b'])


if __name__ == '__main__':
    unittest.main()
