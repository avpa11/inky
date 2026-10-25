import copy
import hashlib
import io
import logging
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import lessons
from .weather import location_key, validate_city
from .render import render

log = logging.getLogger(__name__)
DEFAULTS = {"city": None, "units": "C", "timezone": "America/Los_Angeles", "rollover": "07:00"}


class RateLimited(ValueError):
    pass


class Dashboard:
    """State under one short-held lock; network and panel I/O run on separate workers."""
    def __init__(self, store, display, weather, sample=False, clock=None):
        self.store, self.display, self.weather = store, display, weather
        self.sample = sample
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.changed = threading.Event()
        self.fetch_event = threading.Event()
        self.settings = {**DEFAULTS, **store.get("settings", {})}
        self.state = {"app": "weather", "weather_view": "today", "card": 0, "browse_day": None,
                      **store.get("selection", {})}
        day = self.day()
        self.progress = store.get("progress", {"anchor": day, "day": day})
        self.cache = store.get("weather_cache")
        self.fetch_error = None
        self.display_error = None
        self.button_error = None
        self.buttons = None
        self.updating = False
        self.fetching = False
        self.last_display_at = None
        self.last_manual = None
        self.last_fetch_attempt = None
        self.fetch_requested = False
        self.preview = None
        self.display_hash = None
        self.version = 0
        self.rendered_version = -1
        self.threads = []
        self.tick()
        self.persist()

    def day(self):
        return lessons.learning_day(self.clock(), self.settings["timezone"], self.settings["rollover"])

    def persist(self):
        self.store.put(settings=self.settings, selection=self.state, progress=self.progress)

    def touch(self):
        self.version += 1
        self.changed.set()

    def start(self):
        with self.lock:
            self.touch()
        for name, target in (("display", self.display_loop), ("weather", self.weather_loop),
                             ("scheduler", self.scheduler_loop)):
            thread = threading.Thread(name=name, target=target, daemon=True)
            thread.start()
            self.threads.append(thread)

    def close(self):
        self.stop.set()
        self.changed.set()
        self.fetch_event.set()
        if self.buttons:
            self.buttons.close()
        for thread in self.threads:
            thread.join(timeout=15)
        self.display.close()

    def tick(self):
        with self.lock:
            now = self.clock()
            day = self.day()
            if day != self.progress["day"]:
                self.progress["day"] = day
                self.state.update(card=0, browse_day=None)
                self.persist()
                self.touch()
            if self.settings["city"] and not self.fetch_requested and not self.fetching:
                matches = self.usable_cache() is not None
                age = (now - datetime.fromisoformat(self.cache["fetched_at"])).total_seconds() if matches else float("inf")
                retry = self.last_fetch_attempt is None or (now - self.last_fetch_attempt).total_seconds() >= 300
                if age >= 3600 and retry:
                    self.queue_fetch()
            # Crossing the stale boundary must update the panel, not only the web status.
            stale = self.is_stale()
            if stale != getattr(self, "previous_stale", None):
                self.previous_stale = stale
                self.touch()
            local_date = (now.astimezone(ZoneInfo(self.settings["timezone"])).date(),
                          now.astimezone(ZoneInfo(self.settings["city"]["timezone"])).date()
                          if self.settings["city"] else None)
            if local_date != getattr(self, "previous_date", None):
                self.previous_date = local_date
                self.touch()

    def queue_fetch(self):
        self.fetch_requested = True
        self.fetch_event.set()

    def select(self, app):
        if app not in ("weather", "french"):
            raise ValueError("Unknown app")
        with self.lock:
            self.state["app"] = app
            self.persist()
            self.touch()

    def action(self, button, physical=False):
        if button not in "ABCD" or len(button) != 1:
            raise ValueError("Button must be A, B, C, or D")
        with self.lock:
            if button in "AB":
                self.select("weather" if button == "A" else "french")
                return
            if self.state["app"] == "weather":
                if button == "C":
                    self.state["weather_view"] = "three_days" if self.state["weather_view"] == "today" else "today"
                else:
                    if not self.settings["city"]:
                        raise ValueError("Choose a city in Settings first")
                    now = self.clock()
                    if self.last_manual and (now - self.last_manual).total_seconds() < 60:
                        raise RateLimited("Please wait one minute between manual weather updates")
                    self.last_manual = now
                    self.queue_fetch()
            else:
                self.state["card"] = (self.state["card"] + (-1 if button == "C" else 1)) % 3
            self.persist()
            self.touch()

    def update_settings(self, changes):
        if not isinstance(changes, dict) or set(changes) - set(DEFAULTS):
            raise ValueError("Unknown settings")
        with self.lock:
            settings = copy.deepcopy(self.settings)
            settings.update(changes)
            city_changed = "city" in changes and changes["city"] != self.settings["city"]
            if city_changed:
                settings["city"] = validate_city(changes["city"])
                if "timezone" not in changes:
                    settings["timezone"] = settings["city"]["timezone"]
            if settings["units"] not in ("C", "F"):
                raise ValueError("Units must be C or F")
            try:
                if not isinstance(settings["timezone"], str):
                    raise ValueError()
                ZoneInfo(settings["timezone"])
            except (KeyError, ValueError, TypeError):
                raise ValueError("Enter an IANA timezone, such as Europe/Paris") from None
            try:
                rollover = settings["rollover"]
                if not isinstance(rollover, str) or len(rollover) != 5:
                    raise ValueError()
                datetime.strptime(rollover, "%H:%M")
            except (ValueError, TypeError):
                raise ValueError("Daily lesson time must be HH:MM") from None
            self.settings = settings
            if city_changed:
                self.fetch_error = None
                self.last_fetch_attempt = None
                # Keep old-location cache in storage until successful replacement, but never display it.
                self.queue_fetch()
            self.persist()
            self.tick()
            self.touch()

    def browse(self, day):
        with self.lock:
            if day is not None:
                if not isinstance(day, str):
                    raise ValueError("Invalid lesson date")
                try:
                    datetime.strptime(day, "%Y-%m-%d")
                except ValueError:
                    raise ValueError("Invalid lesson date") from None
                if not self.progress["anchor"] <= day <= self.day():
                    raise ValueError("Choose a date between your first lesson and today")
            self.state.update(app="french", browse_day=day, card=0)
            self.persist()
            self.touch()

    def usable_cache(self):
        city = self.settings["city"]
        return self.cache if city and self.cache and self.cache.get("location_key") == location_key(city) and self.cache.get("source", "live") == ("sample" if self.sample else "live") else None

    def is_stale(self):
        cache = self.usable_cache()
        return bool(cache and (self.fetch_error or
                    (self.clock() - datetime.fromisoformat(cache["fetched_at"])).total_seconds() >= 3600))

    def snapshot(self):
        with self.lock:
            day = self.state["browse_day"] or self.day()
            return copy.deepcopy({"settings": self.settings, "selection": self.state,
                "lesson": lessons.lesson_for(day, self.progress["anchor"]), "lesson_day": day,
                "today": self.day(), "first_day": self.progress["anchor"], "weather": self.usable_cache(),
                "stale": self.is_stale(), "sample": self.sample, "now": self.clock().isoformat(),
                "mode": self.display.mode, "updating": self.updating,
                "pending": self.rendered_version != self.version, "fetching": self.fetching or self.fetch_requested,
                "last_display_at": self.last_display_at,
                "preview_version": self.display_hash,
                "weather_error": self.fetch_error, "display_error": self.display_error,
                "button_error": self.button_error or ("Button listener stopped; restart service" if self.buttons and not self.buttons.healthy else None),
                "connection": "sample" if self.sample else ("error" if self.fetch_error else
                    "not configured" if not self.settings["city"] else "cached" if self.usable_cache() else "waiting"),
                "buttons": "ABCD"})

    def scheduler_loop(self):
        while not self.stop.wait(5):
            try:
                self.tick()
            except Exception:
                log.exception("Scheduler tick failed")

    def weather_loop(self):
        while not self.stop.is_set():
            self.fetch_event.wait(1)
            self.fetch_event.clear()
            if self.stop.is_set():
                break
            with self.lock:
                if not self.fetch_requested:
                    continue
                self.fetch_requested = False
                city = copy.deepcopy(self.settings["city"])
                if not city:
                    continue
                self.fetching = True
                self.last_fetch_attempt = self.clock()
            result, error = None, None
            try:
                result = self.weather.fetch(city, self.clock())
            except Exception as exc:
                log.warning("Weather fetch failed: %s", exc)
                error = "Could not reach weather provider. Cached weather is kept; retrying in five minutes."
            with self.lock:
                self.fetching = False
                # Discard results/errors for a city changed while the request was in flight.
                if self.settings["city"] and location_key(city) == location_key(self.settings["city"]):
                    self.fetch_error = error
                    if result:
                        result["source"] = "sample" if self.sample else "live"
                        self.cache = result
                        self.store.put(weather_cache=result)
                    self.touch()

    def display_loop(self):
        while not self.stop.is_set():
            self.changed.wait(1)
            self.changed.clear()
            if self.stop.is_set():
                break
            # Short gathering window combines a burst of actions before starting a slow refresh.
            if self.stop.wait(0.12):
                break
            with self.lock:
                if self.rendered_version == self.version:
                    continue
                version = self.version
                snapshot = self.snapshot()
            try:
                image = render(snapshot)
                digest = hashlib.sha256(image.tobytes()).hexdigest()
                with self.lock:
                    if version != self.version:
                        self.changed.set()
                        continue
                    if digest == self.display_hash:
                        self.rendered_version = version
                        continue
                    self.updating = True
                self.display.show(image)
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                with self.lock:
                    self.preview = buffer.getvalue()
                    self.display_hash = digest
                    self.last_display_at = self.clock().isoformat()
                    self.rendered_version = version
                    self.display_error = None
            except Exception as exc:
                log.exception("Display refresh failed")
                with self.lock:
                    self.display_error = str(exc)[:240]
                # Back off to avoid hammering GPIO on a persistent hardware failure.
                if self.stop.wait(30):
                    break
                self.changed.set()
            finally:
                with self.lock:
                    self.updating = False
