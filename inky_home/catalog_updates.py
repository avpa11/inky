"""Download data only. Never execute code or install dependencies from a catalog."""
import hashlib
import json
import logging
from pathlib import Path
import ssl
import time
from urllib.request import urlopen

import certifi
from .lessons import LessonCatalog

BASE = 'https://github.com/avpa11/inky/releases/'
MANIFEST = BASE + 'latest/download/catalog.json'
MAX_BYTES = 20 * 1024 * 1024


def read_url(url, limit):
    with urlopen(url, timeout=15, context=ssl.create_default_context(cafile=certifi.where())) as response:
        chunks, size = [], 0
        deadline = time.monotonic() + 60
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError('Catalog download timed out')
            chunk = response.read(min(65536, limit + 1 - size))
            if not chunk:
                return b''.join(chunks)
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise ValueError('Catalog download exceeds size limit')


def installed_catalog(directory, fallback):
    try:
        name = (Path(directory) / 'catalog-current').read_text().strip()
        if Path(name).name != name or not name.startswith('catalog-') or not name.endswith('.sqlite3'):
            raise ValueError('Invalid installed catalog path')
        catalog = LessonCatalog(Path(directory) / name)
        catalog.validate()
        if catalog.metadata['built_at'] < fallback.metadata['built_at']:
            return fallback
        return catalog
    except Exception as exc:
        # A damaged downloaded file must not prevent startup with the bundled catalog.
        if (Path(directory) / 'catalog-current').exists():
            logging.getLogger(__name__).warning('Using bundled catalog: %s', exc)
        return fallback


def download_catalog(directory, current):
    manifest = json.loads(read_url(MANIFEST, 16384))
    digest = manifest['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid catalog checksum')
    tag = manifest['tag']
    if not isinstance(tag, str) or not tag.startswith('french-catalog-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-.' for c in tag):
        raise ValueError('Invalid catalog release')
    size = manifest['bytes']
    if not isinstance(size, int) or not 1 <= size <= MAX_BYTES:
        raise ValueError('Invalid catalog size')
    directory = Path(directory)
    target = directory / ('catalog-' + digest + '.sqlite3')
    if current.path == target.resolve():
        return None
    payload = read_url(BASE + 'download/' + tag + '/french.sqlite3', MAX_BYTES)
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError('Catalog checksum or size mismatch')
    temporary = directory / 'catalog-download.tmp'
    try:
        temporary.write_bytes(payload)
        candidate = LessonCatalog(temporary)
        candidate.validate()
        if candidate.metadata['built_at'] < current.metadata['built_at']:
            raise ValueError('Refusing an older catalog')
        # Validate every card before activation. Existing daily assignments stay pinned.
        for index in range(candidate.count):
            lesson = candidate.lesson_at(index)
            if len(lesson['cards']) != 3 or not lesson['theme']:
                raise ValueError('Invalid catalog lesson')
        temporary.replace(target)
        pointer = directory / 'catalog-current.tmp'
        pointer.write_text(target.name)
        pointer.replace(directory / 'catalog-current')
        for old in directory.glob('catalog-*.sqlite3'):
            if old.resolve() not in (target.resolve(), current.path):
                old.unlink(missing_ok=True)
        return LessonCatalog(target)
    finally:
        temporary.unlink(missing_ok=True)
