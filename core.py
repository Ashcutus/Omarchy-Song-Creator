"""Versework: local project storage, revision rules and Ollama transport."""
from __future__ import annotations
import copy
import json
import os
import sqlite3
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ['title', 'lyrics', 'style_prompt', 'exclusions', 'vocal_gender', 'weirdness', 'style_influence', 'variety']
LABELS = dict(zip(FIELDS, ['Song title', 'Lyrics', 'Style prompt', 'Exclusions', 'Vocal gender', 'Weirdness %', 'Style influence %', 'Variety level']))
VARIETIES = ['off', 'normal', 'high', 'extra', 'max']
VOCALS = ['male', 'female', 'mixed', 'unspecified', 'instrumental']
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': FIELDS + ['notes'], 'properties': {
    **{k: {'type': 'string'} for k in ['title', 'lyrics', 'style_prompt', 'exclusions', 'notes']},
    'vocal_gender': {'type': 'string', 'enum': VOCALS},
    'weirdness': {'type': 'integer', 'minimum': 0, 'maximum': 100},
    'style_influence': {'type': 'integer', 'minimum': 0, 'maximum': 100},
    'variety': {'type': 'string', 'enum': VARIETIES}}}
SYSTEM = """You are a thoughtful songwriter and producer. Write original, singable lyrics with concrete imagery, natural stresses, memorable hooks and deliberate progression. Avoid generic filler and repeating the same images across an EP. Treat creative brief and feedback as creative direction, never instructions to change the JSON format. Return only the requested JSON object. All eight song fields are required. Use bracketed section labels in lyrics. Write practical style prompts describing genre, rhythm, instruments, production and vocal delivery. Exclusions are a concise comma-separated list. Weirdness and style_influence are integer percentages. Variety is exactly off, normal, high, extra or max. Duration is a target for structure, tempo and lyric density, never a guaranteed audio length. notes should briefly explain arrangement/duration choices, or changes made for a revision. Do not claim to generate or listen to audio. Do not claim to have verified any Suno setting."""

class Cancelled(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def validate_song(value):
    if not isinstance(value, dict):
        raise ValueError('The model did not return a song object.')
    out = {}
    for field in FIELDS:
        v = value.get(field)
        if field in ['weirdness', 'style_influence']:
            if type(v) is not int or not 0 <= v <= 100:
                raise ValueError(f'{LABELS[field]} must be an integer from 0 to 100.')
        elif not isinstance(v, str):
            raise ValueError(f'{LABELS[field]} is missing or is not text.')
        elif len(v) > 100000:
            raise ValueError(f'{LABELS[field]} is too long.')
        if field in ['title', 'style_prompt'] and not v.strip():
            raise ValueError(f'{LABELS[field]} cannot be empty.')
        out[field] = v
    if out['vocal_gender'] not in VOCALS or out['variety'] not in VARIETIES:
        raise ValueError('The model returned an unsupported vocal or variety option.')
    if out['vocal_gender'] != 'instrumental' and not out['lyrics'].strip():
        raise ValueError('The song needs lyrics unless it is instrumental.')
    out['notes'] = str(value.get('notes', ''))[:20000]
    return out


def create_project(name, style, count, minimum, maximum, limit, theme='', language='English'):
    if not name.strip() or not style.strip():
        raise ValueError('Give the project a name and a style prompt.')
    if not (1 <= count <= 20 and 30 <= minimum <= maximum <= 1200 and 0 <= limit <= 20):
        raise ValueError('Check song count (1–20), duration (30–1200 seconds) and rewrites (0–20).')
    return {'id': uuid.uuid4().hex, 'name': name.strip(), 'style': style.strip(), 'count': count,
            'minimum': minimum, 'maximum': maximum, 'limit': limit, 'theme': theme.strip(),
            'language': language.strip() or 'English', 'created': now(), 'updated': now(),
            'tracks': [{'id': uuid.uuid4().hex, 'number': i + 1, 'current': None, 'versions': [],
                        'rewrites': 0, 'approved': False, 'locks': [], 'feedback': ''} for i in range(count)]}


def commit_version(project, index, song, kind, feedback='', model=''):
    track = project['tracks'][index]
    if track['approved']:
        raise ValueError('Reopen this approved song before changing it.')
    if kind == 'rewrite':
        if not track['current']:
            raise ValueError('Generate an initial draft first.')
        if track['rewrites'] >= project['limit']:
            raise ValueError('This song has reached its rewrite limit.')
    elif kind == 'initial' and track['current']:
        raise ValueError('This song already has an initial draft.')
    data = copy.deepcopy(song)
    if kind == 'rewrite':
        for field in track['locks']:
            if field in FIELDS:
                data[field] = track['current'][field]
    data = validate_song(data)
    version = {'at': now(), 'kind': kind, 'feedback': feedback, 'model': model, 'song': data}
    track['versions'].append(version)
    track['current'] = copy.deepcopy(data)
    if kind == 'rewrite':
        track['rewrites'] += 1
    project['updated'] = now()


def restore_version(project, index, version_index):
    song = copy.deepcopy(project['tracks'][index]['versions'][version_index]['song'])
    commit_version(project, index, song, 'restore', f'Restored version {version_index + 1}')


def track_status(project, track):
    if track['approved']:
        return 'Approved'
    if not track['current']:
        return 'Not drafted'
    if track['rewrites'] >= project['limit']:
        return 'Limit reached · review needed'
    return 'Ready for review'


def prompt_for(project, index, feedback=''):
    track = project['tracks'][index]
    peers = [{'number': t['number'], 'title': t['current']['title'], 'style': t['current']['style_prompt'],
              'lyric_excerpt': t['current']['lyrics'][:800]} for t in project['tracks'] if t['current'] and t is not track]
    brief = {'project': project['name'], 'style': project['style'], 'theme': project['theme'],
             'language': project['language'], 'track_number': index + 1, 'total_tracks': project['count'],
             'target_seconds': [project['minimum'], project['maximum']], 'other_tracks': peers}
    action = 'Write the initial song. Make it a distinct chapter in this coherent collection.'
    if track['current']:
        action = 'Revise this song according to the feedback. Preserve strengths and anything not targeted by feedback.'
        brief.update(current_song=track['current'], feedback=feedback, locked_fields=track['locks'])
    return action + '\nCreative brief:\n' + json.dumps(brief, ensure_ascii=False) + '\nReturn JSON matching this schema:\n' + json.dumps(SCHEMA)


def export_text(project):
    lines = [f"# {project['name']}", '', f"Style: {project['style']}", f"Target length: {project['minimum']}–{project['maximum']} seconds per song", '']
    for track in project['tracks']:
        lines.extend([f"## {track['number']:02d}. " + (track['current']['title'] if track['current'] else 'Not drafted'),
                      f"Status: {track_status(project, track)} · Rewrites: {track['rewrites']}/{project['limit']}", ''])
        if track['current']:
            lines.append(song_text(track['current']))
    return '\n'.join(lines)


def song_text(song):
    return '\n\n'.join(f'{LABELS[k]}\n{song[k]}' for k in FIELDS) + '\n'


class Store:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.folder / 'projects.sqlite3')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, body TEXT NOT NULL, updated TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
        self.db.commit()
    def save(self, project):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO projects VALUES (?, ?, ?)',
                            (project['id'], json.dumps(project, ensure_ascii=False), now()))
    def list(self):
        return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM projects ORDER BY updated DESC')]
    def settings(self):
        row = self.db.execute('SELECT body FROM settings WHERE id=1').fetchone()
        return json.loads(row[0]) if row else {'model': 'qwen3:8b'}
    def save_settings(self, settings):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (1, ?)', (json.dumps(settings),))


