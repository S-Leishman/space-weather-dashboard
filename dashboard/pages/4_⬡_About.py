"""
Page 4: About / IBM Bob Integration
IBM Bob generated — Frontend Phase.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.theme import (
    inject_design_system, section_label, telemetry_table, ibm_bob_badge
)

st.set_page_config(
    page_title="SWL · About",
    page_icon="⬡",
    layout="wide",
)
inject_design_system()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-family:Orbitron,monospace;font-size:1.4rem;font-weight:800;'
    'letter-spacing:0.1em;color:#E8EDF5;padding:0.6rem 0 0.2rem;">'
    'ABOUT <span style="color:#00D4FF;">THIS PROJECT</span></div>'
    '<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
    'color:#4A5568;letter-spacing:0.2em;">IBM BOB · CHALLENGE FIT · ARCHITECTURE</div>',
    unsafe_allow_html=True,
)
st.markdown('<hr style="border-color:#1C2640;margin:0.6rem 0 1rem;">', unsafe_allow_html=True)

# ── IBM Bob badge ─────────────────────────────────────────────────────────────
col_badge, col_spacer = st.columns([1, 3])
with col_badge:
    ibm_bob_badge()
    st.markdown(
        '<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
        'color:#4A5568;margin-top:6px;">August AI Builders Challenge</div>',
        unsafe_allow_html=True,
    )

st.markdown('<br>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# IBM BOB USAGE LOG
# ═══════════════════════════════════════════════════════════════════════════════
section_label("IBM Bob Usage — Phase-by-Phase Log")

BOB_LOG = [
    ("Phase 1", "Repository scaffolding",
     "Generated requirements.txt, directory structure, README.md skeleton, "
     ".github/workflows/ci.yml, pyproject.toml"),
    ("Phase 2", "Data ingestion pipeline",
     "Generated dashboard/components/ingestion.py — DONKI API client, retry logic, "
     "manifest serialization; notebooks/01_data_ingestion.ipynb, 02_eda_and_cleaning.ipynb"),
    ("Phase 3", "Feature engineering",
     "Generated dashboard/components/features.py — rolling windows, lag features, "
     "CME arrival score, cyclical encoding, FEATURE_PROVENANCE.json writer; "
     "notebooks/03_feature_engineering.ipynb"),
    ("Phase 4", "Model training",
     "Generated dashboard/components/model_trainer.py — LR/RF/XGBoost pipelines, "
     "GridSearchCV, evaluation metrics, SHAP explainability; "
     "notebooks/04_model_training.ipynb, 05_evaluation_and_explainability.ipynb"),
    ("Phase 5", "Streamlit dashboard",
     "Generated dashboard/app.py, dashboard/components/utils.py — "
     "gauge chart, KP time series, SHAP panel, provenance display"),
    ("Phase 6", "Test suite + CI",
     "Generated tests/test_ingestion.py, test_features.py, test_model.py, "
     "test_dashboard_utils.py; .github/workflows/ci.yml with coverage reporting"),
    ("Frontend", "Design system + multi-page UI",
     "Generated dashboard/assets/css/space_theme.css, components/theme.py, "
     "app.py (hero), pages/1–4 (Data Pipeline, Model Lab, Prediction Explorer, About)"),
]

bob_rows = [
    {"Phase": p, "Task": t, "Bob Output": o}
    for p, t, o in BOB_LOG
]
telemetry_table(bob_rows, ["Phase","Task","Bob Output"])

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT ABSTRACT
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Project Abstract")

st.markdown(
    """
    <div style="background:#0D1220;border:1px solid #1C2640;border-radius:8px;
                padding:1.2rem 1.5rem;font-family:IBM Plex Mono,monospace;
                font-size:0.78rem;color:#8892A4;line-height:1.8;max-width:800px;">
    Space weather events — solar flares, coronal mass ejections, and geomagnetic storms —
    pose significant risks to launch vehicles, on-board electronics, and crew safety.
    Despite this, most launch probability tools treat meteorological weather as the primary
    environmental constraint and model space weather qualitatively.
    <br><br>
    This project addresses that gap by building an end-to-end AI pipeline that ingests
    real-time <span style="color:#00D4FF;">NASA DONKI telemetry</span>, engineers
    temporally-aware features (rolling Kp averages, CME arrival scores, cyclical time
    encodings), and trains an ensemble of classifiers (Logistic Regression, Random Forest,
    <span style="color:#00FF41;">XGBoost</span>) to predict binary launch go/no-go decisions.
    The best model is explained using <span style="color:#FF6B35;">SHAP</span> to make
    predictions interpretable for mission planners.
    <br><br>
    An interactive <span style="color:#00D4FF;">Streamlit dashboard</span> surfaces current
    conditions, historical trends, and per-prediction explanations with a gauge-style launch
    probability readout. All data artifacts carry SHA-256 hashes in a provenance file, all
    model checkpoints are versioned with metadata JSONs, and a
    <span style="color:#4A5568;">GitHub Actions CI pipeline</span> validates correctness on
    every push. Built throughout with <span style="color:#78A9FF;">IBM Bob</span>.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# JUDGING CRITERIA MAPPING
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Judging Criteria Mapping")

CRITERIA = [
    ("Technical Execution",
     "End-to-end ML pipeline: ingestion → feature engineering → LR/RF/XGBoost → SHAP. "
     "SHA-256 provenance on every artifact. pytest suite with CI on GitHub Actions."),
    ("Innovation",
     "Quantitative space-weather–driven launch go/no-go via CME arrival scoring and "
     "cyclical temporal features. Per-prediction SHAP explanations for mission planners. "
     "Animated starfield design with CRT overlay."),
    ("Challenge Fit",
     "Directly advances space exploration: AI system reduces risk of launching into "
     "geomagnetically active conditions. Consumes real NASA DONKI and NOAA SWPC data."),
    ("Feasibility",
     "Fully self-contained Python stack. Runs on a laptop with pip install. "
     "DEMO_KEY works without registration. No paid infrastructure required."),
    ("Real-World Impact",
     "Mission planners can model hypothetical launch windows in real time. "
     "System is extensible to satellite operators, CubeSat launches, and crewed missions."),
]

crit_rows = [{"Criterion": c, "Justification": j} for c, j in CRITERIA]
telemetry_table(crit_rows, ["Criterion","Justification"])

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA SOURCES
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Data Sources")

SOURCES = [
    ("NASA DONKI", "Solar flares, CMEs, geomagnetic storms, SEPs",
     "https://kauai.ccmc.gsfc.nasa.gov/DONKI/", "Public / no license restriction"),
    ("NOAA SWPC Kp 1-min", "Real-time geomagnetic Kp index stream",
     "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json", "Public domain"),
    ("NOAA Solar Cycle Indices", "Historical F10.7 solar flux (proxy for UV/EUV)",
     "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json",
     "Public domain"),
]

src_rows = [
    {"Source": s, "Content": c, "License": l}
    for s, c, _, l in SOURCES
]
telemetry_table(src_rows, ["Source","Content","License"])

st.markdown('<br>', unsafe_allow_html=True)
for s, c, url, _ in SOURCES:
    st.markdown(
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="font-family:IBM Plex Mono,monospace;font-size:0.70rem;'
        f'color:#00D4FF;text-decoration:none;">'
        f'↗ {s}: {url}</a><br>',
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:1.5rem 0 0.5rem;'
    'font-family:IBM Plex Mono,monospace;font-size:0.65rem;'
    'color:#4A5568;letter-spacing:0.1em;">'
    'SWL · AUGUST AI BUILDERS CHALLENGE WITH IBM BOB</div>',
    unsafe_allow_html=True,
)
