"""Record repository activity before a catalog build, using its built-in Actions token.

Only the timestamp marker is written. Run on GitHub Actions, never on the Pi.
"""
import base64
from datetime import datetime, timezone
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('This script runs only inside GitHub Actions.')
    repository = os.environ['GITHUB_REPOSITORY']
    branch = os.environ['CATALOG_DEFAULT_BRANCH']
    if os.environ['GITHUB_REF'] != 'refs/heads/' + branch:
        raise SystemExit('Catalog activity can only be recorded from the default branch.')
    endpoint = 'https://api.github.com/repos/' + repository + '/contents/.github/catalog-heartbeat.json'
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
               'Accept': 'application/vnd.github+json',
               'User-Agent': 'inky-catalog-activity'}
    marker = {'last_run_started_at': datetime.now(timezone.utc).isoformat(),
              'run_id': os.environ['GITHUB_RUN_ID'],
              'run_attempt': os.environ['GITHUB_RUN_ATTEMPT']}
    payload = {'message': 'Keep monthly French catalog updates active', 'branch': branch,
               'content': base64.b64encode((json.dumps(marker, indent=2) + '\n').encode()).decode()}
    for attempt in range(3):
        try:
            with urlopen(Request(endpoint + '?ref=' + quote(branch, safe=''), headers=headers), timeout=20) as response:
                payload['sha'] = json.load(response)['sha']
        except HTTPError as exc:
            if exc.code != 404:
                raise
            payload.pop('sha', None)
        request = Request(endpoint, data=json.dumps(payload).encode(),
                          headers={**headers, 'Content-Type': 'application/json'}, method='PUT')
        try:
            with urlopen(request, timeout=20) as response:
                result = json.load(response)
            print('Recorded monthly catalog activity:', result['commit']['sha'])
            return
        except HTTPError as exc:
            if exc.code != 409 or attempt == 2:
                raise
    raise RuntimeError('Could not record catalog activity')


if __name__ == '__main__':
    main()
