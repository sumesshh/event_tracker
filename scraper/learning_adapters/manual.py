"""
Manual-entry adapter for sources that cannot be scraped automatically.

Some platforms are login-gated with client-side-encrypted API traffic (Sayuj
is the case that prompted this: sayuj-client.humanitics.com encrypts every
request/response body, so automating it would mean reverse-engineering their
encryption rather than reading a public page - not something this project
does). For those, a human logs in, reads the real program details off the
screen, and copies them into config/manual_learning_programs.json. This
adapter is the DISCOVER + EXTRACT step for that file - everything downstream
(normalize/verify/store) is identical to every other source.

Nothing here is generated or guessed: an entry only exists in the output
because someone typed in what they actually saw on the source's site. Entries
missing a real title/provider/official_url are still rejected by
scraper/learning_pipeline.py's validation, same as a scraped result would be.
"""

import json
import os

from config import settings
from utils.logger import get_logger

log = get_logger("learning.manual")

MANUAL_FILE = os.path.join(settings.BASE_DIR, "config", "manual_learning_programs.json")


def fetch():
    """Load every real, human-entered program from the fill-in file."""
    if not os.path.isfile(MANUAL_FILE):
        return []

    try:
        with open(MANUAL_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not read %s: %s", MANUAL_FILE, exc)
        return []

    programs = []
    for entry in data.get("programs", []):
        if entry.get("_example"):
            continue
        entry = {k: v for k, v in entry.items() if not k.startswith("_")}
        # source_name is deliberately NOT taken from the entry: it has to
        # stay "Manual Entries" (the adapter name) so that removing a row
        # from the JSON file correctly removes it from the database on the
        # next crawl (see learning_pipeline.run_source's delete_stale call,
        # which is keyed by adapter name). `provider` is still whatever the
        # entry says (e.g. "Sayuj (STPI)") and is what the UI shows.
        entry.pop("source_name", None)
        programs.append(entry)

    log.info("Manual entries: loaded %d program(s) from %s", len(programs), MANUAL_FILE)
    return programs


ADAPTER = {
    "name": "Manual Entries",
    "source_type": "SECONDARY",
    "fetch": fetch,
}
