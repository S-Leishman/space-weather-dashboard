"""
Page: Prediction Explorer
Interactive per-scenario inference with SHAP waterfall and feature sweep.
IBM Bob generated — Frontend Phase.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.theme import (
    inject_design_system, section_label, verdict_badge, shap_bar_chart,
    telemetry_table, plotly_dark_layout
)
from dashboard.components.utils import (
    MODELS_DIR,
    build_single_feature_vector, shap_top_n,
    load_best_model_metadata, load_metrics_summary
)

st.set_page_config(
    page_title="SWL · Prediction Explorer",
    page_icon="🔬",
    layout="wide",
)
inject_design_system()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-family:Orbitron,monospace;font-size:1.4rem;font-weight:800;'
    'letter-spacing:0.1em;color:#E8EDF5;padding:0.6rem 0 0.2rem;">'
    'PREDICTION <span style="color:#00D4FF;">EXPLORER</span></div>'
    '<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
    'color:#4A5568;letter-spacing:0.2em;">INTERACTIVE INFERENCE · SHAP · SCENARIO SWEEP</div>',
    unsafe_allow_html=True,
)
st.markdown('<hr style="border-color:#1C2640;margin:0.6rem 0 1rem;">', unsafe_allow_html=True)

# ── Model loading ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _load_model():
    import joblib
    for name in ["xgboost", "random_forest", "logistic_regression"]:
        p = MODELS_DIR / f"{name}.joblib"
        if p.exists():
            model = joblib.load(p)
            meta_p = MODELS_DIR / f"{name}_metadata.json"
            meta   = json.loads(meta_p.read_text()) if meta_p.exists() else {}
            return model, name, meta
    return None, None, {}

@st.cache_resource(show_spinner=False)
def _load_explainer(model_name: str):
    try:
        import shap, joblib
        from sklearn.pipeline import Pipeline
        model = joblib.load(MODELS_DIR / f"{model_name}.joblib")
        if isinstance(model, Pipeline):
            return None
        return shap.TreeExplainer(model)
    except Exception:
        return None

model, model_name, model_meta = _load_model()
model_loaded  = model is not None
feat_names    = model_meta.get("feature_names") or [
    "kp_3d_avg","kp_7d_avg","flux_3d_avg","flux_7d_avg",
    "kp_lag1","kp_lag3","kp_lag7","xclass_72h","mclass_72h",
    "cme_arrival_score","gst_level","day_sin","day_cos","hour_sin","hour_cos",
]

if not model_loaded:
    st.warning("⚠️ No trained model found. Run `notebooks/04_model_training.ipynb` first. "
               "Demo mode shows synthetic outputs.")
else:
    st.warning("Prototype model artifact: generated from synthetic test data; not operationally qualified.")

# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO INPUT
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Scenario Configuration")

col_inp1, col_inp2, col_inp3 = st.columns(3)

with col_inp1:
    kp   = st.slider("Kp Index",    0.0, 9.0, 2.5, 0.1, key="pe_kp")
    flux = st.slider("F10.7 (sfu)", 65.0, 300.0, 120.0, 1.0, key="pe_flux")
    hour = st.slider("Launch Hour (UTC)", 0, 23, 14, key="pe_hour")

with col_inp2:
    gst   = st.selectbox("Geomag Storm", [0,1,2,3,4,5],
                         format_func=lambda x: f"G{x}", key="pe_gst")
    cme_s = st.slider("CME Speed (km/s)",    0, 3000, 0,   key="pe_cmes")
    cme_a = st.slider("CME Half-angle (°)", 0, 90,   30,  key="pe_cmea")

with col_inp3:
    xclass   = st.checkbox("X-class flare ≤72h",  key="pe_xfl")
    mclass   = st.checkbox("M-class flare ≤72h",  key="pe_mfl")
    doy      = st.slider("Day of Year",  1, 365,
                         datetime.now().timetuple().tm_yday, key="pe_doy")

cme_score = cme_s * math.cos(math.radians(cme_a)) if cme_s > 0 else 0.0

X_vec, feat_names_used = build_single_feature_vector(
    kp=kp, f10_7=flux, launch_hour=hour, day_of_year=doy,
    cme_score=cme_score, gst_level=gst,
    xclass_72h=int(xclass), mclass_72h=int(mclass),
    feature_names=feat_names,
)

if model_loaded:
    try:
        prob_go = float(model.predict_proba(X_vec)[0][1])
    except Exception:
        prob_go = 0.5
else:
    # Reproducible synthetic probability from inputs
    raw   = kp * 0.12 + (gst * 0.15) + (int(xclass) * 0.2) - (flux / 300 * 0.1)
    prob_go = max(0.05, min(0.95, 0.75 - raw * 0.08))

verdict_txt = "GO"    if prob_go >= 0.65 else "HOLD"  if prob_go >= 0.40 else "SCRUB"
gauge_color = "#00FF41" if prob_go >= 0.65 else "#FFD700" if prob_go >= 0.40 else "#FF4444"
verdict_cls = {"GO":"swl-verdict-go","HOLD":"swl-verdict-hold","SCRUB":"swl-verdict-scrub"}[verdict_txt]

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION RESULT
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Inference Result")

col_g, col_v, col_b = st.columns([1.2, 1, 1.8])

with col_g:
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(prob_go * 100, 1),
        number={"suffix":"%","font":{"size":36,"color":gauge_color,
                                     "family":"Orbitron,monospace"}},
        gauge={
            "axis":{"range":[0,100],"tickcolor":"#4A5568",
                    "tickfont":{"family":"IBM Plex Mono","size":9}},
            "bar": {"color":gauge_color,"thickness":0.2},
            "bgcolor":"#0D1220","bordercolor":"#1C2640",
            "steps":[
                {"range":[0,40],"color":"rgba(255,68,68,0.07)"},
                {"range":[40,65],"color":"rgba(255,215,0,0.06)"},
                {"range":[65,100],"color":"rgba(0,255,65,0.07)"},
            ],
            "threshold":{"line":{"color":"#4A5568","width":1},"thickness":0.6,"value":65},
        },
    ))
    fig_g.update_layout(**plotly_dark_layout(
        height=220, margin=dict(l=20, r=20, t=10, b=10)
    ))
    st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar":False})

with col_v:
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'justify-content:center;height:200px;gap:12px;">'
        f'<div class="swl-verdict {verdict_cls}" style="font-size:1.2rem;padding:0.7rem 1.6rem;">'
        f'{verdict_txt}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;color:#4A5568;">'
        f'p(GO) = {prob_go:.4f}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#4A5568;">'
        f'Model: {model_name or "demo"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_b:
    section_label("SHAP Explanation")
    shap_done = False
    if model_loaded and model_name in ("xgboost","random_forest"):
        explainer = _load_explainer(model_name)
        if explainer:
            try:
                sv = explainer.shap_values(X_vec)
                if isinstance(sv, list):
                    sv = sv[1]
                top_shap = shap_top_n(sv[0], feat_names_used, n=8)
                shap_bar_chart(top_shap)
                shap_done = True
            except Exception:
                pass
    if not shap_done:
        demo_shap = [
            {"feature": "kp_3d_avg",        "shap_value": -0.182 * (kp / 5)},
            {"feature": "flux_3d_avg",       "shap_value":  0.110 * (flux / 150)},
            {"feature": "gst_level",         "shap_value": -0.087 * gst},
            {"feature": "xclass_72h",        "shap_value": -0.064 * int(xclass)},
            {"feature": "cme_arrival_score", "shap_value": -0.039 * min(cme_score/1000,1)},
            {"feature": "kp_lag1",           "shap_value": -0.031 * (kp / 5)},
            {"feature": "day_sin",           "shap_value":  0.020},
            {"feature": "hour_sin",          "shap_value":  0.012},
        ]
        shap_bar_chart(demo_shap)
        st.caption("⚠️ Synthetic SHAP · run notebook 04 for real values")
    st.caption("▲ Green pushes GO · ▼ Red pushes SCRUB")

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# KP SWEEP CHART
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Kp Index Sensitivity Sweep")

kp_range = np.linspace(0, 9, 46)
sweep_probs = []

for kp_val in kp_range:
    Xsw, _ = build_single_feature_vector(
        kp=float(kp_val), f10_7=flux, launch_hour=hour, day_of_year=doy,
        cme_score=cme_score, gst_level=gst,
        xclass_72h=int(xclass), mclass_72h=int(mclass),
        feature_names=feat_names_used,
    )
    if model_loaded:
        try:
            p = float(model.predict_proba(Xsw)[0][1])
        except Exception:
            p = 0.5
    else:
        raw2 = kp_val * 0.12 + gst * 0.15 + int(xclass) * 0.2 - flux/300*0.1
        p = max(0.05, min(0.95, 0.75 - raw2 * 0.08))
    sweep_probs.append(p)

fig_sweep = go.Figure()
fig_sweep.add_trace(go.Scatter(
    x=kp_range, y=sweep_probs,
    line=dict(color="#00D4FF", width=2),
    fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
    name="P(GO)",
    hovertemplate="Kp=%{x:.1f} → P(GO)=%{y:.3f}<extra></extra>",
))
# Current Kp marker
fig_sweep.add_vline(x=kp, line_dash="dot", line_color=gauge_color,
                    annotation_text=f"Current Kp={kp:.1f}",
                    annotation_font=dict(color=gauge_color, size=9, family="IBM Plex Mono"))
fig_sweep.add_hline(y=0.65, line_dash="dot", line_color="#00FF41",
                    annotation_text="GO threshold (0.65)",
                    annotation_font=dict(color="#00FF41",size=9,family="IBM Plex Mono"),
                    annotation_position="top right")
fig_sweep.add_hline(y=0.40, line_dash="dot", line_color="#FFD700",
                    annotation_text="HOLD threshold (0.40)",
                    annotation_font=dict(color="#FFD700",size=9,family="IBM Plex Mono"),
                    annotation_position="top right")
fig_sweep.update_layout(**plotly_dark_layout(
    height=250, xaxis_title="Kp Index", yaxis_title="P(GO)",
    yaxis=dict(range=[0,1.05], gridcolor="#1C2640", linecolor="#1C2640", tickcolor="#4A5568"),
))
st.plotly_chart(fig_sweep, use_container_width=True, config={"displayModeBar":False})

st.caption(
    f"All other parameters held constant: F10.7={flux:.0f}  "
    f"Storm=G{gst}  CME={cme_s}km/s  X-flare={'YES' if xclass else 'NO'}"
)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE VECTOR INSPECTION
# ═══════════════════════════════════════════════════════════════════════════════
with st.expander("🔍 Raw Feature Vector", expanded=False):
    vec_rows = [
        {"Feature": n, "Value": f"{X_vec[0][i]:.6f}"}
        for i, n in enumerate(feat_names_used)
    ]
    telemetry_table(vec_rows, ["Feature","Value"])

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:1rem 0 0;font-family:IBM Plex Mono,monospace;'
    'font-size:0.62rem;color:#4A5568;letter-spacing:0.1em;">'
    'SWL PREDICTION EXPLORER · INTERACTIVE INFERENCE · SHAP EXPLANATIONS</div>',
    unsafe_allow_html=True,
)
