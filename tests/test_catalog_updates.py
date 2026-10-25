import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from inky_home import catalog_updates as updates
from inky_home.lessons import CATALOG, LessonCatalog
from inky_home.service import Dashboard
from inky_home.store import Store
from inky_home.display import PreviewDisplay
from inky_home.weather import SampleWeatherClient
from inky_home.web import create_app


class CatalogUpdatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root)
        self.home = Dashboard(self.store, PreviewDisplay(), SampleWeatherClient(), sample=True)

    def tearDown(self):
        self.home.close()
        self.temp.cleanup()

    def test_explore_preserves_daily_and_restart_and_avoids_seen_words(self):
        daily = self.home.snapshot()['lesson']
        self.home.explore()
        first = self.home.snapshot()['lesson']
        self.assertNotEqual(first['theme'], daily['theme'])
        for _ in range(3): self.home.action('D')
        second = self.home.snapshot()['lesson']
        self.assertNotIn(second['theme'], [first['theme'], daily['theme']])
        restored = Dashboard(Store(self.root), PreviewDisplay(), SampleWeatherClient(), sample=True)
        self.assertEqual(restored.snapshot()['lesson'], second)
        restored.browse(None)
        self.assertEqual(restored.snapshot()['lesson'], daily)
        restored.close()

    def test_identity_survives_changed_examples_and_legacy_day_migration(self):
        lesson = CATALOG.lesson_at(0)
        lesson.pop('lexeme_id')
        self.store.daily_lesson('2026-01-01', lambda: lesson)
        self.assertIn(lesson['theme'].casefold(), Store(self.root).seen_words())
        self.assertNotEqual(self.home.next_lesson()['theme'], lesson['theme'])

    def test_exhaustion_is_explicit_and_daily_can_review(self):
        for _, word in CATALOG.identities(): self.store.remember({'theme':word})
        with self.assertRaisesRegex(ValueError, 'every word'): self.home.explore()
        self.assertTrue(self.home.next_lesson(review=True)['review'])

    def manifest(self, payload):
        return json.dumps({'tag':'french-catalog-test', 'bytes':len(payload),
            'sha256':hashlib.sha256(payload).hexdigest()}).encode()

    def test_download_validation_activation_and_offline_restart(self):
        payload = CATALOG.path.read_bytes()
        with patch.object(updates, 'read_url', side_effect=[self.manifest(payload), payload]):
            installed = updates.download_catalog(self.root, CATALOG)
        self.assertEqual(installed.validate(), CATALOG.count)
        with patch.object(updates, 'read_url', side_effect=OSError('offline')):
            self.assertEqual(updates.installed_catalog(self.root, CATALOG).path, installed.path)
        before = (self.root/'catalog-current').read_text()
        manifest = self.manifest(payload)
        with patch.object(updates, 'read_url', side_effect=[manifest, b'corrupt']):
            with self.assertRaises(ValueError): updates.download_catalog(self.root, CATALOG)
        self.assertEqual((self.root/'catalog-current').read_text(), before)

    def test_invalid_database_and_oversize_are_rejected(self):
        payload = b'not a sqlite database'
        with patch.object(updates, 'read_url', side_effect=[self.manifest(payload), payload]):
            with self.assertRaises(Exception): updates.download_catalog(self.root, CATALOG)
        self.assertFalse((self.root/'catalog-current').exists())
        manifest = json.loads(self.manifest(payload));manifest['bytes'] = updates.MAX_BYTES+1
        with patch.object(updates, 'read_url', return_value=json.dumps(manifest)):
            with self.assertRaises(ValueError):updates.download_catalog(self.root, CATALOG)

    def test_controls_and_sources_use_active_catalog(self):
        client = create_app(self.home).test_client()
        self.assertEqual(client.post('/api/french/explore',json={}).status_code,200)
        self.assertEqual(client.get('/api/status').json['selection']['french_mode'],'explore')
        self.assertEqual(client.post('/api/french/day',json={'day':None}).status_code,200)
        self.assertEqual(client.post('/api/french/update',json={}).status_code,200)
        self.assertTrue(self.home.catalog_event.is_set())
        self.assertEqual(client.get('/api/french/sources').json['metadata'], self.home.catalog.metadata)


if __name__ == '__main__':unittest.main()
