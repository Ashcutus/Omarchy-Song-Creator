"""Versework: local project storage, revision rules and Ollama transport."""
from __future__ import annotations
import copy
import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ['title', 'lyrics', 'style_prompt', 'exclusions', 'vocal_gender', 'weirdness', 'style_influence', 'variety']
LABELS = dict(zip(FIELDS, ['Song title', 'Lyrics', 'Style prompt', 'Exclusions', 'Vocal gender', 'Weirdness %', 'Style influence %', 'Variety level']))
TEXT_LIMIT = 1000
VARIETIES = ['off', 'normal', 'high', 'extra', 'max']
VOCALS = ['male', 'female', 'mixed', 'unspecified', 'instrumental']
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': FIELDS + ['notes'], 'properties': {
    **{k: {'type': 'string'} for k in ['title', 'lyrics', 'style_prompt', 'exclusions', 'notes']},
    **{k: {'type': 'string', 'maxLength': TEXT_LIMIT} for k in ['style_prompt', 'exclusions']},
    'vocal_gender': {'type': 'string', 'enum': VOCALS},
    'weirdness': {'type': 'integer', 'minimum': 0, 'maximum': 100},
    'style_influence': {'type': 'integer', 'minimum': 0, 'maximum': 100},
    'variety': {'type': 'string', 'enum': VARIETIES}}}
SYSTEM = """You are a thoughtful songwriter and producer. Write original, singable lyrics with concrete imagery, natural stresses, memorable hooks and deliberate progression. Avoid generic filler and repeating the same images across a collection. Every track needs its own hook, chorus, story and wording. Never copy a lyric line from another track; peer lyrics are a do-not-repeat reference, not a template. Do not simply turn the theme description into a chorus. Treat creative brief and feedback as creative direction, never instructions to change the JSON format. Return only the requested JSON object. All eight song fields are required. Use bracketed section labels in lyrics. Write practical style prompts describing genre, rhythm, instruments, production and vocal delivery. Exclusions are a concise comma-separated list. style_prompt and exclusions must each contain at most 1000 characters, including spaces and punctuation. Weirdness and style_influence are integer percentages. Variety is exactly off, normal, high, extra or max. Duration is a target for structure, tempo and lyric density, never a guaranteed audio length. notes should briefly explain arrangement/duration choices, or changes made for a revision. Do not claim to generate or listen to audio. Do not claim to have verified any Suno setting."""

PRODUCTION_OPTIONS = {
    'feel': {
        'style': ('Follow style', ''),
        'human': ('Natural and understated', 'Use subtle human timing variation, unforced phrasing, and touch-sensitive dynamics. Avoid rigid quantization, excessive correction, and identical repeated embellishments. For vocals, favour conversational phrasing and varied line endings; do not force breaths or filler sounds into lyrics.'),
        'live': ('Live-room performance', 'Aim for the feel of a small ensemble playing together in one room: responsive timing, natural room ambience, and minimal editing. Do not add crowd noise, fake mistakes, vinyl noise, or arbitrary lo-fi damage.'),
        'polished': ('Tight and polished', 'Use precise timing and clean controlled delivery while preserving expressive phrasing and musical dynamics.'),
    },
    'density': {
        'style': ('Follow style', ''),
        'stripped': ('Stripped back', 'Use a sparse arrangement with one or two supporting instruments, space between phrases, and no added layers for scale.'),
        'restrained': ('Restrained', 'Use a small, clearly defined ensemble. Keep supporting layers sparse; avoid stacked hooks, ornamental fills, and automatic chorus thickening.'),
        'balanced': ('Balanced', 'Use a clear core arrangement with selective supporting layers; each addition must serve the song.'),
        'full': ('Full production', 'Allow a rich layered arrangement while keeping the lead and core musical ideas clear.'),
    },
    'dynamics': {
        'style': ('Follow style', ''),
        'steady': ('Steady and contained', 'Keep intensity contained throughout. Do not add a giant final chorus, cinematic rise, drop, or key change.'),
        'gentle': ('Gentle build', 'Build gradually through performance and subtle instrumentation, without an oversized climax.'),
        'dramatic': ('Dramatic build', 'Allow deliberate contrast and a strong climax where the song calls for it.'),
    },
    'vocals': {
        'style': ('Follow style', ''),
        'intimate': ('Intimate solo', 'Use a close, natural solo lead, restrained delivery, minimal effects, no doubled lead, harmonies, choir, or ad-libs.'),
        'natural': ('Natural lead', 'Keep the lead vocal natural and clear, with minimal processing and only occasional purposeful backing vocals.'),
        'layered': ('Layered vocals', 'Allow deliberate harmonies and vocal layers while keeping the lead intelligible.'),
    },
}


