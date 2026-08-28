"""
Kerala-first curated opportunities, plus the India-wide programmes Kerala
applicants are eligible for.

Same rules as config/priority_opportunities.py, which folds this list into
PRIORITY_OPPORTUNITIES:

  * Every populated field was read off the official page named in
    `source_url` on the VERIFIED_ON date.
  * A field the official page does not state is left as "" and renders as
    "Not available". No date, deadline, prize or funding amount here was
    inferred, rounded or recalled - KSUM runs most of its grants as rolling
    calls, and an invented deadline would be worse than an empty one.
  * Where official channels disagreed, the field is empty and the description
    says so (IEDC Startup Summit 2026 is the live example: KSUM's own channels
    have announced two different dates).
"""

# ---------------------------------------------------------------------------
# Kerala - Kerala Startup Mission, K-DISC and the state ecosystem
# ---------------------------------------------------------------------------

KERALA_OPPORTUNITIES = [
    {
        "title": "Huddle Global 2026",
        "category": "Conference",
        "subcategory": "Startup / Investor",
        "description": (
            "Kerala's flagship startup conference, organised by Kerala Startup "
            "Mission - founders, investors and innovators over three days at "
            "Kovalam. Diamond Pass holders can additionally apply for product "
            "launch slots and investor matchmaking."
        ),
        "organizer": "Kerala Startup Mission (KSUM)",
        "location": "The Leela Raviz Kovalam, Thiruvananthapuram, Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Offline",
        "start_date": "2026-11-12",
        "end_date": "2026-11-14",
        "deadline": "",
        "source_url": "https://huddleglobal.co.in/",
        "application_url": "https://tickets.startupmission.in/huddle-global-2026",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "huddle, ksum, kerala startup mission, startup, investor, "
                "networking, conference, kerala",
    },
    {
        "title": "KSUM Idea Grant",
        "category": "Grant",
        "subcategory": "Startup Funding",
        "description": (
            "An early-stage funding scheme for startups at the Ideation, "
            "Design, Proof of Concept and early MVP stages. Applications are "
            "made through the KSUM grant portal during an official call, "
            "screened by KSUM, then pitched to an Expert Committee; funds are "
            "released against milestones."
        ),
        "organizer": "Kerala Startup Mission (KSUM)",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://startupmission.kerala.gov.in/schemes/idea-grant",
        "application_url": "https://grants.startupmission.in",
        "eligibility": (
            "Innovators based out of Kerala; innovative technology-based "
            "products only; company incorporation required before disbursal; "
            "cannot re-apply within 3 months of a previous application."
        ),
        "cost": "",
        "prize_or_funding": "Up to Rs 3 lakhs",
        "tags": "ksum, kerala startup mission, grant, idea grant, startup "
                "funding, seed, kerala, students",
    },
    {
        "title": "KSUM Productisation Grant",
        "category": "Grant",
        "subcategory": "Startup Funding",
        "description": (
            "State-funded grant for converting a validated idea or MVP into a "
            "market-ready product. Applied for through the KSUM grant portal."
        ),
        "organizer": "Kerala Startup Mission (KSUM)",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://startupmission.kerala.gov.in/schemes/early-stage-funding",
        "application_url": "https://grants.startupmission.in",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "Up to Rs 7 lakhs",
        "tags": "ksum, kerala startup mission, grant, productisation, startup "
                "funding, innovation grant, kerala",
    },
    {
        "title": "KSUM Women / Transgender Productisation Grant",
        "category": "Grant",
        "subcategory": "Startup Funding",
        "description": (
            "The productisation grant at a higher ceiling for women-led and "
            "transgender-led startups, funded by the Government of Kerala and "
            "applied for through the KSUM grant portal."
        ),
        "organizer": "Kerala Startup Mission (KSUM)",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://startupmission.kerala.gov.in/schemes/early-stage-funding",
        "application_url": "https://grants.startupmission.in",
        "eligibility": "Women-led and transgender-led startups.",
        "cost": "",
        "prize_or_funding": "Up to Rs 12 lakhs",
        "tags": "ksum, kerala startup mission, grant, women founders, startup "
                "funding, kerala",
    },
    {
        "title": "KSUM Seed Support Scheme",
        "category": "Funding",
        "subcategory": "Startup Funding",
        "description": (
            "Seed funding from the Government of Kerala, given as a soft loan "
            "at 6% simple interest with a 12-month moratorium and 36 monthly "
            "instalments; prepayment carries no penalty. Applications are "
            "submitted online, followed by a call with KSUM and a final pitch "
            "to the Seed Expert Committee."
        ),
        "organizer": "Kerala Startup Mission (KSUM)",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://startupmission.kerala.gov.in/schemes/seed-fund",
        "application_url": "https://startupmission.kerala.gov.in/schemes/seed-fund",
        "eligibility": (
            "Registered in Kerala as an LLP or Private Limited Company; active "
            "KSUM Unique ID; DPIIT registration and Active/Active Compliant "
            "status with MCA; product or technology startup, not a service "
            "startup; no pending government dues or blacklisting."
        ),
        "cost": "",
        "prize_or_funding": "Up to Rs 15 lakhs (soft loan at 6% p.a.)",
        "tags": "ksum, kerala startup mission, seed fund, seed funding, "
                "startup funding, government funding, kerala",
    },
    {
        "title": "Young Innovators Programme (YIP) Kerala",
        "category": "Competition",
        "subcategory": "Innovation Programme",
        "description": (
            "K-DISC's innovation challenge for young people across Kerala, in "
            "which student teams submit ideas for products, services or models "
            "that address real needs. District and state winning teams receive "
            "grants. Edition 9.0 is the one currently launched; the portal "
            "carries the open registration window."
        ),
        "organizer": "Kerala Development and Innovation Strategic Council (K-DISC)",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Hybrid",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://yip.kerala.gov.in/",
        "application_url": "https://yip.kerala.gov.in/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": (
            "Grant for district winning teams Rs 25,000 each; grant for state "
            "winning teams Rs 50,000 each"
        ),
        "tags": "yip, k-disc, kerala, innovation, students, competition, "
                "grant, young innovators",
    },
    {
        "title": "IEDC Startup Summit 2026",
        "category": "Conference",
        "subcategory": "Student Entrepreneurship",
        "description": (
            "Kerala's student startup summit, run through the Innovation and "
            "Entrepreneurship Development Centre network of Kerala Startup "
            "Mission. KSUM's own channels have announced two different dates "
            "for this edition, so none is stored here - confirm on the "
            "official site before travelling."
        ),
        "organizer": "Kerala Startup Mission (KSUM) - IEDC",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Offline",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://iedcstartupsummit.in/",
        "application_url": "https://iedc.startupmission.in/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "iedc, ksum, kerala startup mission, students, "
                "entrepreneurship, summit, kerala",
    },
    {
        "title": "Kerala Innovation Festival",
        "category": "Showcase",
        "subcategory": "Innovation",
        "description": (
            "Kerala Startup Mission's festival bringing startups, creators, "
            "investors, policymakers and students together. KSUM lists it "
            "among its flagship events; no date for the next edition is "
            "published on the events page."
        ),
        "organizer": "Kerala Startup Mission (KSUM)",
        "location": "Kerala",
        "country": "India",
        "region": "Kerala",
        "mode": "Offline",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://startupmission.kerala.gov.in/events",
        "application_url": "https://startupmission.kerala.gov.in/events",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "",
        "tags": "ksum, kerala startup mission, innovation, festival, "
                "showcase, startup, kerala",
    },
]


