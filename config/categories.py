"""
Category vocabulary and the keyword rules used to auto-tag every event.

The categoriser is deliberately keyword based (not a paid AI API) so the whole
system stays free to run. Rules are ordered: the first category whose keywords
match the event title wins, which is why the very specific categories
(Hackathon, Funding) are listed before the broad ones (Technology).
"""

# The categories shown in the UI filter bar. Rextech Studios builds games,
# AR/VR experiences and apps, so those three lead the list.
CATEGORIES = [
    "Grant",
    "Funding",
    "Fellowship",
    "Accelerator",
    "Incubator",
    "Startup Program",
    "Hackathon",
    "Game Jam",
    "Pitch Competition",
    "Competition",
    "Challenge",
    "Awards",
    "Showcase",
    "Expo",
    "Conference",
    "Webinar",
    "Workshop",
    "Networking",
    "Gaming Event",
    "EdTech Event",
    "Technology Event",
    "Industry Event",
]

# The three categories the studio actually works in. Events in these are
# ranked above everything else and can be isolated with the "Core focus"
# filter on the events page.
# The category list no longer carries separate "AR VR" and "Apps" entries, so
# only the two gaming categories name focus work directly. This costs nothing:
# focus_score() reads FOCUS_KEYWORDS against the title first, and that list
# still covers AR/VR and app keywords in full - the category is only a
# secondary signal.
FOCUS_CATEGORIES = ["Gaming Event", "Game Jam"]

# category -> keywords that identify it. Matching is case-insensitive and done
# on the event title plus any short description text found next to it.
#
# Order matters: the first category whose keywords match wins, so the list runs
# from the most specific opportunity type to the broadest subject label. A
# "Game Development Grant" files under Grant, not Gaming Event; "India Game
# Awards" under Awards, not Gaming Event. The trailing four subject categories
# (Gaming/EdTech/Technology/Industry Event) only catch listings that named no
# opportunity type at all.
#
# None of this affects the "Core focus" filter or ranking - those read the
# separate `focus` score, computed from the title independently of category.
CATEGORY_KEYWORDS = {
    # --- Money ---------------------------------------------------------
    "Grant": [
        "grant", "grants", "grant scheme", "innovation grant", "research grant",
        "seed grant", "matching grant", "grant-in-aid", "subsidy",
    ],
    "Fellowship": [
        "fellowship", "fellowships", "fellow program", "fellow programme",
    ],
    "Accelerator": [
        "accelerator", "acceleration program", "acceleration programme",
        "scale-up program", "scaleup program",
    ],
    "Incubator": [
        "incubator", "incubation", "incubation program", "incubation programme",
    ],
    "Funding": [
        "funding", "fund ", "seed funding", "seed round", "investor", "venture",
        "vc ", "angel investor", "financial support", "capital",
    ],
    # --- Build / compete -----------------------------------------------
    "Game Jam": [
        "game jam", "gamejam", "ludum dare", "byog", "build your own game",
        "jam ", "gamedev jam",
    ],
    "Hackathon": [
        "hackathon", "hack ", "hackfest", "codefest", "code fest", "ideathon",
        "datathon", "buildathon", "sprint challenge",
    ],
    "Pitch Competition": [
        "pitch competition", "pitch day", "pitchfest", "demo day",
        "pitch event", "startup pitch",
    ],
    "Awards": [
        "award", "awards", "prize", "honours", "honors", "recognition program",
    ],
    "Competition": [
        "competition", "contest", "idea competition", "grand challenge",
        "olympiad", "tournament",
    ],
    "Challenge": [
        "challenge", "challenges", "innovation challenge", "open challenge",
    ],
    # --- Programs -------------------------------------------------------
    "Startup Program": [
        "startup program", "startup programme", "innovation program",
        "innovation programme", "entrepreneurship program", "student program",
        "residency", "cohort", "call for applications", "call for",
        "applications open", "application open", "invites applications",
        "programme", "program",
    ],
    # --- Gatherings -----------------------------------------------------
    "Showcase": [
        "showcase", "utsav", "indieverse", "exhibition", "demo night",
        "screening", "festival",
    ],
    "Expo": [
        "expo", "trade show", "trade fair", "convention",
    ],
    "Conference": [
        "conference", "summit", "congress", "symposium", "keynote", "con 20",
        "devfest", "conclave", "gdc", "igdc",
    ],
    "Webinar": [
        "webinar", "online session", "livestream", "live stream", "virtual session",
        "ask me anything", "office hours", "info session", "information session",
    ],
    "Workshop": [
        "workshop", "masterclass", "hands-on", "hands on", "orientation",
        "clinic", "lab session",
    ],
    "Networking": [
        "networking", "meetup", "meet-up", "mixer", "roundtable", "mentor",
        "founders night", "user group", "community event",
    ],
    # --- Subject fallbacks (only when no opportunity type matched) -------
    "Gaming Event": [
        "game", "games", "gaming", "gamedev", "game dev", "esports", "unity",
        "unreal", "godot", "gamescom", "indie dev", "console", "game engine",
        "level design", "game art", "indie game", "mobile game", "game design",
        "gameplay", "game studio", "playtest", "steam", "itch.io",
        "godotcon", "godotfest", "unitecon", "unrealfest", "devcom", "devgamm",
        "casual connect", "reboot develop", "white nights", "gamesbeat",
        # AR/VR/XR and app keywords land here too - the studio treats them as
        # one body of work, and the focus score keeps them ranked together.
        "ar/vr", "ar vr", "augmented reality", "virtual reality", "mixed reality",
        "xr", "metaverse", "spatial computing", "immersive", "vision pro",
        "openxr", "webxr", "arkit", "arcore", "hololens", "oculus", "meta quest",
    ],
    "EdTech Event": [
        "edtech", "ed-tech", "education technology", "didac", "edu expo",
        "education expo", "learning technology", "school technology",
        "higher education", "academic technology",
    ],
    "Technology Event": [
        "ai ", " ai", "artificial intelligence", "machine learning",
        "deep learning", "llm", "genai", "generative", "data science", "nlp",
        "computer vision", "neural", "gpu", "gtc", "mlops", "analytics",
        "app", "apps", "mobile app", "android", "ios ", " ios", "flutter",
        "react native", "kotlin", "swift", "droidcon", "wwdc",
        "cloud", "devops", "blockchain", "robotics", "iot", "cybersecurity",
        "technology", "tech ",
    ],
    "Industry Event": [
        "startup", "start-up", "entrepreneur", "founder", "unicorn", "msme",
        "business plan", "industry", "b2b", "enterprise",
    ],
}

