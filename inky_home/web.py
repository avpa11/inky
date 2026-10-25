from flask import Flask, Response, jsonify, render_template, request
from urllib.parse import urlsplit

from .service import RateLimited
from .weather import search_cities
from .lessons import CATALOG


def create_app(dashboard):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    @app.before_request
    def same_origin():
        # LAN-only app: prevent a page on another origin issuing control requests.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("Origin")
            if (origin and urlsplit(origin).netloc != request.host) or request.headers.get("Sec-Fetch-Site") == "cross-site":
                return jsonify(error="Cross-origin controls are not allowed"), 403
            if not request.is_json:
                return jsonify(error="Send application/json"), 415

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    @app.errorhandler(ValueError)
    def invalid(exc):
        return jsonify(error=str(exc)), 429 if isinstance(exc, RateLimited) else 400

    def body():
        value = request.get_json()
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/french/sources")
    def french_sources():
        return render_template('french_sources.html', sources=dashboard.catalog.sources(), metadata=dashboard.catalog.metadata)

    @app.get("/api/french/sources")
    def french_sources_api():
        return jsonify(sources=dashboard.catalog.sources(), metadata=dashboard.catalog.metadata)

    @app.get("/api/status")
    def status():
        return jsonify(dashboard.snapshot())

    @app.get("/api/preview.png")
    def preview():
        with dashboard.lock:
            data = dashboard.preview
        if not data:
            return jsonify(error="First screen is being prepared"), 503
        return Response(data, mimetype="image/png")

    @app.post("/api/app")
    def select():
        dashboard.select(body().get("app"))
        return jsonify(ok=True)

    @app.post("/api/action")
    def action():
        button = body().get("button")
        if not isinstance(button, str):
            raise ValueError("Specify a button")
        dashboard.action(button)
        return jsonify(ok=True)

    @app.post("/api/settings")
    def settings():
        dashboard.update_settings(body())
        return jsonify(ok=True)

    @app.get("/api/cities")
    def cities():
        query = request.args.get("q", "").strip()
        if not 2 <= len(query) <= 100:
            raise ValueError("Enter between 2 and 100 characters")
        try:
            return jsonify(results=search_cities(query))
        except Exception:
            return jsonify(error="City search is unavailable. Check the Pi's internet connection and try again."), 502

    @app.post('/api/french/explore')
    def explore():
        body()
        dashboard.explore()
        return jsonify(ok=True)

    @app.post('/api/french/update')
    def update_catalog():
        body()
        dashboard.catalog_event.set()
        return jsonify(ok=True)

    @app.post("/api/french/day")
    def browse():
        data = body()
        if "day" not in data:
            raise ValueError("Specify a lesson date, or null for today")
        dashboard.browse(data["day"])
        return jsonify(ok=True)

    return app
