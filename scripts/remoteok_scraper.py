"""
remoteok_scraper.py  —  SkillScavenge Data Pipeline
====================================================
Scraper for fetching job postings from RemoteOK API (https://remoteok.com/api).

Revised Location Filtering & Mapping Rule:
  1. Real Identifiable Countries -> Map to country code ('us', 'gb', 'in', 'ca', 'au', 'br', 'ph', 'es', 'mx', 'de', 'fr', 'pe', etc.) [KEEP]
  2. Genuine Worldwide/Anywhere  -> Map to 'worldwide' [KEEP]
  3. Blank, Unparseable, or Regional-only (Europe, APAC, LATAM, etc.) -> DROP (Do not store)

Usage:
    python scripts/remoteok_scraper.py --dry-run
    python scripts/remoteok_scraper.py

Exit codes:
    0 = success
    1 = failure
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import text

# ── Path bootstrap so config.py is importable ─────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import config  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

log = logging.getLogger("remoteok_scraper")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
log.addHandler(_sh)

_fh = logging.FileHandler(LOG_DIR / "remoteok_scraper.log", encoding="utf-8")
_fh.setFormatter(_fmt)
log.addHandler(_fh)

REMOTEOK_API_URL = "https://remoteok.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# ─────────────────────────────────────────────────────────────────────────────
# LOCATION PARSING & NORMALIZATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

GENUINE_WORLDWIDE_KEYWORDS = {"worldwide", "anywhere", "global", "everywhere"}

REGIONAL_DROPS = {
    "europe", "apac", "latam", "emea", "americas", "asia", "africa", 
    "middle east", "caribbean", "balkans", "nordics", "eu", "us/canada", 
    "us & canada", "latin america", "southeast asia", "northeast region"
}

# Ordered list of (pattern, iso_code)
EXACT_LOCATION_PATTERNS = [
    # Worldwide
    (r"\b(worldwide|anywhere|global|everywhere)\b", "worldwide"),

    # Australia & New Zealand
    (r"\b(australia|sydney|melbourne|brisbane|perth|adelaide|albury|wagga wagga|wynn vale|berwick)\b", "au"),
    (r"\b(new zealand|auckland|wellington)\b", "nz"),

    # United States
    (r"\b(united states|usa|us|u\.s\.a|u\.s|remote - usa|remote usa)\b", "us"),
    (r"\b(new york|california|texas|florida|washington|illinois|nevada|connecticut|pennsylvania|ohio|georgia|michigan|north carolina|virginia|massachusetts|indiana|tennessee|missouri|maryland|wisconsin|minnesota|colorado|alabama|south carolina|louisiana|kentucky|oregon|oklahoma|puerto rico|utah|iowa|kansas|arkansas|mississippi|nebraska|hawaii|idaho|west virginia|rhode island|montana|delaware|south dakota|north dakota|alaska|vermont|wyoming)\b", "us"),
    (r"\b(austin|houston|chicago|pasadena|las vegas|sacramento|palm beach|pittsburgh|glendale|cloquet|apopka|greater houston)\b", "us"),

    # United Kingdom
    (r"\b(united kingdom|uk|great britain|england|scotland|wales|london|manchester|birmingham|leeds|glasgow|edinburgh|bristol|cambridge|oxford|chester|frome|fort william|high beech|walling)\b", "gb"),

    # India
    (r"\b(india|bangalore|bengaluru|hyderabad|mumbai|delhi|pune|chennai|kolkata|ahmedabad|surat|jaipur|lucknow|kanpur|nagpur|indore|thane|bhopal|visakhapatnam|patna|vadodara|ghaziabad|ludhiana|agra|nashik|faridabad|meerut|rajkot|kalyan|varanasi|srinagar|aurangabad|dhanbad|amritsar|navi mumbai|allahabad|howrah|gwalior|jabalpur|coimbatore|vijayawada|jodhpur|madurai|raipur|kota|chandigarh|guwahati|solapur|hubli|bareilly|moradabad|mysore|gurgaon|noida|guindy|dharmavaram|anupgarh|goilkera|kanke|dehradun)\b", "in"),

    # Brazil
    (r"\b(brasil|brazil|sao paulo|rio de janeiro)\b", "br"),

    # Philippines
    (r"\b(philippines|manila|cebu)\b", "ph"),

    # Canada
    (r"\b(canada|toronto|vancouver|montreal|calgary|edmonton|ottawa|ontario|quebec|lethbridge)\b", "ca"),

    # Spain
    (r"\b(espana|spain|madrid|barcelona|valencia|sevilla|granada|andalucia)\b", "es"),

    # Mexico
    (r"\b(mexico|ciudad de mexico|mexico city|guadalajara|monterrey|ciudad valles)\b", "mx"),

    # Peru
    (r"\b(peru|lima|san isidro)\b", "pe"),

    # Germany
    (r"\b(germany|deutschland|berlin|munich|hamburg|frankfurt|cologne)\b", "de"),

    # France
    (r"\b(france|paris|lyon|marseille|gironde)\b", "fr"),

    # Netherlands
    (r"\b(netherlands|amsterdam|rotterdam)\b", "nl"),

    # Italy
    (r"\b(italy|italia|rome|milan)\b", "it"),

    # Portugal
    (r"\b(portugal|lisbon|porto)\b", "pt"),

    # Poland
    (r"\b(poland|polska|warsaw|krakow)\b", "pl"),

    # Indonesia
    (r"\b(indonesia|jakarta|surabaya|bali)\b", "id"),

    # Ecuador
    (r"\b(ecuador|quito|guayaquil)\b", "ec"),

    # Venezuela
    (r"\b(venezuela|caracas)\b", "ve"),

    # Colombia
    (r"\b(colombia|bogota|medellin)\b", "co"),

    # Argentina
    (r"\b(argentina|buenos aires)\b", "ar"),

    # Nigeria
    (r"\b(nigeria|lagos)\b", "ng"),

    # Kenya
    (r"\b(kenya|nairobi)\b", "ke"),

    # Ukraine
    (r"\b(ukraine|kyiv|kiev)\b", "ua"),

    # Singapore
    (r"\b(singapore)\b", "sg"),

    # Japan
    (r"\b(japan|tokyo)\b", "jp"),
]


def clean_location_string(text_str: str) -> str:
    """Normalize unicode characters and clean non-breaking whitespace."""
    if not text_str:
        return ""
    cleaned_bytes = text_str.encode("utf-8", "ignore").decode("utf-8", "ignore")
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", cleaned_bytes)
        if unicodedata.category(c) != "Mn"
    )
    cleaned = re.sub(r"[\s\xa0]+", " ", normalized).strip()
    return cleaned


def parse_and_classify_location(raw_loc: str) -> tuple[str, str, str]:
    """
    Parse raw location under the revised KEEP vs DROP rules.
    Returns: (action ['KEEP'/'DROP'], code, reason)
    """
    if not raw_loc or not isinstance(raw_loc, str) or not raw_loc.strip():
        return "DROP", None, "Blank / Empty location"

    clean_loc = clean_location_string(raw_loc)
    loc_lower = clean_loc.lower()

    if "espa" in loc_lower:
        return "KEEP", "es", "Matched country pattern -> ES"

    if any(re.search(r"\b" + re.escape(r) + r"\b", loc_lower) for r in REGIONAL_DROPS):
        return "DROP", None, f"Regional restriction/scope ('{clean_loc}')"

    for pattern, code in EXACT_LOCATION_PATTERNS:
        if re.search(pattern, loc_lower):
            if code == "worldwide":
                return "KEEP", "worldwide", "Genuine Worldwide / Anywhere"
            else:
                return "KEEP", code, f"Matched country/city pattern -> {code.upper()}"

    return "DROP", None, f"Unparseable / Non-country location ('{clean_loc}')"


# ─────────────────────────────────────────────────────────────────────────────
# API & DB INSERTION
# ─────────────────────────────────────────────────────────────────────────────

def fetch_remoteok_postings() -> list[dict]:
    """Fetch raw job objects from RemoteOK API."""
    log.info("Fetching job postings from RemoteOK API (%s)...", REMOTEOK_API_URL)
    try:
        resp = requests.get(REMOTEOK_API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if isinstance(data, list) and len(data) > 0:
            postings = [item for item in data if isinstance(item, dict) and "id" in item]
            log.info("Successfully fetched %d job postings from RemoteOK.", len(postings))
            return postings
        else:
            log.warning("Unexpected response format from RemoteOK API.")
            return []
    except Exception as exc:
        log.error("Failed to fetch RemoteOK postings: %s", exc)
        return []


def insert_remoteok_postings(postings: list[dict], engine, dry_run: bool = False) -> int:
    """Map RemoteOK postings to job_postings schema with deduplication and insert into MySQL."""
    rows = []
    
    # Load existing fingerprints for cross-source deduplication
    with engine.connect() as conn:
        existing_df = pd.read_sql("SELECT title, company, country, description FROM job_postings", con=conn)
        
    existing_hashes = set()
    for _, row in existing_df.iterrows():
        comp = "|||".join([
            str(row["title"] or "").lower().strip(),
            str(row["company"] or "").lower().strip(),
            str(row["country"] or "").lower().strip(),
            str(row["description"] or "").lower().strip()[:200],
        ])
        existing_hashes.add(hashlib.md5(comp.encode("utf-8")).hexdigest())

    inserted_hashes = set()

    # ── Funnel counters ──
    n_location_dropped = 0
    n_dedup_dropped = 0

    for p in postings:
        raw_loc = str(p.get("location", "")).strip()
        action, code, reason = parse_and_classify_location(raw_loc)
        
        if action != "KEEP":
            n_location_dropped += 1
            continue

        title = str(p.get("position") or p.get("title") or "").strip()
        company = str(p.get("company") or "").strip()
        description = str(p.get("description") or "").strip()

        # Compute dedup fingerprint
        comp = "|||".join([
            title.lower(),
            company.lower(),
            str(code).lower(),
            description.lower()[:200],
        ])
        fingerprint = hashlib.md5(comp.encode("utf-8")).hexdigest()

        if fingerprint in existing_hashes or fingerprint in inserted_hashes:
            n_dedup_dropped += 1
            continue
        inserted_hashes.add(fingerprint)

        # Parse salary
        sal_min = p.get("salary_min")
        sal_max = p.get("salary_max")
        try:
            sal_min = float(sal_min) if sal_min is not None else None
        except Exception:
            sal_min = None
        try:
            sal_max = float(sal_max) if sal_max is not None else None
        except Exception:
            sal_max = None

        # Parse date
        epoch = p.get("epoch")
        if epoch:
            posted_date = time.strftime("%Y-%m-%d", time.gmtime(epoch))
        else:
            posted_date = str(p.get("date", ""))[:10] or None

        # Direct link
        url = str(p.get("url") or p.get("apply_url") or "").strip()
        if url and not url.startswith("http"):
            url = f"https://remoteok.com{url}"

        rows.append({
            "source":       "remoteok",
            "country":      code,
            "title":        title,
            "company":      company,
            "location":     raw_loc,
            "salary_min":   sal_min,
            "salary_max":   sal_max,
            "description":  description,
            "posted_date":  posted_date,
            "redirect_url": url,
            "raw_json":     json.dumps(p),
        })

    # ── Funnel summary (always logged to file) ──
    log.info("─── RemoteOK Scraper Funnel Summary ───")
    log.info("  Raw postings received:       %d", len(postings))
    log.info("  (-) Location filter drops:   %d", n_location_dropped)
    log.info("  (=) Location-kept:           %d", len(postings) - n_location_dropped)
    log.info("  (-) Cross-source dedup:      %d", n_dedup_dropped)
    log.info("  (=) Net insertable rows:     %d", len(rows))
    log.info("──────────────────────────────────────")

    if not rows:
        log.info("No new unique RemoteOK rows to insert.")
        return 0

    df = pd.DataFrame(rows)
    if dry_run:
        log.info("[DRY-RUN] Would insert %d unique RemoteOK rows.", len(df))
        return len(df)

    df.to_sql("job_postings", con=engine, if_exists="append", index=False)
    log.info("Inserted %d unique RemoteOK job postings into MySQL.", len(df))
    return len(df)


def run_scrape_remoteok(dry_run: bool = False) -> dict:
    """Run RemoteOK scraping and insertion."""
    postings = fetch_remoteok_postings()
    if not postings:
        return {"total_fetched": 0, "inserted": 0, "errors": 1}

    engine = config.get_sqlalchemy_engine()
    inserted = insert_remoteok_postings(postings, engine, dry_run=dry_run)

    return {"total_fetched": len(postings), "inserted": inserted, "dry_run": dry_run, "errors": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RemoteOK Job Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and analyze without inserting into DB.")
    args = parser.parse_args()

    res = run_scrape_remoteok(dry_run=args.dry_run)
    sys.exit(0 if res.get("errors", 0) == 0 else 1)
