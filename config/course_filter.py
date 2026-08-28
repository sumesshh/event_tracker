"""
Course rejection rules.

The dashboard tracks *opportunities* - grants, funding, hackathons, webinars,
programs, competitions and short practical workshops. It deliberately does not
track courses: anything whose main purpose is teaching a syllabus over time
(certification courses, diplomas, bootcamps, training programmes, academies).

`is_course` is applied at ingestion, so course listings never reach the
database, and again by the purge script that cleans out records stored before
these rules existed.

Two tiers, because the giveaway words differ in strength:

  HARD  - the word alone settles it. "Course", "Diploma", "Bootcamp" and
          friends do not appear in the title of a genuine grant or hackathon.

  SOFT  - suggestive but reusable. "Training", "Certification" and "Curriculum"
          show up inside real opportunities ("Hackathon with training
          sessions", "Grant for certification bodies"), so a soft hit is only
          a rejection when no OPPORTUNITY_OVERRIDES term is present.

Masterclasses, orientation/info sessions and one-off workshops are NOT courses
and are intentionally absent from both lists.
"""

import re

# Settles it on its own - no override can rescue a title matching these.
HARD_COURSE_KEYWORDS = [
    "course", "courses", "coursework",
    "certification course", "certificate course", "certificate programme",
    "certificate program",
    "certificate in", "certificate of",
    "diploma", "degree program", "degree programme",
    "bootcamp", "boot camp",
    "academy",
    "mooc", "moocs",
    "online course", "online learning", "e-learning", "elearning",
    "training course", "training program", "training programme",
    "classes", "class series",
    "semester", "syllabus", "tuition",
    "self-paced", "self paced",
    "learn to code",
    "skill development course", "vocational course", "vocational training",
]

# Suggestive only - rejected unless the title also names a real opportunity.
SOFT_COURSE_KEYWORDS = [
    "training", "trainings",
    "certification", "certifications", "certified", "certificate",
    "curriculum",
    "upskilling", "reskilling",
    "tutorial", "tutorials",
    "enroll", "enrol", "enrollment", "enrolment",
    "admission", "admissions",
    "study program", "study programme",
    "workshop series",
    "lecture series",
]

# Unambiguous opportunity nouns. A SOFT hit alongside one of these is kept.
OPPORTUNITY_OVERRIDES = [
    "hackathon", "hack", "game jam", "gamejam", "ideathon", "datathon",
    "buildathon", "codefest", "code fest",
    "grant", "grants", "funding", "fund", "seed funding", "fellowship",
    "scholarship", "subsidy",
    "demo day", "pitch", "accelerator", "incubation", "incubator",
    "competition", "challenge", "contest", "award", "awards",
    "webinar", "conference", "summit", "expo", "conclave", "symposium",
    "meetup", "networking",
    "call for", "applications open", "call for applications",
    # Short practical formats the dashboard deliberately keeps.
    "workshop", "masterclass", "info session", "information session",
    "orientation", "bootcamp challenge",
    # Named industry conferences - talks at these are sessions, not courses.
    "gtc", "gdc", "wwdc", "devfest", "i/o",
]

# "Training" has a second, unrelated meaning in AI listings: training a model.
# "Advanced Techniques for Training, Inference, and Deployment" is a
# conference talk, not a training course, and these neighbours tell them apart.
ML_TRAINING_CONTEXT = [
    "inference", "fine-tuning", "fine tuning", "pretraining", "pre-training",
    "model", "models", "llm", "llms", "neural", "gpu", "gpus", "distributed",
    "checkpoint", "dataset", "datasets", "deployment", "quantization",
    "diffusion", "transformer", "transformers",
]


def _compile(keywords):
    """One word-boundary regex per list; longest keyword first so the most
    specific phrase wins the match."""
    parts = sorted({k.strip() for k in keywords if k.strip()}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in parts) + r")\b", re.I)


_HARD_PATTERN = _compile(HARD_COURSE_KEYWORDS)
_SOFT_PATTERN = _compile(SOFT_COURSE_KEYWORDS)
_OVERRIDE_PATTERN = _compile(OPPORTUNITY_OVERRIDES)
_ML_CONTEXT_PATTERN = _compile(ML_TRAINING_CONTEXT)


def _is_ml_training(match, haystack):
    """True when a soft "training" hit means training a model, not a course."""
    return match.group(0).lower().startswith("training") and bool(
        _ML_CONTEXT_PATTERN.search(haystack)
    )


def is_course(title, context=""):
    """
    True when the listing is a course / structured training programme and must
    be kept out of the dashboard.

    `context` is any short description text scraped next to the title. It is
    only consulted for the override check - a stray "course" in a sidebar
    should not reject an otherwise good event, but a "hackathon" mentioned in
    the blurb is fair evidence the listing is a hackathon.
    """
    if not title:
        return False

    if _HARD_PATTERN.search(title):
        return True

    soft = _SOFT_PATTERN.search(title)
    if soft:
        haystack = f"{title} {context or ''}"
        if _is_ml_training(soft, haystack):
            return False
        return not _OVERRIDE_PATTERN.search(haystack)

    return False


def course_reason(title, context=""):
    """The matched keyword behind an `is_course` rejection, for crawl logs."""
    if not title:
        return None
    hard = _HARD_PATTERN.search(title)
    if hard:
        return f"hard:{hard.group(0).lower()}"
    soft = _SOFT_PATTERN.search(title)
    if soft:
        haystack = f"{title} {context or ''}"
        if not _is_ml_training(soft, haystack) and not _OVERRIDE_PATTERN.search(haystack):
            return f"soft:{soft.group(0).lower()}"
    return None
