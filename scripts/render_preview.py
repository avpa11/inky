"""Render a sample of both apps without GPIO or network access."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from inky_home.display import PreviewDisplay
from inky_home.render import render
from inky_home.service import Dashboard
from inky_home.store import Store
from inky_home.weather import SampleWeatherClient


def main():
    now = datetime(2026, 10, 24, 15, 0, tzinfo=timezone.utc)
    with TemporaryDirectory() as directory:
        home = Dashboard(Store(directory), PreviewDisplay(), SampleWeatherClient(),
                         sample=True, clock=lambda: now)
        home.update_settings({'city': {'name': 'Paris', 'region': 'Île-de-France',
            'country': 'France', 'latitude': 48.85, 'longitude': 2.35, 'timezone': 'Europe/Paris'}})
        home.cache = SampleWeatherClient().fetch(home.settings['city'], now)
        home.cache['source'] = 'sample'
        snapshot = home.snapshot()
        weather = render(snapshot)
        snapshot['selection']['app'] = 'french'
        french = render(snapshot)
        sheet = Image.new('RGB', (1200, 400), 'white')
        sheet.paste(weather, (0, 0))
        sheet.paste(french, (600, 0))
        output = Path(__file__).resolve().parents[1] / 'docs' / 'preview.png'
        output.parent.mkdir(exist_ok=True)
        sheet.save(output)
        credits = ['# Preview attribution', '', 'The weather is sample data. French content comes from the bundled offline catalog.', '']
        for card in snapshot['lesson']['cards']:
            credits += ['## ' + card['kind'], '']
            for source in card.get('sources', []):
                credits.append('- [' + source['name'] + '](' + source['url'] + ') · [' + source['license'] + '](' + source['license_url'] + ')')
            credits.append('')
        output.with_name('preview-sources.md').write_text('\n'.join(credits))
        print(output)


if __name__ == '__main__':
    main()
