"""
Curated priority opportunities.

These eleven listings are seeded directly rather than scraped, because they are
the anchor set the platform is built around: Indian gaming, EdTech, startup and
AI opportunities relevant to students, developers and early-stage teams.

RULES FOR THIS FILE - they matter more than completeness:

  * Every populated field was read off the official source listed in
    `source_url`, or off an official government/organiser announcement.
  * A field that could not be verified is left as "" (the UI renders that as
    "Not available"). Nothing here is inferred, rounded or filled in from
    memory - no invented dates, prizes, deadlines, organisers or links.
  * Where sources disagreed, the field is left empty rather than picking one.
    GAISA is the live example: its 6th edition is variously announced for
    10-11 Feb, 18-19 Feb and 1-2 Sep 2026, so it carries no date.
  * `verified_on` records when a human-checkable pass was last made, so stale
    entries are obvious later.

Three corrections to the originally requested list, made because the official
sources say otherwise:

  * DIDAC India 2026 is in Bengaluru (BIEC), not New Delhi. The 2025 edition
    was the New Delhi one.
  * ET Tech X / Edu Expo Global 2026 is at Yashobhoomi, New Delhi, not Greater
    Noida. (Bharat Shiksha Expo is the Greater Noida education expo.)
  * GamingCon Bharat 2026 is at the Bombay Exhibition Centre, Mumbai, and
    "Indieverse" is its indie-showcase track rather than a separate event.

Dates are ISO. Several 2026 editions have already taken place - they are stored
with their real dates and the status logic files them as past, which is
correct. Inventing a future date to make them look current would be worse.
"""

from config.kerala_opportunities import INDIA_OPPORTUNITIES, KERALA_OPPORTUNITIES

VERIFIED_ON = "2026-08-28"

