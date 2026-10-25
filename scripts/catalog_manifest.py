"""Create release metadata after a successful corpus build."""
import argparse
import hashlib
import json
from pathlib import Path
from inky_home.lessons import LessonCatalog

parser = argparse.ArgumentParser()
parser.add_argument('--tag', required=True)
parser.add_argument('--database', type=Path, default=Path('inky_home/data/french.sqlite3'))
parser.add_argument('--output', type=Path, default=Path('catalog.json'))
args = parser.parse_args()
catalog = LessonCatalog(args.database)
catalog.validate()
payload = args.database.read_bytes()
args.output.write_text(json.dumps({'schema': 1, 'tag': args.tag, 'sha256': hashlib.sha256(payload).hexdigest(),
    'bytes': len(payload), 'lessons': catalog.count, 'built_at': catalog.metadata['built_at']}, indent=2) + '\n')
