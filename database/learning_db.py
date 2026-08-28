"""
Persistence layer for real, individually-verified Learning Programs.

Deliberately a separate table from `events` (see database/db.py): a learning
program has a materially different shape - costType/fundingType/certificate/
eligibleCountries instead of a single category/date/location - and every
record here is produced by a source adapter that reads one real official
page, never guessed or hand-entered.

SOURCE -> DISCOVER -> EXTRACT -> NORMALIZE -> VERIFY -> STORE -> FILTER -> DISPLAY
This module is the STORE + FILTER half of that pipeline; scraper/learning_*
implements the rest.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_programs (
    id                    TEXT    PRIMARY KEY,   -- sha256(provider|normalised title|url)
    title                 TEXT    NOT NULL,
    provider              TEXT    NOT NULL,
    description           TEXT    DEFAULT '',

    category              TEXT    DEFAULT '[]',  -- JSON list
    subcategory           TEXT    DEFAULT '',
    skills                TEXT    DEFAULT '[]',  -- JSON list

    program_type          TEXT    DEFAULT 'Course',

    country               TEXT    DEFAULT 'Unknown',
    city                  TEXT    DEFAULT '',
    location_type         TEXT    DEFAULT 'Unknown',   -- Online / Offline / Hybrid / Unknown

    eligible_countries     TEXT    DEFAULT '[]',  -- JSON list

    cost_type             TEXT    DEFAULT 'UNKNOWN',   -- FREE/PAID/SCHOLARSHIP/PARTIALLY_FUNDED/FULLY_FUNDED/UNKNOWN
    price                 REAL,
    currency              TEXT    DEFAULT '',

    funding_type          TEXT    DEFAULT 'UNKNOWN',   -- NONE/SCHOLARSHIP/GRANT/STIPEND/FULLY_FUNDED/PARTIALLY_FUNDED/UNKNOWN
    funding_amount        TEXT    DEFAULT '',

    certificate_available TEXT    DEFAULT 'unknown',   -- 'true' / 'false' / 'unknown'

    eligibility           TEXT    DEFAULT '{}',  -- JSON object

    start_date            TEXT    DEFAULT '',
    end_date              TEXT    DEFAULT '',
    application_deadline  TEXT    DEFAULT '',

    official_url          TEXT    NOT NULL,
    application_url       TEXT    DEFAULT '',

    status                TEXT    DEFAULT 'OPEN',       -- UPCOMING/OPEN/CLOSING_SOON/CLOSED/ONGOING

    source_type           TEXT    DEFAULT 'SECONDARY',  -- GOVERNMENT/UNIVERSITY/INSTITUTION/COMPANY/PROVIDER/SECONDARY
    source_name           TEXT    DEFAULT '',
    verified              INTEGER NOT NULL DEFAULT 0,
    last_verified_at      TEXT    DEFAULT '',

    created_at            TEXT    NOT NULL,
    updated_at            TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lp_status       ON learning_programs (status);
CREATE INDEX IF NOT EXISTS idx_lp_cost_type    ON learning_programs (cost_type);
CREATE INDEX IF NOT EXISTS idx_lp_funding_type ON learning_programs (funding_type);
CREATE INDEX IF NOT EXISTS idx_lp_country      ON learning_programs (country);
CREATE INDEX IF NOT EXISTS idx_lp_provider     ON learning_programs (provider);
"""

_JSON_COLUMNS = {"category", "skills", "eligible_countries", "eligibility"}
_JSON_DEFAULTS = {"category": [], "skills": [], "eligible_countries": [], "eligibility": {}}


def get_connection():
    os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row):
    data = {key: row[key] for key in row.keys()}
    for column in _JSON_COLUMNS:
        if column in data:
            try:
                data[column] = json.loads(data[column]) if data[column] else _JSON_DEFAULTS[column]
            except (TypeError, json.JSONDecodeError):
                data[column] = _JSON_DEFAULTS[column]
    if "certificate_available" in data:
        data["certificate_available"] = {"true": True, "false": False}.get(
            data["certificate_available"], "unknown"
        )
    data["verified"] = bool(data.get("verified"))
    return data


# ---------------------------------------------------------------------------
# Writing - upsert keyed on the stable id (see make_program_id)
# ---------------------------------------------------------------------------

