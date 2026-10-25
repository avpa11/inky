"""Build the offline French catalog from sources downloaded on your Mac."""
import argparse
from pathlib import Path

from inky_home.corpus import build_catalog
from inky_home.lessons import LessonCatalog



def write_notices(database):
    catalog = LessonCatalog(database)
    lines = ['# Offline French data sources', '',
        'The adapted dictionary/frequency selection and authored usage notes are shared under',
        '[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).',
        'Individual Tatoeba sentence and translation texts retain CC BY 2.0 FR and their',
        'contributor attribution. Some Tatoeba contributions are additionally CC0 at source; those original rights are unaffected.',
        'No audio, dictionary quotations, or external example quotations are used.', '',
        'Source records, sense IDs, contributor names, and individual sentence URLs are retained',
        'in the SQLite database and shown by the local web app. Source text is selected and joined,',
        'not rewritten. Usage rules in lessons.py are authored application content, not corpus grammar lessons.', '',
        'Difficulty is a frequency-based intermediate estimate, not a verified CEFR classification.',
        'Sentence-to-sense matching uses lexical overlap and can be imperfect. Definitions may have',
        'other senses; consult each linked entry. Raw corpora remain on the Mac.', '']
    for source in catalog.sources():
        lines += ['## ' + source['name'], '', source['attribution'], '',
                  '- Export: ' + source['url'], '- License: [' + source['license'] + '](' + source['license_url'] + ')',
                  '- Retrieved: ' + source['retrieved_at'], '- SHA256: `' + source['sha256'] + '`', '']
    lines += ['## Rebuild', '', 'See the project README for download and build commands.',
              'The importer verifies the manifest checksums before reading inputs.',
              'Input selection is deterministic; source export URLs can change over time.', '']
    database.with_name('SOURCES.md').write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=Path('var-corpus'))
    parser.add_argument('--output', type=Path, default=Path('inky_home/data/french.sqlite3'))
    parser.add_argument('--limit', type=int, default=730)
    parser.add_argument('--minimum-lessons', type=int, default=365)
    parser.add_argument("--minimum-rank", type=int, default=500)
    parser.add_argument("--maximum-rank", type=int, default=10000)
    args = parser.parse_args()
    if args.limit < args.minimum_lessons or args.minimum_lessons < 1:
        parser.error('Limit must be at least minimum-lessons, which must be positive')
    if not 1 <= args.minimum_rank <= args.maximum_rank:
        parser.error("Frequency ranks must be positive and ordered")
    build_catalog(args.sources, args.output, args.limit, args.minimum_lessons,
                  args.minimum_rank, args.maximum_rank,
                  progress=lambda message: print(message, flush=True))
    write_notices(args.output)


if __name__ == '__main__':
    main()
