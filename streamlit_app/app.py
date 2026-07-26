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
    background-color: #080c0e;
}

/* ── Hide sidebar entirely ── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* ── Container padding ── */
.block-container {
    padding-top: 2.5rem !important;
    padding-left: 2.2rem !important;
    padding-right: 2.2rem !important;
    max-width: 1250px !important;
}

/* ── Brand Header Title ── */
.brand-title-spec {
    font-family: 'Georgia', serif;
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.01em;
    padding-top: 2px;
}

/* ── Top Tabs Styling (Right Aligned in col_nav) ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border: none !important;
    gap: 1.8rem !important;
    justify-content: flex-end !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    color: #6b7f8a !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
    padding: 4px 0px 8px 0px !important;
    border-radius: 0 !important;
    border-bottom: 2.5px solid transparent !important;
    transition: all 0.15s ease !important;
}
.stTabs [data-baseweb="tab"]:focus,
.stTabs [data-baseweb="tab"]:active,
.stTabs [data-baseweb="tab"]:focus-visible {
    outline: none !important;
    box-shadow: none !important;
    border-color: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #d6e4ec !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #5DCAA5 !important;
    font-weight: 600 !important;
    border-bottom: 2.5px solid #5DCAA5 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Subtitle ── */
.page-subtitle-spec {
    font-size: 13.5px;
    color: #6b7f8a;
    font-weight: 400;
    margin-top: 1.2rem;
    margin-bottom: 1.8rem;
    line-height: 1.5;
    max-width: 650px;
}

/* ── Bento Grid Cards Spec ── */
.card-vault {
    background: #0b1815;
    border: 1px solid #142e27;
    border-radius: 12px;
    padding: 24px 28px;
    height: 100%;
}
.card-runs {
    background: #180e15;
    border: 1px solid #2e1425;
    border-radius: 12px;
    padding: 24px 28px;
    height: 100%;
}
.card-sm-teal {
    background: #0b1513;
    border: 1.5px solid #1d4036;
    border-radius: 12px;
    padding: 18px 22px;
    height: 100%;
}
.card-sm-pink {
    background: #160c13;
    border: 1.5px solid #401d35;
    border-radius: 12px;
    padding: 18px 22px;
    height: 100%;
}
.card-panel-teal {
    background: #091210;
    border: 1px solid #142923;
    border-radius: 12px;
    padding: 22px 26px;
    height: 100%;
}
.card-panel-pink {
    background: #140911;
    border: 1px solid #291422;
    border-radius: 12px;
    padding: 22px 26px;
    height: 100%;
}

.lbl-teal {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #5DCAA5;
    margin-bottom: 10px;
}
.lbl-pink {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #D4537E;
    margin-bottom: 10px;
}

.val-hero {
    font-family: 'Inter', sans-serif;
    font-size: 46px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 12px;
}
.val-sm {
    font-family: 'Inter', sans-serif;
    font-size: 30px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.02em;
    line-height: 1;
}

.sub-pink {
    font-size: 11px;
    color: #7a5068;
    margin-top: 8px;
}

/* ── Spark Bars ── */
.spark-row {
    display: flex;
    align-items: flex-end;
    gap: 4px;
    height: 24px;
    margin-top: 8px;
}
.spark-bar-green {
    background: #1d9e75;
    border-radius: 2px 2px 0 0;
    width: 9px;
}

/* ── Country Progress Bars ── */
.c-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 14px;
}
.c-lbl {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    width: 20px;
}
.c-track {
    flex-grow: 1;
    background: #12241f;
    border-radius: 20px;
    height: 8px;
    overflow: hidden;
}
.c-fill {
    background: #1d9e75;
    height: 100%;
    border-radius: 20px;
}
.c-val {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #5DCAA5;
    width: 36px;
    text-align: right;
}

