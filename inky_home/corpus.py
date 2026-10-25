"""Build a small, attributed teaching catalog from open corpora on a desktop.

No network calls: inputs are downloaded separately. The Pi only reads the result.
"""
import bz2
import csv
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tarfile
import unicodedata
from urllib.parse import quote

POS = {'NOM': 'noun', 'VER': 'verb', 'ADJ': 'adj', 'ADV': 'adv'}
BAD_TAGS = {'archaic', 'obsolete', 'dated', 'historical', 'rare', 'vulgar', 'offensive',
            'derogatory', 'slur', 'nonstandard', 'form-of', 'abbreviation', 'initialism', 'literary', 'poetic'}
STOP = set('a an the to of in on at for and or is be being one something someone person thing '
           'act action state quality kind type used having relating make take get put this that '
           'with without from by as any some usually especially very more less other'.split())
BAD_TEXT = re.compile(r'\b(fuck\w*|shit\w*|bitch\w*|putain|connard\w*|merde)\b', re.I)
WORD = re.compile(r"^[^\W\d_]+(?:[-'][^\W\d_]+)*$", re.UNICODE)

SCHEMA = '''
PRAGMA user_version=1;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE sources (id TEXT PRIMARY KEY, name TEXT, url TEXT, license TEXT,
 license_url TEXT, attribution TEXT, sha256 TEXT, retrieved_at TEXT);
CREATE TABLE entries (id INTEGER PRIMARY KEY, lemma TEXT, pos TEXT, gender TEXT,
 definition TEXT, usage TEXT, frequency REAL, frequency_rank INTEGER, source_url TEXT,
 sense_id TEXT);
CREATE TABLE sentences (id INTEGER PRIMARY KEY, french TEXT, english_id INTEGER,
 english TEXT, french_author TEXT, english_author TEXT);
CREATE TABLE lessons (id INTEGER PRIMARY KEY, stable_id TEXT UNIQUE NOT NULL,
 entry_id INTEGER REFERENCES entries(id), sentence_id INTEGER REFERENCES sentences(id),
 context_id INTEGER REFERENCES sentences(id));
CREATE INDEX lesson_entry ON lessons(entry_id);
'''


def normalized(text):
    return unicodedata.normalize('NFC', text).casefold().replace('’', "'")


def tokens(text):
    text = re.sub(r"\b(?:[cdjlmnst]|qu)['’]", '', normalized(text))
    return re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", text)


def stems(text):
    return {word[:5] for word in tokens(text) if len(word) >= 3 and word not in STOP}


def safe_sentence(text, language):
    minimum, maximum = (24, 94) if language == 'fra' else (15, 110)
    return (minimum <= len(text) <= maximum and '\n' not in text and '\t' not in text
            and not re.search(r'[<>@{}]|https?://|www\.', text) and not BAD_TEXT.search(text)
            and 4 <= len(tokens(text)) <= 18
            and len(re.findall(r'[.!?](?:\s|$)', text)) <= 1)


def lexique_entries(path, minimum_rank=500, maximum_rank=10000):
    entries = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream, delimiter='\t', quoting=csv.QUOTE_NONE):
            lemma, form = normalized(row['lemme']), normalized(row['ortho'])
            pos = POS.get(row['cgram'])
            if not pos or not 3 <= len(lemma) <= 24 or not WORD.fullmatch(lemma):
                continue
            try:
                frequency = max(float(row['freqlemfilms2'].replace(',', '.')),
                                float(row['freqlemlivres'].replace(',', '.')))
            except (KeyError, ValueError):
                continue
            if frequency <= 0:
                continue
            key = (lemma, pos)
            entry = entries.setdefault(key, {'lemma': lemma, 'pos': pos, 'gender': row.get('genre', ''),
                                             'frequency': frequency, 'forms': set(), 'senses': [], 'genders': set()})
            if row.get('genre') in ('m', 'f'):
                entry['genders'].add(row['genre'])
            entry['forms'].add(form)
            entry['forms'].add(lemma)
            entry['frequency'] = max(entry['frequency'], frequency)
    ranked = sorted(entries, key=lambda key: (-entries[key]['frequency'], key))
    selected = {}
    for rank, key in enumerate(ranked, 1):
        if minimum_rank <= rank <= maximum_rank:
            entry = entries[key]
            entry['gender'] = 'm/f' if entry['genders'] == {'m','f'} else next(iter(entry['genders']), '')
            selected[key] = {**entry, 'frequency_rank': rank}
    return selected


