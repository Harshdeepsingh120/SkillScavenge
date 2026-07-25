"""
adzuna_scraper.py  —  SkillScavenge Phase 8 Automation
=====================================================
Standalone scraper extracted from notebooks/01_setup_and_scrape.ipynb.

Fetches job postings from the Adzuna API across three countries
(IN, GB, US) and four tech keywords, then writes raw rows into
the `job_postings` table in MySQL (Aiven, SSL-enabled).

Usage:
    python scripts/adzuna_scraper.py                    # default run
    python scripts/adzuna_scraper.py --max-pages 5      # limit pages per keyword
    python scripts/adzuna_scraper.py --countries gb us  # specific countries
    python scripts/adzuna_scraper.py --dry-run          # fetch but do not insert

Exit codes:
    0 = success (at least 1 row inserted or dry-run OK)
    1 = failure (API error or DB error)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import text

# ── Path bootstrap so config.py is importable from any working dir ────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import config  # noqa: E402  (after sys.path tweak)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("adzuna_scraper")

# ── Defaults (match original notebook configuration) ─────────────────────────
DEFAULT_COUNTRIES = ["in", "gb", "us"]
DEFAULT_KEYWORDS = [
    "data scientist",
    "software engineer",
    "machine learning engineer",
    "backend developer",
]
DEFAULT_MAX_PAGES = 10
RESULTS_PER_PAGE = 50
RATE_LIMIT_DELAY = 1     # seconds between successful page fetches
ERROR_RETRY_DELAY = 5    # seconds after a fetch error


# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_page(
    page: int,
    country: str = "in",
    keyword: str = "data scientist",
    results_per_page: int = RESULTS_PER_PAGE,
) -> list[dict]:
    """
    Fetch one page of Adzuna job results.

    Args:
        page: Page number (1-indexed).
        country: Adzuna country code ('in', 'gb', 'us').
        keyword: Job search keyword.
        results_per_page: Number of results per page (max 50).

    Returns:
        List of raw result dicts from Adzuna.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status.
    """
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "results_per_page": results_per_page,
        "what": keyword,
        "content-type": "application/json",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("results", [])


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def insert_postings(
    results: list[dict],
    engine,
    source: str = "adzuna",
    country: str = "gb",
    dry_run: bool = False,
) -> int:
    """
    Insert a batch of Adzuna job results into `job_postings`.

    Args:
        results: Raw result dicts from Adzuna API.
        engine: SQLAlchemy engine (from config.get_sqlalchemy_engine()).
        source: Data source label (default 'adzuna').
        country: Country code used during this fetch.
        dry_run: If True, build the DataFrame but do NOT insert.

    Returns:
        Number of rows inserted (0 if dry_run).
    """
    rows = []
    for r in results:
        rows.append({
            "source":      source,
            "country":     country,
            "title":       r.get("title"),
            "company":     r.get("company", {}).get("display_name"),
            "location":    r.get("location", {}).get("display_name"),
            "salary_min":  r.get("salary_min"),
            "salary_max":  r.get("salary_max"),
            "description": r.get("description"),
            "posted_date": (r.get("created", "") or "")[:10] or None,
            "redirect_url": r.get("redirect_url"),
            "raw_json":    json.dumps(r),
        })

    df = pd.DataFrame(rows)

    if dry_run:
        log.info("[DRY-RUN] Would insert %d rows (%s)", len(df), country)
        return 0

    df.to_sql("job_postings", con=engine, if_exists="append", index=False)
    log.info("Inserted %d rows (%s)", len(df), country)
    return len(df)


def cleanup_null_countries(engine, dry_run: bool = False) -> int:
    """
    Remove rows with NULL country from job_postings
    (can happen from malformed API responses).

    Returns:
        Number of rows deleted (0 if dry_run).
    """
    if dry_run:
        log.info("[DRY-RUN] Skipping NULL-country cleanup.")
        return 0

    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM job_postings WHERE country IS NULL")
        )
    deleted = result.rowcount
    if deleted:
        log.info("Cleaned up %d rows with NULL country.", deleted)
    return deleted


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCRAPE LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_scrape(
    countries: list[str] = DEFAULT_COUNTRIES,
    keywords: list[str] = DEFAULT_KEYWORDS,
    max_pages: int = DEFAULT_MAX_PAGES,
    dry_run: bool = False,
) -> dict:
    """
    Run the full paginated scrape across all countries and keywords.

    Args:
        countries: List of Adzuna country codes to scrape.
        keywords: List of search keywords.
        max_pages: Maximum pages per (country, keyword) combination.
        dry_run: If True, fetch from API but do NOT write to DB.

    Returns:
        Summary dict with totals per country.
    """
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        log.error("ADZUNA_APP_ID or ADZUNA_APP_KEY not set in environment.")
        sys.exit(1)

    engine = config.get_sqlalchemy_engine()
    log.info("DB engine created. SSL=%s | Host=%s", config.DB_USE_SSL, config.DB_HOST)

    totals: dict[str, int] = {c: 0 for c in countries}
    errors = 0

    for country_code in countries:
        for kw in keywords:
            log.info("--- Scraping: country=%s | keyword='%s' | max_pages=%d",
                     country_code, kw, max_pages)
            for page in range(1, max_pages + 1):
                try:
                    results = fetch_page(
                        page=page,
                        keyword=kw,
                        results_per_page=RESULTS_PER_PAGE,
                        country=country_code,
                    )
                    if not results:
                        log.info("  Page %d empty — moving to next keyword.", page)
                        break

                    inserted = insert_postings(
                        results, engine,
                        source="adzuna",
                        country=country_code,
                        dry_run=dry_run,
                    )
                    totals[country_code] += inserted
                    time.sleep(RATE_LIMIT_DELAY)

                except requests.HTTPError as http_err:
                    log.warning("  HTTP error on %s/%s page %d: %s",
                                country_code, kw, page, http_err)
                    errors += 1
                    time.sleep(ERROR_RETRY_DELAY)

                except Exception as exc:
                    log.warning("  Unexpected error on %s/%s page %d: %s",
                                country_code, kw, page, exc)
                    errors += 1
                    time.sleep(ERROR_RETRY_DELAY)

    # Post-scrape cleanup
    cleanup_null_countries(engine, dry_run=dry_run)

    # Summary
    total_inserted = sum(totals.values())
    summary = {
        "total_inserted": total_inserted,
        "by_country": totals,
        "errors": errors,
        "dry_run": dry_run,
    }

    print("\n" + "=" * 60)
    print("  SkillScavenge — Adzuna Scraper Complete")
    print("=" * 60)
    for c, n in totals.items():
        print(f"  {c.upper():>4} : {n:,} rows {'(dry-run, not inserted)' if dry_run else 'inserted'}")
    print(f"  {'TOTAL':>4} : {total_inserted:,}")
    print(f"  Errors : {errors}")
    print("=" * 60 + "\n")

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkillScavenge Adzuna scraper — fetches job postings into MySQL."
    )
    parser.add_argument(
        "--countries",
        nargs="+",
        choices=["in", "gb", "us"],
        default=DEFAULT_COUNTRIES,
        help="Countries to scrape (default: in gb us)",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="Keywords to search (default: 4 standard tech roles)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Max pages per (country, keyword) combo (default: {DEFAULT_MAX_PAGES})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch from API but do NOT insert into DB.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary = run_scrape(
        countries=args.countries,
        keywords=args.keywords,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    )
    sys.exit(0 if summary["errors"] == 0 else 1)
