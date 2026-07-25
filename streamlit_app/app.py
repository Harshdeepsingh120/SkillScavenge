import os
import json
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkillScavenge — Live Job Market Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090d16 0%, #0f172a 100%);
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* Main Background */
.stApp {
    background-color: #0b0f19;
    color: #f1f5f9;
}

/* Card layout */
.metric-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    text-align: center;
}
.metric-card .label {
    font-size: 11px;
    color: #9ca3af;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.metric-card .value {
    font-size: 32px;
    font-weight: 800;
    color: #0d9488;
    margin-top: 6px;
}

/* Custom Predictions Card */
.prediction-card {
    background: linear-gradient(135deg, #0d9488 0%, #0f766e 50%, #115e59 100%);
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 10px 30px rgba(13, 148, 136, 0.25);
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.prediction-card .val {
    font-size: 54px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
}
.prediction-card .sub-val {
    font-size: 16px;
    color: #ccfbf1;
    margin-top: 5px;
    font-weight: 500;
}

/* Style Selectors & Inputs */
div[data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0d9488 0%, #0d9488 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 12px 30px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 15px rgba(13, 148, 136, 0.4) !important;
    transition: all 0.2s ease-in-out;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(13, 148, 136, 0.6) !important;
}

/* Table container styling */
.stDataFrame {
    border: 1px solid #1f2937;
    border-radius: 10px;
    background: #0f172a;
}
</style>
""", unsafe_allow_html=True)

# ── Plotly Custom Dark Style ──────────────────────────────────────────────────
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#9ca3af", family="Inter"),
    xaxis=dict(gridcolor="#1f2937", zeroline=False, tickfont=dict(color="#9ca3af")),
    yaxis=dict(gridcolor="#1f2937", zeroline=False, tickfont=dict(color="#9ca3af")),
)

# ── DB & Model Connection Caching ─────────────────────────────────────────────
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from mlops.shap_explainer import compute_prediction_shap
from mlops.skill_recommender import recommend_similar_skills

@st.cache_resource
def get_db_engine():
    return config.get_sqlalchemy_engine()

@st.cache_resource
def get_prediction_model():
    model = joblib.load("models/xgboost_model.joblib")
    with open("data_exports/feature_names.json", "r") as f:
        feature_names = json.load(f)
    return model, feature_names

try:
    engine = get_db_engine()
    model, FEATURE_NAMES = get_prediction_model()
except Exception as e:
    st.error(f"Failed to connect to the database or load the ML model: {e}")
    st.stop()

# ── Database Query Helper ─────────────────────────────────────────────────────
def run_query(sql, params=None):
    with engine.connect() as conn:
        res = conn.execute(text(sql), params or {})
        return pd.DataFrame(res.fetchall(), columns=res.keys())

# ── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='color:#0d9488;'>⚡ SkillScavenge</h2>", unsafe_allow_html=True)
    st.markdown("🌐 **MLOps Market Analytics Portal**")
    st.markdown("---")
    menu = st.radio(
        "Choose Dashboard View",
        ["🏠 Market Overview", "📊 Skill Intelligence", "💼 Apply for Jobs", "💰 Salary Predictor", "⚙️ Model Diagnostics"]
    )
    st.markdown("---")
    st.caption("Active Stack:")
    st.caption("• XGBoost Regressor")
    st.caption("• Optuna Hyper-Tuning")
    st.caption("• MySQL Database Store")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: MARKET OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if menu == "🏠 Market Overview":
    st.markdown("# 🏠 Job Market Overview")
    st.markdown("Real-time telemetry and database ingestion statistics.")
    st.markdown("---")

    # Ingested counts
    stats = run_query("""
        SELECT 
            (SELECT COUNT(*) FROM job_postings) AS total_rows,
            (SELECT COUNT(*) FROM job_skills) AS total_mappings,
            (SELECT COUNT(*) FROM skills) AS total_skills,
            (SELECT COUNT(*) FROM model_runs) AS total_runs
    """).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="label">Total Job Postings</div><div class="value">{stats["total_rows"]:,}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="label">Skills Mapped</div><div class="value">{stats["total_mappings"]:,}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="label">Tracked Tech Skills</div><div class="value">{stats["total_skills"]}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="label">ML Model Runs</div><div class="value">{stats["total_runs"]}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌎 Distribution of Postings by Country")
        country_data = run_query("""
            SELECT country, COUNT(*) AS count 
            FROM job_postings 
            GROUP BY country
        """)
        country_data["Country Name"] = country_data["country"].map({
            "us": "United States", "gb": "United Kingdom", "in": "India", "worldwide": "Worldwide"
        }).fillna(country_data["country"])
        
        fig = px.pie(
            country_data, values="count", names="Country Name",
            color_discrete_sequence=["#f59e0b", "#818cf8", "#0d9488", "#10b981", "#6366f1"],
            hole=0.4
        )
        fig.update_layout(**PLOTLY_THEME, height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 💵 Salary Data Transparency Profile")
        transparency = run_query("""
            SELECT country,
                   COUNT(*) AS total,
                   SUM(CASE WHEN salary_min IS NOT NULL THEN 1 ELSE 0 END) AS populated
            FROM job_postings
            GROUP BY country
        """)
        transparency["Country Name"] = transparency["country"].map({
            "us": "United States", "gb": "United Kingdom", "in": "India", "worldwide": "Worldwide"
        }).fillna(transparency["country"])
        # Cast columns to float to ensure compatibility with .round() across all pandas/numpy versions
        transparency["populated"] = transparency["populated"].astype(float)
        transparency["total"] = transparency["total"].astype(float)
        transparency["Coverage %"] = (transparency["populated"] / transparency["total"] * 100).round(1)

        fig2 = px.bar(
            transparency, x="Country Name", y="Coverage %",
            color="Country Name",
            labels={"Coverage %": "Coverage (%)"}
        )
        fig2.update_layout(**PLOTLY_THEME, showlegend=False, height=320, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🏢 Top 10 Hiring Companies")
    top_cos = run_query("""
        SELECT company AS Company, COUNT(*) AS `Open Postings`
        FROM job_postings
        WHERE company IS NOT NULL AND company != ''
        GROUP BY company
        ORDER BY `Open Postings` DESC
        LIMIT 10
    """)
    st.dataframe(top_cos, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: SKILL INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📊 Skill Intelligence":
    st.markdown("# 📊 Skill Demand Intelligence")
    st.markdown("Deep analytical tracking of technology profiles and skill correlation frameworks.")
    st.markdown("---")

    fc1, fc2 = st.columns(2)
    with fc1:
        selected_country = st.selectbox("Filter Country Focus", ["All Countries", "United States", "United Kingdom", "India", "Worldwide"])
    with fc2:
        selected_source = st.selectbox("Filter Data Source", ["All Sources", "Adzuna", "RemoteOK"])

    country_code_map = {"United States": "us", "United Kingdom": "gb", "India": "in", "Worldwide": "worldwide"}
    country_code = country_code_map.get(selected_country)

    where_clauses = []
    params = {}
    if country_code:
        where_clauses.append("jp.country = :country")
        params["country"] = country_code
    if selected_source != "All Sources":
        where_clauses.append("LOWER(jp.source) = :source")
        params["source"] = selected_source.lower()

    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(f"### 🔥 Top 15 Technologies ({selected_country} | {selected_source})")
        top_skills = run_query(f"""
            SELECT s.name AS Skill, COUNT(js.job_id) AS Mentions
            FROM skills s
            JOIN job_skills js ON js.skill_id = s.id
            JOIN job_postings jp ON jp.id = js.job_id
            {where_str}
            GROUP BY s.name
            ORDER BY Mentions DESC
            LIMIT 15
        """, params)

        fig = px.bar(
            top_skills, x="Mentions", y="Skill", orientation="h",
            color="Mentions", color_continuous_scale="Viridis",
            labels={"Mentions": "Count of Mentions", "Skill": ""}
        )
        fig.update_layout(**PLOTLY_THEME, height=450, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🧠 AI Semantic Skill Recommender")
        st.caption("Sentence-Transformer (`all-MiniLM-L6-v2`) vector embedding similarity for tech skill progression:")

        # Pull all distinct skill names
        all_skills_list = run_query("SELECT name FROM skills ORDER BY name")["name"].tolist()
        base_skill = st.selectbox("Select Target Skill", all_skills_list, index=all_skills_list.index("Python") if "Python" in all_skills_list else 0)

        recs = recommend_similar_skills(base_skill, all_skills=all_skills_list, top_n=8)
        rec_df = pd.DataFrame(recs)

        if rec_df.empty:
            st.info("No semantic recommendations found for this selection.")
        else:
            fig3 = px.bar(
                rec_df, x="similarity_pct", y="skill", orientation="h",
                color="similarity_pct", color_continuous_scale="Tealgrn",
                labels={"similarity_pct": "Semantic Match %", "skill": ""},
                text="similarity_pct"
            )
            fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig3.update_layout(**PLOTLY_THEME, height=350, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
            fig3.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.markdown("### 💰 High-Value Tech Skills (US & UK)")
    st.caption("Average salary baseline (in USD) associated with specific skill mentions across jobs containing salary information.")
    
    val_skills = run_query("""
        SELECT s.name AS Skill,
               ROUND(AVG((jp.salary_min + jp.salary_max) / 2 * CASE WHEN jp.country = 'gb' THEN 1.27 ELSE 1.0 END), 2) AS `Average Salary (USD)`,
               COUNT(jp.id) AS `Sample Size`
        FROM skills s
        JOIN job_skills js ON js.skill_id = s.id
        JOIN job_postings jp ON jp.id = js.job_id
        WHERE jp.salary_min IS NOT NULL AND jp.salary_max IS NOT NULL AND jp.country IN ('us', 'gb')
        GROUP BY s.name
        HAVING `Sample Size` >= 10
        ORDER BY `Average Salary (USD)` DESC
        LIMIT 15
    """)
    
    if not val_skills.empty:
        fig4 = px.bar(
            val_skills, x="Skill", y="Average Salary (USD)",
            color="Average Salary (USD)", color_continuous_scale="Cividis",
            labels={"Average Salary (USD)": "Salary (USD)"}
        )
        fig4.update_layout(**PLOTLY_THEME, height=380, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Insufficient salary-populated mappings to generate valuation charts.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: APPLY FOR JOBS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "💼 Apply for Jobs":
    st.markdown("# 💼 Apply for Jobs")
    st.markdown("Browse active job postings across global markets and apply directly with one click.")
    st.markdown("---")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
        sel_country = st.selectbox("Country Filter", ["All Countries", "United States", "United Kingdom", "India", "Worldwide"])
    with col_f2:
        sel_source = st.selectbox("Source Filter", ["All Sources", "Adzuna", "RemoteOK"])
    with col_f3:
        all_skills_df = run_query("SELECT name FROM skills ORDER BY name")
        all_skills = ["All Skills"] + (all_skills_df["name"].tolist() if not all_skills_df.empty else [])
        sel_skill = st.selectbox("Required Skill", all_skills)
    with col_f4:
        search_term = st.text_input("Keyword Search", placeholder="e.g. Python, Engineer...")

    where_conds = ["jp.redirect_url IS NOT NULL AND jp.redirect_url != ''"]
    params = {}

    code_map = {"United States": "us", "United Kingdom": "gb", "India": "in", "Worldwide": "worldwide"}
    if sel_country != "All Countries":
        where_conds.append("jp.country = :country")
        params["country"] = code_map.get(sel_country)

    if sel_source != "All Sources":
        where_conds.append("LOWER(jp.source) = :source")
        params["source"] = sel_source.lower()

    if search_term.strip():
        where_conds.append("(LOWER(jp.title) LIKE :kw OR LOWER(jp.company) LIKE :kw OR LOWER(jp.description) LIKE :kw)")
        params["kw"] = f"%{search_term.strip().lower()}%"

    join_skill = ""
    if sel_skill != "All Skills":
        join_skill = "JOIN job_skills js ON js.job_id = jp.id JOIN skills s ON s.id = js.skill_id"
        where_conds.append("s.name = :skill_name")
        params["skill_name"] = sel_skill

    where_sql = "WHERE " + " AND ".join(where_conds)

    query_jobs = f"""
        SELECT DISTINCT jp.id, jp.source, jp.country, jp.title, jp.company, jp.location, 
                        jp.salary_min, jp.salary_max, jp.description, jp.redirect_url, jp.posted_date
        FROM job_postings jp
        {join_skill}
        {where_sql}
        ORDER BY jp.id DESC
        LIMIT 30
    """

    job_results = run_query(query_jobs, params)

    st.caption("Showing up to 30 active postings matching your filter criteria.")

    if job_results.empty:
        st.info("No job postings found matching your active filter choices. Try broadening your search parameters.")
    else:
        for _, job in job_results.iterrows():
            with st.container():
                src_label = str(job["source"]).upper()
                badge_color = "#0d9488" if src_label == "ADZUNA" else "#818cf8"
                country_display = str(job["country"]).upper()

                salary_display = "Salary Not Listed"
                if pd.notnull(job["salary_min"]) and pd.notnull(job["salary_max"]):
                    s_min = float(job["salary_min"])
                    s_max = float(job["salary_max"])
                    salary_display = f"${s_min:,.0f} - ${s_max:,.0f}"

                desc_snippet = str(job["description"] or "")[:280] + "..." if job["description"] else "No description preview available."

                st.markdown(f"""
                <div style="background:#111827; border:1px solid #1f2937; border-radius:12px; padding:20px; margin-bottom:15px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="background:{badge_color}; color:white; font-size:10px; font-weight:800; padding:4px 10px; border-radius:12px; letter-spacing:0.05em;">{src_label} • {country_display}</span>
                        <span style="color:#0d9488; font-weight:700; font-size:14px;">{salary_display}</span>
                    </div>
                    <h3 style="color:#f1f5f9; margin-top:10px; margin-bottom:4px; font-size:18px;">{job['title']}</h3>
                    <p style="color:#9ca3af; font-size:13px; margin-bottom:10px;"><strong>{job['company']}</strong> | 📍 {job['location'] or country_display}</p>
                    <p style="color:#cbd5e1; font-size:13px; line-height:1.5;">{desc_snippet}</p>
                </div>
                """, unsafe_allow_html=True)
                st.link_button(f"Apply Now for {job['title']} 🔗", job["redirect_url"], use_container_width=True)
                st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: SALARY PREDICTOR & MATCHING JOBS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "💰 Salary Predictor":
    st.markdown("# 💰 Salary Prediction Engine")
    st.markdown("Estimate candidate valuations using our optimized XGBoost model and scan matching live listings.")
    st.markdown("---")

    # Get skill items that are in feature names list
    model_skills = sorted([col for col in FEATURE_NAMES if col not in ["country_gb", "country_us"]])

    col1, col2 = st.columns([3, 1])
    with col1:
        user_skills = st.multiselect(
            "🛠️ Select Technology Competencies",
            options=model_skills,
            default=["Python", "AWS", "SQL"] if "Python" in model_skills else []
        )
    with col2:
        user_country = st.selectbox("🌍 Target Geography", ["United States (USD)", "United Kingdom (GBP)"])

    country_key = "us" if "United States" in user_country else "gb"

    st.markdown("")
    if st.button("🔮 Calculate Salary & Scan Postings"):
        if not user_skills:
            st.warning("Please select at least one technology competence feature.")
        else:
            # Build feature array for prediction
            skills_lower = {s.lower() for s in user_skills}
            fv = []
            for col in FEATURE_NAMES:
                if col == "country_gb":
                    fv.append(1 if country_key == "gb" else 0)
                elif col == "country_us":
                    fv.append(1 if country_key == "us" else 0)
                else:
                    fv.append(1 if col.lower() in skills_lower else 0)

            # Predict
            pred_log = float(model.predict(np.array([fv], dtype=np.float32))[0])
            pred_usd = float(np.expm1(pred_log))

            if country_key == "gb":
                pred_local = pred_usd / 1.27
                local_symbol = "£"
                local_suffix = "GBP"
            else:
                pred_local = pred_usd
                local_symbol = "$"
                local_suffix = "USD"

            # Display card
            st.markdown(f"""
                <div class="prediction-card">
                    <div class="label" style="color:rgba(255,255,255,0.7)">Projected Salary Base Valuation</div>
                    <div class="val">{local_symbol}{pred_local:,.2f} {local_suffix}</div>
                    <div class="sub-val">Equivalent to ${pred_usd:,.2f} USD</div>
                </div>
            """, unsafe_allow_html=True)

            # ── SHAP Feature Impact Breakdown ──────────────────────────────
            st.markdown("---")
            st.markdown("### 🧩 Per-Prediction Feature Contributions (SHAP)")
            st.caption("Breakdown of how your selected skills and target geography impact this specific salary estimate:")

            shap_info = compute_prediction_shap(model, fv, FEATURE_NAMES, top_n=10)
            shap_df = pd.DataFrame(shap_info["feature_contributions"])

            if not shap_df.empty:
                shap_df["Color"] = shap_df["shap_value"].apply(lambda v: "#0d9488" if v >= 0 else "#ef4444")
                fig_shap = px.bar(
                    shap_df,
                    x="shap_value",
                    y="feature",
                    orientation="h",
                    color="Color",
                    color_discrete_map="identity",
                    labels={"shap_value": "SHAP Impact (Log Salary)", "feature": "Feature"},
                    title=f"Base Expected Log Salary: {shap_info['base_value_log']}"
                )
                fig_shap.update_layout(**PLOTLY_THEME, height=350, margin=dict(l=10, r=10, t=30, b=10))
                fig_shap.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig_shap, use_container_width=True)

            # Display gauges
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pred_local,
                number={"prefix": local_symbol, "font": {"size": 38, "color": "#0d9488"}},
                gauge={
                    "axis": {"range": [30000, 220000], "tickcolor": "#9ca3af"},
                    "bar": {"color": "#0d9488"},
                    "bgcolor": "#111827",
                    "bordercolor": "#1f2937",
                    "steps": [
                        {"range": [30000, 90000], "color": "#1f2937"},
                        {"range": [90000, 150000], "color": "#111827"},
                        {"range": [150000, 220000], "color": "#032b26"}
                    ]
                }
            ))
            fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e5e7eb", height=240, margin=dict(t=10, b=10))
            st.plotly_chart(fig_g, use_container_width=True)

            # Fetch matching jobs from the database
            st.markdown("---")
            st.markdown("### 🏢 Matching Job Openings in Database")
            st.caption("Live postings in the database that mention one or more of your selected tech skills:")

            placeholders = ", ".join(f":skill_{i}" for i in range(len(user_skills)))
            query_params = {f"skill_{i}": s for i, s in enumerate(user_skills)}
            query_params["country"] = country_key

            matching_jobs = run_query(f"""
                SELECT jp.title AS Title, jp.company AS Company, jp.location AS Location,
                       CONCAT(jp.salary_min, ' - ', jp.salary_max) AS `Salary Range`,
                       jp.description AS Description
                FROM job_postings jp
                JOIN job_skills js ON js.job_id = jp.id
                JOIN skills s ON s.id = js.skill_id
                WHERE s.name IN ({placeholders}) AND jp.country = :country
                GROUP BY jp.id
                ORDER BY jp.id DESC
                LIMIT 10
            """, query_params)

            if matching_jobs.empty:
                st.info("No active jobs matching these parameters were found in the database.")
            else:
                st.dataframe(matching_jobs, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: MODEL DIAGNOSTICS & HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "⚙️ Model Diagnostics":
    st.markdown("# ⚙️ Model Diagnostics & MLOps Runs")
    st.markdown("Governance records, parameter footprints, and feature relevance indicators.")
    st.markdown("---")

    # DB records
    runs = run_query("""
        SELECT id AS RunID, trained_at AS `Trained At`, model_type AS Type,
               ROUND(mae, 4) AS `Log MAE`, ROUND(rmse, 4) AS `Log RMSE`, notes
        FROM model_runs
        ORDER BY trained_at DESC
    """)

    if runs.empty:
        st.info("No run telemetry logged inside target database tables yet.")
    else:
        # Diagnostic summary
        best_run_idx = runs["Log RMSE"].idxmin()
        best_run = runs.loc[best_run_idx]

        c1, c2, c3 = st.columns(3)
        c1.metric("Governance Database Record Count", len(runs))
        c2.metric("Best Log Validation MAE", best_run["Log MAE"])
        c3.metric("Best Log Validation RMSE", best_run["Log RMSE"])

        st.markdown("---")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### 🪵 Historical Training Runs")
            st.dataframe(
                runs[["RunID", "Trained At", "Type", "Log MAE", "Log RMSE"]],
                use_container_width=True,
                hide_index=True
            )

        with col2:
            st.markdown("### 🏆 Optimal XGBoost Parameters")
            try:
                run_notes = json.loads(best_run["notes"])
                opt_params = run_notes.get("best_params", {})
                opt_r2 = run_notes.get("r2", "N/A")
                opt_raw_mae = run_notes.get("raw_mae_usd", "N/A")

                st.markdown(f"**Optimization R² Score:** `{opt_r2}`")
                st.markdown(f"**Mean Absolute Error (USD):** `${opt_raw_mae:,.2f}`")
                
                params_df = pd.DataFrame(opt_params.items(), columns=["Hyperparameter", "Value"])
                st.dataframe(params_df, use_container_width=True, hide_index=True)
            except Exception:
                st.code(best_run["notes"])

        # Display Feature importance
        st.markdown("---")
        st.markdown("### 📊 Tuned Estimator Feature Relevance")
        st.caption("Relative weight of variables inside the final trained regressor.")

        feat_imps = model.feature_importances_
        importance_df = pd.DataFrame({
            "Feature": FEATURE_NAMES,
            "Importance": feat_imps
        }).sort_values(by="Importance", ascending=False).head(15)

        fig_imp = px.bar(
            importance_df, x="Importance", y="Feature", orientation="h",
            color="Importance", color_continuous_scale="Teal",
            labels={"Importance": "Relevance Score", "Feature": ""}
        )
        fig_imp.update_layout(**PLOTLY_THEME, height=400, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        fig_imp.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_imp, use_container_width=True)
