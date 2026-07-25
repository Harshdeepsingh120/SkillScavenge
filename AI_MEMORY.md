# SkillScavenge - AI Memory Document & System Design

**Real-Time Job Market & Skills-Demand Tracker • MLOps Pipeline**

| Profile Details | Values |
|---|---|
| **System Architect** | Harshdeep Singh (Computer Science Engineering) |
| **Project Domain** | Data Science, MLOps, NLP, Salary Prediction |
| **Core Tech Stack** | Python, MySQL, SQLAlchemy, XGBoost, FastAPI, Streamlit, Evidently AI, Docker |
| **Database Model** | DB-First Schema (5 Target Tables + Multi-Source Support) |
| **Current Pipeline Phase** | Cloud Migration, Dual-Source Expansion & Rebrand Complete (v8.5) |
| **Last Updated** | July 26, 2026 |

---

## 1. Architectural Blueprint & Design Principles

SkillScavenge is an automated, production-grade MLOps pipeline built to ingest unstructured job postings across target countries (India, UK, US) and worldwide remote markets, parse complex skills requirements using NLP, and train an XGBoost regressor to predict salary distributions.

Unlike typical batch data-science experiments, SkillScavenge implements a **DB-first architecture**, bypassing local intermediate CSV file formats to write raw data directly to a production schema. This ensures relational integrity, transactional safety via SQLAlchemy, and a seamless data migration workflow suitable for containerization.

### Key Multi-Country & Dual-Source Strategy:
* **Adzuna API**: Primary multi-country source for India (`in`), UK (`gb`), and US (`us`). Possesses near-100% salary transparency in UK & US, serving as the sole ground-truth dataset for XGBoost regression model training.
* **RemoteOK API**: Secondary source expanding global and regional tech role coverage (`worldwide` + country roles). RemoteOK data is stored with `source = 'remoteok'` and used exclusively for posting telemetry, skill intelligence, and job applications — **hard-excluded** from salary regressor training.

---

## 2. Phase 1 Accomplishments (Completed Milestones)

We have successfully established the base collection infrastructure, localized data stores, and raw data schemas.

### A. Production Database Implementation
A relational MySQL schema has been constructed and verified locally. Database connectivity is managed securely via environment variables loaded via `python-dotenv`. The connection string actively handles special characters (such as `@` in passwords) using `urllib.parse.quote_plus()` to prevent string parsing errors.

### B. Automated Data Ingestion (`adzuna_scraper.py` / `01_setup_and_scrape.ipynb`)
* Built and executed a localized notebook-based script to query the Adzuna API across 3 target countries (IN, GB, US) and 4 tech-industry target keywords (`data scientist`, `software engineer`, `machine learning engineer`, `backend developer`).
* Built-in rate limiting, failure handling, and state preservation during paginated fetches.
* Collected, cleaned, and populated **6,000 unique records** written directly into the `job_postings` table.

### C. Current Target Tables Verified inside MySQL:

| Table Name | Purpose | Key Columns / Types |
|---|---|---|
| **job_postings** | Stores raw scraped metadata from Adzuna & RemoteOK | `id` (PK), `source` (VARCHAR), `country` (VARCHAR), `title` (VARCHAR), `company` (VARCHAR), `location` (VARCHAR), `salary_min`, `salary_max`, `description` (TEXT), `redirect_url` (VARCHAR) |
| **skills** | Master dictionary of technology skills to extract | `id` (PK), `name` (VARCHAR, UNIQUE) |
| **job_skills** | Many-to-many relationship tracking matrix | `job_id` (FK), `skill_id` (FK), composite primary key |
| **model_runs** | Log history of XGBoost runs, metrics, and dates | `id` (PK), `trained_at`, `model_type`, `mae`, `rmse`, `notes` |
| **drift_reports** | Tracks features & target drift over time (Evidently) | `id` (PK), `run_date`, `report_json` |

---

## 3. Technical Deep-Dive: EDA & Model Isolation Architecture

### A. Target Variable Calibration & Log Transformation
Salary distributions are universally right-skewed. Training an XGBoost regressor directly on raw, skewed continuous labels forces the algorithm to over-index on massive salary outliers, harming normal range prediction accuracy. During EDA, we applied log-transformation:
$$y_{log} = \ln(\text{Salary} + 1)$$

### B. Multi-Source Isolation Guardrail (Adzuna vs. RemoteOK)
To prevent unstandardized or missing salary formats from distorting model metrics:
* **Model Export Filter**: `notebooks/03_eda_and_feature_engineering.ipynb` explicitly filters data export queries:
  ```sql
  SELECT id, country, title, company, salary_min, salary_max 
  FROM job_postings 
  WHERE (source = 'adzuna' OR source IS NULL)
  ```
* **Strict Rule**: RemoteOK expands skill tracking and job board listings, but **never** touches the XGBoost training pipeline.

---

