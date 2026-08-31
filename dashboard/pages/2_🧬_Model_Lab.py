"""
Page: Model Training Lab
Shows training metrics, model comparison, and feature engineering details.
IBM Bob generated — Frontend Phase.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.theme import (
    inject_design_system, section_label, telemetry_table,
    metric_pill, plotly_dark_layout
)
from dashboard.components.utils import MODELS_DIR, load_metrics_summary, load_best_model_metadata

st.set_page_config(
    page_title="SWL · Model Training Lab",
    page_icon="🧬",
    layout="wide",
)
inject_design_system()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-family:Orbitron,monospace;font-size:1.4rem;font-weight:800;'
    'letter-spacing:0.1em;color:#E8EDF5;padding:0.6rem 0 0.2rem;">'
    'MODEL <span style="color:#00D4FF;">TRAINING LAB</span></div>'
    '<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
    'color:#4A5568;letter-spacing:0.2em;">LR · RANDOM FOREST · XGBOOST · SHAP</div>',
    unsafe_allow_html=True,
)
st.markdown('<hr style="border-color:#1C2640;margin:0.6rem 0 1rem;">', unsafe_allow_html=True)

# ── Load metrics ──────────────────────────────────────────────────────────────
metrics_sum = load_metrics_summary()
best_meta   = load_best_model_metadata()

has_metrics = "note" not in metrics_sum
metrics_list = metrics_sum.get("metrics", []) if has_metrics else []
best_name    = metrics_sum.get("best_model", "") if has_metrics else ""

if has_metrics:
    st.warning("Prototype metrics only: bundled artifacts were generated from synthetic test data and are not operational qualification evidence.")

# There is deliberately no fabricated fallback. The previous metrics-fallback block
# published invented accuracy/AUC figures under real metric labels whenever the
# artifacts were absent, which is indistinguishable from a measurement.
display_metrics = metrics_list
demo_note = not has_metrics

if demo_note:
    st.warning(
        "Model metrics NOT_EVALUATED — `models/metrics_summary.json` is absent, so no "
        "metrics are shown. Run `notebooks/04_model_training.ipynb` to produce them."
    )
    best_name = ""

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL COMPARISON OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Model Performance Overview")

METRIC_KEYS = ["accuracy","precision","recall","f1","roc_auc","log_loss"]
MODEL_COLORS = {
    "logistic_regression": "#4A5568",
    "random_forest":       "#00D4FF",
    "xgboost":             "#00FF41",
}
MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest":       "Random Forest",
    "xgboost":             "XGBoost",
}

# Metric cards
cols = st.columns(len(METRIC_KEYS))
for ci, key in enumerate(METRIC_KEYS):
    best_m = max(
        display_metrics,
        key=lambda m: m.get(key, 0) if key != "log_loss" else -m.get(key, 999)
    )
    val = best_m.get(key, 0)
    cols[ci].metric(
        key.upper().replace("_"," "),
        f"{val:.4f}",
        delta=f"Best: {MODEL_LABELS.get(best_m['model'],best_m['model'])}",
        delta_color="off",
    )

st.markdown('<br>', unsafe_allow_html=True)

# ── Radar chart ───────────────────────────────────────────────────────────────
col_radar, col_bar = st.columns([1, 1.4])

with col_radar:
    section_label("Performance Radar")
    radar_metrics = ["accuracy","precision","recall","f1","roc_auc"]
    fig_radar = go.Figure()

    for m in display_metrics:
        vals = [m.get(k, 0) for k in radar_metrics]
        vals.append(vals[0])  # close polygon
        color = MODEL_COLORS.get(m["model"], "#8892A4")
        fig_radar.add_trace(go.Scatterpolar(
            r=vals,
            theta=radar_metrics + [radar_metrics[0]],
            name=MODEL_LABELS.get(m["model"], m["model"]),
            line=dict(color=color, width=2),
            fill="toself",
            fillcolor=f"rgba{hex_to_rgb(color) + (0.05,)}",
            hovertemplate="%{theta}: %{r:.4f}<extra></extra>",
        ))

    fig_radar.update_layout(
        polar=dict(
            bgcolor="#0D1220",
            radialaxis=dict(
                visible=True, range=[0,1],
                gridcolor="#1C2640", linecolor="#1C2640",
                tickcolor="#4A5568",
                tickfont=dict(family="IBM Plex Mono", size=9, color="#4A5568"),
            ),
            angularaxis=dict(
                gridcolor="#1C2640", linecolor="#1C2640",
                tickfont=dict(family="IBM Plex Mono", size=9, color="#8892A4"),
            ),
        ),
        paper_bgcolor="#0D1220",
        font=dict(family="IBM Plex Mono", color="#8892A4", size=10),
        legend=dict(font=dict(size=9), bgcolor="rgba(13,18,32,0.8)",
                    bordercolor="#1C2640"),
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_radar, use_container_width=True,
                    config={"displayModeBar": False})

with col_bar:
    section_label("ROC-AUC Comparison")
    # A refused AUC (insufficient class support / single-class split) arrives as
    # None. It is charted as absent rather than coerced to a number.
    _scored = [m for m in display_metrics if m.get("roc_auc") is not None]
    _refused = [m for m in display_metrics if m.get("roc_auc") is None]
    model_names = [MODEL_LABELS.get(m["model"],m["model"]) for m in _scored]
    auc_vals    = [m["roc_auc"] for m in _scored]
    colors      = [MODEL_COLORS.get(m["model"],"#8892A4") for m in _scored]
    if _refused:
        st.caption(
            "ROC-AUC REFUSED (not charted) for: "
            + ", ".join(MODEL_LABELS.get(m["model"], m["model"]) for m in _refused)
            + " — " + (_refused[0].get("roc_auc_note") or "insufficient validation support")
        )

    fig_auc = go.Figure()
    fig_auc.add_trace(go.Bar(
        x=model_names, y=auc_vals,
        marker=dict(color=colors, line=dict(color="#080B14", width=1)),
        text=[f"{v:.4f}" for v in auc_vals],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=10, color="#8892A4"),
        hovertemplate="%{x}<br>ROC-AUC: %{y:.4f}<extra></extra>",
    ))
    fig_auc.add_hline(y=0.5, line_dash="dot", line_color="#4A5568",
                      annotation_text="Random baseline",
                      annotation_font=dict(size=9, color="#4A5568"))
    fig_auc.update_layout(**plotly_dark_layout(
        height=300,
        yaxis=dict(range=[0,1.05], gridcolor="#1C2640", linecolor="#1C2640",
                   tickcolor="#4A5568"),
        yaxis_title="ROC-AUC",
        showlegend=False,
    ))
    st.plotly_chart(fig_auc, use_container_width=True,
                    config={"displayModeBar": False})

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FULL METRICS TABLE
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Complete Metrics Table")

table_rows = []
for m in display_metrics:
    row = {"Model": MODEL_LABELS.get(m["model"],m["model"])}
    for k in METRIC_KEYS:
        row[k.upper()] = f"{m.get(k,0):.4f}"
    row["Best"] = "★" if m["model"] == best_name else ""
    table_rows.append(row)

cols_hdr = ["Model"] + [k.upper() for k in METRIC_KEYS] + ["Best"]
telemetry_table(table_rows, cols_hdr, color_col="ROC_AUC")

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Feature Engineering Reference")

FEATURE_DOCS = [
    ("kp_3d_avg",         "Rolling 3-day mean Kp index",          "Continuous"),
    ("kp_7d_avg",         "Rolling 7-day mean Kp index",          "Continuous"),
    ("flux_3d_avg",       "Rolling 3-day mean F10.7 solar flux",  "Continuous"),
    ("flux_7d_avg",       "Rolling 7-day mean F10.7 solar flux",  "Continuous"),
    ("kp_lag1",           "Kp index 1-day lag",                   "Continuous"),
    ("kp_lag3",           "Kp index 3-day lag",                   "Continuous"),
    ("kp_lag7",           "Kp index 7-day lag",                   "Continuous"),
    ("xclass_72h",        "X-class flare in prior 72h (binary)",  "Binary 0/1"),
    ("mclass_72h",        "M-class flare in prior 72h (binary)",  "Binary 0/1"),
    ("cme_arrival_score", "CME speed × cos(half-angle) heuristic","Continuous"),
    ("gst_level",         "Ordinal geomag storm level 0–5",       "Ordinal 0–5"),
    ("day_sin",           "Day-of-year cyclical sin encoding",     "[-1, 1]"),
    ("day_cos",           "Day-of-year cyclical cos encoding",     "[-1, 1]"),
    ("hour_sin",          "Launch hour cyclical sin encoding",     "[-1, 1]"),
    ("hour_cos",          "Launch hour cyclical cos encoding",     "[-1, 1]"),
]

feat_rows = [{"Feature": f, "Description": d, "Type": t} for f,d,t in FEATURE_DOCS]
telemetry_table(feat_rows, ["Feature","Description","Type"])

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SAVED MODEL ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Saved Model Artifacts")

artifact_rows = []
if MODELS_DIR.exists():
    for jl in sorted(MODELS_DIR.glob("*.joblib")):
        meta_p = MODELS_DIR / f"{jl.stem}_metadata.json"
        meta   = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        sha    = meta.get("sha256","—")[:20]+"…" if meta.get("sha256") else "—"
        artifact_rows.append({
            "File":    jl.name,
            "Size":    f"{jl.stat().st_size:,} B",
            "SHA-256": sha,
            "AUC":     str(meta.get("roc_auc","—")),
        })

if artifact_rows:
    telemetry_table(artifact_rows, ["File","Size","SHA-256","AUC"])
else:
    st.info("No .joblib files found in models/. Run notebook 04 to train and save models.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:1rem 0 0;font-family:IBM Plex Mono,monospace;'
    'font-size:0.62rem;color:#4A5568;letter-spacing:0.1em;">'
    'SWL MODEL TRAINING LAB · SCIKIT-LEARN · XGBOOST · SHAP</div>',
    unsafe_allow_html=True,
)
