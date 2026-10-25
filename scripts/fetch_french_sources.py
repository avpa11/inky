"""Download official corpus exports on the Mac; never run during Pi installation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import ssl
from urllib.request import urlopen

import certifi

SOURCES = {
    'kaikki': ('kaikki.jsonl.gz', 'https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl.gz'),
    'lexique': ('lexique.tsv', 'https://www.lexique.org/databases/Lexique383/Lexique383.tsv'),
    'french': ('fra.tsv.bz2', 'https://downloads.tatoeba.org/exports/per_language/fra/fra_sentences_detailed.tsv.bz2'),
    'english': ('eng.tsv.bz2', 'https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_detailed.tsv.bz2'),
    'links': ('links.tar.bz2', 'https://downloads.tatoeba.org/exports/links.tar.bz2'),
}


def fetch(key, directory, refresh=False):
    name, url = SOURCES[key]
    target = directory / name
    modified = None
    if refresh or not target.exists():
        temporary = target.with_suffix(target.suffix + '.part')
        context = ssl.create_default_context(cafile=certifi.where())
        try:
            with urlopen(url, timeout=60, context=context) as response, temporary.open('wb') as out:
                modified = response.headers.get('Last-Modified')
                expected = int(response.headers.get('Content-Length', 0))
                count = 0
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > 2_000_000_000:
                        raise ValueError('Unexpectedly large source export')
                    out.write(chunk)
                if expected and count != expected:
                    raise ValueError('Incomplete source download')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256()
    with target.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    result = {'file': name, 'url': url, 'bytes': target.stat().st_size,
              'sha256': digest.hexdigest(), 'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'last_modified': modified}
    print(f'{key}: {result["bytes"]:,} bytes, SHA256 {result["sha256"][:16]}', flush=True)
    return key, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('var-corpus'))
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(lambda key: fetch(key, args.directory, args.refresh), SOURCES))
    path = args.directory / 'downloads.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)
    print(f'Metadata: {path}')


if __name__ == '__main__':
    main()
