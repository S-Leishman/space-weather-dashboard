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
    load_best_model_metadata, load_metrics_summary,
    load_active_model, explainer_state, load_provenance, positive_class_column,
)
from dashboard.components.evidence import (
    HUMAN_AUTHORITY_NOTICE,
    build_evidence_package,
    policy_check,
    render_decision_chain,
    render_evidence_drawer,
    render_policy_state,
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
    # Identity comes from the shared resolver, never from a preference order
    # local to this page — that is how this page served xgboost while HOME
    # served the recorded validation champion.
    return load_active_model()

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

# No synthetic fallback: if the model cannot score the scenario, the score is
# absent and every downstream readout says so. Inventing a plausible number here
# is indistinguishable from a real inference to anyone reading the screen.
prob_go = None
if model_loaded:
    try:
        prob_go = float(model.predict_proba(X_vec)[0][positive_class_column(model)])
    except Exception:
        prob_go = None

prediction_available = prob_go is not None
if not prediction_available:
    verdict_txt, gauge_color = "UNAVAILABLE", "#8892A4"
elif prob_go >= 0.65:
    verdict_txt, gauge_color = "GO", "#00FF41"
elif prob_go >= 0.40:
    verdict_txt, gauge_color = "HOLD", "#FFD700"
else:
    verdict_txt, gauge_color = "SCRUB", "#FF4444"
verdict_cls = {"GO":"swl-verdict-go","HOLD":"swl-verdict-hold",
               "SCRUB":"swl-verdict-scrub"}.get(verdict_txt, "swl-verdict-hold")

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION RESULT
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Prototype GO Score")
st.caption(
    "Prototype GO Score — a model score, NOT a calibrated launch-success probability. "
    "The training label is synthetic and independent of the space-weather features."
)
render_decision_chain(st, active="MODEL INFERENCE")

col_g, col_v, col_b = st.columns([1.2, 1, 1.8])

with col_g:
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(prob_go * 100, 1) if prediction_available else 0,
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
    _score_txt = (
        f"Prototype model score = {prob_go:.4f}" if prediction_available
        else "Prototype model score = UNAVAILABLE"
    )
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'justify-content:center;height:200px;gap:12px;">'
        f'<div class="swl-verdict {verdict_cls}" style="font-size:1.2rem;padding:0.7rem 1.6rem;">'
        f'{verdict_txt}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;color:#4A5568;">'
        f'{_score_txt}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#4A5568;">'
        f'SELECTED MODEL: {model_name or "UNAVAILABLE"}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.58rem;color:#4A5568;">'
        f'VALIDATION CHAMPION: {load_metrics_summary().get("best_model") or "NONE"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_b:
    section_label("SHAP Explanation")
    # Availability is decided by the shared explainer_state so this page cannot
    # disagree with HOME about whether SHAP exists.
    _exp = explainer_state(model)
    shap_done = False

    if _exp["available"]:
        explainer = _load_explainer(model_name)
        if explainer:
            try:
                sv = explainer.shap_values(X_vec)
                if isinstance(sv, list):
                    sv = sv[1]
                top_shap = shap_top_n(sv[0], feat_names_used, n=8)
                shap_bar_chart(top_shap)
                shap_done = True
                st.caption("▲ Green pushes GO · ▼ Red pushes SCRUB")
            except Exception:
                shap_done = False

    if not shap_done:
        # No attribution values are shown. The previous synthetic vector was
        # never computed from this model, and a plausible-looking attribution
        # is the most misleading kind of fabrication.
        st.info(
            "SHAP explanation UNAVAILABLE — "
            f"{_exp['reason']}. No attribution values are shown."
        )

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE-GATED MISSION DECISION
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Mission Decision — Evidence Gated")
render_decision_chain(st, active="POLICY CHECK")

_prov = load_provenance()
_artifacts_ok = bool(_prov and not _prov.get("note"))
_decision = policy_check(prob_go, _artifacts_ok)
render_policy_state(st, _decision)

_pkg = build_evidence_package(
    inputs={
        "kp_index": kp, "f107_flux": flux, "gst_level": gst,
        "x_class_flare": bool(xclass),
    },
    source="NASA DONKI / NOAA SWPC (scenario inputs)",
    model_name=model_name,
    model_sha256=(load_best_model_metadata() or {}).get("sha256"),
    score=prob_go,
    artifacts_ok=_artifacts_ok,
)
render_evidence_drawer(st, _pkg)
st.caption(HUMAN_AUTHORITY_NOTICE)

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
