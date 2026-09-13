import copy
import sqlite3
import tempfile
import unittest
from core import Store, create_project, commit_version, track_status
from test_core import song


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.project = create_project('Working title', 'Folk', 1, 180, 240, 3)
        self.store.save(self.project)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_default_and_existing_limits_are_separate(self):
        self.store.apply_settings({'rewrite_limit': None})
        self.assertEqual(self.store.get(self.project['id'])['limit'], 3)
        self.store.apply_settings({'rewrite_limit': None}, apply_existing=True)
        self.assertIsNone(self.store.get(self.project['id'])['limit'])
        with self.assertRaises(ValueError):
            self.store.apply_settings({'rewrite_limit': -1}, apply_existing=True)
        self.assertIsNone(self.store.settings()['rewrite_limit'])

    def test_restore_keeps_a_safety_backup(self):
        snapshot = self.store.backup()
        self.project['name'] = 'Edited'
        self.store.save(self.project)
        before = set(self.store.backups())
        self.store.restore_backup(snapshot)
        self.assertEqual(self.store.get(self.project['id'])['name'], 'Working title')
        safety = next(iter(set(self.store.backups()) - before))
        self.store.restore_backup(safety)
        self.assertEqual(self.store.get(self.project['id'])['name'], 'Edited')

    def test_bulk_setting_failure_rolls_back_default_too(self):
        self.store.save_settings({'rewrite_limit': 3})
        self.store.db.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON projects BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.apply_settings({'rewrite_limit': None}, apply_existing=True)
        self.assertEqual(self.store.settings()['rewrite_limit'], 3)
        self.assertEqual(self.store.get(self.project['id'])['limit'], 3)

    def test_import_assigns_new_ids_and_is_atomic(self):
        payload = {'songs': [{'brief': {k: v for k, v in self.project.items() if k != 'tracks'},
                              'track': self.project['tracks'][0]}]}
        ids = self.store.import_history(payload)
        self.assertNotEqual(ids[0], self.project['id'])
        self.assertNotEqual(self.store.get(ids[0])['tracks'][0]['id'], self.project['tracks'][0]['id'])
        bad = copy.deepcopy(payload)
        bad['songs'].append({'brief': {}, 'track': {}})
        with self.assertRaises(ValueError):
            self.store.import_history(bad)
        self.assertEqual(len(self.store.list()), 2)

    def test_archive_trash_restore_duplicate(self):
        ident = self.project['tracks'][0]['id']
        for state in ('archive', 'trash', 'active'):
            self.assertEqual(self.store.set_song_state(ident, state)['tracks'][0]['state'], state)
        duplicate = self.store.duplicate_song(ident)
        self.assertNotEqual(duplicate['id'], self.project['id'])
        self.assertNotEqual(duplicate['tracks'][0]['id'], ident)
        self.assertEqual(len(self.store.library_metadata()), 2)

    def test_unknown_history_version_is_rejected(self):
        self.project['schema_version'] = 99
        with self.assertRaises(ValueError):
            self.store.save(self.project)

    def test_jobs_survive_reopening(self):
        jobs = [(self.project['id'], 0, 'Looser drums', 'sound', '')]
        self.store.save_jobs(jobs)
        self.store.db.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.store.list_jobs(), jobs)
        self.store.save_jobs([])
        self.assertEqual(self.store.list_jobs(), [])

    def test_library_projection_preserves_status_without_lyrics_or_history(self):
        draft = song()
        draft['lyrics'] = 'Private lyric content\n' * 200
        commit_version(self.project, 0, draft, 'initial')
        self.store.save(self.project)
        summary = self.store.library_projects()[0]
        self.assertEqual(summary['tracks'][0]['current'], {'title': draft['title']})
        self.assertNotIn('versions', summary['tracks'][0])
        self.assertEqual(track_status(summary, summary['tracks'][0]), track_status(self.project, self.project['tracks'][0]))
        self.assertEqual(self.store.get(self.project['id'])['tracks'][0]['current']['lyrics'], draft['lyrics'])

    def test_malformed_import_has_clear_error_and_no_writes(self):
        for entry in (None, [], {'brief': [], 'track': {}}):
            with self.assertRaisesRegex(ValueError, 'brief and track'):
                self.store.import_history({'songs': [entry]})
        self.assertEqual(len(self.store.list()), 1)