def add_dictionary(path, entries):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('lang_code', 'fr') != 'fr':
                continue
            key = (normalized(row.get('word', '')), row.get('pos'))
            if key not in entries:
                continue
            for sense in row.get('senses', []):
                tags = set(row.get('tags') or []) | set(sense.get('tags') or [])
                if tags & BAD_TAGS or sense.get('form_of') or sense.get('alt_of'):
                    continue
                gloss = next((g for g in sense.get('glosses', [])
                              if 3 <= len(g) <= 115 and not BAD_TEXT.search(g)
                              and not re.search(r'^(plural|inflection|alternative form) of', g, re.I)), None)
                if not gloss or not stems(gloss):
                    continue
                entry = entries[key]
                if len(entry['senses']) < 4 and gloss not in [s['definition'] for s in entry['senses']]:
                    entry['senses'].append({'definition': gloss, 'sense_id': sense.get('id', ''),
                                            'usage': ', '.join(sorted(tags)), 'stems': stems(gloss),
                                            'gender': 'f' if 'feminine' in tags and 'masculine' not in tags else
                                                      'm' if 'masculine' in tags and 'feminine' not in tags else ''})
    useful = {key: entry for key, entry in entries.items() if entry['senses']}
    categories = Counter(key[0] for key in useful)
    return {key: entry for key, entry in useful.items() if categories[key[0]] == 1}


def sentence_rows(path, language):
    with bz2.open(path, 'rt', encoding='utf-8', newline='') as stream:
        for row in csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE):
            if len(row) < 3 or row[1] != language or not row[0].isdigit():
                continue
            text = row[2]
            if safe_sentence(text, language):
                owner = row[3] if len(row) > 3 and row[3] not in ('', '\\N') else 'Tatoeba contributors'
                yield int(row[0]), text, owner


def french_candidates(path, entries, per_word=12):
    forms = {}
    for key, entry in entries.items():
        # An inflected verb can share its spelling with an unrelated noun or adjective.
        candidates = {entry['lemma']} if entry['pos'] == 'verb' else entry['forms']
        for form in candidates:
            forms.setdefault(form, set()).add(key)
    choices = {key: [] for key in entries}
    french = {}
    for sid, text, owner in sentence_rows(path, 'fra'):
        words = tokens(text)
        original = re.sub(r"\b(?:[cdjlmnst]|qu)['’]", '', unicodedata.normalize('NFC', text), flags=re.I)
        spelled = re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", original)
        # Capitalized target words in the middle of a sentence are probably names.
        eligible = [(i, normalized(word)) for i,word in enumerate(spelled) if i == 0 or not word[0].isupper()]
        keys = {key for i,word in eligible for key in forms.get(word, set())
                if i > 0 or entries[key]['pos'] != 'noun'}
        if not keys:
            continue
        score = abs(len(words) - 10) * 10 + abs(len(text) - 65) / 100
        for key in keys:
            selected = choices[key]
            candidate = (score, sid)
            if len(selected) < per_word or candidate < selected[-1]:
                selected.append(candidate)
                selected.sort()
                del selected[per_word:]
                french[sid] = (text, owner)
    chosen_ids = {sid for candidates in choices.values() for _, sid in candidates}
    french = {sid: french[sid] for sid in chosen_ids}
    inverse = {}
    scores = {}
    for key, candidates in choices.items():
        for score, sid in candidates:
            inverse.setdefault(sid, []).append(key)
            scores[sid] = score
    return french, inverse, scores


def link_rows(path):
    # Read only the archive member; never extract paths from an untrusted archive.
    with tarfile.open(path, 'r|bz2') as archive:
        for member in archive:
            if member.isfile() and Path(member.name).name == 'links.csv':
                with archive.extractfile(member) as stream:
                    for row in stream:
                        parts = row.strip().split(b'\t')
                        if len(parts) == 2 and all(p.isdigit() for p in parts):
                            yield int(parts[0]), int(parts[1])
                return
    raise ValueError('Tatoeba archive does not contain links.csv')


def matched_examples(path, entries, french, inverse, scores, english):
    matches = {}
    for fr_id, en_id in link_rows(path):
        if fr_id not in french or en_id not in english:
            continue
        english_text = english[en_id][0]
        english_stems = stems(english_text)
        for key in inverse[fr_id]:
            for sense_index, sense in enumerate(entries[key]['senses']):
                # Conservative lexical overlap is a heuristic, not sense annotation.
                if not (english_stems & sense['stems']):
                    continue
                group = matches.setdefault((key, sense_index), {})
                score = scores[fr_id] + abs(len(english_text) - len(french[fr_id][0]) * .9) / 100
                candidate = (score, fr_id, en_id)
                if fr_id not in group or candidate < group[fr_id]:
                    group[fr_id] = candidate
    return matches