/* ── Salary Range Track Visual ── */
.sal-track-box {
    margin: 24px 0 16px 0;
}
.sal-track {
    background: #2a1420;
    height: 6px;
    border-radius: 10px;
    width: 100%;
    position: relative;
}
.sal-fill {
    background: #D4537E;
    height: 6px;
    border-radius: 10px;
    position: absolute;
}
.sal-dot {
    width: 14px;
    height: 14px;
    background: #ffffff;
    border-radius: 50%;
    position: absolute;
    top: -4px;
    box-shadow: 0 0 6px rgba(255,255,255,0.7);
}
.sal-sub {
    font-family: 'Inter', sans-serif;
    font-size: 11.5px;
    color: #8c5570;
    margin-top: 12px;
}

/* ── Tables & Controls ── */
.stDataFrame {
    border: 1px solid #182228 !important;
    border-radius: 8px !important;
    background: #090e11 !important;
}
div[data-baseweb="select"] > div {
    background-color: #0c1216 !important;
    border: 1px solid #182228 !important;
    border-radius: 7px !important;
}
.stTextInput > div > div {
    background: #0c1216 !important;
    border: 1px solid #182228 !important;
    border-radius: 7px !important;
    color: #d6e4ec !important;
}
.stButton > button {
    background: #0c1216 !important;
    color: #5DCAA5 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border: 1px solid #1d9e75 !important;
    padding: 10px 28px !important;
    border-radius: 7px !important;
}
.stButton > button:hover {
    background: rgba(29,158,117,0.1) !important;
}
.stLinkButton > a {
    background: transparent !important;
    color: #5DCAA5 !important;
    font-size: 12px !important;
    border: 1px solid #182228 !important;
    border-radius: 7px !important;
}
[data-baseweb="tag"] {
    background: rgba(29,158,117,0.15) !important;
    border: 1px solid #1d9e75 !important;
}
[data-baseweb="tag"] span { color: #5DCAA5 !important; }

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

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #090e10; }
::-webkit-scrollbar-thumb { background: #141c22; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Plotly Dark Theme ─────────────────────────────────────────────────────────
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#4a6070", family="Inter"),
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

# ── Header Row: Title Left, Tabs Right ────────────────────────────────────────
col_brand, col_nav = st.columns([1.1, 2.9])

with col_brand:
    st.markdown('<div class="brand-title-spec">SkillScavenge</div>', unsafe_allow_html=True)

with col_nav:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "the hunt",
        "skill signals",
        "open roles",
        "pay predictor",
        "model health",
    ])

