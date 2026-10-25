# Security and privacy

## Intended deployment

Inky Home is a single-user application for a trusted home network. It has no login:
anyone who can reach the local service can view its preview, saved city and lessons,
and use its controls. Do not forward port 8080, publish it through an internet tunnel,
or expose it to an untrusted shared network. A public GitHub repository does not
publish the running Pi service or grant SSH access.

The service rejects untrusted Host headers (browser DNS rebinding), cross-site control
requests and non-JSON mutations. It limits request bodies, uses a content security
policy and parameterized SQL, verifies HTTPS certificates, and serializes hardware
writes. These controls do not replace network access control or authentication.

## Data in the public repository

The repository contains application code, attributed public French language data,
a sample preview, documentation, and a non-sensitive workflow timestamp marker.
It must not contain passwords, private SSH keys, access tokens, `.env` files, logs,
user databases, location preferences, or learning history. These are ignored by Git;
common credential files are also excluded from deployment. Git ignore rules do not
protect files deliberately added with force or information already committed.

Commit author names/emails and licensed source contributor names are public. The
sample preview uses sample locations. Your selected city and progress remain in the
Pi's runtime database. Weather requests send saved city coordinates to Open-Meteo;
GitHub sees ordinary catalog-download requests, but no learning-history upload.

## Updates and workflow credentials

Catalog updates contain data only. HTTPS, size limits, SHA-256 checks and SQLite
validation run before activation; a failure keeps the previous catalog. Checksums
protect integrity, not against compromise of the repository owner account. Protect
your GitHub account with strong authentication; no Pi credentials are stored there.

The catalog workflow uses a short-lived built-in token only for its activity marker
and release publishing steps. Checkout does not persist that token for build steps.
Official actions are pinned to immutable commit IDs. There are no workflows that
execute pull-request code with repository write credentials.

## Review and limits

The 2026-10-24 review scanned reachable Git history with Gitleaks, checked GitHub
secret-scanning alerts, inspected tracked files and public data, reviewed web controls
and updater/workflow code, and audited Python runtime dependencies with pip-audit.
Known Pillow issues were addressed by requiring version 13.0 or newer; the Pi’s
older certificate bundle was replaced by requiring certifi 2026.10.19 or newer. Regression
tests cover untrusted Host rejection and checksum failures preserving prior data.

This is a targeted code/dependency review, not a guarantee that no vulnerabilities
exist. It does not audit your router, Mac security, Raspberry Pi OS packages, Python's
bundled libraries, or other software running on the Pi. Keep those updated separately.

## Reporting

Do not put credentials or private runtime data in a public issue. For a suspected
secret exposure, revoke the credential first; deleting a file does not remove it
from Git history or copies already downloaded.
