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
    page_title="SkillScavenge — Job Market Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS / Design System ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #d6e4ec;
}

.stApp {
    background-color: #0a0f12;
}

/* ── Hide sidebar entirely ── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* ── Top padding reduction ── */
.block-container {
    padding-top: 1.2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
}

/* ── Tabs (top nav) ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1a2228 !important;
    gap: 0rem;
    margin-bottom: 2rem;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    color: #4a6070 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    padding: 10px 22px 10px 22px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.2s ease, border-color 0.2s ease !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #5DCAA5 !important;
    border-bottom: 2px solid #5DCAA5 !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #d6e4ec !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: transparent !important;
    display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── Page header ── */
.page-header {
    margin-bottom: 2rem;
}
.page-heading {
    font-family: 'Inter', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: #d6e4ec;
    letter-spacing: -0.01em;
    margin: 0 0 6px 0;
}
.page-subtitle {
    font-size: 13px;
    color: #4a6070;
    font-weight: 400;
    margin: 0;
    line-height: 1.5;
}

/* ── Section label ── */
.section-label {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a6070;
    margin-bottom: 1.2rem;
    margin-top: 2rem;
}

/* ── Bento cards ── */
.bento-card {
    background: #0e1417;
    border: 1px solid #1a2228;
    border-radius: 10px;
    padding: 24px 26px 20px 26px;
    height: 100%;
    box-sizing: border-box;
}
.bento-hero {
    padding: 28px 30px 24px 30px;
    min-height: 170px;
}
.bento-sm {
    padding: 20px 22px 18px 22px;
    min-height: 110px;
}
.bento-teal  { border-top: 3px solid #5DCAA5 !important; }
.bento-pink  { border-top: 3px solid #D4537E !important; }

.card-label {
    font-family: 'Inter', sans-serif;
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #4a6070;
    margin-bottom: 8px;
}
.card-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 38px;
    font-weight: 700;
    color: #d6e4ec;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 4px;
}
.card-value-sm {
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 700;
    color: #d6e4ec;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 4px;
}
.card-sub {
    font-size: 11px;
    color: #4a6070;
    font-weight: 400;
    margin-top: 4px;
}

/* ── Spark bars (inline) ── */
.spark-row {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    margin-top: 14px;
    height: 28px;
}
.spark-bar {
    background: #1d9e75;
    border-radius: 2px 2px 0 0;
    width: 9px;
    opacity: 0.8;
}

/* ── Prediction result card ── */
.predict-result {
    background: #0e1417;
    border: 1px solid #1a2228;
    border-top: 3px solid #D4537E;
    border-radius: 10px;
    padding: 32px 36px;
    text-align: center;
    margin: 1.5rem 0;
}
.predict-label {
    font-family: 'Inter', sans-serif;
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #4a6070;
    margin-bottom: 12px;
}
.predict-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 52px;
    font-weight: 700;
    color: #D4537E;
    letter-spacing: -0.02em;
    line-height: 1;
}
.predict-sub {
    font-size: 13px;
    color: #4a6070;
    margin-top: 8px;
}

