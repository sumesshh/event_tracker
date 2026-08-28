"""
Geographic and organisational priority.

Every stored opportunity carries a deterministic `geo_score`, and the whole
platform - home page, All Events, search, category pages, the API - sorts on
it first. The order the score encodes is:

    Kerala -> Tamil Nadu (Chennai ahead of the rest) -> Karnataka ->
    rest of India -> Middle East -> Japan -> everywhere else

On top of that, five priority collections add a bonus when the record is
genuinely related to them. "Related" means the event's own fields say so -
organiser, source, title, tags or description - never a guess. A collection
with no matching data renders as an empty section, which is the honest
outcome; inventing a relationship to fill it would not be.

LOCATION IS READ FROM LOCATION FIELDS ONLY. `assign_location` looks at the
city / region / country / venue the source published, plus the online-or-not
flag. It deliberately ignores the title, so an event organised by a Kerala
company but held in Tokyo is filed under Japan, and an online webinar run
from Kochi scores in the online tier rather than as a Kerala event.
"""

from config.regions import CITY_TO_STATE, normalize_country, normalize_state

# --- geographic tiers ------------------------------------------------------

MIDDLE_EAST_COUNTRIES = [
    "UAE", "Saudi Arabia", "Qatar", "Bahrain", "Oman", "Kuwait",
]

# Spellings and cities the sources use for those countries.
_MIDDLE_EAST_LOOKUP = {
    "uae": "UAE", "united arab emirates": "UAE", "u.a.e": "UAE",
    "dubai": "UAE", "abu dhabi": "UAE", "sharjah": "UAE",
    "saudi arabia": "Saudi Arabia", "ksa": "Saudi Arabia",
    "riyadh": "Saudi Arabia", "jeddah": "Saudi Arabia",
    "qatar": "Qatar", "doha": "Qatar",
    "bahrain": "Bahrain", "manama": "Bahrain",
    "oman": "Oman", "muscat": "Oman",
    "kuwait": "Kuwait",
}

_JAPAN_LOOKUP = ["japan", "tokyo", "osaka", "kyoto", "yokohama", "fukuoka"]

GEO_SCORES = {
    "Kerala": 1000,
    "Tamil Nadu": 700,
    "Karnataka": 650,
    "India": 500,
    "Middle East": 300,
    "Japan": 200,
}

# Chennai is called out separately because it is a startup / gaming /
# conference hub in its own right, so it leads Tamil Nadu.
CITY_BONUS = {"Chennai": 50}

DEFAULT_GEO_SCORE = 100          # anywhere not named above
ONLINE_GEO_SCORE = 450           # open to everyone; sits just under India

# --- priority collections --------------------------------------------------
#
# tag -> (bonus, keywords). A keyword hits only against the record's own
# organiser / source / title / tags / description text.
#
# "Thinker" is its own priority tag, distinct from the "TinkerHub" source in
# config/sources.py. It only matches when a record's own text actually says
# "thinker" - it no longer folds in "tinkerhub" just because the names are a
# letter apart. TinkerHub stays a normal source/organiser; an event from it
# only earns the Thinker tag if the source itself uses that word.
PRIORITY_TAGS = {
    "Sayuj":     (900, ["sayuj"]),
    "Huddle":    (850, ["huddle"]),
    "Thinker":   (800, ["thinker"]),
    "Hackathon": (750, ["hackathon", "ideathon", "datathon", "buildathon",
                        "game jam", "gamejam", "codefest", "hackfest"]),
    "KSUM":      (700, ["ksum", "kerala startup mission", "startupmission",
                        "iedc", "young innovators programme"]),
}

# Sections that must stay visible even with zero matching records, instead of
# being hidden like an ordinary empty section - so the home page can label
# them "No verified opportunities found" rather than pretending they don't
# exist. Sayuj has no source registered anywhere in config/sources.py or
# config/kerala_opportunities.py, and none should be invented to fill it.
ALWAYS_SHOW_SECTIONS = {"Sayuj"}

# The order the home page renders its sections in, and the query behind each
# one. This is the geographic progression the brief specifies - Kerala, the
# priority collections, Tamil Nadu, Chennai, Karnataka, India, Middle East,
# Japan - followed by the topic sections, which are subject views rather than
# places and so sit after the geography rather than interrupting it.
#
# Every filter dict is passed straight through to db.query_events, and the
# same dict becomes the section's "See all" link, so what a section shows and
# what its link opens can never drift apart. A section with no matching data
# comes back empty and the home page hides it - a collection with nothing in
# it costs the user no scrolling, and filling it would mean inventing a
# relationship that the data does not support.
#
# There is no separate AR/VR section because there is no AR/VR *category*:
# the classifier files XR listings under Gaming Event and marks them with the
# `focus` score, so the honest section for them is the focus one.
SECTION_ORDER = [
    ("Kerala Opportunities", {"region": "Kerala"}),
    ("KSUM / Huddle", {"tag": "KSUM,Huddle"}),
    ("Sayuj", {"tag": "Sayuj"}),
    ("Thinker", {"tag": "Thinker"}),
    ("Hackathons & Game Jams", {"tag": "Hackathon"}),
    ("Grants & Funding", {"category": "Startup Funding"}),
    ("Tamil Nadu", {"region": "Tamil Nadu"}),
    ("Chennai", {"city": "Chennai"}),
    ("Karnataka", {"region": "Karnataka"}),
    ("India", {"country": "India"}),
    ("Middle East", {"country": "Middle East"}),
    ("Japan", {"country": "Japan"}),
    ("Gaming · AR/VR · Apps", {"focus_only": True}),
    ("EdTech", {"category": "EdTech Event"}),
    ("Technology", {"category": "Technology Event"}),
]