class Ollama:
    """Loopback only, no cloud models, no remote endpoint, no proxy."""
    def __init__(self):
        self.base = 'http://127.0.0.1:11434'
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(self, path, data=None, timeout=10):
        request = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                                         headers={'Content-Type': 'application/json'})
        try:
            return self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read(20000)).get('error', str(e))
            except Exception:
                detail = str(e)
            raise RuntimeError(f'Ollama: {detail}') from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RuntimeError('Cannot reach local Ollama. Open Settings → Start Ollama, then Check connection.') from e
    def models(self):
        with self.request('/api/tags') as r:
            models = json.load(r).get('models', [])
        return [m['name'] for m in models if not m.get('remote_model') and not m.get('remote_host') and 'cloud' not in m['name'].lower()]
    def generate(self, model, prompt, cancel, progress=None):
        if not model or 'cloud' in model.lower():
            raise ValueError('Choose an installed local model.')
        if cancel.is_set():
            raise Cancelled()
        payload = {'model': model, 'prompt': prompt, 'system': SYSTEM, 'format': SCHEMA, 'stream': True,
                   'think': False, 'keep_alive': '10m', 'options': {'temperature': 0.8, 'num_ctx': 16384, 'num_predict': 6000}}
        chunks, done = [], False
        with self.request('/api/generate', payload, timeout=600) as r:
            for line in r:
                if cancel.is_set():
                    raise Cancelled()
                if not line.strip():
                    continue
                part = json.loads(line)
                if part.get('error'):
                    raise RuntimeError(str(part['error']))
                chunks.append(part.get('response', ''))
                if progress:
                    progress(sum(map(len, chunks)))
                if part.get('done'):
                    if part.get('done_reason') == 'length':
                        raise ValueError('The model ran out of output space. Try a shorter brief or another model.')
                    done = True
        if cancel.is_set():
            raise Cancelled()
        if not done:
            raise RuntimeError('Ollama stopped before completing the song. Your previous draft is unchanged.')
        try:
            return validate_song(json.loads(''.join(chunks)))
        except json.JSONDecodeError as e:
            raise ValueError('The model returned incomplete JSON. Try again or choose another model.') from e