/* ── Job card ── */
.job-card {
    background: #0e1417;
    border: 1px solid #1a2228;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 12px;
}
.job-badge {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: 4px;
    display: inline-block;
}
.badge-teal { background: rgba(93,202,165,0.12); color: #5DCAA5; }
.badge-pink  { background: rgba(212,83,126,0.12); color: #D4537E; }
.job-title {
    font-size: 16px;
    font-weight: 600;
    color: #d6e4ec;
    margin: 10px 0 3px 0;
}
.job-meta {
    font-size: 12px;
    color: #4a6070;
    margin-bottom: 8px;
}
.job-desc {
    font-size: 12px;
    color: #8099a8;
    line-height: 1.55;
}
.job-salary {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: #5DCAA5;
}

/* ── Tables / DataFrames ── */
.stDataFrame {
    border: 1px solid #1a2228 !important;
    border-radius: 8px !important;
    background: #0e1417 !important;
}

/* ── Selectbox / Inputs ── */
div[data-baseweb="select"] > div {
    background-color: #0e1417 !important;
    border: 1px solid #1a2228 !important;
    border-radius: 7px !important;
}
.stTextInput > div > div {
    background: #0e1417 !important;
    border: 1px solid #1a2228 !important;
    border-radius: 7px !important;
    color: #d6e4ec !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #0e1417 !important;
    color: #5DCAA5 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.04em !important;
    border: 1px solid #1d9e75 !important;
    padding: 10px 28px !important;
    border-radius: 7px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: rgba(29,158,117,0.1) !important;
    border-color: #5DCAA5 !important;
}
.stLinkButton > a {
    background: transparent !important;
    color: #5DCAA5 !important;
    font-size: 12px !important;
    border: 1px solid #1a2228 !important;
    border-radius: 7px !important;
    padding: 8px 16px !important;
    font-weight: 500 !important;
}

/* ── Multiselect ── */
[data-baseweb="tag"] {
    background: rgba(29,158,117,0.15) !important;
    border: 1px solid #1d9e75 !important;
    border-radius: 4px !important;
}
[data-baseweb="tag"] span { color: #5DCAA5 !important; }

/* ── Divider ── */
hr { border-color: #1a2228 !important; opacity: 1 !important; }

/* ── st.metric override ── */
[data-testid="stMetric"] {
    background: #0e1417;
    border: 1px solid #1a2228;
    border-top: 3px solid #D4537E;
    border-radius: 10px;
    padding: 18px 20px;
}
[data-testid="stMetricLabel"] p {
    font-size: 9.5px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #4a6070 !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #d6e4ec !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0f12; }
::-webkit-scrollbar-thumb { background: #1a2228; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Plotly Dark Theme ─────────────────────────────────────────────────────────
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#4a6070", family="Inter"),
    xaxis=dict(gridcolor="#1a2228", zeroline=False, tickfont=dict(color="#6b7f8a"), linecolor="#1a2228"),
    yaxis=dict(gridcolor="#1a2228", zeroline=False, tickfont=dict(color="#8099a8"), linecolor="#1a2228"),
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

# ── Wordmark ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:1.5rem;">
    <span style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;
                 color:#d6e4ec;letter-spacing:-0.01em;">SkillScavenge</span>
    <span style="font-size:10px;font-weight:600;letter-spacing:0.12em;
                 text-transform:uppercase;color:#4a6070;padding-top:2px;">
        job market intelligence
    </span>
</div>
""", unsafe_allow_html=True)

# ── Top Navigation ────────────────────────────────────────────────────────────
tab_hunt, tab_signals, tab_roles, tab_predict, tab_health = st.tabs([
    "the hunt",
    "skill signals",
    "open roles",
    "pay predictor",
    "model health",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: THE HUNT — Market Overview
# ══════════════════════════════════════════════════════════════════════════════
with tab_hunt:
    st.markdown("""
    <div class="page-header">
        <div class="page-heading">the hunt</div>
        <div class="page-subtitle">Every posting scraped, every skill logged, every dollar traced back to the data that predicts it.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch stats ──
    stats = run_query("""
        SELECT 
            (SELECT COUNT(*) FROM job_postings) AS total_rows,
            (SELECT COUNT(*) FROM job_skills) AS total_mappings,
            (SELECT COUNT(*) FROM skills) AS total_skills,
            (SELECT COUNT(*) FROM model_runs) AS total_runs,
            (SELECT COUNT(DISTINCT country) FROM job_postings) AS total_markets
    """).iloc[0]

    # ── Last retrain date ──
    try:
        last_run = run_query("SELECT MAX(trained_at) AS last_run FROM model_runs").iloc[0]["last_run"]
        last_run_str = str(last_run)[:10] if last_run else "—"
    except Exception:
        last_run_str = "—"

    # ── Bento row 1: hero + medium ──
    col_hero, col_mid = st.columns([3, 2])

    with col_hero:
        spark_html = "".join([
            f'<div class="spark-bar" style="height:{h}px;"></div>'
            for h in [9, 13, 10, 18, 14, 22, 16, 28]
        ])
        st.markdown(f"""
        <div class="bento-card bento-hero bento-teal">
            <div class="card-label">Postings in the Vault</div>
            <div class="card-value">{stats['total_rows']:,}</div>
            <div class="spark-row">{spark_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_mid:
        st.markdown(f"""
        <div class="bento-card bento-hero bento-pink">
            <div class="card-label">Model Runs Logged</div>
            <div class="card-value">{stats['total_runs']}</div>
            <div class="card-sub">last retrain {last_run_str}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Bento row 2: 3 small cards ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="bento-card bento-sm bento-teal">
            <div class="card-label">Skills Mapped</div>
            <div class="card-value-sm">{stats['total_mappings']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="bento-card bento-sm bento-pink">
            <div class="card-label">Tech Vocab Size</div>
            <div class="card-value-sm">{stats['total_skills']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="bento-card bento-sm bento-teal">
            <div class="card-label">Markets Covered</div>
            <div class="card-value-sm">{stats['total_markets']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ── Charts row ──
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown('<div class="section-label">Where the Roles Are</div>', unsafe_allow_html=True)
        country_data = run_query("""
            SELECT country, COUNT(*) AS count 
            FROM job_postings 
            GROUP BY country
            ORDER BY count DESC
        """)
        label_map = {"us": "US", "gb": "GB", "in": "IN", "worldwide": "WW"}
        country_data["code"] = country_data["country"].map(label_map).fillna(country_data["country"].str.upper())
        country_data = country_data.sort_values("count", ascending=True)

        fig_country = px.bar(
            country_data, x="count", y="code", orientation="h",
            text="count",
            color_discrete_sequence=["#1d9e75"],
        )
        fig_country.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=11, color="#5DCAA5"),
            marker_color="#1d9e75",
            marker_line_width=0,
        )
        fig_country.update_layout(
            **PLOTLY_THEME,
            height=240,
            margin=dict(l=0, r=60, t=0, b=0),
            bargap=0.35,
        )
        fig_country.update_xaxes(visible=False)
        fig_country.update_yaxes(tickfont=dict(family="JetBrains Mono", size=12, color="#8099a8"),
                                 gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_country, use_container_width=True)

    with chart_col2:
        st.markdown('<div class="section-label">Salary Spread (USD)</div>', unsafe_allow_html=True)
        salary_data = run_query("""
            SELECT country,
                   (salary_min + salary_max) / 2 * CASE WHEN country = 'gb' THEN 1.27 ELSE 1.0 END AS midpoint
            FROM job_postings
            WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
              AND country IN ('us', 'gb')
        """)
        label_map2 = {"us": "US", "gb": "GB"}
        salary_data["code"] = salary_data["country"].map(label_map2)

        fig_box = px.box(
            salary_data, x="code", y="midpoint",
            color="code",
            color_discrete_map={"US": "#D4537E", "GB": "#F4C0D1"},
            labels={"midpoint": "USD", "code": ""},
            points=False,
        )
        fig_box.update_traces(line_color="#D4537E", marker_color="#D4537E", fillcolor="rgba(212,83,126,0.12)")
        fig_box.update_layout(
            **PLOTLY_THEME,
            height=240,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
        fig_box.update_yaxes(tickprefix="$", tickformat=",.0f", gridcolor="#1a2228",
                             tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"))
        fig_box.update_xaxes(tickfont=dict(family="JetBrains Mono", size=12, color="#8099a8"),
                             gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown('<div class="section-label">Top Hiring Companies</div>', unsafe_allow_html=True)
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
# TAB 2: SKILL SIGNALS — Skill Intelligence
# ══════════════════════════════════════════════════════════════════════════════
with tab_signals:
    st.markdown("""
    <div class="page-header">
        <div class="page-heading">skill signals</div>
        <div class="page-subtitle">What the market is paying attention to — and what it's quietly starting to ignore.</div>
    </div>
    """, unsafe_allow_html=True)

    fc1, fc2 = st.columns(2)
    with fc1:
        selected_country = st.selectbox("Country", ["All Countries", "United States", "United Kingdom", "India", "Worldwide"])
    with fc2:
        selected_source = st.selectbox("Source", ["All Sources", "Adzuna", "RemoteOK"])

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
        st.markdown('<div class="section-label">Demand by Technology</div>', unsafe_allow_html=True)
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
            color_discrete_sequence=["#1d9e75"],
            labels={"Mentions": "Mentions", "Skill": ""},
        )
        fig.update_traces(marker_color="#1d9e75", marker_line_width=0)
        fig.update_layout(**PLOTLY_THEME, height=450, margin=dict(l=0, r=10, t=0, b=0))
        fig.update_yaxes(categoryorder="total ascending",
                         tickfont=dict(family="Inter", size=12, color="#8099a8"))
        fig.update_xaxes(tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-label">Learn What\'s Adjacent</div>', unsafe_allow_html=True)
        st.caption("Sentence-transformer similarity — `all-MiniLM-L6-v2`")

        all_skills_list = run_query("SELECT name FROM skills ORDER BY name")["name"].tolist()
        base_skill = st.selectbox(
            "Target skill",
            all_skills_list,
            index=all_skills_list.index("Python") if "Python" in all_skills_list else 0
        )

        recs = recommend_similar_skills(base_skill, all_skills=all_skills_list, top_n=8)
        rec_df = pd.DataFrame(recs)

        if rec_df.empty:
            st.info("No semantic recommendations found for this selection.")
        else:
            fig3 = px.bar(
                rec_df, x="similarity_pct", y="skill", orientation="h",
                color_discrete_sequence=["#5DCAA5"],
                labels={"similarity_pct": "Match %", "skill": ""},
                text="similarity_pct",
            )
            fig3.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=10, color="#5DCAA5"),
                marker_color="#1d9e75",
                marker_line_width=0,
            )
            fig3.update_layout(**PLOTLY_THEME, height=350, margin=dict(l=0, r=50, t=0, b=0))
            fig3.update_yaxes(categoryorder="total ascending",
                              tickfont=dict(family="Inter", size=11, color="#8099a8"))
            fig3.update_xaxes(visible=False)
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">Skills That Move Salary</div>', unsafe_allow_html=True)
    st.caption("Average salary (USD) per skill — US and UK postings with salary data, min 10 samples.")

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
            color_discrete_sequence=["#D4537E"],
            labels={"Average Salary (USD)": "Avg Salary (USD)"},
        )
        fig4.update_traces(marker_color="#D4537E", marker_line_width=0)
        fig4.update_layout(**PLOTLY_THEME, height=360, margin=dict(l=0, r=0, t=0, b=0))
        fig4.update_yaxes(tickprefix="$", tickformat=",.0f",
                          tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"))
        fig4.update_xaxes(tickfont=dict(family="Inter", size=11, color="#8099a8"))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Insufficient salary-populated mappings to generate valuation charts.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: OPEN ROLES — Apply for Jobs
# ══════════════════════════════════════════════════════════════════════════════
with tab_roles:
    st.markdown("""
    <div class="page-header">
        <div class="page-heading">open roles</div>
        <div class="page-subtitle">Live postings, filtered to your stack. Click through and apply directly.</div>
    </div>
    """, unsafe_allow_html=True)

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
        sel_country = st.selectbox("Country", ["All Countries", "United States", "United Kingdom", "India", "Worldwide"])
    with col_f2:
        sel_source = st.selectbox("Source", ["All Sources", "Adzuna", "RemoteOK"])
    with col_f3:
        all_skills_df = run_query("SELECT name FROM skills ORDER BY name")
        all_skills = ["All Skills"] + (all_skills_df["name"].tolist() if not all_skills_df.empty else [])
        sel_skill = st.selectbox("Required Skill", all_skills)
    with col_f4:
        search_term = st.text_input("Keyword", placeholder="Python, Engineer...")

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

    st.caption(f"Showing up to 30 active postings")

    if job_results.empty:
        st.info("No postings match the current filters. Try broadening your criteria.")
    else:
        for _, job in job_results.iterrows():
            src_label = str(job["source"]).upper()
            badge_class = "badge-teal" if src_label == "ADZUNA" else "badge-pink"
            country_display = str(job["country"]).upper()

            salary_display = "salary not listed"
            if pd.notnull(job["salary_min"]) and pd.notnull(job["salary_max"]):
                s_min = float(job["salary_min"])
                s_max = float(job["salary_max"])
                salary_display = f"${s_min:,.0f} — ${s_max:,.0f}"

            desc_snippet = (str(job["description"] or "")[:260] + "…") if job["description"] else "No preview available."

            st.markdown(f"""
            <div class="job-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span class="job-badge {badge_class}">{src_label} &nbsp;·&nbsp; {country_display}</span>
                    <span class="job-salary">{salary_display}</span>
                </div>
                <div class="job-title">{job['title']}</div>
                <div class="job-meta">{job['company']} &nbsp;·&nbsp; {job['location'] or country_display}</div>
                <div class="job-desc">{desc_snippet}</div>
            </div>
            """, unsafe_allow_html=True)
            st.link_button(f"Apply — {job['title']}", job["redirect_url"], use_container_width=False)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: PAY PREDICTOR — Salary Predictor
# ══════════════════════════════════════════════════════════════════════════════
with tab_predict:
    st.markdown("""
    <div class="page-header">
        <div class="page-heading">pay predictor</div>
        <div class="page-subtitle">Build your stack. Get a number. Understand exactly which skills are moving the needle.</div>
    </div>
    """, unsafe_allow_html=True)

    model_skills = sorted([col for col in FEATURE_NAMES if col not in ["country_gb", "country_us"]])

    col1, col2 = st.columns([3, 1])
    with col1:
        user_skills = st.multiselect(
            "Select skills",
            options=model_skills,
            default=["Python", "AWS", "SQL"] if "Python" in model_skills else []
        )
    with col2:
        user_country = st.selectbox("Geography", ["United States (USD)", "United Kingdom (GBP)"])

    country_key = "us" if "United States" in user_country else "gb"

    st.markdown("")
    if st.button("Calculate salary estimate"):
        if not user_skills:
            st.warning("Select at least one skill to generate an estimate.")
        else:
            # Build feature array — identical logic, no changes
            skills_lower = {s.lower() for s in user_skills}
            fv = []
            for col in FEATURE_NAMES:
                if col == "country_gb":
                    fv.append(1 if country_key == "gb" else 0)
                elif col == "country_us":
                    fv.append(1 if country_key == "us" else 0)
                else:
                    fv.append(1 if col.lower() in skills_lower else 0)

            # Predict — identical, read-only
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

            # Result card
            st.markdown(f"""
            <div class="predict-result">
                <div class="predict-label">Projected Base</div>
                <div class="predict-value">{local_symbol}{pred_local:,.0f}</div>
                <div class="predict-sub">{local_suffix} &nbsp;·&nbsp; equivalent to ${pred_usd:,.0f} USD</div>
            </div>
            """, unsafe_allow_html=True)

            # ── SHAP breakdown ──
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<div class="section-label">What\'s Driving It</div>', unsafe_allow_html=True)
            st.caption("Per-feature SHAP contributions for this prediction — positive values push salary up, negative push down.")

            shap_info = compute_prediction_shap(model, fv, FEATURE_NAMES, top_n=10)
            shap_df = pd.DataFrame(shap_info["feature_contributions"])

            if not shap_df.empty:
                shap_df["Color"] = shap_df["shap_value"].apply(lambda v: "#5DCAA5" if v >= 0 else "#D4537E")
                fig_shap = px.bar(
                    shap_df,
                    x="shap_value",
                    y="feature",
                    orientation="h",
                    color="Color",
                    color_discrete_map="identity",
                    labels={"shap_value": "SHAP impact (log salary)", "feature": ""},
                    title=f"Base log salary: {shap_info['base_value_log']}",
                )
                fig_shap.update_traces(marker_line_width=0)
                fig_shap.update_layout(
                    **PLOTLY_THEME,
                    height=340,
                    margin=dict(l=0, r=10, t=30, b=0),
                    title_font=dict(size=11, color="#4a6070"),
                )
                fig_shap.update_yaxes(categoryorder="total ascending",
                                      tickfont=dict(family="Inter", size=11, color="#8099a8"))
                fig_shap.update_xaxes(tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"))
                st.plotly_chart(fig_shap, use_container_width=True)

            # Gauge
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pred_local,
                number={"prefix": local_symbol, "font": {"size": 36, "color": "#D4537E", "family": "JetBrains Mono"}},
                gauge={
                    "axis": {"range": [30000, 220000], "tickcolor": "#4a6070",
                             "tickfont": {"family": "JetBrains Mono", "size": 9, "color": "#4a6070"}},
                    "bar": {"color": "#D4537E"},
                    "bgcolor": "#0e1417",
                    "bordercolor": "#1a2228",
                    "steps": [
                        {"range": [30000, 90000],  "color": "#0e1417"},
                        {"range": [90000, 150000], "color": "#0e1417"},
                        {"range": [150000, 220000],"color": "#0e1417"},
                    ]
                }
            ))
            fig_g.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#6b7f8a",
                height=220,
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_g, use_container_width=True)

            # Matching jobs
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<div class="section-label">Positions in Range</div>', unsafe_allow_html=True)
            st.caption("Live database postings mentioning one or more of your selected skills.")

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
                st.info("No matching postings found for this skill set and geography.")
            else:
                st.dataframe(matching_jobs, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: MODEL HEALTH — Model Diagnostics
# ══════════════════════════════════════════════════════════════════════════════
with tab_health:
    st.markdown("""
    <div class="page-header">
        <div class="page-heading">model health</div>
        <div class="page-subtitle">Training runs, hyperparameter records, and feature weight distribution — all in one place.</div>
    </div>
    """, unsafe_allow_html=True)

    # DB records — identical query
    runs = run_query("""
        SELECT id AS RunID, trained_at AS `Trained At`, model_type AS Type,
               ROUND(mae, 4) AS `Log MAE`, ROUND(rmse, 4) AS `Log RMSE`, notes
        FROM model_runs
        ORDER BY trained_at DESC
    """)

    if runs.empty:
        st.info("No training runs logged yet.")
    else:
        best_run_idx = runs["Log RMSE"].idxmin()
        best_run = runs.loc[best_run_idx]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Runs", len(runs))
        c2.metric("Best Log MAE", best_run["Log MAE"])
        c3.metric("Best Log RMSE", best_run["Log RMSE"])

        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown('<div class="section-label">Run History</div>', unsafe_allow_html=True)
            st.dataframe(
                runs[["RunID", "Trained At", "Type", "Log MAE", "Log RMSE"]],
                use_container_width=True,
                hide_index=True,
            )

        with col2:
            st.markdown('<div class="section-label">Optimal Parameters</div>', unsafe_allow_html=True)
            try:
                run_notes = json.loads(best_run["notes"])
                opt_params = run_notes.get("best_params", {})
                opt_r2 = run_notes.get("r2", "N/A")
                opt_raw_mae = run_notes.get("raw_mae_usd", "N/A")

                st.markdown(f"**R² Score:** `{opt_r2}`")
                st.markdown(f"**MAE (USD):** `${opt_raw_mae:,.2f}`")

                params_df = pd.DataFrame(opt_params.items(), columns=["Hyperparameter", "Value"])
                st.dataframe(params_df, use_container_width=True, hide_index=True)
            except Exception:
                st.code(best_run["notes"])

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Feature Weight Distribution</div>', unsafe_allow_html=True)
        st.caption("Relative importance of each variable in the final trained regressor.")

        feat_imps = model.feature_importances_
        importance_df = pd.DataFrame({
            "Feature": FEATURE_NAMES,
            "Importance": feat_imps
        }).sort_values(by="Importance", ascending=False).head(15)

        fig_imp = px.bar(
            importance_df, x="Importance", y="Feature", orientation="h",
            color_discrete_sequence=["#D4537E"],
            labels={"Importance": "Weight", "Feature": ""},
        )
        fig_imp.update_traces(marker_color="#D4537E", marker_line_width=0)
        fig_imp.update_layout(**PLOTLY_THEME, height=400, margin=dict(l=0, r=10, t=0, b=0))
        fig_imp.update_yaxes(categoryorder="total ascending",
                             tickfont=dict(family="Inter", size=11, color="#8099a8"))
        fig_imp.update_xaxes(tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"))
        st.plotly_chart(fig_imp, use_container_width=True)
