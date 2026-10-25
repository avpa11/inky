import copy
import io
import tempfile
import threading
import time
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PIL import Image, ImageDraw
from inky_home.display import PreviewDisplay, InkyDisplay
from inky_home.lessons import LESSONS, learning_day, lesson_for
from inky_home.render import render, temp
from inky_home.service import Dashboard, RateLimited
from inky_home.store import Store
from inky_home.weather import SampleWeatherClient, normalize, validate_city
from inky_home.weather_art import weather_icon
from inky_home.palette import COLORS, indexed_image
from inky_home.web import create_app

CITY = {"name": "San Francisco", "region": "California", "country": "United States",
        "latitude": 37.7749, "longitude": -122.4194, "timezone": "America/Los_Angeles"}


def wait_for(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError("Timed out waiting for worker")


class RecordingDisplay(PreviewDisplay):
    def __init__(self):
        self.calls = 0
        self.active = 0
        self.overlapped = False
        self.entered = threading.Event()
        self.release = threading.Event()
        self.block = False

    def show(self, image):
        self.active += 1
        self.overlapped |= self.active > 1
        self.calls += 1
        self.entered.set()
        if self.block:
            self.release.wait(3)
        self.active -= 1


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        self.store = Store(self.temp.name)
        self.display = RecordingDisplay()
        self.home = Dashboard(self.store, self.display, SampleWeatherClient(), sample=True, clock=lambda: self.now)
        self.client = create_app(self.home).test_client()

    def tearDown(self):
        self.display.release.set()
        self.home.close()
        self.temp.cleanup()

    def configured(self):
        self.home.update_settings({"city": CITY})
        self.home.cache = SampleWeatherClient().fetch(CITY, self.now)
        self.home.cache["source"] = "sample"
        self.home.fetch_requested = False
        self.home.fetch_event.clear()

    def test_settings_and_selection_survive_restart(self):
        self.configured()
        self.home.update_settings({"units": "F", "rollover": "08:30"})
        self.home.select("french")
        self.home.action("D")
        restored = Dashboard(self.store, PreviewDisplay(), SampleWeatherClient(), True, lambda: self.now)
        self.assertEqual(restored.settings["units"], "F")
        self.assertEqual(restored.settings["timezone"], CITY["timezone"])
        self.assertEqual(restored.state["card"], 1)
        self.assertEqual(restored.state["app"], "french")

    def test_rollover_timezone_dst_and_history(self):
        self.home.select("french")
        self.home.action("D")
        self.now += timedelta(hours=22)  # Next local day, before 7am.
        self.home.tick()
        self.assertEqual(self.home.state["card"], 1)
        self.now += timedelta(hours=2)
        self.home.tick()
        self.assertEqual(self.home.state["card"], 0)
        self.home.browse("2026-10-25")
        self.assertEqual(self.home.snapshot()["lesson"]["id"], 1)
        with self.assertRaises(ValueError): self.home.browse("2026-10-27")
        self.assertEqual(learning_day(datetime(2026, 11, 1, 14, 59, tzinfo=timezone.utc), CITY['timezone'], '07:00'), '2026-10-31')
        self.assertEqual(learning_day(datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc), CITY['timezone'], '07:00'), '2026-11-01')

    def test_validation_and_failed_settings_are_atomic(self):
        before = copy.deepcopy(self.home.settings)
        for payload in ({"units":"K"}, {"timezone":"Mars/Base"}, {"rollover":"25:00"}, {"rollover":None}, {"units":[]}, {"city":{"name":"Missing coordinates"}}):
            self.assertEqual(self.client.post('/api/settings', json=payload).status_code, 400)
            self.assertEqual(self.home.settings, before)
        self.assertEqual(self.client.post('/api/action', json={"button":None}).status_code, 400)
        self.assertEqual(self.client.post('/api/app', json={"app":[]}).status_code, 400)
        self.assertEqual(self.client.post('/api/settings', json=[]).status_code, 400)
        self.assertEqual(self.client.post('/api/french/day', json={"day":1}).status_code, 400)
        self.assertEqual(self.client.post('/api/settings', data='{}').status_code, 415)
        self.assertEqual(self.client.post('/api/app', json={"app":"french"}, headers={"Origin":"http://evil.test"}).status_code, 403)

    def test_weather_manual_rate_limit(self):
        self.configured()
        self.home.action("D")
        with self.assertRaises(RateLimited): self.home.action("D")
        self.now += timedelta(seconds=60)
        self.home.action("D")

    def test_hardware_initialization_failure_keeps_web_controls_available(self):
        driver = types.ModuleType("inky.auto")
        def unavailable():
            raise OSError("I2C device unavailable")
        driver.auto = unavailable
        self.home.display = InkyDisplay()
        with patch.dict(sys.modules, {"inky": types.ModuleType("inky"), "inky.auto": driver}):
            self.home.start()
            wait_for(lambda: self.home.display_error)
            self.assertEqual(self.client.get('/api/status').status_code, 200)
            self.assertEqual(self.client.post('/api/app', json={"app":"french"}).status_code, 200)
            self.assertIsNone(self.home.display.device)
            self.assertIn("I2C", self.home.snapshot()["display_error"])

    def test_weather_cache_not_shared_across_locations_or_modes(self):
        self.configured()
        self.assertIsNotNone(self.home.usable_cache())
        self.home.update_settings({"city":{**CITY, "name":"Paris", "latitude":48.85, "longitude":2.35, "timezone":"Europe/Paris"}})
        self.assertIsNone(self.home.usable_cache())
        self.assertEqual(self.home.settings["timezone"], "Europe/Paris")
        self.home.update_settings({"city":CITY, "timezone":"UTC"})
        self.assertEqual(self.home.settings["timezone"], "UTC")
        self.store.put(weather_cache=self.home.cache)
        live = Dashboard(self.store, PreviewDisplay(), SampleWeatherClient(), False, lambda: self.now)
        self.assertIsNone(live.usable_cache())

    def test_weather_failure_keeps_cache_and_french_usable(self):
        self.configured()
        class Failing:
            def fetch(self, city, now): raise OSError("Offline")
        self.home.weather = Failing()
        self.home.queue_fetch()
        self.home.start()
        wait_for(lambda: self.home.fetch_error)
        self.assertTrue(self.home.is_stale())
        self.assertIsNotNone(self.home.usable_cache())
        self.home.select("french")
        self.home.action("D")
        wait_for(lambda: self.home.preview and not self.home.snapshot()["pending"])
        self.assertEqual(self.client.get('/api/preview.png').status_code, 200)
        self.assertEqual(self.home.state["card"], 1)
        # Offline restart uses the same persisted cache (save fixture first).
        self.store.put(weather_cache=self.home.cache)
        restored = Dashboard(self.store, PreviewDisplay(), Failing(), True, lambda: self.now)
        self.assertEqual(restored.usable_cache(), self.home.cache)

    def test_scheduler_refresh_and_stale_boundary(self):
        self.configured()
        self.home.last_fetch_attempt = self.now
        self.now += timedelta(seconds=3601)
        self.home.tick()
        self.assertTrue(self.home.fetch_requested)
        self.assertTrue(self.home.is_stale())

    def test_refresh_serialization_coalescing_and_api_responsiveness(self):
        self.configured()
        self.display.block = True
        self.home.start()
        self.assertTrue(self.display.entered.wait(2))
        start = time.monotonic()
        self.assertEqual(self.client.get('/api/status').status_code, 200)
        self.assertLess(time.monotonic() - start, .2)
        for _ in range(20):
            self.home.select("french")
            self.home.action("D")
        self.display.release.set()
        wait_for(lambda: not self.home.snapshot()["pending"])
        self.assertFalse(self.display.overlapped)
        self.assertEqual(self.display.calls, 2)
        calls = self.display.calls
        self.home.select("french")
        wait_for(lambda: not self.home.snapshot()["pending"])
        self.assertEqual(self.display.calls, calls)
        data = self.client.get('/api/preview.png').data
        self.assertEqual(Image.open(io.BytesIO(data)).size, (600,400))

    def test_city_change_during_network_request_discards_old_results(self):
        entered, release = threading.Event(), threading.Event()
        class SlowWeather:
            def fetch(self, city, now):
                entered.set()
                release.wait(2)
                return SampleWeatherClient().fetch(city, now)
        self.home.weather = SlowWeather()
        self.home.update_settings({"city": CITY})
        self.home.start()
        self.assertTrue(entered.wait(1))
        paris = {**CITY, "name":"Paris", "latitude":48.85, "longitude":2.35, "timezone":"Europe/Paris"}
        self.home.update_settings({"city":paris})
        release.set()
        wait_for(lambda: self.home.usable_cache())
        self.assertEqual(self.home.cache["location_key"], "48.85000,2.35000")

    def test_city_search_results_and_provider_failure(self):
        with patch('inky_home.web.search_cities', return_value=[CITY]):
            response = self.client.get('/api/cities?q=San')
            self.assertEqual(response.json['results'], [CITY])
        with patch('inky_home.web.search_cities', side_effect=OSError()):
            self.assertEqual(self.client.get('/api/cities?q=San').status_code, 502)

    def test_all_lessons_and_weather_variants_render(self):
        self.assertEqual(len(LESSONS), 90)
        self.assertEqual(len({x["cards"][0]["example"] for x in LESSONS}), 90)
        self.assertEqual(len({x["cards"][2]["example"] for x in LESSONS}), 90)
        snapshot = self.home.snapshot()
        snapshot["selection"]["app"] = "french"
        for lesson in LESSONS:
            snapshot["lesson"] = lesson
            for index in range(3):
                snapshot["selection"]["card"] = index
                image = render(snapshot)
                self.assertEqual(image.size, (600,400))
        self.configured()
        snapshot = self.home.snapshot()
        for view in ('today', 'three_days'):
            for units in ('C', 'F'):
                snapshot['selection']['weather_view'] = view
                snapshot['settings']['units'] = units
                snapshot['settings']['city']['name'] = 'Saint-Remy-en-Bouzemont-Saint-Genest-et-Isson / très longue ville'
                snapshot['weather']['temperature'] = None
                snapshot['weather']['days'][0]['high'] = None
                self.assertEqual(render(snapshot).size, (600,400))
        self.assertEqual(temp(0,'F'), '32°F')
        self.assertEqual(temp(None,'C'), '—')

    def test_normalize_missing_weather_fields(self):
        data = {'daily':{'time':['2026-10-25']}, 'current':{}}
        result = normalize(data, CITY, self.now)
        self.assertIsNone(result['temperature'])
        self.assertIsNone(result['days'][0]['high'])
        self.assertIsNone(result['rain'])
        with self.assertRaises(ValueError): normalize({}, CITY, self.now)
        with self.assertRaises(ValueError): validate_city({**CITY, 'latitude':float('nan')})

    def test_weather_illustrations_cover_conditions_and_stay_inside_their_box(self):
        for code in (0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65,
                     66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99, None):
            image = Image.new('RGB', (200, 160), '#dedede')
            weather_icon(ImageDraw.Draw(image), code, (20, 20, 160, 120))
            # Icons must not paint outside their allocated area into text/other days.
            for outside in ((0, 0, 200, 20), (0, 141, 200, 160), (0, 0, 20, 160), (181, 0, 200, 160)):
                self.assertEqual(len(image.crop(outside).getcolors()), 1)
            colors = {color for _, color in image.getcolors(maxcolors=10000)}
            self.assertGreater(len(colors), 1)
            if code == 0:
                self.assertIn((255, 255, 0), colors)
            if code in (61, 71, 45):
                self.assertIn((0, 0, 255), colors)
            if code is None:
                self.assertNotIn((255, 255, 0), colors)

    def test_french_cards_use_small_red_accents_and_solid_black_text(self):
        snapshot = self.home.snapshot()
        snapshot['selection']['app'] = 'french'
        for index in range(3):
            snapshot['selection']['card'] = index
            image = render(snapshot)
            colors = {color for _, color in image.getcolors(maxcolors=1_000_000)}
            self.assertIn((255, 0, 0), colors)
            self.assertIn((0, 0, 0), colors)
            self.assertLess(sum(count for count, color in image.getcolors(1_000_000) if color == (255, 0, 0)), 2000)
            self.assertLessEqual(colors, set(COLORS))


    def test_hardware_receives_exact_six_ink_palette_without_gray_text(self):
        sent = []
        device = types.SimpleNamespace(resolution=(600,400), set_image=sent.append, show=lambda: None)
        driver = types.ModuleType("inky.auto")
        driver.auto = lambda: device
        image = Image.new('RGB', (600,400), 'white')
        image.putpixel((0,0), (0,0,0))
        image.putpixel((1,0), (255,0,0))
        with patch.dict(sys.modules, {"inky": types.ModuleType("inky"), "inky.auto": driver}):
            InkyDisplay().show(image)
        panel = sent[0]
        self.assertEqual(panel.mode, 'P')
        self.assertEqual(len(panel.palette.colors), 6)  # E640's no-dither branch.
        self.assertEqual(panel.getpixel((0,0)), 0)  # Physical black ink.
        self.assertEqual(panel.getpixel((1,0)), 3)  # Physical red ink.
        self.assertEqual(panel.getpixel((2,0)), 1)  # Physical white ink.



    def test_all_six_inks_are_used_without_coloring_main_text(self):
        self.configured()
        snapshot = self.home.snapshot()
        for view in ('today', 'three_days'):
            snapshot['selection']['weather_view'] = view
            colors = {color for _, color in render(snapshot).getcolors(1_000_000)}
            self.assertEqual(colors, set(COLORS))
        snapshot['selection']['app'] = 'french'
        for index in range(3):
            snapshot['selection']['card'] = index
            image = render(snapshot)
            colors = {color for _, color in image.getcolors(1_000_000)}
            self.assertEqual(colors, set(COLORS))
            title_colors = {color for _, color in image.crop((24,89,576,156)).getcolors(1_000_000)}
            self.assertEqual(title_colors, {(0,0,0),(255,255,255)})


if __name__ == '__main__':
    unittest.main()
