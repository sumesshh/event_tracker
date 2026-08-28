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
    "Gaming",
    "AR VR",
    "Apps",
    "Hackathon",
    "AI",
    "Startup",
    "Conference",
    "Meetup",
    "Funding",
    "Workshop",
    "Webinar",
    "Networking",
    "Technology",
]

# The three categories the studio actually works in. Events in these are
# ranked above everything else and can be isolated with the "Core focus"
# filter on the events page.
FOCUS_CATEGORIES = ["Gaming", "AR VR", "Apps"]

# category -> keywords that identify it. Matching is case-insensitive and done
# on the event title plus any short description text found next to it.
#
# Order matters: the first category whose keywords match wins. The three focus
# categories are checked first, so "AI for Game Developers" files under Gaming
# rather than AI and "Flutter Workshop" under Apps rather than Workshop.
CATEGORY_KEYWORDS = {
    "AR VR": [
        "ar/vr", "ar vr", "augmented reality", "virtual reality", "mixed reality",
        "xr", "metaverse", "spatial computing", "immersive", "headset", "quest",
        "vision pro", "visionos", "openxr", "webxr", "arkit", "arcore",
        "hololens", "oculus", "meta quest", "3d scanning", "digital twin",
        "volumetric", "haptic", "6dof", "passthrough",
    ],
    "Gaming": [
        "game", "gaming", "gamedev", "game dev", "esports", "unity", "unreal",
        "godot", "gamescom", "gdc", "indie dev", "console", "game jam",
        "gamejam", "ludum dare", "game engine", "level design", "game art",
        # Compound event names. Keyword matching is whole-word, so "godot"
        # alone never fires on "GodotCon" - the compounds need listing.
        "godotcon", "godotfest", "unitecon", "unrealfest", "devcom", "devgamm",
        "casual connect", "reboot develop", "white nights", "gamesbeat",
        "game audio", "playtest", "indie game", "mobile game", "game design",
        "gameplay", "game studio", "publisher", "steam", "itch.io",
    ],
    "Apps": [
        "app", "apps", "app dev", "mobile app", "android", "ios ", " ios",
        "flutter", "react native", "kotlin", "swift", "swiftui", "jetpack compose",
        "play store", "google play", "app store", "droidcon", "mobile dev",
        "cross-platform", "pwa", "progressive web app", "wwdc", "xcode",
        "app growth", "mobile first", "appdev",
    ],
    "Hackathon": [
        "hackathon", "hack ", "codefest",
        "code fest", "ideathon", "datathon", "buildathon", "sprint challenge",
    ],
    "Funding": [
        "grant", "funding", "fund ", "seed", "accelerator", "incubation",
        "incubator", "investor", "pitch", "demo day", "venture", "scheme",
        "subsidy", "fellowship", "cohort", "application open", "call for",
    ],
    "AI": [
        "ai ", " ai", "artificial intelligence", "machine learning", "deep learning",
        "llm", "genai", "generative", "data science", "nlp", "computer vision",
        "neural", "gpu", "gtc", "mlops", "analytics",
    ],
    "Webinar": [
        "webinar", "online session", "livestream", "live stream", "virtual session",
        "ask me anything", "office hours",
    ],
    "Workshop": [
        "workshop", "bootcamp", "training", "masterclass", "course", "tutorial",
        "hands-on", "hands on", "learning session", "certification",
    ],
    "Conference": [
        "conference", "summit", "expo", "congress", "symposium", "convention",
        "keynote", "con 20", "devfest", "fest", "week ",
    ],
    "Meetup": [
        "meetup", "meet-up", "chapter event", "user group", "community event",
        "study jam",
    ],
    "Networking": [
        "networking", "mixer", "connect", "roundtable", "mentor", "founders night",
        "networking night",
    ],
    "Startup": [
        "startup", "start-up", "entrepreneur", "founder", "unicorn", "msme",
        "business plan",
    ],
}

