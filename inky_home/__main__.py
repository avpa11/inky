import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal

from .display import Buttons, InkyDisplay, PreviewDisplay
from .service import Dashboard
from .store import Store
from .lessons import CATALOG
from .weather import SampleWeatherClient, WeatherClient, validate_city
from .web import create_app


def main():
    parser = argparse.ArgumentParser(description="Inky Home dashboard")
    parser.add_argument("--display", choices=("preview", "hardware"), default="preview")
    parser.add_argument("--sample-weather", action="store_true", help="Explicit sample data, for previews only")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data-dir", default=os.environ.get("INKY_HOME_DATA", "var"))
    args = parser.parse_args()
    if args.sample_weather and args.display == "hardware":
        parser.error("Sample weather is only supported in preview mode")
    CATALOG.validate()
    store = Store(args.data_dir)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = RotatingFileHandler(Path(args.data_dir) / "home.log", maxBytes=500_000, backupCount=2)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger("waitress").setLevel(logging.WARNING)
    display = InkyDisplay() if args.display == "hardware" else PreviewDisplay()
    dashboard = Dashboard(store, display, SampleWeatherClient() if args.sample_weather else WeatherClient(), args.sample_weather)
    if args.sample_weather and not dashboard.settings["city"]:
        dashboard.update_settings({"city": validate_city({"name": "San Francisco", "region": "California", "country": "United States", "latitude": 37.7749, "longitude": -122.4194, "timezone": "America/Los_Angeles"})})
    if args.display == "hardware":
        try:
            dashboard.buttons = Buttons(lambda button: dashboard.action(button, physical=True))
        except Exception as exc:
            logging.exception("GPIO buttons unavailable; web controls remain available")
            dashboard.button_error = str(exc)[:240]
    dashboard.start()
    def terminate(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    try:
        from waitress import serve
        logging.info("Dashboard: http://%s:%s (%s)", args.host, args.port, args.display)
        serve(create_app(dashboard), host=args.host, port=args.port, threads=4,
              channel_timeout=30, max_request_body_size=16 * 1024, clear_untrusted_proxy_headers=True)
    except KeyboardInterrupt:
        pass
    finally:
        dashboard.close()


if __name__ == "__main__":
    main()