# Words that mark an event as squarely inside the studio's line of work.
# `strong` is an unambiguous hit (the event is about games, XR or app
# building); `weak` is a supporting signal that only counts as focus when the
# event also lands in one of the FOCUS_CATEGORIES. The scores feed the ranking
# that puts these events at the top of every list.
FOCUS_KEYWORDS = {
    "strong": [
        # Games
        "game", "games", "gaming", "gamedev", "game dev", "game jam", "gamejam",
        "unity", "unreal", "godot", "esports", "indie game", "game design",
        "game art", "game audio", "level design", "gdc", "gamescom",
        "ludum dare", "game engine", "game studio",
        "godotcon", "godotfest", "unitecon", "unrealfest", "devcom", "devgamm",
        # AR / VR / XR
        "ar/vr", "ar vr", "xr", "augmented reality", "virtual reality",
        "mixed reality", "metaverse", "immersive", "spatial computing",
        "vision pro", "visionos", "openxr", "webxr", "arkit", "arcore",
        "meta quest", "oculus", "hololens", "volumetric",
        # Apps
        "app", "apps", "mobile app", "app dev", "android", "ios", "flutter",
        "react native", "kotlin", "swift", "swiftui", "jetpack compose",
        "droidcon", "play store", "app store", "wwdc", "mobile dev",
    ],
    "weak": [
        "3d", "animation", "vfx", "graphics", "rendering", "shader", "blender",
        "maya", "houdini", "simulation", "interactive", "creative tech",
        "developer", "sdk", "engine", "multiplayer", "ux", "ui", "product design",
    ],
}

# An event must mention at least one of these to be considered relevant to
# Rextech Studios. Government "what's new" pages publish a lot of unrelated
# notices, and this filter keeps them out of the dashboard.
RELEVANCE_KEYWORDS = [
    # Gaming
    "game", "gaming", "gamedev", "esports", "unity", "unreal", "godot", "jam",
    # Mobile / software
    "app", "mobile", "android", "ios", "flutter", "react", "developer", "dev",
    "software", "engineering", "coding", "code", "programming", "python",
    "cloud", "devops", "docker", "kubernetes", "open source", "api", "web",
    # AR / VR / XR
    "ar", "vr", "xr", "augmented", "virtual reality", "metaverse", "immersive",
    "spatial",
    # AI
    "ai", "artificial intelligence", "machine learning", "deep learning", "llm",
    "data", "analytics", "generative", "genai", "gpu",
    # Startup / funding
    "startup", "entrepreneur", "founder", "incubat", "accelerat", "grant",
    "funding", "fund", "seed", "investor", "pitch", "demo day", "venture",
    "innovation", "msme", "fellowship", "scheme",
    # Event words
    "hackathon", "conference", "summit", "expo", "meetup", "webinar", "workshop",
    "networking", "challenge", "competition", "contest", "event",
    "tech", "technology", "digital", "design", "product", "3d", "animation",
    "vfx",
    # Opportunity words. Course vocabulary (course, certification, diploma,
    # bootcamp, academy) is deliberately absent - those listings are rejected
    # outright by config.course_filter, so treating them as relevant would only
    # pull work into a pipeline that discards them.
    "scholarship", "cybersecurity", "residency", "cohort",
]