def upsert_program(program):
    """
    Insert a new program or update an existing one (same id = same provider +
    normalised title + official URL, see scraper/learning_pipeline.py).

    Re-running the pipeline therefore refreshes deadlines/status instead of
    creating duplicates, satisfying the "no duplicates on refresh" rule.
    """
    conn = get_connection()
    now = datetime.utcnow().isoformat(timespec="seconds")
    try:
        existing = conn.execute(
            "SELECT created_at FROM learning_programs WHERE id = ?", (program["id"],)
        ).fetchone()
        created_at = existing["created_at"] if existing else now

        cert = program.get("certificate_available")
        cert_str = "true" if cert is True else "false" if cert is False else "unknown"

        conn.execute(
            """
            INSERT INTO learning_programs (
                id, title, provider, description, category, subcategory, skills,
                program_type, country, city, location_type, eligible_countries,
                cost_type, price, currency, funding_type, funding_amount,
                certificate_available, eligibility, start_date, end_date,
                application_deadline, official_url, application_url, status,
                source_type, source_name, verified, last_verified_at,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, provider=excluded.provider,
                description=excluded.description, category=excluded.category,
                subcategory=excluded.subcategory, skills=excluded.skills,
                program_type=excluded.program_type, country=excluded.country,
                city=excluded.city, location_type=excluded.location_type,
                eligible_countries=excluded.eligible_countries,
                cost_type=excluded.cost_type, price=excluded.price,
                currency=excluded.currency, funding_type=excluded.funding_type,
                funding_amount=excluded.funding_amount,
                certificate_available=excluded.certificate_available,
                eligibility=excluded.eligibility, start_date=excluded.start_date,
                end_date=excluded.end_date,
                application_deadline=excluded.application_deadline,
                official_url=excluded.official_url,
                application_url=excluded.application_url, status=excluded.status,
                source_type=excluded.source_type, source_name=excluded.source_name,
                verified=excluded.verified, last_verified_at=excluded.last_verified_at,
                updated_at=excluded.updated_at
            """,
            (
                program["id"], program["title"], program["provider"],
                program.get("description", ""),
                json.dumps(program.get("category", [])),
                program.get("subcategory", ""),
                json.dumps(program.get("skills", [])),
                program.get("program_type", "Course"),
                program.get("country", "Unknown"),
                program.get("city", ""),
                program.get("location_type", "Unknown"),
                json.dumps(program.get("eligible_countries", [])),
                program.get("cost_type", "UNKNOWN"),
                program.get("price"),
                program.get("currency", ""),
                program.get("funding_type", "UNKNOWN"),
                program.get("funding_amount", ""),
                cert_str,
                json.dumps(program.get("eligibility", {})),
                program.get("start_date", ""),
                program.get("end_date", ""),
                program.get("application_deadline", ""),
                program["official_url"],
                program.get("application_url", ""),
                program.get("status", "OPEN"),
                program.get("source_type", "SECONDARY"),
                program.get("source_name", ""),
                1 if program.get("verified") else 0,
                program.get("last_verified_at", now),
                created_at, now,
            ),
        )
        conn.commit()
        return existing is None  # True = newly discovered, False = refreshed
    finally:
        conn.close()


