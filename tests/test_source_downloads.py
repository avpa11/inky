import io
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
