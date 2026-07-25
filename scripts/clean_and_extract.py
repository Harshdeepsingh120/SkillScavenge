"""
clean_and_extract.py  —  SkillScavenge Phase 8 Automation
=======================================================
Standalone cleaning + NLP skill extraction script extracted from
notebooks/02_cleaning_and_extraction.ipynb.

Steps performed:
  1. Load all raw job_postings from MySQL
  2. Clean HTML/text noise
  3. Deduplicate via MD5 fingerprint hash
  4. Extract 47 tech skills using regex patterns
  5. Populate `skills` master table (idempotent)
  6. Rebuild `job_skills` mappings (DELETE + bulk INSERT)

Usage:
    python scripts/clean_and_extract.py              # full run
    python scripts/clean_and_extract.py --dry-run    # no DB writes

Exit codes:
    0 = success
    1 = failure
"""

import hashlib
import logging
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.mysql import insert as mysql_insert

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import config  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("clean_and_extract")

# ─────────────────────────────────────────────────────────────────────────────
# SKILL PATTERNS (exact mirror of notebook cell 6)
# ─────────────────────────────────────────────────────────────────────────────
SKILLS_PATTERNS = {
    # Languages
    "Python":     re.compile(r"\b(python|py)\b", re.IGNORECASE),
    "SQL":        re.compile(r"\b(sql|mysql|postgresql|sqlite|oracle|mssql|plsql)\b", re.IGNORECASE),
    "JavaScript": re.compile(r"\b(javascript|js|es6)\b", re.IGNORECASE),
    "TypeScript": re.compile(r"\b(typescript|ts)\b", re.IGNORECASE),
    "Java":       re.compile(r"\b(java)\b", re.IGNORECASE),
    "C++":        re.compile(r"\bc\+\+\b", re.IGNORECASE),
    "C#":         re.compile(r"\bc#|c-sharp\b", re.IGNORECASE),
    "Go":         re.compile(r"\b(golang|go\s*lang)\b|\bGo\b", re.ASCII),
    "Ruby":       re.compile(r"\b(ruby|rails)\b", re.IGNORECASE),
    "Rust":       re.compile(r"\b(rust)\b", re.IGNORECASE),
    "HTML/CSS":   re.compile(r"\b(html5?|css3?|sass|scss|less)\b", re.IGNORECASE),
    "PHP":        re.compile(r"\b(php)\b", re.IGNORECASE),
    "Kotlin":     re.compile(r"\b(kotlin)\b", re.IGNORECASE),
    "Swift":      re.compile(r"\b(swift)\b", re.IGNORECASE),
    # Frameworks
    "React":        re.compile(r"\b(react|reactjs|react\.js)\b", re.IGNORECASE),
    "Angular":      re.compile(r"\b(angular|angularjs|angular\.js)\b", re.IGNORECASE),
    "Vue":          re.compile(r"\b(vue|vuejs|vue\.js)\b", re.IGNORECASE),
    "FastAPI":      re.compile(r"\b(fastapi|fast-api)\b", re.IGNORECASE),
    "Flask":        re.compile(r"\b(flask)\b", re.IGNORECASE),
    "Django":       re.compile(r"\b(django)\b", re.IGNORECASE),
    "Node.js":      re.compile(r"\b(node|nodejs|node\.js)\b", re.IGNORECASE),
    "Spring Boot":  re.compile(r"\b(spring\s*boot|spring\s*mvc|spring)\b", re.IGNORECASE),
    "Next.js":      re.compile(r"\b(nextjs|next\.js)\b", re.IGNORECASE),
    # Databases
    "MongoDB":       re.compile(r"\b(mongo|mongodb)\b", re.IGNORECASE),
    "Redis":         re.compile(r"\b(redis)\b", re.IGNORECASE),
    "Cassandra":     re.compile(r"\b(cassandra)\b", re.IGNORECASE),
    "Elasticsearch": re.compile(r"\b(elasticsearch|elastic)\b", re.IGNORECASE),
    "DynamoDB":      re.compile(r"\b(dynamodb)\b", re.IGNORECASE),
    # Tools & Platforms
    "AWS":          re.compile(r"\b(aws|amazon\s*web\s*services|ec2|s3)\b", re.IGNORECASE),
    "Azure":        re.compile(r"\b(azure|microsoft\s*azure)\b", re.IGNORECASE),
    "GCP":          re.compile(r"\b(gcp|google\s*cloud|google\s*cloud\s*platform)\b", re.IGNORECASE),
    "Docker":       re.compile(r"\b(docker|containers)\b", re.IGNORECASE),
    "Kubernetes":   re.compile(r"\b(kubernetes|k8s)\b", re.IGNORECASE),
    "Git":          re.compile(r"\b(git|github|gitlab)\b", re.IGNORECASE),
    "Jenkins":      re.compile(r"\b(jenkins)\b", re.IGNORECASE),
    "Terraform":    re.compile(r"\b(terraform)\b", re.IGNORECASE),
    "CI/CD":        re.compile(r"\b(ci/cd|cicd|continuous\s*integration|continuous\s*deployment)\b", re.IGNORECASE),
    "Airflow":      re.compile(r"\b(airflow|apache\s*airflow)\b", re.IGNORECASE),
    "Snowflake":    re.compile(r"\b(snowflake)\b", re.IGNORECASE),
    "Kafka":        re.compile(r"\b(kafka|apache\s*kafka)\b", re.IGNORECASE),
    # Concepts
    "Agile":           re.compile(r"\b(agile|scrum|kanban)\b", re.IGNORECASE),
    "Machine Learning":re.compile(r"\b(machine\s*learning|ml)\b", re.IGNORECASE),
    "Deep Learning":   re.compile(r"\b(deep\s*learning|dl)\b", re.IGNORECASE),
    "NLP":             re.compile(r"\b(nlp|natural\s*language\s*processing)\b", re.IGNORECASE),
    "DevOps":          re.compile(r"\b(devops)\b", re.IGNORECASE),
    "Microservices":   re.compile(r"\b(microservices|micro-services)\b", re.IGNORECASE),
    "API":             re.compile(r"\b(api|apis|restful|rest\s*api)\b", re.IGNORECASE),
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def clean_html_text(text_val: str) -> str:
    """Strip HTML tags and entities, normalise whitespace."""
    if not text_val or not isinstance(text_val, str):
        return ""
    clean = re.sub(r"<[^>]+>", " ", text_val)
    clean = (clean
             .replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&quot;", '"')
             .replace("&#39;", "'"))
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def generate_dedup_hash(row) -> str:
    """MD5 fingerprint from (title, company, country, desc[:200])."""
    composite = "|||".join([
        str(row["title_clean"]).lower().strip(),
        str(row["company_clean"]).lower().strip(),
        str(row["country"]).lower().strip(),
        str(row["description_clean"]).lower().strip()[:200],
    ])
    return hashlib.md5(composite.encode("utf-8")).hexdigest()


def extract_skills_from_text(title: str, description: str) -> list[str]:
    """Return list of unique matched skill names from title + description."""
    combined = f"{title} {description}"
    matched = []
    for skill, pattern in SKILLS_PATTERNS.items():
        if skill == "Go":
            if (re.search(r"\b(golang|go\s*lang)\b", combined, re.IGNORECASE)
                    or re.search(r"\bGo\b", combined)):
                matched.append(skill)
        else:
            if pattern.search(combined):
                matched.append(skill)
    return list(set(matched))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_clean_and_extract(dry_run: bool = False) -> dict:
    """
    Execute the full clean + skill extraction pipeline.

    Args:
        dry_run: If True, compute everything but skip all DB writes.

    Returns:
        Summary dict with row counts.
    """
    engine = config.get_sqlalchemy_engine()
    log.info("DB engine ready. SSL=%s | Host=%s", config.DB_USE_SSL, config.DB_HOST)

    # ── 1. Load raw postings ────────────────────────────────────────────────
    log.info("Loading raw job_postings from DB...")
    df_raw = pd.read_sql(
        "SELECT id, source, country, title, company, location, "
        "salary_min, salary_max, description FROM job_postings",
        con=engine,
    )
    log.info("Loaded %d raw rows.", len(df_raw))

    # ── 2. Clean text ───────────────────────────────────────────────────────
    log.info("Cleaning HTML and normalising text...")
    df = df_raw.copy()
    df["title_clean"]       = df["title"].apply(clean_html_text)
    df["company_clean"]     = df["company"].apply(clean_html_text)
    df["description_clean"] = df["description"].apply(clean_html_text)

    # ── 3. Deduplicate ──────────────────────────────────────────────────────
    log.info("Deduplicating via MD5 fingerprint...")
    df["dedup_hash"] = df.apply(generate_dedup_hash, axis=1)
    df_unique = df.drop_duplicates(subset=["dedup_hash"], keep="first")
    removed = len(df) - len(df_unique)
    pct = removed / len(df) * 100 if len(df) else 0
    log.info("Deduplicated: %d → %d rows (removed %d, %.1f%%)",
             len(df), len(df_unique), removed, pct)

    # ── 4. Skill extraction ─────────────────────────────────────────────────
    log.info("Extracting skills (47 patterns)...")
    df_unique = df_unique.copy()
    df_unique["matched_skills"] = df_unique.apply(
        lambda r: extract_skills_from_text(r["title_clean"], r["description_clean"]),
        axis=1,
    )
    jobs_with_skills = int((df_unique["matched_skills"].apply(len) > 0).sum())
    log.info("Skills extracted. Jobs with ≥1 skill: %d / %d (%.1f%%)",
             jobs_with_skills, len(df_unique),
             jobs_with_skills / len(df_unique) * 100 if df_unique.shape[0] else 0)

    if dry_run:
        log.info("[DRY-RUN] Skipping all DB writes.")
        return {
            "raw_rows": len(df_raw),
            "unique_rows": len(df_unique),
            "jobs_with_skills": jobs_with_skills,
            "dry_run": True,
        }

    # ── 5. Populate `skills` master table (idempotent) ─────────────────────
    log.info("Upserting skills master table...")
    meta = MetaData()
    skills_table = Table("skills", meta, autoload_with=engine)
    with engine.begin() as conn:
        for skill_name in SKILLS_PATTERNS:
            stmt = mysql_insert(skills_table).values(name=skill_name)
            conn.execute(stmt.on_duplicate_key_update(name=stmt.inserted.name))
    log.info("Skills master table populated (%d skills).", len(SKILLS_PATTERNS))

    # ── 6. Build job_skills mapping ─────────────────────────────────────────
    with engine.connect() as conn:
        df_skills_db = pd.read_sql("SELECT id, name FROM skills", con=conn)
    skill_to_id = dict(zip(df_skills_db["name"], df_skills_db["id"]))

    job_skills_rows = []
    for _, row in df_unique.iterrows():
        job_id = int(row["id"])
        for skill_name in row["matched_skills"]:
            sid = skill_to_id.get(skill_name)
            if sid is not None:
                job_skills_rows.append({"job_id": job_id, "skill_id": sid})

    log.info("Prepared %d job-skill relationships.", len(job_skills_rows))

    job_skills_table = Table("job_skills", meta, autoload_with=engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM job_skills"))
        log.info("Cleared job_skills table.")
        if job_skills_rows:
            conn.execute(job_skills_table.insert(), job_skills_rows)
    log.info("Inserted %d job-skill relationships.", len(job_skills_rows))

    summary = {
        "raw_rows": len(df_raw),
        "unique_rows": len(df_unique),
        "duplicates_removed": removed,
        "jobs_with_skills": jobs_with_skills,
        "job_skill_mappings": len(job_skills_rows),
        "dry_run": False,
    }

    print("\n" + "=" * 60)
    print("  SkillScavenge — Clean & Extract Complete")
    print("=" * 60)
    print(f"  Raw rows loaded    : {summary['raw_rows']:,}")
    print(f"  After dedup        : {summary['unique_rows']:,}")
    print(f"  Duplicates removed : {summary['duplicates_removed']:,} ({pct:.1f}%)")
    print(f"  Jobs with skills   : {summary['jobs_with_skills']:,}")
    print(f"  job_skills rows    : {summary['job_skill_mappings']:,}")
    print("=" * 60 + "\n")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SkillScavenge clean + skill extraction")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without writing to DB.")
    args = parser.parse_args()
    result = run_clean_and_extract(dry_run=args.dry_run)
    sys.exit(0)
