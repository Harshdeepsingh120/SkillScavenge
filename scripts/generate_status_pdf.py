"""Generate SkillScavenge project status PDF (done vs not done)."""

from datetime import date
from pathlib import Path

from fpdf import FPDF


def ascii_safe(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2192": "->",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2022": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")


class StatusPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, ascii_safe("SkillScavenge - Project Status Report"), align="R")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title, r=13, g=148, b=136):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(r, g, b)
        self.cell(0, 10, ascii_safe(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(r, g, b)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 41, 59)
        self.cell(0, 8, ascii_safe(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, ascii_safe(text))
        self.ln(2)

    def bullet(self, text, symbol="+"):
        self.set_font("Helvetica", "", 10)
        if symbol == "+":
            self.set_text_color(22, 163, 74)
        elif symbol == "-":
            self.set_text_color(220, 38, 38)
        else:
            self.set_text_color(217, 119, 6)
        line = ascii_safe(f"[{symbol}] {text}")
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, line)
        self.ln(1)
        if self.get_y() > self.h - 25:
            self.add_page()

    def status_table_row(self, item, status, notes="", col_w=(75, 25, 70)):
        if self.get_y() > self.h - 20:
            self.add_page()
        y0 = self.get_y()
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(col_w[0], 5, ascii_safe(item), border=0)
        h = max(5, self.get_y() - y0)
        self.set_xy(self.l_margin + col_w[0], y0)
        self.set_font("Helvetica", "B", 9)
        if status == "Done":
            self.set_text_color(22, 163, 74)
        elif status == "Not Done":
            self.set_text_color(220, 38, 38)
        else:
            self.set_text_color(217, 119, 6)
        self.cell(col_w[1], h, ascii_safe(status), border=0)
        self.set_xy(self.l_margin + col_w[0] + col_w[1], y0)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        self.multi_cell(col_w[2], 5, ascii_safe(notes), border=0)
        self.set_y(y0 + max(h, self.get_y() - y0))
        self.set_draw_color(230, 230, 230)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)