# Titles containing any of these are almost never real events - they are
# navigation links, cookie banners or boilerplate.
NOISE_KEYWORDS = [
    "cookie", "privacy policy", "terms of", "sign in", "sign up", "log in",
    "login", "register now", "subscribe", "newsletter", "read more",
    "learn more", "click here", "contact us", "about us", "home page",
    "view all", "see all", "load more", "back to top", "skip to", "menu",
    "search", "download", "follow us", "share", "copyright", "all rights",
    "faq", "careers", "press release", "sitemap", "accessibility",
    # Section headings that look like titles but only label a list.
    "upcoming events", "past events", "all events", "recent events",
    "our events", "event calendar", "latest news", "quick links",
    "grievance", "tender", "recruitment", "vacancy", "annual report",
    "notification no", "office order", "circular", "disclaimer",
    "help desk", "website policy", "screen reader", "feedback",
    "open workspace", "go premium", "find my grants", "show grants for me",
    # Marketing and editorial copy that reads like a title but is not an
    # event: product blurbs, blog posts and community write-ups.
    # "in action" was here too, but it rejected real listings such as
    # "Kubeflow Community Showcase 2026: GenAI and MLOps in Action".
    "hall of fame", "tune in", "community spotlight",
    "spotlight:", "get the app", "download the app", "code of conduct",
    "meet the team", "our story", "job board", "merch", "become a sponsor",
    "sponsorship", "media kit", "brand guidelines", "archive policy",
    "watch the replay", "on demand", "on-demand",
    "case study", "success story", "testimonial", "what is ",
]

# Government and corporate sites publish news *reports about* events that
# already happened. These past-tense verbs are the giveaway - an announcement
# nobody can register for is not useful on the dashboard.
PAST_REPORT_KEYWORDS = [
    "organised", "organized", "conducted", "was held", "were held",
    "held in", "held at", "concluded", "inaugurat", "flagged off",
    "participate", "participated", "participates", "attended", "addresses",
    "launched", "unveiled", "celebrat", "review meeting", "visited",
    "signed mou", "highlights of", "recap", "wrap-up", "wrap up",
    "successfully", "takeaways",
]

# A title with no usable date still earns a place on the dashboard if it names
# a real, joinable opportunity. Used to filter the weakest extraction strategy.
STRONG_EVENT_KEYWORDS = [
    "hackathon", "conference", "summit", "expo", "webinar", "workshop",
    "meetup", "game jam", "gamejam", "jam", "challenge",
    "competition", "contest", "grant", "funding", "fellowship", "scholarship",
    "accelerator", "incubation", "incubator", "cohort", "demo day", "pitch",
    "devfest", "festival", "fest", "conclave", "symposium", "convention",
    "masterclass", "programme", "program", "apply", "registration",
    "call for", "applications open", "invites", "award", "awards", "gtc",
    "gdc", "wwdc", "i/o", "connect", "con 2", "expo 2", "2026", "2027",
]


# ---------------------------------------------------------------------------
# Dashboard groupings
# ---------------------------------------------------------------------------

# The counters on the home page. Each label maps to the categories that roll
# up into it, so "Funding" covers the three money categories the classifier
# distinguishes and "Startup Programs" covers the three programme categories.
# Nothing here counts a course - courses never reach the table (see
# config.course_filter), so the numbers are opportunity counts by definition.
OPPORTUNITY_GROUPS = {
    "Grants": ["Grant"],
    "Funding": ["Funding", "Fellowship"],
    "Hackathons": ["Hackathon", "Game Jam"],
    "Meetups": ["Networking"],
    "Startup Programs": ["Startup Program", "Accelerator", "Incubator"],
    "Competitions": ["Competition", "Pitch Competition", "Challenge", "Awards"],
    "Webinars": ["Webinar"],
    "Conferences": ["Conference", "Expo", "Showcase"],
    "Workshops": ["Workshop"],
}

# The subset of categories the "Startup Funding" shortcut resolves to. The
# brief asks for it as its own filter; it is a view over the money categories
# rather than a fourth one, because a scraped title cannot reliably be told
# apart from a plain "Funding" listing.
STARTUP_FUNDING_CATEGORIES = ["Funding", "Grant", "Accelerator", "Incubator"]
