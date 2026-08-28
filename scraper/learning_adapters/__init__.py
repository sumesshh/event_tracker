"""
Registry of Learning Programs source adapters.

Each adapter is a plain module exposing `ADAPTER = {"name", "source_type",
"fetch"}` where `fetch()` returns a list of raw program dicts (see
scraper/learning_pipeline.py for the shape they are normalised into).

Adding a new official source is a two-step job: write scraper/learning_
adapters/<source>.py following swayam.py or ksum.py as a template, then add
its ADAPTER to LEARNING_SOURCES below.
"""

from scraper.learning_adapters import ksum, manual, swayam

LEARNING_SOURCES = [
    swayam.ADAPTER,
    ksum.ADAPTER,
    # Sources that cannot be scraped automatically (login-gated, encrypted
    # API traffic, etc.) - see config/manual_learning_programs.json and
    # scraper/learning_adapters/manual.py for how entries get in here.
    manual.ADAPTER,
]
