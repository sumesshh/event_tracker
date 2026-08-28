"""
The web server - pure Python http.server, no Django, no FastAPI, no Flask.

Two kinds of route:

  Static pages   /            -> frontend/index.html   (dashboard)
                 /new         -> frontend/events.html  (new events page)
                 /events      -> frontend/events.html  (all events, filtered)
                 /static/*    -> frontend/static/*     (CSS + JS)

  JSON API       /api/summary        home page sections in one request
                 /api/events         filtered + searchable event list
                 /api/stats          counters and filter options
                 /api/mark-seen      clears the 🔔 badge
                 /api/refresh        triggers a crawl right now
"""

import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import settings
from config.categories import CATEGORIES, FOCUS_CATEGORIES
from database import db, learning_db
from scheduler import scheduler
from utils.logger import get_logger

log = get_logger("server")


class DashboardHandler(BaseHTTPRequestHandler):
    """Handles every request the dashboard makes."""

    server_version = "RextechEventDashboard/1.0"

    # -------------------------------------------------------------------
    # Response helpers
    # -------------------------------------------------------------------

    def _send_json(self, payload, status=200):
        """Serialise `payload` as JSON and write it to the socket."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # The dashboard polls these endpoints; never let the browser cache them.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, relative_path, status=200):
        """Serve one file out of the frontend folder."""
        # Normalise and confine the path to FRONTEND_DIR so a crafted URL
        # such as /static/../../database/events.db cannot escape the folder.
        safe_path = os.path.normpath(
            os.path.join(settings.FRONTEND_DIR, relative_path.lstrip("/\\"))
        )
        if not safe_path.startswith(os.path.normpath(settings.FRONTEND_DIR)):
            self._send_error_page(403, "Forbidden")
            return

        if not os.path.isfile(safe_path):
            self._send_error_page(404, "Not found")
            return

        content_type, _ = mimetypes.guess_type(safe_path)
        with open(safe_path, "rb") as handle:
            body = handle.read()

        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_page(self, status, message):
        """Small plain-text error response."""
        body = f"{status} {message}".encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _query(self):
        """Parse the query string into a flat {key: value} dictionary."""
        parsed = urllib.parse.urlparse(self.path)
        raw = urllib.parse.parse_qs(parsed.query)
        return {key: values[0] for key, values in raw.items() if values}

    # -------------------------------------------------------------------
    # Routing
    # -------------------------------------------------------------------

    def do_GET(self):
        """Route every GET request."""
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

        # --- pages -----------------------------------------------------
        if path == "/":
            return self._send_file("index.html")
        if path in ("/new", "/events"):
            return self._send_file("events.html")
        if path == "/learning":
            return self._send_file("learning.html")
        if path.startswith("/static/"):
            # "/static/app.js" -> frontend/static/app.js
            return self._send_file(path.lstrip("/"))
        if path == "/favicon.ico":
            return self._send_error_page(204, "")

        # --- API -------------------------------------------------------
        if path == "/api/summary":
            return self._api_summary()
        if path == "/api/events":
            return self._api_events()
        if path == "/api/stats":
            return self._api_stats()
        if path == "/api/learning":
            return self._api_learning()

        return self._send_error_page(404, "Not found")

    def do_POST(self):
        """Route every POST request (the two action endpoints)."""
        path = urllib.parse.urlparse(self.path).path.rstrip("/")

        if path == "/api/mark-seen":
            # `cutoff` lets the New Events page keep showing the batch it just
            # marked as read, instead of emptying itself on the next query.
            cutoff, cleared = db.mark_seen()
            log.info("Cleared the new badge on %d events (cutoff %s)", cleared, cutoff)
            return self._send_json({"ok": True, "cleared": cleared, "cutoff": cutoff})

        if path == "/api/refresh":
            scheduler.trigger_now()
            return self._send_json({"ok": True, "message": "Crawl started"})

        return self._send_error_page(404, "Not found")

    # -------------------------------------------------------------------
    # API implementations
    # -------------------------------------------------------------------

    def _api_summary(self):
        """
        Everything the home page needs, in one request:
        the badge count plus the three home page sections.
        """
        payload = {
            "new_count": db.count_new_events(),
            # "Game · AR/VR · App Events" = what the studio actually builds.
            "focus": db.query_events(
                focus_only=True, upcoming=True, order="focus", limit=12
            ),
            # "Recent Events" = most recently discovered.
            "recent": db.query_events(order="recent", limit=12),
            # "Upcoming Events" = soonest future date first.
            "upcoming": db.query_events(upcoming=True, order="date", limit=12),
            # "Registration Closing Soon" = starts within 14 days.
            "closing_soon": db.query_events(
                status="Closing Soon", order="date", limit=12
            ),
            "stats": db.get_stats(),
            "next_run_at": scheduler.get_next_run_at(),
        }
        self._send_json(payload)

    def _api_events(self):
        """The filtered / searchable list used by the events page."""
        params = self._query()

        # The limit arrives from the query string, so it may be anything.
        try:
            limit = max(1, min(int(params.get("limit", 1000)), 2000))
        except ValueError:
            limit = 1000

        events = db.query_events(
            only_new=params.get("new") == "1",
            since=params.get("since"),
            focus_only=params.get("focus") == "1",
            category=params.get("category"),
            country=params.get("country"),
            region=params.get("state") or params.get("region"),
            mode=params.get("mode"),
            status=params.get("status"),
            upcoming=params.get("upcoming") == "1",
            search=params.get("q"),
            order=params.get("order", "focus"),
            limit=limit,
        )
        self._send_json({"count": len(events), "events": events})

    def _api_stats(self):
        """Counters plus the values that fill the filter drop-downs."""
        stats = db.get_stats()
        stats["categories"] = CATEGORIES
        stats["focus_categories"] = FOCUS_CATEGORIES
        stats["next_run_at"] = scheduler.get_next_run_at()
        stats["interval_hours"] = settings.SCRAPE_INTERVAL_HOURS
        # Real Learning Programs counters - computed from the same table and
        # the same (empty) filter set the /learning page starts with, so the
        # dashboard card always matches what "See all" leads to.
        stats["learning"] = learning_db.get_learning_stats()
        stats["learning_filters"] = learning_db.get_filter_options()
        self._send_json(stats)

    def _learning_filters_from_query(self, params):
        """Shared filter-argument parsing for /api/learning and /api/learning/stats."""
        return dict(
            country=params.get("country"),
            category=params.get("category"),
            program_type=params.get("programType"),
            cost_type=params.get("costType"),
            funding_type=params.get("fundingType"),
            certificate=params.get("certificate"),
            location_type=params.get("locationType"),
            skill=params.get("skill"),
            search=params.get("q"),
            closing_soon=params.get("closingSoon") == "1",
        )

    def _api_learning(self):
        """
        The filtered / searchable learning-programs list, sourced from the
        real ingestion pipeline (database/learning_db.py) - never generated
        or hand-entered.
        """
        params = self._query()
        try:
            limit = max(1, min(int(params.get("limit", 1000)), 2000))
        except ValueError:
            limit = 1000

        filters = self._learning_filters_from_query(params)
        programs = learning_db.query_programs(
            order=params.get("order", "relevance"), limit=limit, **filters
        )
        # Rule #10: the counters shown alongside a filtered list must describe
        # the SAME filtered dataset, so they are computed with the identical
        # filter arguments rather than a separate unfiltered query.
        stats = learning_db.get_learning_stats(**filters)
        self._send_json({"count": len(programs), "programs": programs, "stats": stats})

    # -------------------------------------------------------------------

    def log_message(self, fmt, *args):
        """Send http.server's access log through our own logger."""
        log.debug("%s - %s", self.address_string(), fmt % args)


def run_server():
    """Start the HTTP server and block until Ctrl+C."""
    address = (settings.SERVER_HOST, settings.SERVER_PORT)

    # ThreadingHTTPServer means a slow request never blocks the dashboard.
    httpd = ThreadingHTTPServer(address, DashboardHandler)

    log.info("Dashboard running at http://%s:%d", *address)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        httpd.server_close()
