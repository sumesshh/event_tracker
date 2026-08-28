"""
Location vocabulary.

The Country filter lists whole countries; the State filter lists Indian
states and union territories. Scraped pages are inconsistent about which of
the two they name - a source can report its region as "India", "Global",
"Kochi" or "Hyderabad" - so everything is folded onto this one vocabulary
before it is stored, and the State drop-down is built from INDIAN_STATES
rather than from whatever strings happen to be in the table.

Kerala leads the list because Kerala opportunities are the platform's primary
focus; the rest is alphabetical.
"""

# Canonical state / UT names. Anything not in here is not a state.
INDIAN_STATES = [
    "Kerala",
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh",
    "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jammu and Kashmir", "Jharkhand", "Karnataka", "Ladakh", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
    "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

_STATE_LOOKUP = {name.lower(): name for name in INDIAN_STATES}

# Spellings and short forms that mean a state but do not match it literally.
STATE_ALIASES = {
    "new delhi": "Delhi", "delhi ncr": "Delhi", "ncr": "Delhi",
    "orissa": "Odisha", "pondicherry": "Puducherry",
    "j&k": "Jammu and Kashmir", "jammu & kashmir": "Jammu and Kashmir",
    "uttaranchal": "Uttarakhand", "up": "Uttar Pradesh",
    "tn": "Tamil Nadu", "ap": "Andhra Pradesh",
}

# Cities the sources name instead of their state. Only unambiguous ones - a
# city that shares its name with a town in another state is left out rather
# than filed under a guess.
CITY_TO_STATE = {
    # Kerala
    "kochi": "Kerala", "cochin": "Kerala", "ernakulam": "Kerala",
    "thiruvananthapuram": "Kerala", "trivandrum": "Kerala", "kovalam": "Kerala",
    "kozhikode": "Kerala", "calicut": "Kerala", "thrissur": "Kerala",
    "kollam": "Kerala", "kannur": "Kerala", "alappuzha": "Kerala",
    "kottayam": "Kerala", "palakkad": "Kerala", "malappuram": "Kerala",
    "kakkanad": "Kerala", "technopark": "Kerala", "infopark": "Kerala",
    "cyberpark": "Kerala",
    # Rest of India
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "mysuru": "Karnataka",
    "mysore": "Karnataka", "mangaluru": "Karnataka",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu",
    "madurai": "Tamil Nadu", "tiruchirappalli": "Tamil Nadu",
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra",
    "navi mumbai": "Maharashtra", "thane": "Maharashtra",
    "hyderabad": "Telangana", "warangal": "Telangana",
    "ahmedabad": "Gujarat", "surat": "Gujarat", "gandhinagar": "Gujarat",
    "vadodara": "Gujarat",
    "kolkata": "West Bengal", "howrah": "West Bengal",
    "jaipur": "Rajasthan", "udaipur": "Rajasthan", "jodhpur": "Rajasthan",
    "lucknow": "Uttar Pradesh", "noida": "Uttar Pradesh",
    "greater noida": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "gurugram": "Haryana", "gurgaon": "Haryana", "faridabad": "Haryana",
    "indore": "Madhya Pradesh", "bhopal": "Madhya Pradesh",
    "patna": "Bihar", "ranchi": "Jharkhand", "raipur": "Chhattisgarh",
    "bhubaneswar": "Odisha", "guwahati": "Assam", "dehradun": "Uttarakhand",
    "chandigarh": "Chandigarh", "mohali": "Punjab", "ludhiana": "Punjab",
    "visakhapatnam": "Andhra Pradesh", "vijayawada": "Andhra Pradesh",
    "tirupati": "Andhra Pradesh",
    "panaji": "Goa", "goa": "Goa", "shillong": "Meghalaya",
    "srinagar": "Jammu and Kashmir", "jammu": "Jammu and Kashmir",
    "yashobhoomi": "Delhi", "pragati maidan": "Delhi", "biec": "Karnataka",
}

# Region strings that name no state at all. Stored as "" so the State filter
# never offers them as if they were places.
NON_STATE_REGIONS = {
    "", "india", "global", "worldwide", "online", "virtual", "international",
    "remote", "anywhere", "n/a", "not specified", "various", "multiple",
    "pan india", "all india", "asia", "europe", "usa", "world",
}


def normalize_state(*candidates):
    """
    Fold any number of location strings onto one canonical Indian state.

    Each candidate - a scraped `region`, a `location` line, a venue name - is
    tried in order and the first one that resolves wins. Returns "" when
    nothing names a state, which is the correct answer for a global webinar
    and for "India" on its own.
    """
    for raw in candidates:
        if not raw:
            continue
        text = " ".join(str(raw).split()).strip().strip(",.")
        low = text.lower()

        if low in NON_STATE_REGIONS:
            continue
        if low in _STATE_LOOKUP:
            return _STATE_LOOKUP[low]
        if low in STATE_ALIASES:
            return STATE_ALIASES[low]
        if low in CITY_TO_STATE:
            return CITY_TO_STATE[low]

        # "Chennai Trade Centre, Chennai" / "Kochi, Kerala" - check each comma
        # separated part, then each word-run, longest keys first so
        # "greater noida" beats "noida".
        parts = [p.strip().lower() for p in text.replace("|", ",").split(",")]
        for part in parts:
            if part in _STATE_LOOKUP:
                return _STATE_LOOKUP[part]
            if part in STATE_ALIASES:
                return STATE_ALIASES[part]
            if part in CITY_TO_STATE:
                return CITY_TO_STATE[part]

        for key in sorted(CITY_TO_STATE, key=len, reverse=True):
            if key in low:
                return CITY_TO_STATE[key]
        for key, name in sorted(_STATE_LOOKUP.items(), key=lambda kv: -len(kv[0])):
            if key in low:
                return name

    return ""


def normalize_country(country, *fallbacks):
    """
    Canonical country name. A record that resolves to an Indian state is
    India even when the source labelled it "Global", because that is what the
    Country filter has to agree with.
    """
    text = (country or "").strip()
    low = text.lower()

    # "India" may arrive in either the country column or a location line, so
    # every candidate is checked before anything else is considered.
    for value in (text,) + tuple(fallbacks):
        if str(value or "").strip().lower() in ("india", "bharat"):
            return "India"
    if normalize_state(text, *fallbacks):
        return "India"
    if low in ("", "global", "worldwide", "online", "international", "virtual"):
        return "Global"
    if low in ("us", "usa", "united states", "united states of america"):
        return "USA"
    if low in ("uk", "united kingdom", "great britain"):
        return "UK"
    return text or "Global"
