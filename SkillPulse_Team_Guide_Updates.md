# SkillScavenge Team Guide — v8.5 Update Log

> **Note:** This file tracks all changes made after Phase 7 (v7.0). The original `SkillScavenge_Team_Guide.pdf` covers Phases 1–7. This document should be appended to the Team Guide PDF when regenerating it.

---

## Phase 8: Cloud Migration, Automation & Data Expansion

### 8.1 Database: Local MySQL → Aiven Cloud (Completed — July 25, 2026)

The project database has been migrated from a local MySQL instance to a **managed Aiven MySQL 8.4.8** instance.

#### Connection Details (team members update your `.env`):

```env
DB_USER=avnadmin
DB_PASSWORD=<ask team lead>
DB_HOST=mysql-399a1f84-skillpulse-mysql.d.aivencloud.com
DB_PORT=27694
DB_NAME=defaultdb
DB_USE_SSL=true
```

> **IMPORTANT:** Aiven enforces `SSL mode = REQUIRED`. You **must** set `DB_USE_SSL=true` in your `.env`. Without this, connections will be rejected.

#### Codebase Refactoring:

| File | Change |
|---|---|
| `config.py` | Added `DB_USE_SSL` env var; `get_sqlalchemy_engine()` passes SSL args when enabled |
| `.env` | Updated to Aiven credentials (gitignored — ask team lead for password) |
| `.env.example` | Updated to show Aiven-compatible format |

#### Data in Aiven:

| Table | Rows |
|---|---|
| `job_postings` | 13,683 |
| `job_skills` | 5,914 |
| `skills` | 47 |
| `model_runs` | 1 |
| `drift_reports` | 0 |

---

### 8.2 Standalone Scraper Script — `scripts/adzuna_scraper.py` (Completed — July 25, 2026)

Extracted the full scraping pipeline from `notebooks/01_setup_and_scrape.ipynb` into a callable, CLI-friendly standalone script.

**Usage:**
```bash
python scripts/adzuna_scraper.py                    # Default run
python scripts/adzuna_scraper.py --dry-run          # Test without DB write
python scripts/adzuna_scraper.py --countries gb us  # Specific countries
```

---

### 8.3 Data Expansion: RemoteOK Integration — `scripts/remoteok_scraper.py` (Completed — July 26, 2026)

Added a second active data source (RemoteOK API) alongside Adzuna to expand global tech role coverage.

**Key features:**
- **Location Normalization Engine**:
  - Real Identifiable Countries $\rightarrow$ ISO country codes (`us`, `gb`, `in`, `au`, `br`, `es`, `ca`, `ph`, `mx`, `id`, `fr`, `ec`, `ve`, `pe`).
  - Explicit `Worldwide` / `Anywhere` $\rightarrow$ `'worldwide'`.
  - Dropped blank, generic `Remote`, regional restrictions (`Northeast Region`), and unparseable strings.
- **Cross-Source Deduplication**: MD5 hash fingerprinting (`title + company + country + description[:200]`).
- **Database Schema Addition**: Added `redirect_url` column (`VARCHAR(512)`) to `job_postings` for direct job application links.
- **Data Isolation Rule**: RemoteOK data is stored with `source = 'remoteok'`. It is included in skill intelligence and posting views but **hard-excluded** from XGBoost salary model training.

---

### 8.4 Weekly Automation Pipeline — `scripts/weekly_pipeline.py` (Completed — July 26, 2026)

Updated master pipeline orchestrator and helper script `scripts/clean_and_extract.py`.

**Pipeline Workflow:**
1. **Scrape:** Runs both `adzuna_scraper.py` and `remoteok_scraper.py`
2. **Clean & Extract:** `clean_and_extract.py` (NLP skill extraction)
3. **Drift Check:** `mlops/drift_monitor.py`
4. **Auto-Retrain:** `mlops/retrain.py` (triggered automatically if drift $\ge 30\%$)

---

### 8.5 GitHub Actions CI/CD Workflow — `.github/workflows/weekly_pipeline.yml` (Completed — July 25, 2026)

Configured GitHub Actions for weekly automated execution (Mondays at 06:00 UTC).

---

### 8.6 New Feature: "Apply for Jobs" Dashboard View (Completed — July 26, 2026)

Built a dedicated direct job application view in `streamlit_app/app.py`:
- Multi-filter toolbar: Country (`US`, `GB`, `IN`, `Worldwide`, `All`), Source (`Adzuna`, `RemoteOK`), Required Skill, and Keyword Search.
- Renders job cards with Title, Company, Location, Description snippet, Salary range, and Source badge.
- Direct `st.link_button("Apply Now 🔗", redirect_url)` for 1-click application access.
- Backfilled `redirect_url` across 19,600 existing database records.

---

### 8.7 Project Rebrand & Repository Clean-Up (Completed — July 26, 2026)

- Project rebranded to **SkillScavenge** across all UI headers, FastAPI endpoints, Streamlit page titles, Docker configs, and notebook titles.
- `README.md` updated with continuity note: `SkillScavenge (formerly SkillPulse)`.

---

*This document is maintained by Antigravity AI and updated after each completed step.*