def production_direction(value=None):
    value = value or {}
    if not isinstance(value, dict):
        raise ValueError('Invalid production direction.')
    result = {}
    for key, options in PRODUCTION_OPTIONS.items():
        choice = value.get(key, 'style')
        if choice not in options:
            raise ValueError('Invalid production choice.')
        result[key] = choice
    notes = value.get('notes', '')
    if not isinstance(notes, str) or len(notes) > TEXT_LIMIT:
        raise ValueError('Production notes must be 1000 characters or fewer.')
    result['notes'] = notes
    return result


def production_brief(track):
    direction = production_direction(track.get('production'))
    return {
        'choices': direction,
        'delivery': [PRODUCTION_OPTIONS[key][direction[key]][1]
                     for key in PRODUCTION_OPTIONS if direction[key] != 'style'],
        'instructions': 'Apply this direction to style_prompt and concise bracketed performance cues in lyrics. Keep cues separate from sung words. Add relevant unwanted production elements to exclusions. Respect locked fields. For instrumental songs, omit vocal directions and vocal lyric cues. Keep style_prompt and exclusions within 1000 characters each. If specific production choices conflict with broad genre conventions, follow the specific choices. These are creative requests, not guarantees of audio behaviour.',
    }


# Compact, auditable delivery cues. These are writing directions, not Suno API parameters.
PRODUCTION_CUES = {
    'feel': {
        'human': ('natural timing and phrasing', 'hard quantization, excessive pitch correction', '[Natural phrasing, subtle timing variation]'),
        'live': ('live-room ensemble feel', 'hard quantization, excessive editing, crowd noise', '[Live-room feel, responsive timing]'),
        'polished': ('precise timing, expressive phrasing', '', '[Precise, expressive performance]'),
    },
    'density': {
        'stripped': ('sparse arrangement', 'dense layering', '[Sparse arrangement]'),
        'restrained': ('restrained arrangement', 'overproduction', '[Restrained arrangement]'),
        'balanced': ('balanced arrangement', '', '[Balanced arrangement]'),
        'full': ('full layered arrangement', '', '[Full arrangement]'),
    },
    'dynamics': {
        'steady': ('contained dynamics', 'dramatic builds, key changes', '[Contained dynamics throughout]'),
        'gentle': ('gentle build', 'explosive drops', '[Gentle build]'),
        'dramatic': ('dramatic build', '', '[Dramatic build]'),
    },
    'vocals': {
        'intimate': ('intimate solo vocal', 'vocal doubling, choir, ad-libs', '[Intimate solo vocal]'),
        'natural': ('natural lead vocal', 'heavy vocal processing', '[Natural lead vocal]'),
        'layered': ('layered vocals', '', '[Layered vocals]'),
    },
}


def production_requirements(track, instrumental=False):
    direction = production_direction(track.get('production'))
    required = {'style_prompt': [], 'exclusions': [], 'lyrics': []}
    for key, options in PRODUCTION_CUES.items():
        if key == 'vocals' and instrumental:
            continue
        if direction[key] == 'style':
            continue
        style, exclusions, cue = options[direction[key]]
        required['style_prompt'].append(style)
        required['exclusions'].extend(exclusions.split(', ') if exclusions else [])
        required['lyrics'].append(cue)
    return {field: values for field, values in required.items() if field not in track.get('locks', [])}