def _scan(lookup, candidates):
    """First lookup key found in any candidate string, longest key first."""
    for raw in candidates:
        low = " ".join(str(raw or "").split()).lower()
        if not low:
            continue
        if low in lookup:
            return lookup[low]
        for key in sorted(lookup, key=len, reverse=True):
            if key in low:
                return lookup[key]
    return ""


def detect_middle_east(*candidates):
    """The Middle East country named by any location string, or ""."""
    return _scan(_MIDDLE_EAST_LOOKUP, candidates)


def detect_japan(*candidates):
    """True when a location string names Japan or a Japanese host city."""
    for raw in candidates:
        low = " ".join(str(raw or "").split()).lower()
        if any(key in low for key in _JAPAN_LOOKUP):
            return True
    return False


# Preferred spelling for the cities that have more than one, and for the
# venues and tech parks the sources name instead of a city.
_CITY_SPELLING = {
    "cochin": "Kochi", "ernakulam": "Kochi", "infopark": "Kochi",
    "kakkanad": "Kochi", "trivandrum": "Thiruvananthapuram",
    "technopark": "Thiruvananthapuram", "calicut": "Kozhikode",
    "cyberpark": "Kozhikode", "bangalore": "Bengaluru", "biec": "Bengaluru",
    "mysore": "Mysuru", "gurgaon": "Gurugram", "new delhi": "Delhi",
    "yashobhoomi": "Delhi", "pragati maidan": "Delhi", "goa": "Panaji",
}


def _canonical_city(key):
    return _CITY_SPELLING.get(key, key.title())


def detect_city(*candidates):
    """
    The city named by a location line, restricted to the cities the platform
    tracks. Returns "" when the source named none of them.
    """
    for raw in candidates:
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        parts = [p.strip().lower() for p in text.replace("|", ",").split(",")]
        for part in parts:
            if part in CITY_TO_STATE:
                return _canonical_city(part)
        low = text.lower()
        for key in sorted(CITY_TO_STATE, key=len, reverse=True):
            if key in low:
                return _canonical_city(key)
    return ""


def assign_location(region="", country="", location="", mode=""):
    """
    Work out (country, state, city, tier) from location fields only.

    `tier` is the label the geographic score is looked up under: a state name,
    "India", "Middle East", "Japan", "Online" or "Other".
    """
    online = str(mode or "").strip().lower() in ("online", "virtual", "remote")

    middle_east = detect_middle_east(country, region, location)
    if middle_east:
        return middle_east, "", detect_city(location, region), "Middle East"

    if detect_japan(country, region, location):
        return "Japan", "", detect_city(location, region), "Japan"

    state = normalize_state(region, location)
    resolved_country = normalize_country(country, region, location)
    city = detect_city(location, region)

    if state:
        # An online event is not held *in* the state that runs it. It keeps
        # the state so the Kerala filter still finds it, but it scores in the
        # online tier instead of outranking events actually taking place there.
        return "India", state, city, ("Online" if online else state)
    if resolved_country == "India":
        return "India", "", city, ("Online" if online else "India")
    if online or resolved_country == "Global":
        return resolved_country, "", city, "Online"
    return resolved_country, "", city, "Other"


def match_tags(*texts):
    """
    The priority collections a record genuinely belongs to.

    Matching is on the record's own organiser / source / title / tags /
    description text. Returns a comma-separated string, stored alongside the
    event so filters and home page sections can select on it directly.
    """
    haystack = " ".join(str(t or "") for t in texts).lower()
    hits = [tag for tag, (_, words) in PRIORITY_TAGS.items()
            if any(word in haystack for word in words)]
    return ", ".join(hits)


def geo_score(tier, city="", tags=""):
    """
    The deterministic sort key - higher sorts first.

    geographic tier + Chennai bonus + every priority collection the record
    genuinely belongs to.
    """
    score = ONLINE_GEO_SCORE if tier == "Online" else GEO_SCORES.get(
        tier, DEFAULT_GEO_SCORE
    )
    score += CITY_BONUS.get(city, 0)

    for tag in [t.strip() for t in (tags or "").split(",") if t.strip()]:
        score += PRIORITY_TAGS.get(tag, (0, []))[0]
    return score
