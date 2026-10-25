import bz2
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from inky_home.corpus import build_catalog, french_candidates, safe_sentence
from inky_home.lessons import CATALOG, LessonCatalog, lesson_for
from inky_home.store import Store
from inky_home.web import create_app


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output = self.root / 'catalog.sqlite3'
        self.make_inputs()

    def tearDown(self):
        self.temporary.cleanup()

    def make_inputs(self):
        columns = ['ortho','lemme','cgram','genre','freqlemfilms2','freqlemlivres']
        with (self.root/'lexique.tsv').open('w', newline='') as stream:
            writer=csv.writer(stream,delimiter='\t')
            writer.writerow(columns)
            writer.writerows([['chat','chat','NOM','m',30,25],['chien','chien','NOM','m',20,15]])
        with gzip.open(self.root/'kaikki.gz','wt') as stream:
            for word, gloss in [('chat','cat'),('chien','dog')]:
                stream.write(json.dumps({'word':word,'lang_code':'fr','pos':'noun','senses':[{'glosses':[gloss],'id':'fixture-'+word}]})+'\n')
        rows = [
          (1,'Le chat noir dort près de la fenêtre.',101,'The black cat sleeps by the window.'),
          (2,'Mon chat aime se cacher sous cette table.',102,'My cat likes hiding under this table.'),
          (3,'Le chien attend devant la grande porte.',103,'The dog waits in front of the big door.'),
          (4,'Notre chien aime courir dans le jardin.',104,'Our dog likes running in the garden.')]
        for name,lang,index,text_index in [('fra.bz2','fra',0,1),('eng.bz2','eng',2,3)]:
            with bz2.open(self.root/name,'wt') as stream:
                for row in rows:
                    stream.write(f'{row[index]}\t{lang}\t{row[text_index]}\tfixture-author\t2026-01-01\t2026-01-01\n')
        links=''.join(f'{row[0]}\t{row[2]}\n{row[2]}\t{row[0]}\n' for row in rows).encode()
        with tarfile.open(self.root/'links.tar.bz2','w:bz2') as archive:
            member=tarfile.TarInfo('links.csv'); member.size=len(links)
            archive.addfile(member,io.BytesIO(links))
        self.files={'kaikki':'kaikki.gz','lexique':'lexique.tsv','french':'fra.bz2','english':'eng.bz2','links':'links.tar.bz2'}
        manifest={key:{'file':name,'url':'https://example.invalid/'+name,
                       'sha256':hashlib.sha256((self.root/name).read_bytes()).hexdigest(),
                       'retrieved_at':'2026-01-01T00:00:00+00:00'} for key,name in self.files.items()}
        (self.root/'downloads.json').write_text(json.dumps(manifest))

    def build(self, minimum=2):
        return build_catalog(self.root,self.output,limit=max(2,minimum),minimum_lessons=minimum,
                             minimum_rank=1,maximum_rank=100,progress=lambda text:None)

    def test_builds_relational_attributed_readonly_catalog(self):
        self.assertEqual(self.build(),2)
        catalog=LessonCatalog(self.output)
        self.assertEqual(catalog.validate(),2)
        with catalog.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sentences').fetchone()[0],4)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM lessons")
        lesson=catalog.lesson_at(0)
        self.assertEqual(len(lesson['cards']),3)
        self.assertNotEqual(lesson['cards'][0]['example'],lesson['cards'][1]['example'])
        self.assertIn('fixture-author',lesson['cards'][0]['sources'][1]['name'])
        self.assertTrue(all(source['license_url'].startswith('https://') for source in lesson['cards'][0]['sources']))
        self.assertEqual(catalog.lesson_at(2),lesson)

    def test_failed_build_keeps_original_database_and_rejects_corrupt_sources(self):
        self.build()
        before=self.output.read_bytes()
        with self.assertRaises(ValueError): self.build(minimum=3)
        self.assertEqual(self.output.read_bytes(),before)
        (self.root/'lexique.tsv').write_text('damaged source')
        with self.assertRaisesRegex(ValueError,'checksum'):self.build()
        self.assertEqual(self.output.read_bytes(),before)

    def test_selection_is_deterministic_for_same_inputs(self):
        self.build()
        before=[LessonCatalog(self.output).lesson_at(i)['stable_id'] for i in range(2)]
        self.build()
        after=[LessonCatalog(self.output).lesson_at(i)['stable_id'] for i in range(2)]
        self.assertEqual(before,after)

    def test_filters_names_ambiguous_verb_forms_and_multiple_sentences(self):
        path=self.root/'collisions.bz2'
        with bz2.open(path,'wt') as stream:
            for sid,text in [(1,'Mon chien Cookie dort près de la fenêtre.'),
                             (2,'Ces cookies au chocolat sont vraiment délicieux.'),
                             (3,'Nous avons du double vitrage dans la maison.'),
                             (4,'Je vais doubler la quantité de farine.')]:
                stream.write(f'{sid}\tfra\t{text}\tfixture-author\n')
        entries={('cookie','noun'):{'lemma':'cookie','pos':'noun','forms':{'cookie','cookies'}},
                 ('doubler','verb'):{'lemma':'doubler','pos':'verb','forms':{'doubler','double'}}}
        french,inverse,scores=french_candidates(path,entries)
        self.assertNotIn(1,french)
        self.assertNotIn(3,french)
        self.assertEqual(set(french),{2,4})
        self.assertFalse(safe_sentence('Va donc là ! Reviens tout de suite !','fra'))

    def test_existing_user_state_migrates_without_losing_progress(self):
        directory=self.root/'user'
        directory.mkdir()
        with sqlite3.connect(directory/'home.sqlite3') as db:
            db.execute('CREATE TABLE state (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            db.execute('INSERT INTO state VALUES (?,?)',('selection',json.dumps({'app':'french','card':2})))
        store=Store(directory)
        self.assertEqual(store.get('selection'),{'app':'french','card':2})
        first=store.daily_lesson('2026-10-24',lambda:CATALOG.lesson_at(0))
        second=Store(directory).daily_lesson('2026-10-24',lambda:CATALOG.lesson_at(1))
        self.assertEqual(first,second)
        self.assertNotEqual(store.daily_lesson('2026-10-25',lambda:CATALOG.lesson_at(1))['stable_id'],first['stable_id'])

    def test_offline_catalog_access_never_uses_network(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('Network must not be used')):
            self.assertEqual(len(lesson_for('2026-10-24','2026-10-24')['cards']),3)
            self.assertGreater(CATALOG.validate(),0)

    def test_missing_or_unsupported_catalog_fails_clearly(self):
        with self.assertRaisesRegex(RuntimeError,'missing'):LessonCatalog(self.root/'missing').validate()
        self.build()
        with sqlite3.connect(self.output) as db:db.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(RuntimeError,'schema'):LessonCatalog(self.output).validate()


if __name__=='__main__':unittest.main()