# ---------------------------------------------------------------------------
# EdTech & Learning Programs
# ---------------------------------------------------------------------------
# A second, independent category system layered on top of the event
# categories above. A learning opportunity gets ONE or MORE of these tags
# (stored as a JSON list in `events.categories`) in addition to its primary
# `category` value. Kept separate from CATEGORY_KEYWORDS because a program can
# legitimately carry several of these at once ("AI Fellowship" -> EdTech + AI
# & Machine Learning + Skill Development), whereas the event categoriser above
# picks exactly one.

LEARNING_CATEGORIES = [
    "EdTech",
    "Online Learning",
    "Skill Development",
    "Professional Training",
    "Coding & Programming",
    "AI & Machine Learning",
    "Data Science",
    "Cybersecurity",
    "Game Development",
    "AR/VR/XR",
    "Entrepreneurship",
    "Business & Management",
    "Digital Marketing",
    "Design & UI/UX",
    "Cloud & DevOps",
    "Software Development",
    "STEM",
    "Research",
    "Language Learning",
    "Career Development",
    "Leadership",
    "Financial Literacy",
    "Creative Technology",
]

# Keywords that identify a learning-category tag. Unlike CATEGORY_KEYWORDS,
# every matching category is kept (a program can carry several tags).
LEARNING_CATEGORY_KEYWORDS = {
    "AI & Machine Learning": [
        "ai ", " ai", "artificial intelligence", "machine learning", "deep learning",
        "llm", "genai", "generative ai", "neural network", "mlops",
    ],
    "Data Science": [
        "data science", "data analytics", "data analysis", "big data",
        "data engineering", "data visualization", "statistics",
    ],
    "Cybersecurity": [
        "cybersecurity", "cyber security", "ethical hacking", "penetration testing",
        "infosec", "information security", "network security", "ceh",
    ],
    "Game Development": [
        "game development", "game dev", "unity", "unreal", "godot", "game design",
        "game programming",
    ],
    "AR/VR/XR": [
        "ar/vr", "ar vr", "xr", "augmented reality", "virtual reality",
        "mixed reality", "metaverse", "immersive tech",
    ],
    "Cloud & DevOps": [
        "cloud computing", "aws", "azure", "google cloud", "devops", "kubernetes",
        "docker", "site reliability",
    ],
    "Software Development": [
        "software development", "software engineering", "web development",
        "full stack", "full-stack", "backend", "frontend", "app development",
        "programming", "coding bootcamp",
    ],
    "Coding & Programming": [
        "coding", "programming", "learn to code", "python course", "java course",
        "javascript course", "c++ course", "sql course",
    ],
    "Design & UI/UX": [
        "ui/ux", "ui ux", "user experience", "user interface", "product design",
        "graphic design", "figma",
    ],
    "Digital Marketing": [
        "digital marketing", "seo", "sem", "social media marketing", "content marketing",
        "performance marketing", "growth marketing",
    ],
    "Entrepreneurship": [
        "entrepreneurship", "startup program", "founder program", "venture building",
        "business incubation",
    ],
    "Business & Management": [
        "business management", "mba", "management program", "project management",
        "product management",
    ],
    "STEM": [
        "stem", "science technology engineering", "robotics", "electronics",
        "iot workshop",
    ],
    "Research": [
        "research fellowship", "research program", "research internship",
        "phd program", "doctoral", "postdoc",
    ],
    "Language Learning": [
        "language course", "english proficiency", "ielts", "toefl", "spoken english",
        "foreign language",
    ],
    "Career Development": [
        "career development", "career program", "job readiness", "employability",
        "career guidance", "placement training",
    ],
    "Leadership": [
        "leadership program", "leadership training", "leadership development",
    ],
    "Financial Literacy": [
        "financial literacy", "personal finance", "investing course",
        "financial planning",
    ],
    "Creative Technology": [
        "creative technology", "creative coding", "digital art", "animation course",
        "vfx course", "3d modeling",
    ],
    "Professional Training": [
        "professional training", "corporate training", "upskilling", "reskilling",
        "vocational training",
    ],
    "Skill Development": [
        "skill development", "skilling", "skill india", "vocational course",
    ],
    "Online Learning": [
        "online course", "online learning", "e-learning", "mooc", "self-paced",
    ],
    "EdTech": [
        "edtech", "ed-tech", "learning platform", "learning app",
    ],
}

