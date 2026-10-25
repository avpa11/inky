"""Read-only offline catalog. Daily assignments are pinned in the user's Store."""
import copy
from datetime import datetime, time, timedelta
from functools import cached_property
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

DEFAULT_DATABASE = Path(__file__).parent / 'data' / 'french.sqlite3'


def learning_day(now, timezone, rollover):
    local = now.astimezone(ZoneInfo(timezone))
    cutoff = time.fromisoformat(rollover)
    return (local.date() - timedelta(days=local.time().replace(tzinfo=None) < cutoff)).isoformat()


class LessonCatalog:
    def __init__(self, path=DEFAULT_DATABASE):
        self.path = Path(path).resolve()

    def connect(self):
        if not self.path.is_file():
            raise RuntimeError('French catalog is missing. Run scripts/build_french_db.py on your Mac.')
        db = sqlite3.connect(self.path.as_uri() + '?mode=ro&immutable=1', uri=True)
        db.row_factory = sqlite3.Row
        return db

    @cached_property
    def metadata(self):
        with self.connect() as db:
            return {row['key']: json.loads(row['value']) for row in db.execute('SELECT key,value FROM metadata')}

    @cached_property
    def count(self):
        with self.connect() as db:
            count = db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
        if count < 1:
            raise RuntimeError('French catalog contains no lessons')
        return count

    def validate(self):
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise RuntimeError('Unsupported French catalog schema')
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise RuntimeError('French catalog is damaged')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('French catalog has broken source references')
            providers = {row[0] for row in db.execute('SELECT id FROM sources')}
            if not {'kaikki', 'lexique', 'french', 'english', 'links'} <= providers:
                raise RuntimeError('French catalog is missing required sources')
        if self.metadata.get('lesson_count') != self.count:
            raise RuntimeError('French catalog lesson count is inconsistent')
        return self.count

    def sources(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM sources ORDER BY id')]

    def lesson_at(self, index):
        offset = max(0, index) % self.count
        with self.connect() as db:
            row = db.execute('''SELECT l.id AS lesson_id,l.stable_id,l.sentence_id,l.context_id,e.*
                FROM lessons l JOIN entries e ON e.id=l.entry_id ORDER BY l.id LIMIT 1 OFFSET ?''', (offset,)).fetchone()
            entry = dict(row)
            example = dict(db.execute('SELECT * FROM sentences WHERE id=?', (entry['sentence_id'],)).fetchone())
            context = dict(db.execute('SELECT * FROM sentences WHERE id=?', (entry['context_id'],)).fetchone())
        word = entry['lemma']
        gender = {'m': 'm.', 'f': 'f.', 'm/f': 'm./f.'}.get(entry['gender']) if entry['pos'] == 'noun' else None
        title = f'{word} ({gender})' if gender else word
        usage_title, usage_meaning = usage_rule(entry)
        labels = entry['usage'].split(', ')[:3] if entry['usage'] else []
        usage_note = 'Dictionary labels: ' + ', '.join(labels) if labels else 'Usage note derived from dictionary metadata.'
        if len(usage_note) > 95:
            usage_note = 'See the dictionary source for full usage labels.'
        def card(kind, title, meaning, sentence, note, authored=False):
            references = references_for(entry, sentence)
            if authored:
                references.append({'name': 'Inky Home usage rules', 'url': 'https://github.com/avpa11/inky/blob/main/inky_home/lessons.py',
                                   'license': 'CC BY-SA 4.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/'})
            return {'kind': kind, 'title': title, 'meaning': meaning,
                    'example': sentence['french'], 'translation': sentence['english'], 'note': note,
                    'sources': references, 'credit': f'Tatoeba #{sentence["id"]} · Wiktionary / Lexique · Sources in web app'}
        return {'id': entry['lesson_id'], 'stable_id': entry['stable_id'], 'theme': word,
                'level': 'Intermediate estimate', 'catalog_built_at': self.metadata['built_at'],
                'cards': [
                    card('Vocabulary', title, entry['definition'], example,
                         f'Frequency rank {entry["frequency_rank"]:,}; approximate intermediate selection.'),
                    card('Context', 'En contexte', f'Another example using “{word}” or an inflected form.', context,
                         'Read the French first, then check the English translation.'),
                    card('Usage', usage_title, usage_meaning, example, usage_note, authored=True)]}


def usage_rule(entry):
    """Small authored teaching rules, not purported corpus-provided explanations."""
    pos, gender = entry['pos'], entry['gender']
    if pos == 'noun':
        if gender == 'm':
            return 'Nom masculin', 'This noun is masculine. Learn its article together with the word.'
        if gender == 'f':
            return 'Nom féminin', 'This noun is feminine. Learn its article together with the word.'
        return 'Le nom', 'Check the dictionary for this noun’s gender; it can depend on its sense or use.'
    if pos == 'verb':
        return 'Le verbe', 'The dictionary lists the infinitive. Sentence forms change with subject and tense.'
    if pos == 'adj':
        if 'invariable' in entry['usage'].split(', '):
            return 'Adjectif invariable', 'This adjective is invariable: its spelling does not change for gender or number.'
        return 'L’adjectif', 'Adjectives usually agree with the noun in gender and number.'
    return 'L’adverbe', 'Adverbs usually keep the same form; they do not agree with a noun.'


def references_for(entry, sentence):
    return [
        {'name': 'Wiktionary contributors (via Kaikki)', 'url': entry['source_url'],
         'license': 'CC BY-SA 4.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/'},
        {'name': f'Tatoeba French #{sentence["id"]} — {sentence["french_author"]}',
         'url': f'https://tatoeba.org/en/sentences/show/{sentence["id"]}',
         'license': 'CC BY 2.0 FR', 'license_url': 'https://creativecommons.org/licenses/by/2.0/fr/'},
        {'name': f'Tatoeba English #{sentence["english_id"]} — {sentence["english_author"]}',
         'url': f'https://tatoeba.org/en/sentences/show/{sentence["english_id"]}',
         'license': 'CC BY 2.0 FR', 'license_url': 'https://creativecommons.org/licenses/by/2.0/fr/'},
        {'name': 'Lexique 3.83 — New, Pallier and contributors',
         'url': 'https://chrplr.github.io/openlexicon/datasets-info/Lexique383/README-Lexique.html',
         'license': 'CC BY-SA 4.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/'}]


CATALOG = LessonCatalog()


def lesson_for(day, anchor):
    index = (datetime.fromisoformat(day).date() - datetime.fromisoformat(anchor).date()).days
    return CATALOG.lesson_at(index)