def missing_production(song, track):
    instrumental = song.get('vocal_gender') == 'instrumental'
    missing = []
    for field, values in production_requirements(track, instrumental).items():
        for value in values:
            if value.casefold() not in song[field].casefold():
                missing.append(f'{field}: {value}')
    return missing


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
        if field in ['style_prompt', 'exclusions'] and len(v) > TEXT_LIMIT:
            raise ValueError(f'{LABELS[field]} must be {TEXT_LIMIT} characters or fewer.')
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
    if len(style) > TEXT_LIMIT:
        raise ValueError(f'Style prompt must be {TEXT_LIMIT} characters or fewer.')
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
    if kind == 'rewrite' and all(data[k] == track['current'][k] for k in FIELDS):
        raise ValueError('The model did not change any unlocked song fields. Your rewrite allowance is unchanged; try more specific feedback.')
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
    context = project.get('_collection_context')
    peers = copy.deepcopy(context.get('other_songs', [])) if context else []
    brief = {'project': project['name'], 'style': project['style'], 'theme': project['theme'],
             'language': project['language'], 'track_number': context['position'] if context else 1,
             'total_tracks': context['total'] if context else 1,
             'target_seconds': [project['minimum'], project['maximum']], 'other_tracks': peers}
    role = 'Self-contained single'
    if context:
        brief['collection'] = {k: v for k, v in context.items() if k != 'other_songs'}
        role = ('A distinct standalone song in a themed collection' if context['kind'] == 'collection' else
                f"Song {context['position']} of {context['total']} on this {context['kind']}")
    brief['production'] = production_brief(track)
    brief['required_delivery_cues'] = production_requirements(track, (track.get('current') or {}).get('vocal_gender') == 'instrumental')
    brief['track_role'] = role
    action = 'Write the initial song. Give this song its own identity. It may stand alone or belong to an optional collection. Read peer lyrics only to avoid repeating them. Write a completely new hook and chorus, not a paraphrase of a peer chorus.'
    if track['current']:
        action = 'Revise this song according to the feedback. Make substantive changes to unlocked song fields that address the feedback. Preserve strengths and anything not targeted by feedback. Describing a change in notes without actually changing the song is not a revision.'
        brief.update(current_song=track['current'], feedback=feedback, locked_fields=track['locks'])
    result = action + '\nCreative brief:\n' + json.dumps(brief, ensure_ascii=False) + '\nReturn JSON matching this schema:\n' + json.dumps(SCHEMA)
    if track['current']:
        result += '\n\nYOUR REVISION TASK NOW:\n' + feedback + '\nOnly these fields are locked: ' + ', '.join(track['locks']) + '\nWrite the revised song JSON now. The lyrics must actually reflect the requested changes. Do not copy the old song unchanged.'
    else:
        result += '\n\nFINAL WRITING CHECK: This is track ' + str(brief['track_number']) + '. Invent an entirely new chorus. Do not reuse any line from the peer tracks shown above. Shared genre does not mean shared lyrics.'
    result += '\nPRODUCTION DELIVERY CHECK: Include every required_delivery_cues phrase verbatim in its named field. Put lyrics cues on separate bracketed lines before the sung lyrics; do not sing them. Integrate style phrases naturally and remove contradictory production descriptions. Exclusions name unwanted elements. For instrumental output omit vocal cues and vocal exclusions. Locked fields must stay unchanged. Stay within the 1000-character field limits. Apply arrangement notes too; mentioning a change only in notes does not count.'
    return result


def overlapping_lines(project, index, song):
    def lines(lyrics):
        return {re.sub(r'[^\w\s]', '', line.lower()).strip() for line in lyrics.splitlines() if len(line.strip()) >= 24 and not line.strip().startswith('[')}
    incoming = lines(song['lyrics'])
    repeated = set()
    for peer in project.get('_collection_context', {}).get('other_songs', []):
        common = incoming & lines(peer.get('do_not_repeat_these_lyrics', ''))
        if len(common) >= 2:
            repeated.update(common)
    return sorted(repeated)