## 4. Phase 2 Accomplishments: Data Cleaning & NLP Skill Extraction (Completed)

* **String Cleansing**: Stripped HTML tags (`<strong>`, `<br>`) and normalized entities (`&amp;`, `&lt;`, `&gt;`).
* **Fingerprint Deduplication**: MD5 hash fingerprinting on title, company, country, and description preview.
* **Skill Extraction Regex Engine**: Compiled 47 developer skills regex patterns with word boundary protection (`C++`, `C#`, `Java`, `Go`).

---

## 5. Phase 3 & 4 Accomplishments: Model Training & Optimisation (Completed)

* **Dataset**: 7,998 samples (GB + US Adzuna postings with salary details), 48 features.
* **Optuna Hyperparameter Tuning**: 30 trials optimizing validation RMSE.
* **Best Parameters**: `n_estimators=191`, `max_depth=5`, `learning_rate=0.0556`, `subsample=0.952`, `colsample_bytree=0.930`.
* **Performance**: Validation MAE 0.3068 (log scale), raw salary MAE ~$31,188 USD. Model saved to `models/xgboost_model.joblib`.

---

## 6. Phase 5 & 6 Accomplishments: FastAPI & Streamlit Portal (Completed)

* **FastAPI Backend (`app/main.py`)**: `GET /health`, `GET /skills/top`, `POST /predict`.
* **Streamlit Analytics Portal (`streamlit_app/app.py`)**: Dark-themed interactive dashboard featuring Market Overview, Skill Intelligence, Apply for Jobs, Salary Predictor, and Model Diagnostics.

---

## 7. Phase 7 Accomplishments: Continuous MLOps & Docker (Completed)

* **Evidently AI Drift Engine (`mlops/drift_monitor.py`)**: Computes Jensen-Shannon distance for skills and K-S test for salary features against `X_train.csv`.
* **Auto-Retrain Engine (`mlops/retrain.py`)**: Evaluates 30% drift threshold and automatically triggers XGBoost retrain.
* **Containerisation**: `Dockerfile.api`, `Dockerfile.streamlit`, `docker-compose.yml`.

---

## 8. Phase 8 Accomplishments: Cloud Migration, Expansion & Rebrand (Completed)

### Part 1: MySQL Cloud Migration to Aiven (COMPLETED ✓ - July 25, 2026)
* Migrated DB to Aiven managed MySQL 8.4.8 (`mysql-399a1f84-skillpulse-mysql.d.aivencloud.com:27694`).
* SSL mode: **REQUIRED** (`DB_USE_SSL=true`).

### Part 2: Standalone Scrapers (COMPLETED ✓ - July 26, 2026)
* `scripts/adzuna_scraper.py`: Paginated Adzuna API scraper with rate limiting and `--dry-run`.
* `scripts/remoteok_scraper.py`: RemoteOK API scraper with location parsing (country codes + `worldwide`), cross-source MD5 deduplication, and `--dry-run`.

### Part 3: Weekly Automation Pipeline (COMPLETED ✓ - July 26, 2026)
* `scripts/weekly_pipeline.py`: Master orchestrator running Scrape (Adzuna + RemoteOK) $\rightarrow$ Clean/Extract $\rightarrow$ Drift Check $\rightarrow$ Auto-Retrain.

### Part 4: GitHub Actions CI/CD (COMPLETED ✓ - July 25, 2026)
* `.github/workflows/weekly_pipeline.yml`: Runs Mondays 06:00 UTC with automated secret injection and drift report artifact uploads.

### Part 5: "Apply for Jobs" View & Direct Links (COMPLETED ✓ - July 26, 2026)
* Added `redirect_url` column (`VARCHAR(512)`) to `job_postings`. Backfilled 19,600+ existing records.
* Built Page 3 `"💼 Apply for Jobs"` view in Streamlit with multi-filters and 1-click `st.link_button` direct application buttons.

### Part 6: Project Rebrand to SkillScavenge (COMPLETED ✓ - July 26, 2026)
* Full codebase, UI titles, API metadata, container configurations, and notebook headers rebranded to **SkillScavenge (formerly SkillPulse)**.

---

## 9. Security & Credential Management Guardrail

> **CRITICAL RULE FOR AI ASSISTANTS & DEVELOPERS:**
> Real credential values (API keys, passwords, secret tokens, connection strings with embedded passwords) **MUST NEVER** be written into any documentation file, script comments, workflow YAMLs, markdown guides, summaries, or commit messages.
> 
> - **Only `.env`** (which is strictly `.gitignore`d) may contain live secret values.
> - **All other files** (including `.env.example`, `AI_MEMORY.md`, `SkillPulse_Team_Guide_Updates.md`, `walkthrough.md`, GitHub Actions workflow configs, etc.) **MUST ONLY** use descriptive placeholders (e.g., `<your Adzuna App ID>`, `<your Aiven DB password>`).
