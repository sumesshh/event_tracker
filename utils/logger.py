"""
One shared logger, writing to both the console and logs/app.log.
"""

import logging
import os

from config import settings

_configured = False


def get_logger(name="rextech"):
    """Return the application logger, configuring handlers on first use."""
    global _configured

    if not _configured:
        os.makedirs(os.path.dirname(settings.LOG_PATH), exist_ok=True)

        root = logging.getLogger("rextech")
        root.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console output, so `python main.py` shows live progress.
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

        # Persistent file, so failures can be inspected after the fact.
        file_handler = logging.FileHandler(settings.LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

        # Requests/urllib3 are noisy at INFO level.
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        _configured = True

    return logging.getLogger(name if name.startswith("rextech") else f"rextech.{name}")