def build_pdf(output_path: Path) -> None:
    pdf = StatusPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 12, "SkillScavenge", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Project Status Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, "Done vs. Not Done - Compared to Project Overview PDF", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Generated: {date.today().strftime('%B %d, %Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Repository: SkillScavenge (v7.0)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.body_text(
        "This report compares the current SkillScavenge codebase against the original "
        "Project Overview & Build Plan (SkillScavenge_Project_Overview.pdf). "
        "Overall: the core pipeline is built and working, but several items from "
        "the plan - weekly automation, richer features, cloud deployment, and "
        "documentation polish - are not yet complete."
    )

    pdf.section_title("Executive Summary")
    pdf.body_text(
        "COMPLETED (~65%): End-to-end pipeline from Adzuna scraping through skill "
        "extraction, XGBoost training, FastAPI serving, Streamlit dashboard, "
        "Evidently drift monitoring, conditional retraining, and Docker Compose."
    )
    pdf.body_text(
        "NOT COMPLETED (~35%): Weekly re-scraping, RemoteOK integration, spaCy/LLM "
        "benchmark story, time-based splits, linear regression baseline, seniority/"
        "location/recency features, 'skills to learn next' recommender, cloud "
        "deployment, case-study README, and demo video."
    )

    pdf.add_page()
    pdf.section_title("What Is DONE")

    done_items = [
        ("Data ingestion via Adzuna API (India, UK, US)", "notebooks/01_setup_and_scrape.ipynb"),
        ("4 search keywords scraped (data scientist, SWE, MLE, backend dev)", "01_setup_and_scrape.ipynb"),
        ("~6,000 job postings collected (2,000 per country)", "MySQL job_postings table"),
        ("DB-first MySQL architecture (5 tables)", "schema_mysql.sql + notebooks"),
        ("HTML text cleaning and normalization", "02_cleaning_and_extraction.ipynb"),
        ("Fingerprint deduplication (~62% duplicate reduction)", "02_cleaning_and_extraction.ipynb"),
        ("Regex-based skill extraction (~46 skills)", "02_cleaning_and_extraction.ipynb"),
        ("Skill-to-job many-to-many mapping in MySQL", "skills + job_skills tables"),
        ("EDA: salary distributions, currency standardization (USD)", "03_eda_and_feature_engineering.ipynb"),
        ("Log1p target transformation for regression", "03_eda_and_feature_engineering.ipynb"),
        ("India excluded from salary training (documented trade-off)", "03 notebook + README"),
        ("Feature matrix exported (48 features: 46 skills + 2 country flags)", "data_exports/"),
        ("XGBoost model with Optuna hyperparameter tuning (30 trials)", "04_model_training.ipynb"),
        ("5-fold cross-validation during tuning", "04_model_training.ipynb"),
        ("Model saved as joblib", "models/xgboost_model.joblib"),
        ("Model run logged to MySQL", "model_runs table"),
        ("Test MAE ~0.31 (log scale), ~$31k USD average error", "04_model_training.ipynb"),
        ("FastAPI: GET /health", "app/main.py"),
        ("FastAPI: GET /skills/top and /skills/top/{country}", "app/main.py"),
        ("FastAPI: POST /predict (GB + US only)", "app/main.py"),
        ("Streamlit dashboard - 4 views", "streamlit_app/app.py"),
        ("  Market Overview (stats, country pie, salary coverage)", ""),
        ("  Skill Intelligence (top skills, co-occurrence, high-value skills)", ""),
        ("  Salary Predictor (multi-select skills, gauge, matching jobs)", ""),
        ("  Model Diagnostics (run history, params, feature importance)", ""),
        ("Evidently AI drift monitoring", "mlops/drift_monitor.py"),
        ("Auto-retrain on drift >= 30%", "mlops/retrain.py"),
        ("Docker Compose (MySQL + API + Streamlit + drift profile)", "docker-compose.yml"),
        ("Windows control panel (start services, drift, retrain)", "start_services.bat"),
        ("Technical README and AI_MEMORY design doc", "README.md, AI_MEMORY.md"),
        ("EDA plots (salary dist, skills, co-occurrence, feature importance)", "eda_plots/"),
    ]
    for item, loc in done_items:
        text = item if not loc else f"{item}  [{loc}]"
        pdf.bullet(text, "+")

    pdf.add_page()
    pdf.section_title("What Is PARTIALLY Done")

    partial = [
        ("Skill extraction NLP", "Regex only - spaCy mentioned in overview but not implemented"),
        ("Baseline model comparison", "Default XGBoost used as baseline, not Linear Regression"),
        ("Train/test split", "Random 80/20 split - overview requires time-based split"),
        ("Feature engineering", "Skills + country only - no seniority, location, or recency"),
        ("MLOps automation", "Drift + retrain scripts exist but no Airflow/cron scheduler"),
        ("Deployment", "Dockerized locally - not deployed to Render or Hugging Face"),
        ("Streamlit <-> FastAPI integration", "Both exist but Streamlit loads model/DB directly, not via API"),
        ("Documentation", "Strong technical README - not written as case study with surprising findings"),
        ("Database schema file", "schema_mysql.sql missing 'country' column used everywhere in code"),
        ("Data volume", "6,000 postings (one-time) vs 8,000+ weekly in overview"),
    ]
    for item, note in partial:
        pdf.bullet(f"{item}: {note}", "~")

    pdf.add_page()
    pdf.section_title("What Is NOT Done")

    not_done = [
        "RemoteOK API integration (only Adzuna implemented)",
        "Weekly automated re-scraping of job postings",
        "Airflow or cron-based scheduling for retrain pipeline",
        "spaCy NLP for skill extraction",
        "BeautifulSoup for HTML parsing (regex used instead)",
        "LLM-based NER skill extractor",
        "LLM vs regex benchmark with cost/accuracy documentation",
        "Time-based train/test split (train on older, test on newest)",
        "Linear Regression baseline model",
        "Documented LR vs XGBoost comparison (% improvement)",
        "Seniority level feature extraction",
        "Location / fine-grained geo features",
        "Days-since-posted / recency features",
        "'Skills to learn next' personalized recommender in GUI",
        "Streamlit calling FastAPI backend (currently standalone)",
        "Cloud deployment to Render or Hugging Face Spaces",
        "Public live demo URL",
        "README 'Surprising Findings' section",
        "README 'What Didn't Work' section (e.g. LLM-NER dropped)",
        "60-90 second demo video/GIF embedded in README",
        "Resume bullet placeholders filled (LR improvement %, surprising skill insight)",
        "Standalone adzuna_scraper.py script (scraping is notebook-only)",
    ]
    for item in not_done:
        pdf.bullet(item, "-")

    pdf.add_page()
    pdf.section_title("11-Step Pipeline Scorecard")

    steps = [
        ("1. Data collection / EDA", "Partial", "Adzuna only; EDA done; no RemoteOK"),
        ("2. Data processing", "Done", "Clean, dedupe, missing salaries handled"),
        ("3. Feature engineering", "Partial", "Skills only; no seniority/location/recency"),
        ("4. Train/test split", "Not Done", "Random split, not time-based"),
        ("5. Train model", "Partial", "XGBoost only; no Linear Regression baseline"),
        ("6. Evaluation", "Partial", "XGBoost metrics logged; no LR comparison"),
        ("7. Return / select model", "Done", "XGBoost saved with joblib"),
        ("8. Dump model + FastAPI", "Done", "API live with predict endpoint"),
        ("9. Streamlit GUI", "Partial", "Salary yes; 'learn next' recommender no"),
        ("10. Deployment", "Partial", "Docker only; no Render/HF deployment"),
        ("11. MLOps (weekly + drift)", "Partial", "Evidently + retrain yes; weekly automation no"),
    ]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(75, 7, "Step", border=0)
    pdf.cell(25, 7, "Status", border=0)
    pdf.cell(70, 7, "Notes", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    for item, status, notes in steps:
        pdf.status_table_row(item, status, notes)

    pdf.ln(4)
    pdf.section_title("Resume Claims - Can vs Cannot Say Today")

    pdf.sub_title("Safe to claim:")
    for s in [
        "Built end-to-end MLOps pipeline scraping Adzuna across 3 countries",
        "Regex skill extraction with 46 tech skills mapped to job postings",
        "XGBoost salary predictor with Optuna tuning (MAE ~$31k USD)",
        "FastAPI REST API + Streamlit analytics dashboard",
        "Docker Compose deployment with Evidently drift monitoring",
        "Documented engineering trade-off: India excluded from salary training",
    ]:
        pdf.bullet(s, "+")

    pdf.ln(2)
    pdf.sub_title("Do NOT claim yet (not implemented):")
    for s in [
        "8,000+ job postings scraped weekly",
        "spaCy / LLM-based NER with benchmark documentation",
        "Outperformed linear regression baseline by X%",
        "Automated weekly retraining via Airflow",
        "Deployed live Streamlit app at public URL",
        "GUI recommends which skills to learn next",
    ]:
        pdf.bullet(s, "-")

    pdf.add_page()
    pdf.section_title("Recommended Next Steps (Priority Order)")

    next_steps = [
        ("P1 - Critical", "Fix schema_mysql.sql: add missing 'country' column to job_postings"),
        ("P1 - Critical", "Add Linear Regression baseline + document XGBoost improvement %"),
        ("P2 - High", "Switch to time-based train/test split"),
        ("P2 - High", "Add 'skills to learn next' recommender to Streamlit Salary Predictor"),
        ("P2 - High", "Add seniority + recency features to feature engineering"),
        ("P3 - Medium", "Wire Streamlit to FastAPI (or document architectural choice)"),
        ("P3 - Medium", "Add cron/Airflow stub for weekly drift check + retrain"),
        ("P3 - Medium", "Rewrite README as case study with surprising findings"),
        ("P4 - Polish", "Deploy to Render or Hugging Face Spaces"),
        ("P4 - Polish", "Record 60-90s demo video for README"),
        ("P4 - Polish", "Document LLM vs regex experiment (even if regex wins)"),
        ("P4 - Polish", "Remove stray notebooks/3.6 pip log file"),
    ]
    for priority, task in next_steps:
        pdf.bullet(f"[{priority}] {task}", "~")

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0,
        5,
        ascii_safe(
            "Report generated automatically from codebase audit against "
            "SkillScavenge_Project_Overview.pdf. For technical details see README.md and AI_MEMORY.md."
        ),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    out_project = project_root / "SkillScavenge_Status_Report.pdf"
    out_downloads = Path.home() / "Downloads" / "SkillScavenge_Status_Report.pdf"
    build_pdf(out_project)
    build_pdf(out_downloads)
    print(f"PDF saved to: {out_project}")
    print(f"PDF saved to: {out_downloads}")