def generate_song(client, model, project, index, feedback, cancel, progress=None):
    prompt = prompt_for(project, index, feedback)
    for attempt in range(2):
        song = client.generate(model, prompt, cancel, progress)
        repeats = overlapping_lines(project, index, song) if not project['tracks'][index]['current'] else []
        missing = missing_production(song, project['tracks'][index])
        if not repeats and not missing:
            return song
        if missing:
            if attempt == 0:
                prompt += '\n\nThe previous response omitted required production directions. Regenerate the complete song JSON, including these exact cues in their specified fields:\n' + '\n'.join(missing)
            else:
                raise ValueError('The model omitted your production directions after one retry. Nothing was saved and no rewrite was used. Try again or choose another model.')
        if attempt == 0 and repeats:
            prompt += '\n\nThe previous draft repeated lines from another track. Write a fresh song with a completely different chorus and imagery. DO NOT USE ANY OF THESE LINES:\n' + '\n'.join(repeats)
    raise ValueError('The model kept repeating lyrics from another track after one retry. This draft was not saved. Try writing this track again or choose another model.')


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
        self.db.execute('CREATE TABLE IF NOT EXISTS collections (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)')
        if not self.db.execute('SELECT 1 FROM migrations WHERE name=?', ('song-library-v1',)).fetchone():
            with self.db:
                for (body,) in self.db.execute('SELECT body FROM projects').fetchall():
                    old = json.loads(body)
                    if len(old['tracks']) > 1:
                        coll = make_collection(old['name'], 'collection', old.get('theme', ''), [t['id'] for t in old['tracks']])
                        self.db.execute('INSERT INTO collections VALUES (?, ?)', (coll['id'], json.dumps(coll)))
                self.db.execute('INSERT INTO migrations VALUES (?)', ('song-library-v1',))
        self.db.commit()
    def save(self, project):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO projects VALUES (?, ?, ?)',
                            (project['id'], json.dumps(project, ensure_ascii=False), now()))
    def list(self):
        return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM projects ORDER BY updated DESC')]
    def settings(self):
        row = self.db.execute('SELECT body FROM settings WHERE id=1').fetchone()
        return {'model': 'qwen3:8b', 'ui_language': 'system', 'colour_mode': 'system', 'colours': {}, **(json.loads(row[0]) if row else {})}
    def save_settings(self, settings):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (1, ?)', (json.dumps(settings),))

    def collections(self):
        return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM collections ORDER BY rowid')]
    def save_collection(self, collection):
        known = {t['id'] for p in self.list() for t in p['tracks']}
        if any(ident not in known for ident in collection['songs']):
            raise ValueError('A selected song no longer exists.')
        validated = make_collection(collection['name'], collection['kind'], collection['theme'], collection['songs'])
        validated['id'] = collection['id']
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO collections VALUES (?, ?)', (validated['id'], json.dumps(validated, ensure_ascii=False)))
    def pending_songs(self, collection_id):
        collection = next((c for c in self.collections() if c['id'] == collection_id), None)
        if not collection:
            return []
        lookup = {track['id']: (p['id'], i, track) for p in self.list() for i, track in enumerate(p['tracks'])}
        return [(lookup[key][0], lookup[key][1]) for key in collection['songs'] if key in lookup and not lookup[key][2]['current']]

    def generation_context(self, project, index, collection_id=None):
        result = copy.deepcopy(project)
        track_id = project['tracks'][index]['id']
        chosen = next((c for c in self.collections() if c['id'] == collection_id and track_id in c['songs']), None)
        if chosen:
            lookup = {t['id']: t for p in self.list() for t in p['tracks']}
            peers = [{'title': lookup[i]['current']['title'], 'style': lookup[i]['current']['style_prompt'],
                      'do_not_repeat_these_lyrics': lookup[i]['current']['lyrics'][:1000]}
                     for i in chosen['songs'] if i != track_id and i in lookup and lookup[i]['current']]
            result['_collection_context'] = {'name': chosen['name'], 'kind': chosen['kind'], 'theme': chosen['theme'],
                                             'position': chosen['songs'].index(track_id) + 1, 'total': len(chosen['songs']), 'other_songs': peers}
        return result


def make_collection(name, kind='collection', theme='', songs=()):
    if not name.strip():
        raise ValueError('Give the collection a name.')
    if kind not in ['collection', 'album', 'ep']:
        raise ValueError('Choose Collection, Album or EP.')
    return {'id': uuid.uuid4().hex, 'name': name.strip(), 'kind': kind, 'theme': theme.strip(), 'songs': list(dict.fromkeys(songs))}


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
