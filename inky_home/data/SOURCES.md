# Offline French data sources

The adapted dictionary/frequency selection and authored usage notes are shared under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Individual Tatoeba sentence and translation texts retain CC BY 2.0 FR and their
contributor attribution. Some Tatoeba contributions are additionally CC0 at source; those original rights are unaffected.
No audio, dictionary quotations, or external example quotations are used.

Source records, sense IDs, contributor names, and individual sentence URLs are retained
in the SQLite database and shown by the local web app. Source text is selected and joined,
not rewritten. Usage rules in lessons.py are authored application content, not corpus grammar lessons.

Difficulty is a frequency-based intermediate estimate, not a verified CEFR classification.
Sentence-to-sense matching uses lexical overlap and can be imperfect. Definitions may have
other senses; consult each linked entry. Raw corpora remain on the build computer.

## Tatoeba English translations

Individual contributors, credited by name and sentence URL

- Export: https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_detailed.tsv.bz2
- License: [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/)
- Retrieved: 2026-10-25T03:33:19.326067+00:00
- SHA256: `c39d2fab0cc5bc2b798b539134b83abaf5dec723a059ce55496907d08e3e9030`

## Tatoeba French sentences

Individual contributors, credited by name and sentence URL

- Export: https://downloads.tatoeba.org/exports/per_language/fra/fra_sentences_detailed.tsv.bz2
- License: [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/)
- Retrieved: 2026-10-25T03:33:19.227075+00:00
- SHA256: `07208a7630b7ec3e51d9cbbcd5112295cdba41de82cf35d41ab8797ae9a5802e`

## Wiktionary via Kaikki

Wiktionary contributors; extraction by Tatu Ylonen / Wiktextract

- Export: https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl.gz
- License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- Retrieved: 2026-10-25T03:33:13.579566+00:00
- SHA256: `5b1f453229d0024c12df8a110c054c2b194d496a9c71d06f0acf4c2e72141c9c`

## Lexique 3.83

Boris New, Christophe Pallier and Lexique/OpenLexicon contributors

- Export: https://www.lexique.org/databases/Lexique383/Lexique383.tsv
- License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- Retrieved: 2026-10-25T03:33:13.561082+00:00
- SHA256: `637ba37a767a66679c48371d673ece50cbf541b49a4e40e598963d4f3fbce52b`

## Tatoeba translation links

Tatoeba contributors

- Export: https://downloads.tatoeba.org/exports/links.tar.bz2
- License: [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/)
- Retrieved: 2026-10-25T03:33:32.749714+00:00
- SHA256: `f180bcdf64de8fb41ba1e8275b7601c14ed820cb64430867b4ff491b01c13789`

## Rebuild

See the project README for download and build commands.
The importer verifies the manifest checksums before reading inputs.
Input selection is deterministic; source export URLs can change over time.
