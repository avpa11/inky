import io
import gzip
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from scripts.fetch_french_sources import fetch


class Response(io.BytesIO):
    headers = {'Content-Length': '2'}


class SourceDownloadTests(unittest.TestCase):
    def test_transient_failure_retries_and_replaces_only_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'kaikki.jsonl.gz'
            target.write_bytes(b'previous working export')
            def attempt(*args, **kwargs):
                self.assertEqual(target.read_bytes(), b'previous working export')
                if open_url.call_count == 1:
                    raise URLError('temporary timeout')
                return Response(b'{}')
            with patch('scripts.fetch_french_sources.urlopen', side_effect=attempt) as open_url, patch('scripts.fetch_french_sources.time.sleep'):
                key, metadata = fetch('kaikki', root, True)
            self.assertEqual(open_url.call_count, 2)
            self.assertEqual(target.read_bytes(), b'{}')
            self.assertEqual(metadata['bytes'], 2)
            self.assertFalse(list(root.glob('*.part')))

    def test_lexique_mirror_verifies_archive_and_original_bytes(self):
        original = b'ortho\tlemme\nbonjour\tbonjour\n'
        compressed = gzip.compress(original, mtime=0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('scripts.fetch_french_sources.urlopen', return_value=Response(compressed)), patch('scripts.fetch_french_sources.LEXIQUE_GZIP_SHA256', hashlib.sha256(compressed).hexdigest()), patch('scripts.fetch_french_sources.LEXIQUE_SHA256', hashlib.sha256(original).hexdigest()):
                _, metadata = fetch('lexique', root, True)
            self.assertEqual((root/'lexique.tsv').read_bytes(), original)
            self.assertIn('github.com/avpa11/inky/releases/', metadata['download_url'])
            self.assertIn('lexique.org', metadata['url'])
            # A corrupt mirror response must never replace the verified previous TSV.
            with patch('scripts.fetch_french_sources.urlopen', return_value=Response(b'corrupt')):
                with self.assertRaisesRegex(ValueError, 'archive checksum'):fetch('lexique', root, True)
            self.assertEqual((root/'lexique.tsv').read_bytes(), original)
            self.assertFalse(list(root.glob('*.part')))
            # Even a correctly hashed archive must contain the expected original TSV.
            with patch('scripts.fetch_french_sources.urlopen', return_value=Response(compressed)), patch('scripts.fetch_french_sources.LEXIQUE_GZIP_SHA256', hashlib.sha256(compressed).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'TSV checksum'):fetch('lexique', root, True)
            self.assertEqual((root/'lexique.tsv').read_bytes(), original)

    def test_permanent_failure_keeps_old_export_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'kaikki.jsonl.gz'
            target.write_bytes(b'previous')
            error = HTTPError('https://kaikki.org/', 404, 'missing', {}, None)
            with patch('scripts.fetch_french_sources.urlopen', side_effect=error) as open_url:
                with self.assertRaises(HTTPError):fetch('kaikki', root, True)
            self.assertEqual(open_url.call_count, 1)
            self.assertEqual(target.read_bytes(), b'previous')

    def test_retries_are_bounded_and_keep_old_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'kaikki.jsonl.gz'
            target.write_bytes(b'previous')
            with patch('scripts.fetch_french_sources.urlopen', side_effect=URLError('timeout')) as open_url, patch('scripts.fetch_french_sources.time.sleep'):
                with self.assertRaises(URLError):fetch('kaikki', root, True)
            self.assertEqual(open_url.call_count, 3)
            self.assertEqual(target.read_bytes(), b'previous')
            self.assertFalse(list(root.glob('*.part')))


if __name__ == '__main__':unittest.main()