# ---------------------------------------------------------------------------
# India-wide - open to applicants across India, Kerala included
# ---------------------------------------------------------------------------

INDIA_OPPORTUNITIES = [
    {
        "title": "Startup India Seed Fund Scheme",
        "category": "Funding",
        "subcategory": "Startup Funding",
        "description": (
            "Central government seed funding for startups from proof of "
            "concept through to market entry, disbursed through approved "
            "incubators. KSUM lists it among the early-stage funding routes "
            "open to Kerala startups."
        ),
        "organizer": "Department for Promotion of Industry and Internal Trade (DPIIT)",
        "location": "India",
        "country": "India",
        "region": "",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://seedfund.startupindia.gov.in/",
        "application_url": "https://seedfund.startupindia.gov.in/",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "Up to Rs 20 lakhs (grant) or up to Rs 50 lakhs (debt)",
        "tags": "startup india, seed fund, sisfs, government funding, startup "
                "funding, grant, india",
    },
    {
        "title": "NIDHI Startup Seed Support Scheme",
        "category": "Funding",
        "subcategory": "Startup Funding",
        "description": (
            "Central government seed support for post-incubation startups "
            "moving to commercialisation. Applications from Kerala-incubated "
            "startups are routed through the Kerala Startup Mission portal."
        ),
        "organizer": "Department of Science and Technology (NIDHI)",
        "location": "India",
        "country": "India",
        "region": "",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://startupmission.kerala.gov.in/schemes/early-stage-funding",
        "application_url": "https://startups.startupmission.in/application/nidhi_seed_support",
        "eligibility": "Post-incubator startups moving to commercialisation.",
        "cost": "",
        "prize_or_funding": "Rs 25 lakhs to Rs 1 crore",
        "tags": "nidhi, dst, seed support, startup funding, government "
                "funding, incubator, india",
    },
    {
        "title": "Biotechnology Ignition Grant (BIG) Scheme",
        "category": "Grant",
        "subcategory": "Research / Deep Tech",
        "description": (
            "BIRAC's flagship early-stage grant for translating an innovative "
            "idea into proof of concept. Calls are announced twice a year, on "
            "1 January and 1 July, and each typically stays open for about 45 "
            "days - the site carries the current call."
        ),
        "organizer": "Biotechnology Industry Research Assistance Council (BIRAC)",
        "location": "India",
        "country": "India",
        "region": "",
        "mode": "Online",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://birac.nic.in/big.php",
        "application_url": "https://birac.nic.in/big.php",
        "eligibility": "",
        "cost": "",
        "prize_or_funding": "Rs 50 lakhs grant-in-aid over 18 months",
        "tags": "birac, big, grant, research grant, deep tech, biotech, "
                "startup funding, india",
    },
    {
        "title": "Smart India Hackathon 2026",
        "category": "Hackathon",
        "subcategory": "Student Hackathon",
        "description": (
            "The national student hackathon run by the Ministry of Education's "
            "Innovation Cell and AICTE. Teams enter through their college "
            "SPOC. Stage dates are published on the official portal and are "
            "not stored here - the announcements available were second-hand."
        ),
        "organizer": "Ministry of Education Innovation Cell and AICTE",
        "location": "India",
        "country": "India",
        "region": "",
        "mode": "Hybrid",
        "start_date": "",
        "end_date": "",
        "deadline": "",
        "source_url": "https://www.sih.gov.in/",
        "application_url": "https://www.sih.gov.in/",
        "eligibility": "Students nominated by their institution's SPOC.",
        "cost": "",
        "prize_or_funding": "",
        "tags": "smart india hackathon, sih, hackathon, students, government "
                "hackathon, innovation, india, aicte",
    },
]