# Seeded through scripts.seed_opportunities. Keys map onto the events table.
PRIORITY_OPPORTUNITIES = [
    {
        "title": "India Game Developer Conference (IGDC) 2026",
        "category": "Conference",
        "subcategory": "Gaming",
        "description": (
            "The 18th edition of India's largest game developer conference. "
            "B2B conference sessions run 28-29 October, with the public IGDC "
            "Playground on 30-31 October."
        ),
        "organizer": "India Game Developer Conference",
        "location": "Chennai Trade Centre, Chennai",
        "country": "India",
        "region": "Tamil Nadu",
        "mode": "Offline",
        "start_date": "2026-10-28",
        "end_date": "2026-10-31",
        "deadline": "",
        "source_url": "https://indiagdc.com/",
        "application_url": "https://indiagdc.com/register/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "gaming, game development, conference, india, networking",
    },
    {
        "title": "India Game Awards 2026",
        "category": "Awards",
        "subcategory": "Gaming",
        "description": (
            "Awards for Indian game development across 20+ categories, judged "
            "by a national and international jury and presented at IGDC 2026 "
            "in Chennai. Finalists receive two complimentary IGDC passes and "
            "qualify for the Investor-Publisher Connect scrutiny round."
        ),
        "organizer": "Game Developer Association of India",
        "location": "Chennai, Tamil Nadu",
        "country": "India",
        "region": "Tamil Nadu",
        "mode": "Offline",
        "start_date": "",
        "end_date": "",
        # Entry deadline not stated on the official awards page.
        "deadline": "",
        "source_url": "https://indiagdc.com/awards/",
        "application_url": "https://indiagdc.com/awards/",
        # The official FAQ states no application fee; the eligibility window
        # on the page still shows last cycle's dates, so it is left out.
        "eligibility": "",
        "cost": "No application fee",
        "prize_or_funding": "",
        "tags": "gaming, awards, competition, india, indie",
    },
    {
        "title": "Indie Game Utsav",
        "category": "Showcase",
        "subcategory": "Indie Gaming",
        "description": (
            "A festival of Indian indie games, held alongside Mumbai Comic Con "
            "at the Jio World Centre. Developers can apply to exhibit."
        ),
        "organizer": "Indie Game Utsav",
        "location": "Jio World Centre, Mumbai",
        "country": "India",
        "region": "Maharashtra",
        "mode": "Offline",
        # The official site does not state the next edition's date.
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://indiegameutsav.com/",
        "application_url": "https://indiegameutsav.com/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "gaming, indie, showcase, festival, india",
    },
    {
        "title": "GamingCon Bharat 2026 - Indieverse",
        "category": "Gaming Event",
        "subcategory": "Showcase",
        "description": (
            "Third edition of GamingCon Bharat, supported by the Government of "
            "Maharashtra and the IGPDA. Includes Indieverse (a showcase of "
            "Indian independent studios), the Level Up Conference, esports "
            "tournaments, free play zones and MeepleCon board gaming."
        ),
        "organizer": "GamingCon Bharat",
        "location": "Bombay Exhibition Centre, Mumbai",
        "country": "India",
        "region": "Maharashtra",
        "mode": "Offline",
        "start_date": "2026-10-17",
        "end_date": "2026-10-18",
        "deadline": "",
        "source_url": "https://www.gamingcon.in/indieverse",
        "application_url": "https://www.gamingcon.in/indieverse",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "gaming, indie, showcase, esports, mumbai, india",
    },
    {
        "title": "India Games Showcase",
        "category": "Showcase",
        "subcategory": "Indie Gaming",
        "description": (
            "A digital showcase of new and upcoming Indian games, run as part "
            "of Summer Game Fest. An initiative of Nodding Heads Games and "
            "NODWIN Gaming."
        ),
        "organizer": "Nodding Heads Games / NODWIN Gaming",
        "location": "Online",
        "country": "India",
        "region": "",
        "mode": "Online",
        # The 2026 broadcast has aired; no next date announced.
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://www.summergamefest.com/events/india",
        "application_url": "",
        "eligibility": "",
        "cost": "Free to watch",
        "prize_or_funding": "",
        "tags": "gaming, indie, showcase, online, india",
    },
    {
        "title": "BYOG (Build Your Own Game) Jam",
        "category": "Game Jam",
        "subcategory": "Gaming",
        "description": (
            "India's longest-running annual game jam, held since 2010 and run "
            "by GameDev India, a volunteer-driven game creator community. The "
            "2025 edition drew over 1,000 jammers and 200+ submissions."
        ),
        "organizer": "GameDev India",
        "location": "Online / India",
        "country": "India",
        "region": "",
        "mode": "Online",
        # 2026 dates not yet announced; announced via their Discord.
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://gamedev.in/byog/",
        "application_url": "https://gamedev.in/byog/",
        "eligibility": "",
        "cost": "",
        # A Rs 3 lakh pool is advertised on the BYOG page, but not tied to a
        # confirmed 2026 edition, so it is not asserted here.
        "prize_or_funding": "",
        "tags": "game jam, hackathon, gaming, online, india, students",
    },
    {
        "title": "Global Game Jam (GGJ) - Indian Hubs",
        "category": "Game Jam",
        "subcategory": "Gaming",
        "description": (
            "The Indian sites of Global Game Jam, the worldwide annual game "
            "jam in which participants build a game to a shared theme over one "
            "weekend at a local host location."
        ),
        "organizer": "Global Game Jam",
        "location": "India (multiple hubs)",
        "country": "India",
        "region": "",
        "mode": "Hybrid",
        # Next edition's dates and the Indian site list are published on the
        # official site closer to the event.
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://globalgamejam.org/",
        "application_url": "https://globalgamejam.org/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "game jam, hackathon, gaming, india, students, developers",
    },
    {
        "title": "DIDAC India 2026",
        "category": "EdTech Event",
        "subcategory": "Education Expo",
        "description": (
            "Asia's largest B2B education exhibition and skills event, "
            "bringing together education technology suppliers, institutions "
            "and policymakers. Note: the 2026 edition moves to Bengaluru."
        ),
        "organizer": "Worlddidac / DIDAC India",
        "location": "Bangalore International Exhibition Centre (BIEC), Bengaluru",
        "country": "India",
        "region": "Karnataka",
        "mode": "Offline",
        "start_date": "2026-11-25",
        "end_date": "2026-11-27",
        "deadline": "",
        "source_url": "https://didacindia.com/",
        "application_url": "https://didacindia.com/visitors/the-event/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "edtech, education, expo, b2b, india",
    },
    {
        "title": "ET Tech X / Edu Expo Global 2026",
        "category": "EdTech Event",
        "subcategory": "Education Expo",
        "description": (
            "Co-located EdTech expo and conference at Yashobhoomi, New Delhi, "
            "with exhibitions, conference sessions, workshops and awards. "
            "Edu Expo Global runs 22-23 September; ET Tech X runs 22-24 "
            "September."
        ),
        "organizer": "ET Tech X / Edu Expo Global",
        "location": "Yashobhoomi, New Delhi",
        "country": "India",
        "region": "Delhi",
        "mode": "Offline",
        "start_date": "2026-09-22",
        "end_date": "2026-09-24",
        "deadline": "",
        "source_url": "https://www.ettechx.com/",
        "application_url": "https://www.eduexpoglobal.com/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "edtech, education, expo, conference, new delhi, india",
    },
    {
        "title": "TechSparks 2026",
        "category": "Industry Event",
        "subcategory": "Startup",
        "description": (
            "YourStory's flagship startup and technology summit, themed 'The "
            "New Tech Order', bringing together founders, investors, "
            "policymakers, enterprises, developers and creators."
        ),
        "organizer": "YourStory Media",
        "location": "Taj Yeshwantpur, Bengaluru",
        "country": "India",
        "region": "Karnataka",
        "mode": "Offline",
        "start_date": "2026-10-13",
        "end_date": "2026-10-15",
        "deadline": "",
        "source_url": "https://techsparks.yourstory.com/2026/",
        "application_url": "https://techsparks.yourstory.com/2026/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "startup, technology, pitching, investors, bengaluru, india",
    },
    {
        "title": "Global Artificial Intelligence Summit & Awards (GAISA) 2026",
        "category": "Conference",
        "subcategory": "AI / Technology",
        "description": (
            "The 6th edition of the Global Artificial Intelligence Summit & "
            "Awards, organised by the All India Council for Robotics & "
            "Automation (AICRA) in New Delhi. Check the official site for "
            "dates - announcements have differed between sources."
        ),
        "organizer": "All India Council for Robotics & Automation (AICRA)",
        "location": "New Delhi",
        "country": "India",
        "region": "Delhi",
        "mode": "Offline",
        # Sources give 10-11 Feb, 18-19 Feb and 1-2 Sep 2026. Left empty
        # rather than picking one.
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://gaisa.in/",
        "application_url": "https://gaisa.in/schedule",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "ai, artificial intelligence, technology, summit, awards, india",
    },
]

# The Kerala ecosystem leads the platform, so its curated block and the
# India-wide programmes Kerala applicants qualify for are appended here and
# seeded through the same script. Ordering in this list does not affect
# ranking - config/priority.py does that from the stored location.
PRIORITY_OPPORTUNITIES = (
    KERALA_OPPORTUNITIES + INDIA_OPPORTUNITIES + PRIORITY_OPPORTUNITIES
)
