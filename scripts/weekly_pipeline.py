"""
weekly_pipeline.py  —  SkillScavenge Phase 8 Automation
=====================================================
Master orchestrator for the weekly automated pipeline.

Pipeline stages (run in order):
  1. SCRAPE   — Fetch fresh job postings via Adzuna API
  2. CLEAN    — Deduplicate + NLP skill extraction → update DB tables
  3. DRIFT    — Run Evidently drift report vs baseline X_train.csv
  4. RETRAIN  — Auto-retrain XGBoost if drift alert is triggered

Usage:
    python scripts/weekly_pipeline.py                 # full pipeline
    python scripts/weekly_pipeline.py --skip-scrape   # skip scraping (use existing data)
    python scripts/weekly_pipeline.py --dry-run       # no DB writes, no model changes
    python scripts/weekly_pipeline.py --force-retrain # retrain regardless of drift

Exit codes:
    0 = pipeline completed successfully
    1 = one or more stages failed (check logs)
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weekly_pipeline")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE RUNNERS
# Each stage is wrapped so failures are caught, logged, and reported cleanly
# without crashing the whole pipeline prematurely.
# ─────────────────────────────────────────────────────────────────────────────

def stage_scrape(dry_run: bool) -> bool:
    """Stage 1: Fetch fresh postings from Adzuna and RemoteOK into DB."""
    log.info("=" * 60)
    log.info("STAGE 1/4 — SCRAPE: Fetching new job postings (Adzuna + RemoteOK)...")
    log.info("=" * 60)
    adzuna_ok = False
    remoteok_ok = False

    # 1. Adzuna Scraper
    try:
        from scripts.adzuna_scraper import run_scrape as run_adzuna
        summary_adzuna = run_adzuna(dry_run=dry_run)
        log.info("Adzuna scrape complete. Total inserted: %d | Errors: %d",
                 summary_adzuna.get("total_inserted", 0), summary_adzuna.get("errors", 0))
        adzuna_ok = (summary_adzuna.get("errors", 0) == 0)
    except Exception as exc:
        log.error("Adzuna scrape stage FAILED: %s", exc, exc_info=True)

    # 2. RemoteOK Scraper
    try:
        from scripts.remoteok_scraper import run_scrape_remoteok
        summary_rok = run_scrape_remoteok(dry_run=dry_run)
        log.info("RemoteOK scrape complete. Total inserted: %d | Errors: %d",
                 summary_rok.get("inserted", 0), summary_rok.get("errors", 0))
        remoteok_ok = (summary_rok.get("errors", 0) == 0)
    except Exception as exc:
        log.error("RemoteOK scrape stage FAILED: %s", exc, exc_info=True)

    return adzuna_ok or remoteok_ok


def stage_clean(dry_run: bool) -> bool:
    """Stage 2: Deduplicate + extract skills → update DB."""
    log.info("=" * 60)
    log.info("STAGE 2/4 — CLEAN & EXTRACT: Deduplication + NLP...")
    log.info("=" * 60)
    try:
        from scripts.clean_and_extract import run_clean_and_extract
        summary = run_clean_and_extract(dry_run=dry_run)
        log.info("Clean complete. Unique rows: %d | Skill mappings: %s",
                 summary["unique_rows"],
                 summary.get("job_skill_mappings", "N/A (dry-run)"))
        return True
    except Exception as exc:
        log.error("CLEAN stage FAILED: %s", exc, exc_info=True)
        return False


def stage_drift(dry_run: bool) -> tuple[bool, bool]:
    """
    Stage 3: Run Evidently drift report.

    Returns:
        (stage_ok, alert_triggered)
    """
    log.info("=" * 60)
    log.info("STAGE 3/4 — DRIFT: Running Evidently drift check...")
    log.info("=" * 60)
    if dry_run:
        log.info("[DRY-RUN] Skipping drift check.")
        return True, False
    try:
        from mlops.drift_monitor import run_drift_check
        summary = run_drift_check(verbose=True)
        alert = bool(summary.get("alert_triggered", False))
        log.info("Drift check complete. Alert triggered: %s | Drift %%: %.1f",
                 alert, summary.get("feature_drift_pct", 0.0))
        return True, alert
    except Exception as exc:
        log.error("DRIFT stage FAILED: %s", exc, exc_info=True)
        return False, False


def stage_retrain(alert_triggered: bool, force: bool, dry_run: bool) -> bool:
    """Stage 4: Conditionally retrain XGBoost model."""
    log.info("=" * 60)
    log.info("STAGE 4/4 — RETRAIN: Evaluating retraining need...")
    log.info("=" * 60)
    if dry_run:
        log.info("[DRY-RUN] Skipping retrain.")
        return True

    if not alert_triggered and not force:
        log.info("No drift alert and --force-retrain not set. Skipping retrain.")
        print("\nNo drift alert detected — model is stable. Skipping retrain.\n")
        return True

    reason = "--force-retrain flag" if force else "drift alert"
    log.info("Triggering retrain (reason: %s)...", reason)
    try:
        from mlops.retrain import retrain, get_engine
        engine = get_engine()
        retrain(engine)
        log.info("Retrain complete.")
        return True
    except Exception as exc:
        log.error("RETRAIN stage FAILED: %s", exc, exc_info=True)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    skip_scrape: bool = False,
    dry_run: bool = False,
    force_retrain: bool = False,
) -> dict:
    """
    Run the complete weekly pipeline.

    Args:
        skip_scrape: Skip scraping stage (use existing DB data).
        dry_run: Fetch/compute only — no DB writes, no model saves.
        force_retrain: Retrain regardless of drift alert status.

    Returns:
        Summary dict with per-stage results.
    """
    start_ts = datetime.now()
    log.info("*" * 60)
    log.info("  SkillScavenge Weekly Pipeline STARTED")
    log.info("  %s", start_ts.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("  dry_run=%s | skip_scrape=%s | force_retrain=%s",
             dry_run, skip_scrape, force_retrain)
    log.info("*" * 60)

    results = {
        "scrape": None,
        "clean": None,
        "drift": None,
        "retrain": None,
        "drift_alert": False,
        "started_at": start_ts.isoformat(),
        "finished_at": None,
        "success": False,
    }

    # ── Stage 1: Scrape ────────────────────────────────────────────────────
    if skip_scrape:
        log.info("STAGE 1/4 — SCRAPE: Skipped (--skip-scrape).")
        results["scrape"] = "skipped"
    else:
        ok = stage_scrape(dry_run=dry_run)
        results["scrape"] = "ok" if ok else "failed"
        if not ok:
            log.warning("Scrape failed but continuing pipeline with existing data...")

    # ── Stage 2: Clean & Extract ───────────────────────────────────────────
    ok = stage_clean(dry_run=dry_run)
    results["clean"] = "ok" if ok else "failed"
    if not ok:
        log.error("Clean & Extract failed. Aborting pipeline.")
        results["finished_at"] = datetime.now().isoformat()
        _print_summary(results)
        return results

    # ── Stage 3: Drift check ───────────────────────────────────────────────
    drift_ok, alert = stage_drift(dry_run=dry_run)
    results["drift"] = "ok" if drift_ok else "failed"
    results["drift_alert"] = alert

    # ── Stage 4: Retrain ───────────────────────────────────────────────────
    retrain_ok = stage_retrain(
        alert_triggered=alert,
        force=force_retrain,
        dry_run=dry_run,
    )
    results["retrain"] = "ok" if retrain_ok else "failed"

    # ── Final status ───────────────────────────────────────────────────────
    all_ok = all(v in ("ok", "skipped") for v in
                 [results["scrape"], results["clean"], results["drift"], results["retrain"]])
    results["success"] = all_ok
    results["finished_at"] = datetime.now().isoformat()

    elapsed = (datetime.now() - start_ts).total_seconds()
    results["elapsed_seconds"] = round(elapsed, 1)

    _print_summary(results)
    return results


def _print_summary(results: dict):
    """Print a clean human-readable pipeline summary."""
    status_icon = {"ok": "OK", "failed": "FAILED", "skipped": "SKIPPED", None: "?"}
    print("\n" + "=" * 60)
    print("  SkillScavenge Weekly Pipeline — Summary")
    print("=" * 60)
    print(f"  Started  : {results.get('started_at', 'N/A')}")
    print(f"  Finished : {results.get('finished_at', 'N/A')}")
    elapsed = results.get("elapsed_seconds", "?")
    print(f"  Elapsed  : {elapsed}s")
    print()
    print(f"  [1] Scrape        : {status_icon.get(results['scrape'], '?')}")
    print(f"  [2] Clean+Extract : {status_icon.get(results['clean'], '?')}")
    drift_label = status_icon.get(results['drift'], '?')
    if results.get("drift_alert"):
        drift_label += " (ALERT TRIGGERED)"
    print(f"  [3] Drift Check   : {drift_label}")
    print(f"  [4] Retrain       : {status_icon.get(results['retrain'], '?')}")
    print()
    overall = "SUCCESS" if results.get("success") else "FAILED"
    print(f"  Overall : {overall}")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkillScavenge weekly pipeline orchestrator."
    )
    parser.add_argument(
        "--skip-scrape", action="store_true",
        help="Skip the scraping stage and use existing data in the DB."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch/compute only — no DB writes, no model saves."
    )
    parser.add_argument(
        "--force-retrain", action="store_true",
        help="Trigger retraining regardless of drift alert status."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    results = run_pipeline(
        skip_scrape=args.skip_scrape,
        dry_run=args.dry_run,
        force_retrain=args.force_retrain,
    )
    sys.exit(0 if results["success"] else 1)
