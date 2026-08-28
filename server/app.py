"""
The web server - pure Python http.server, no Django, no FastAPI, no Flask.

Two kinds of route:

  Static pages   /            -> frontend/index.html   (dashboard)
                 /new         -> frontend/events.html  (new events page)
                 /events      -> frontend/events.html  (all events, filtered)
                 /event?id=N  -> frontend/event.html   (one opportunity)
                 /static/*    -> frontend/static/*     (CSS + JS)

  JSON API       /api/summary        home page sections in one request
                 /api/events         filtered + searchable event list
                 /api/event?id=N     one opportunity, for the details page
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
from config.categories import CATEGORIES, FOCUS_CATEGORIES, OPPORTUNITY_GROUPS
from config.priority import MIDDLE_EAST_COUNTRIES, PRIORITY_TAGS, SECTION_ORDER
from database import db
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
        if path == "/event":
            return self._send_file("event.html")
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
        if path == "/api/event":
            return self._api_event()
        if path == "/api/stats":
            return self._api_stats()

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

    def _filters(self, params):
        """
        Turn the query string into the keyword arguments db.build_where takes.

        One place, used by both /api/events and /api/stats, so a filtered list
        and the counters above it are always computed from the same set.
        """
        return {
            "only_new": params.get("new") == "1",
            "since": params.get("since"),
            "focus_only": params.get("focus") == "1",
            "category": params.get("category"),
            "country": params.get("country"),
            "region": params.get("state") or params.get("region"),
            "city": params.get("city"),
            "tag": params.get("tag"),
            "provider": params.get("provider"),
            "mode": params.get("mode"),
            "status": params.get("status"),
            "upcoming": params.get("upcoming") == "1",
            "search": params.get("q"),
        }

    def _api_summary(self):
        """
        Everything the home page needs, in one request:
        the badge count, the counters and every priority section.

        The sections come from config.priority.SECTION_ORDER, so the home page
        never hard-codes what "Kerala" or "KSUM / Huddle" means - it renders
        whatever that one list says, in that order.
        """
        sections = []
        for label, filters in SECTION_ORDER:
            events = db.query_events(order="priority", limit=8, **filters)
            if not events:
                # An empty collection is hidden rather than padded with
                # something else - see config/priority.py.
                continue
            sections.append({
                "title": label,
                "filters": filters,
                "total": db.get_stats(**filters)["total"],
                "events": events,
            })

        payload = {
            "new_count": db.count_new_events(),
            "sections": sections,
            # Kept alongside the priority sections: these three answer
            # "what changed" and "what is about to close", which no
            # geographic section does.
            "recent": db.query_events(order="recent", limit=8),
            "closing_soon": db.query_events(
                status="Closing Soon", order="deadline", limit=8
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
            # Geography leads everywhere, so the default is the priority
            # order - not "focus", which put the studio's own subjects above
            # Kerala and made the events page disagree with the home page.
            # focus=1 still narrows the list, and the focus sort is still
            # reachable with order=focus.
            order=params.get("order", "priority"),
            limit=limit,
            **self._filters(params),
        )
        self._send_json({"count": len(events), "events": events})

    def _api_event(self):
        """One opportunity by id - everything the details page renders."""
        event = db.get_event(self._query().get("id"))
        if not event:
            return self._send_json({"error": "Event not found"}, status=404)
        self._send_json({"event": event})

    def _api_stats(self):
        """
        Counters plus the values that fill the filter drop-downs.

        The same filters /api/events accepts are honoured here, so the numbers
        a filtered page shows describe that page rather than the whole table.
        The drop-down option lists stay unfiltered - narrowing them to the
        current selection would make a filter impossible to change back.
        """
        params = self._query()
        stats = db.get_stats(**self._filters(params))
        # "Startup Funding" is offered alongside the stored categories because
        # users ask for it by that name; db.resolve_categories expands it to
        # the money categories behind it.
        stats["categories"] = ["Startup Funding"] + CATEGORIES
        stats["focus_categories"] = FOCUS_CATEGORIES
        stats["opportunity_groups"] = list(OPPORTUNITY_GROUPS)
        stats["tags"] = list(PRIORITY_TAGS)
        # "Middle East" is a filter value in its own right; db.query_events
        # expands it to the member countries.
        stats["middle_east_countries"] = MIDDLE_EAST_COUNTRIES
        if stats.get("middle_east"):
            stats["countries"] = ["Middle East"] + stats["countries"]
        stats["next_run_at"] = scheduler.get_next_run_at()
        stats["interval_hours"] = settings.SCRAPE_INTERVAL_HOURS
        self._send_json(stats)

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