def delete_stale(source_name, seen_ids):
    """
    Remove programs from one source that were not seen in the latest crawl -
    they closed, were pulled, or are no longer listed on the official page.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id FROM learning_programs WHERE source_name = ?", (source_name,)
        ).fetchall()
        stale = [r["id"] for r in rows if r["id"] not in seen_ids]
        if stale:
            conn.executemany(
                "DELETE FROM learning_programs WHERE id = ?", [(i,) for i in stale]
            )
            conn.commit()
        return len(stale)
    finally:
        conn.close()


def refresh_all_statuses(closing_soon_days):
    """Recompute UPCOMING/OPEN/CLOSING_SOON/CLOSED/ONGOING from stored dates."""
    today = datetime.utcnow().date()
    soon = today + timedelta(days=closing_soon_days)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, start_date, application_deadline FROM learning_programs"
        ).fetchall()
        for row in rows:
            status = _compute_status(row["start_date"], row["application_deadline"], today, soon)
            conn.execute(
                "UPDATE learning_programs SET status = ? WHERE id = ?", (status, row["id"])
            )
        conn.commit()
    finally:
        conn.close()


def _compute_status(start_date, deadline, today, soon):
    if deadline:
        try:
            d = datetime.fromisoformat(deadline[:10]).date()
            if d < today:
                return "CLOSED"
            if d <= soon:
                return "CLOSING_SOON"
            return "OPEN"
        except ValueError:
            pass
    if start_date:
        try:
            s = datetime.fromisoformat(start_date[:10]).date()
            if s > today:
                return "UPCOMING"
            return "ONGOING"
        except ValueError:
            pass
    return "OPEN"


# ---------------------------------------------------------------------------
# Reading / filtering
# ---------------------------------------------------------------------------

def query_programs(
    country=None, category=None, program_type=None, cost_type=None,
    funding_type=None, certificate=None, location_type=None, skill=None,
    level=None, search=None, closing_soon=False, order="relevance", limit=1000,
):
    """
    The single filtered read used by both the program list and the dashboard
    counters - passing the same filter arguments to both guarantees the
    numbers describe exactly the same dataset (rule #10 in the brief).
    """
    clauses, params = [], []

    if country and country.lower() != "all":
        clauses.append("(country = ? OR eligible_countries LIKE ?)")
        params.extend([country, f'%"{country}"%'])

    if category and category.lower() != "all":
        clauses.append("category LIKE ?")
        params.append(f'%"{category}"%')

    if program_type and program_type.lower() != "all":
        clauses.append("program_type = ?")
        params.append(program_type)

    if cost_type and cost_type.lower() != "all":
        clauses.append("cost_type = ?")
        params.append(cost_type)

    if funding_type and funding_type.lower() != "all":
        clauses.append("funding_type = ?")
        params.append(funding_type)

    if certificate and certificate.lower() != "all":
        clauses.append("certificate_available = ?")
        params.append({"true": "true", "false": "false"}.get(certificate.lower(), "unknown"))

    if location_type and location_type.lower() != "all":
        clauses.append("location_type = ?")
        params.append(location_type)

    if skill:
        clauses.append("skills LIKE ?")
        params.append(f'%"{skill}"%')

    if search:
        # Structured fields only - title/description/category/subcategory/
        # skills/provider/program_type - never raw scraped HTML.
        term = "%" + search.lower().strip() + "%"
        clauses.append(
            "(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ? "
            "OR LOWER(subcategory) LIKE ? OR LOWER(skills) LIKE ? OR LOWER(provider) LIKE ? "
            "OR LOWER(program_type) LIKE ?)"
        )
        params.extend([term] * 7)

    if closing_soon:
        clauses.append("status = 'CLOSING_SOON'")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    if order == "deadline":
        order_sql = "ORDER BY (application_deadline = '') ASC, application_deadline ASC"
    elif order == "recent":
        order_sql = "ORDER BY created_at DESC"
    else:
        # Verified + funded/free programs first, then soonest deadline.
        order_sql = (
            "ORDER BY verified DESC, "
            "(funding_type IN ('FULLY_FUNDED','SCHOLARSHIP')) DESC, "
            "(cost_type = 'FREE') DESC, "
            "(application_deadline = '') ASC, application_deadline ASC"
        )

    if search:
        term = "%" + search.lower().strip() + "%"
        order_sql = f"ORDER BY (LOWER(title) LIKE ?) DESC, {order_sql[len('ORDER BY '):]}"
        params_order_extra = [term]
    else:
        params_order_extra = []

    sql = f"SELECT * FROM learning_programs {where} {order_sql} LIMIT ?"
    conn = get_connection()
    try:
        rows = conn.execute(sql, params + params_order_extra + [int(limit)]).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_learning_stats(**filters):
    """
    Counters computed from the SAME filtered dataset the list view shows -
    never a separate hardcoded query. `filters` accepts the same keyword
    arguments as `query_programs` (minus limit/order).
    """
    filters.pop("limit", None)
    filters.pop("order", None)
    programs = query_programs(limit=100000, **filters)

    today = datetime.utcnow().date().isoformat()
    return {
        "total": len(programs),
        "free": sum(1 for p in programs if p["cost_type"] == "FREE"),
        "scholarships": sum(1 for p in programs if p["funding_type"] == "SCHOLARSHIP"),
        "fully_funded": sum(1 for p in programs if p["funding_type"] == "FULLY_FUNDED"),
        "certificates": sum(1 for p in programs if p["certificate_available"] is True),
        "closing_soon": sum(1 for p in programs if p["status"] == "CLOSING_SOON"),
        "verified": sum(1 for p in programs if p["verified"]),
    }


def get_filter_options():
    """Distinct values actually present in the table, for the filter drop-downs."""
    conn = get_connection()
    try:
        countries = [r["country"] for r in conn.execute(
            "SELECT DISTINCT country FROM learning_programs WHERE country != '' ORDER BY country"
        )]
        providers = [r["provider"] for r in conn.execute(
            "SELECT DISTINCT provider FROM learning_programs ORDER BY provider"
        )]
        program_types = [r["program_type"] for r in conn.execute(
            "SELECT DISTINCT program_type FROM learning_programs WHERE program_type != '' ORDER BY program_type"
        )]
        categories = set()
        for row in conn.execute("SELECT DISTINCT category FROM learning_programs"):
            try:
                categories.update(json.loads(row["category"]) if row["category"] else [])
            except (TypeError, json.JSONDecodeError):
                pass
        return {
            "countries": countries,
            "providers": providers,
            "program_types": program_types,
            "categories": sorted(categories),
        }
    finally:
        conn.close()