st.markdown("<div style='border-bottom: 1px solid #141c22; margin-top: 2px; margin-bottom: 0px;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: THE HUNT — Market Overview
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div class="page-subtitle-spec">
        Every postings scraped, every skill logged, every dollar traced back to the data that predicts it.
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

    # ── Bento Row 1: Hero Vault Card + Hero Model Runs Card ──
    col_hero, col_mid = st.columns([3, 2])

    with col_hero:
        spark_html = "".join([
            f'<div class="spark-bar-green" style="height:{h}px;"></div>'
            for h in [8, 12, 10, 18, 14, 22, 16, 24]
        ])
        st.markdown(f"""
        <div class="card-vault">
            <div class="lbl-teal">POSTINGS IN THE VAULT</div>
            <div class="val-hero">{stats['total_rows']:,}</div>
            <div class="spark-row">{spark_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_mid:
        st.markdown(f"""
        <div class="card-runs">
            <div class="lbl-pink">MODEL RUNS LOGGED</div>
            <div class="val-hero">{stats['total_runs']}</div>
            <div class="sub-pink">last retrain {last_run_str}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Bento Row 2: 3 Supporting Small Cards ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="card-sm-teal">
            <div class="lbl-teal">SKILLS MAPPED</div>
            <div class="val-sm">{stats['total_mappings']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="card-sm-pink">
            <div class="lbl-pink">TECH VOCAB SIZE</div>
            <div class="val-sm">{stats['total_skills']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="card-sm-teal">
            <div class="lbl-teal">MARKETS COVERED</div>
            <div class="val-sm">{stats['total_markets']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Bento Row 3: Where the roles are + Salary spread ──
    chart_col1, chart_col2 = st.columns([1, 1])

    with chart_col1:
        country_data = run_query("""
            SELECT country, COUNT(*) AS count 
            FROM job_postings 
            GROUP BY country
            ORDER BY count DESC
            LIMIT 3
        """)
        max_c = country_data["count"].max() if not country_data.empty else 1
        
        bar_rows = []
        for _, row in country_data.iterrows():
            code = str(row["country"]).upper()
            cnt = row["count"]
            pct = int((cnt / max_c) * 100)
            cnt_str = f"{cnt/1000:.0f}k" if cnt >= 1000 else str(cnt)
            bar_rows.append(f'<div class="c-row"><div class="c-lbl">{code}</div><div class="c-track"><div class="c-fill" style="width:{pct}%;"></div></div><div class="c-val">{cnt_str}</div></div>')

        bars_html = "".join(bar_rows)

        st.markdown(f'<div class="card-panel-teal"><div class="lbl-teal">WHERE THE ROLES ARE</div><div style="margin-top:18px;">{bars_html}</div></div>', unsafe_allow_html=True)

    with chart_col2:
        salary_data = run_query("""
            SELECT (salary_min + salary_max) / 2 * CASE WHEN country = 'gb' THEN 1.27 ELSE 1.0 END AS midpoint
            FROM job_postings
            WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
              AND country IN ('us', 'gb')
        """)
        if not salary_data.empty and len(salary_data) > 4:
            midpoints = salary_data["midpoint"].astype(float)
            med_k = int(midpoints.median() / 1000)
            q25_k = int(midpoints.quantile(0.25) / 1000)
            q75_k = int(midpoints.quantile(0.75) / 1000)
        else:
            med_k, q25_k, q75_k = 118, 85, 152

        min_scale, max_scale = 30, 220
        left_pct = int(((q25_k - min_scale) / (max_scale - min_scale)) * 100)
        width_pct = int(((q75_k - q25_k) / (max_scale - min_scale)) * 100)
        dot_pct = int(((med_k - min_scale) / (max_scale - min_scale)) * 100)

        st.markdown(f'<div class="card-panel-pink"><div class="lbl-pink">SALARY SPREAD (USD)</div><div class="sal-track-box"><div class="sal-track"><div class="sal-fill" style="left:{left_pct}%; width:{width_pct}%;"></div><div class="sal-dot" style="left:calc({dot_pct}% - 7px);"></div></div></div><div class="sal-sub">median ${med_k}k - IQR ${q25_k}k–${q75_k}k</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="lbl-teal" style="margin-bottom:12px;">TOP HIRING COMPANIES</div>', unsafe_allow_html=True)
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
# PAGE 2: SKILL SIGNALS — Skill Intelligence
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class="page-subtitle-spec">
        What the market is paying attention to — and what it's quietly starting to ignore.
    </div>
    """, unsafe_allow_html=True)

    fc1, fc2 = st.columns(2)
    with fc1:
        selected_country = st.selectbox(
            "Country",
            ["All Countries", "United States", "United Kingdom", "India", "Worldwide"],
            key="tab2_country_select"
        )
    with fc2:
        selected_source = st.selectbox(
            "Source",
            ["All Sources", "Adzuna", "RemoteOK"],
            key="tab2_source_select"
        )

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
        st.markdown('<div class="lbl-teal">DEMAND BY TECHNOLOGY</div>', unsafe_allow_html=True)
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
                         tickfont=dict(family="Inter", size=12, color="#8099a8"),
                         gridcolor="#182228", linecolor="#182228")
        fig.update_xaxes(tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"),
                         gridcolor="#182228", linecolor="#182228")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="lbl-teal">LEARN WHAT\'S ADJACENT</div>', unsafe_allow_html=True)
        st.caption("Sentence-transformer similarity — `all-MiniLM-L6-v2`")

        all_skills_list = run_query("SELECT name FROM skills ORDER BY name")["name"].tolist()
        base_skill = st.selectbox(
            "Target skill",
            all_skills_list,
            index=all_skills_list.index("Python") if "Python" in all_skills_list else 0,
            key="tab2_target_skill_select"
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
                              tickfont=dict(family="Inter", size=11, color="#8099a8"),
                              gridcolor="#182228", linecolor="#182228")
            fig3.update_xaxes(visible=False)
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="lbl-pink">SKILLS THAT MOVE SALARY</div>', unsafe_allow_html=True)
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
                          tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"),
                          gridcolor="#182228", linecolor="#182228")
        fig4.update_xaxes(tickfont=dict(family="Inter", size=11, color="#8099a8"),
                          gridcolor="#182228", linecolor="#182228")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Insufficient salary-populated mappings to generate valuation charts.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: OPEN ROLES — Apply for Jobs
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div class="page-subtitle-spec">
        Live postings, filtered to your stack. Click through and apply directly.
    </div>
    """, unsafe_allow_html=True)

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
        sel_country = st.selectbox(
            "Country",
            ["All Countries", "United States", "United Kingdom", "India", "Worldwide"],
            key="tab3_country_select"
        )
    with col_f2:
        sel_source = st.selectbox(
            "Source",
            ["All Sources", "Adzuna", "RemoteOK"],
            key="tab3_source_select"
        )
    with col_f3:
        all_skills_df = run_query("SELECT name FROM skills ORDER BY name")
        all_skills = ["All Skills"] + (all_skills_df["name"].tolist() if not all_skills_df.empty else [])
        sel_skill = st.selectbox("Required Skill", all_skills, key="tab3_skill_select")
    with col_f4:
        search_term = st.text_input("Keyword", placeholder="Python, Engineer...", key="tab3_kw_input")

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

    st.caption("Showing up to 30 active postings")

    if job_results.empty:
        st.info("No postings match the current filters. Try broadening your criteria.")
    else:
        for idx, job in job_results.iterrows():
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
            <div style="background:#090e11; border:1px solid #182228; border-radius:10px; padding:20px 24px; margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:3px 9px;border-radius:4px;background:rgba(93,202,165,0.12);color:#5DCAA5;">{src_label} &nbsp;·&nbsp; {country_display}</span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;color:#5DCAA5;">{salary_display}</span>
                </div>
                <div style="font-size:16px;font-weight:600;color:#d6e4ec;margin:10px 0 3px 0;">{job['title']}</div>
                <div style="font-size:12px;color:#4a6070;margin-bottom:8px;">{job['company']} &nbsp;·&nbsp; {job['location'] or country_display}</div>
                <div style="font-size:12px;color:#8099a8;line-height:1.55;">{desc_snippet}</div>
            </div>
            """, unsafe_allow_html=True)
            st.link_button(f"Apply — {job['title']}", job["redirect_url"], use_container_width=False, key=f"apply_btn_{job['id']}_{idx}")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: PAY PREDICTOR — Salary Predictor
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div class="page-subtitle-spec">
        Build your stack. Get a number. Understand exactly which skills are moving the needle.
    </div>
    """, unsafe_allow_html=True)

    model_skills = sorted([col for col in FEATURE_NAMES if col not in ["country_gb", "country_us"]])

    col1, col2 = st.columns([3, 1])
    with col1:
        user_skills = st.multiselect(
            "Select skills",
            options=model_skills,
            default=["Python", "AWS", "SQL"] if "Python" in model_skills else [],
            key="tab4_skills_select"
        )
    with col2:
        user_country = st.selectbox(
            "Geography",
            ["United States (USD)", "United Kingdom (GBP)"],
            key="tab4_geo_select"
        )

    country_key = "us" if "United States" in user_country else "gb"

    st.markdown("")
    if st.button("Calculate salary estimate", key="tab4_calc_button"):
        if not user_skills:
            st.warning("Select at least one skill to generate an estimate.")
        else:
            skills_lower = {s.lower() for s in user_skills}
            fv = []
            for col in FEATURE_NAMES:
                if col == "country_gb":
                    fv.append(1 if country_key == "gb" else 0)
                elif col == "country_us":
                    fv.append(1 if country_key == "us" else 0)
                else:
                    fv.append(1 if col.lower() in skills_lower else 0)

            # Predict — read-only
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
            <div style="background:#140911; border:1px solid #291422; border-radius:12px; padding:32px 36px; text-align:center; margin:1.5rem 0;">
                <div class="lbl-pink">PROJECTED BASE</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:52px; font-weight:700; color:#D4537E; line-height:1;">{local_symbol}{pred_local:,.0f}</div>
                <div style="font-size:13px; color:#7a5068; margin-top:8px;">{local_suffix} &nbsp;·&nbsp; equivalent to ${pred_usd:,.0f} USD</div>
            </div>
            """, unsafe_allow_html=True)

            # ── SHAP breakdown ──
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<div class="lbl-teal">WHAT\'S DRIVING IT</div>', unsafe_allow_html=True)
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
                                      tickfont=dict(family="Inter", size=11, color="#8099a8"),
                                      gridcolor="#182228", linecolor="#182228")
                fig_shap.update_xaxes(tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"),
                                      gridcolor="#182228", linecolor="#182228")
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
                    "bgcolor": "#0c1216",
                    "bordercolor": "#182228",
                    "steps": [
                        {"range": [30000, 90000],  "color": "#0c1216"},
                        {"range": [90000, 150000], "color": "#0c1216"},
                        {"range": [150000, 220000],"color": "#0c1216"},
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
            st.markdown('<div class="lbl-teal">POSITIONS IN RANGE</div>', unsafe_allow_html=True)
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
# PAGE 5: MODEL HEALTH — Model Diagnostics
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("""
    <div class="page-subtitle-spec">
        Training runs, hyperparameter records, and feature weight distribution — all in one place.
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
            st.markdown('<div class="lbl-teal">RUN HISTORY</div>', unsafe_allow_html=True)
            st.dataframe(
                runs[["RunID", "Trained At", "Type", "Log MAE", "Log RMSE"]],
                use_container_width=True,
                hide_index=True,
            )

        with col2:
            st.markdown('<div class="lbl-pink">OPTIMAL PARAMETERS</div>', unsafe_allow_html=True)
            try:
                run_notes = json.loads(best_run["notes"])
                opt_params = run_notes.get("best_params", {})
                opt_r2 = run_notes.get("r2", "N/A")
                opt_raw_mae = run_notes.get("raw_mae_usd", "N/A")

                st.markdown(f"**R² Score:** `{opt_r2}`")
                st.markdown(f"**MAE (USD):** `${opt_raw_mae:,.2f}`")

                params_df = pd.DataFrame(opt_params.items(), columns=["Hyperparameter", "Value"])
                params_df["Value"] = params_df["Value"].astype(str)
                st.dataframe(params_df, use_container_width=True, hide_index=True)
            except Exception:
                st.code(best_run["notes"])

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="lbl-pink">FEATURE WEIGHT DISTRIBUTION</div>', unsafe_allow_html=True)
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
                             tickfont=dict(family="Inter", size=11, color="#8099a8"),
                             gridcolor="#182228", linecolor="#182228")
        fig_imp.update_xaxes(tickfont=dict(family="JetBrains Mono", size=10, color="#6b7f8a"),
                             gridcolor="#182228", linecolor="#182228")
        st.plotly_chart(fig_imp, use_container_width=True)