# Words that flag a scraped item as a learning/education opportunity at all,
# rather than an event, funding round or hackathon. Checked before the more
# specific LEARNING_CATEGORY_KEYWORDS classification runs.
LEARNING_SIGNAL_KEYWORDS = [
    "course", "certification", "certificate program", "scholarship", "fellowship",
    "bootcamp", "training program", "training programme", "academy", "masterclass",
    "summer school", "winter school", "mentorship program", "apprenticeship",
    "internship program", "university program", "degree program", "diploma",
    "learning program", "learning programme", "skilling program", "upskilling",
    "reskilling", "moocs", "mooc", "online course", "e-learning", "elearning",
    "workshop series", "study program", "student program", "graduate program",
    "career program", "developer program", "technology academy", "tech academy",
    "corporate learning", "government skill", "skill development scheme",
]

PROGRAM_TYPES = [
    "Course", "Bootcamp", "Fellowship", "Scholarship", "Training", "Certification",
    "Workshop", "Internship", "Apprenticeship", "Mentorship", "Academy",
    "Degree/University", "Research",
]

PROGRAM_TYPE_KEYWORDS = {
    "Scholarship": ["scholarship"],
    "Fellowship": ["fellowship"],
    "Bootcamp": ["bootcamp", "boot camp"],
    "Apprenticeship": ["apprenticeship", "apprentice"],
    "Mentorship": ["mentorship", "mentoring program"],
    "Internship": ["internship", "intern program"],
    "Certification": ["certification", "certificate program", "certified"],
    "Academy": ["academy"],
    "Degree/University": [
        "degree program", "university program", "bachelor", "master's",
        "masters program", "phd", "doctoral", "undergraduate program",
        "postgraduate program",
    ],
    "Research": ["research fellowship", "research program", "research internship"],
    "Workshop": ["workshop", "masterclass", "summer school", "winter school"],
    "Training": ["training", "upskilling", "reskilling", "vocational"],
    "Course": ["course", "mooc", "online learning", "e-learning", "elearning"],
}

LEVELS = ["Beginner", "Intermediate", "Advanced", "Professional"]

LEVEL_KEYWORDS = {
    "Beginner": ["beginner", "introductory", "fundamentals", "for beginners", "starter"],
    "Advanced": ["advanced", "expert level", "in-depth"],
    "Professional": ["professional", "working professional", "executive"],
    "Intermediate": ["intermediate"],
}

FORMATS = ["Online", "Offline", "Hybrid"]

FORMAT_KEYWORDS = {
    "Hybrid": ["hybrid"],
    "Online": [
        "online", "virtual", "e-learning", "elearning", "self-paced", "remote",
        "webinar", "livestream",
    ],
}

DURATIONS = ["1 day", "1 week", "1 month", "3 months", "6 months", "1 year+"]

FUNDING_TYPES = [
    "Fully Funded", "Free", "Scholarship", "Free + Certificate",
    "Partially Funded", "Paid", "Unknown",
]

# Order = discovery priority (fully funded / free ranks above paid).
FUNDING_TYPE_PRIORITY = {
    "Fully Funded": 1,
    "Free": 2,
    "Scholarship": 3,
    "Free + Certificate": 4,
    "Partially Funded": 5,
    "Paid": 6,
    "Unknown": 7,
}

FUNDING_TYPE_KEYWORDS = {
    "Fully Funded": ["fully funded", "fully-funded", "all expenses paid", "100% funded"],
    "Scholarship": ["scholarship", "scholarships"],
    "Free + Certificate": ["free certificate", "free course with certificate"],
    "Partially Funded": ["partially funded", "partial scholarship", "partial funding"],
    "Free": ["free of cost", "no cost", "free course", "free program", "free training", "free access", " free "],
    "Paid": ["paid course", "fee applies", "tuition fee", "course fee", "enrollment fee", "registration fee"],
}