def source_records(downloads):
    attribution = {
        'kaikki': ('Wiktionary via Kaikki', 'CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/', 'Wiktionary contributors; extraction by Tatu Ylonen / Wiktextract'),
        'lexique': ('Lexique 3.83', 'CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/', 'Boris New, Christophe Pallier and Lexique/OpenLexicon contributors'),
        'french': ('Tatoeba French sentences', 'CC BY 2.0 FR', 'https://creativecommons.org/licenses/by/2.0/fr/', 'Individual contributors, credited by name and sentence URL'),
        'english': ('Tatoeba English translations', 'CC BY 2.0 FR', 'https://creativecommons.org/licenses/by/2.0/fr/', 'Individual contributors, credited by name and sentence URL'),
        'links': ('Tatoeba translation links', 'CC BY 2.0 FR', 'https://creativecommons.org/licenses/by/2.0/fr/', 'Tatoeba contributors'),
    }
    records = []
    for key, (name, license, license_url, author) in attribution.items():
        item = downloads[key]
        records.append((key, name, item['url'], license, license_url, author, item['sha256'], item['retrieved_at']))
    return records


def build_catalog(directory, output, limit=730, minimum_lessons=365, minimum_rank=500,
                  maximum_rank=10000, progress=print):
    directory, output = Path(directory), Path(output)
    downloads = json.loads((directory / 'downloads.json').read_text())
    for key, item in downloads.items():
        digest = hashlib.sha256()
        with (directory / item['file']).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != item['sha256']:
            raise ValueError(f'Source checksum mismatch: {key}')
    paths = {key: directory / item['file'] for key, item in downloads.items()}
    progress('Selecting useful Lexique headwords…')
    entries = lexique_entries(paths['lexique'], minimum_rank, maximum_rank)
    progress(f'Matching {len(entries):,} headwords to Kaikki definitions…')
    entries = add_dictionary(paths['kaikki'], entries)
    progress(f'Finding short French examples for {len(entries):,} dictionary entries…')
    french, inverse, scores = french_candidates(paths['french'], entries)
    progress(f'Keeping {len(french):,} candidate French sentences; reading English translations…')
    english = {sid: (text, owner) for sid, text, owner in sentence_rows(paths['english'], 'eng')}
    progress(f'Joining Tatoeba links against {len(english):,} short English sentences…')
    matches = matched_examples(paths['links'], entries, french, inverse, scores, english)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.building')
    temporary.unlink(missing_ok=True)
    count = 0
    used = set()
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript(SCHEMA)
            db.executemany('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)', source_records(downloads))
            # Stable shuffle avoids an alphabetical deck or a monotonic difficulty ramp.
            for key in sorted(entries, key=lambda k: hashlib.sha256('|'.join(k).encode()).hexdigest()):
                entry = entries[key]
                for sense_index, sense in enumerate(entry['senses']):
                    candidates = sorted(matches.get((key, sense_index), {}).values())
                    examples = [row for row in candidates if row[1] not in used]
                    if len(examples) < 2:
                        continue
                    pair = examples[:2]
                    count += 1
                    entry_url = 'https://en.wiktionary.org/wiki/' + quote(entry['lemma'], safe='') + '#French'
                    db.execute('INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?)',
                        (count, entry['lemma'], entry['pos'], sense.get('gender') or entry['gender'], sense['definition'],
                         sense['usage'], entry['frequency'], entry['frequency_rank'], entry_url, sense['sense_id']))
                    for _, fr_id, en_id in pair:
                        db.execute('INSERT INTO sentences VALUES (?,?,?,?,?,?)',
                            (fr_id, french[fr_id][0], en_id, english[en_id][0], french[fr_id][1], english[en_id][1]))
                        used.add(fr_id)
                    stable = hashlib.sha256(f'{key}|{sense["sense_id"]}|{pair[0][1:]}|{pair[1][1:]}'.encode()).hexdigest()[:24]
                    db.execute('INSERT INTO lessons VALUES (?,?,?,?,?)', (count, stable, count, pair[0][1], pair[1][1]))
                    break
                if count >= limit:
                    break
            if count < minimum_lessons:
                raise ValueError(f'Only {count} matched lessons; require {minimum_lessons}. Original catalog kept.')
            metadata = {'schema_version': 1, 'lesson_count': count, 'sentence_count': len(used),
                'difficulty': 'Intermediate estimate; frequency is not CEFR certification',
                'minimum_frequency_rank': minimum_rank, 'maximum_frequency_rank': maximum_rank,
                'selection': 'Lexique frequency + single-POS headwords + dictionary sense filters + short single sentences + English gloss overlap; matches are heuristic',
                'built_at': datetime.now(timezone.utc).isoformat()}
            db.executemany('INSERT INTO metadata VALUES (?,?)', [(k, json.dumps(v, ensure_ascii=False)) for k,v in metadata.items()])
            db.execute('PRAGMA foreign_keys=ON')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('Broken catalog references')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Catalog integrity check failed')
        with sqlite3.connect(temporary) as db:
            db.execute('VACUUM')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    progress(f'Built {count:,} daily sets / {count*3:,} cards: {output} ({output.stat().st_size:,} bytes)')
    return count