CERTIFICATE_STATUS = ["Certificate available", "No certificate", "Unknown"]

CERTIFICATE_KEYWORDS = {
    "Certificate available": [
        "certificate", "certification", "certified", "e-certificate", "e certificate",
    ],
}

# City / country hubs used to detect strict location scope for learning
# programs, separate from the general KNOWN_LOCATIONS list in the classifier.
LEARNING_LOCATIONS = [
    "Kerala", "India", "UAE", "United Arab Emirates", "Saudi Arabia", "Qatar",
    "Bahrain", "Oman", "Kuwait", "Jordan", "Online", "Global",
]

# Skill vocabulary used to populate `skills[]` on a learning program. Matching
# is whole-word / case-insensitive against the title + description.
SKILLS_VOCAB = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "SQL", "R", "Swift", "Kotlin", "PHP",
    "Machine Learning", "Artificial Intelligence", "Deep Learning",
    "Data Science", "Data Analytics", "Data Engineering", "NLP",
    "Computer Vision", "Generative AI",
    "Unity", "Unreal Engine", "Godot", "Game Design", "Game Development",
    "AR/VR", "Augmented Reality", "Virtual Reality", "XR",
    "Web Development", "React", "Angular", "Vue", "Node.js", "Django", "Flask",
    "Cloud Computing", "AWS", "Azure", "Google Cloud", "DevOps", "Docker",
    "Kubernetes",
  "Cybersecurity", "Ethical Hacking", "Network Security",
    "UI/UX Design", "Figma", "Product Design", "Graphic Design",
    "Digital Marketing", "SEO", "Content Marketing", "Social Media Marketing",
    "Entrepreneurship", "Business Management", "Project Management",
    "Blockchain", "Robotics", "IoT", "Embedded Systems",
    "Leadership", "Public Speaking", "Communication Skills",
    "Financial Literacy", "Investing",
    "English Language", "Spoken English",
]

# Career paths a program can prepare a learner for.
CAREER_PATHS_VOCAB = [
    "Software Developer", "Web Developer", "Mobile App Developer",
    "Game Developer", "Unity Developer", "Unreal Developer",
    "AR/VR Developer", "XR Developer",
    "AI Engineer", "Machine Learning Engineer", "Data Scientist",
    "Data Analyst", "Data Engineer",
    "Cybersecurity Analyst", "Ethical Hacker", "Security Engineer",
    "Cloud Engineer", "DevOps Engineer",
    "UI/UX Designer", "Product Designer", "Graphic Designer",
    "Digital Marketer", "SEO Specialist", "Content Strategist",
    "Entrepreneur", "Startup Founder", "Product Manager", "Project Manager",
    "Business Analyst",
    "Research Scientist", "Research Associate",
]

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
    "bootcamp", "networking", "challenge", "competition", "contest", "event",
    "tech", "technology", "digital", "design", "product", "3d", "animation",
    "vfx",
    # EdTech / learning programs
    "scholarship", "course", "certification", "certificate", "training",
    "diploma", "academy", "mentorship", "apprenticeship", "curriculum",
    "skilling", "upskilling", "learning", "education", "degree", "cybersecurity",
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
    "hall of fame", "tune in", "in action", "community spotlight",
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
    "bootcamp", "meetup", "game jam", "gamejam", "jam", "challenge",
    "competition", "contest", "grant", "funding", "fellowship", "scholarship",
    "accelerator", "incubation", "incubator", "cohort", "demo day", "pitch",
    "devfest", "festival", "fest", "conclave", "symposium", "convention",
    "masterclass", "training", "programme", "program", "apply", "registration",
    "call for", "applications open", "invites", "award", "awards", "gtc",
    "gdc", "wwdc", "i/o", "connect", "con 2", "expo 2", "2026", "2027",
]
