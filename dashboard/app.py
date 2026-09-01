"""
Space Weather Launch Probability Dashboard — Entry point / Hero page.
IBM Bob generated — Frontend Phase.

Run:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.theme import (
    inject_design_system,
    section_label,
    verdict_badge,
    ibm_bob_badge,
    shap_bar_chart,
    telemetry_table,
    plotly_dark_layout,
)
from dashboard.components.utils import (
    MODELS_DIR,
    build_single_feature_vector,
    live_space_weather,
    load_kp_history,
    load_metrics_summary,
    load_best_model_metadata,
    load_provenance,
    load_active_model,
    load_selected_model_name,
    positive_class_column,
    feature_importance_state,
    shap_top_n,
    explainer_state,
    summarise_weather,
)
from dashboard.components.evidence import (
    HUMAN_AUTHORITY_NOTICE,
    build_evidence_package,
    policy_check,
    render_artifact_receipt_banner,
    render_decision_chain,
    render_evidence_drawer,
    render_policy_state,
)

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Aevion SpaceOps · Mission Control",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/YOUR_USERNAME/space-weather-dashboard",
        "Report a bug": "https://github.com/YOUR_USERNAME/space-weather-dashboard/issues",
        "About": "Aevion SpaceOps — AI mission-risk decisions with evidence, provenance, and human authority. August AI Builders Challenge with IBM Bob",
    },
)

inject_design_system()

# ── Shared resource loaders ───────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _load_model():
    # Load the model recorded as the validation champion — and only that model.
    # A preference order here is how the UI came to serve a different model than
    # the one it named as champion.
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

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_weather(api_key: str) -> dict:
    return live_space_weather(api_key=api_key, lookback_days=3)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:0.8rem 0 0.4rem;">'
        '<span style="font-family:var(--font-display,monospace);font-size:1.0rem;'
        'font-weight:800;letter-spacing:0.12em;color:#00D4FF;">SWL</span>'
        '<span style="font-family:var(--font-mono,monospace);font-size:0.6rem;'
        'color:#4A5568;display:block;letter-spacing:0.2em;margin-top:2px;">MISSION CONTROL</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    section_label("API Configuration")
    nasa_api_key = st.text_input(
        "NASA API Key",
        value="DEMO_KEY",
        type="password",
        help="Free key at https://api.nasa.gov/",
        label_visibility="collapsed",
        placeholder="NASA API Key (DEMO_KEY for demo)",
    )

    st.markdown("---")
    section_label("Date Range")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "From", value=pd.Timestamp.now() - pd.Timedelta(days=90),
            label_visibility="collapsed",
        )
    with col_e:
        end_date = st.date_input(
            "To", value=pd.Timestamp.now(),
            label_visibility="collapsed",
        )

    st.markdown("---")
    section_label("Scenario Modelling")
    kp_input   = st.slider("Kp Index", 0.0, 9.0, 2.5, 0.1,
                           help="Geomagnetic activity (0 = quiet, 9 = extreme storm)")
    flux_input = st.slider("F10.7 Solar Flux", 65.0, 300.0, 120.0, 1.0,
                           help="Solar radio flux proxy (sfu)")
    hour_input = st.slider("Launch Hour UTC", 0, 23, 14)
    gst_input  = st.selectbox(
        "Geomag Storm",
        [0,1,2,3,4,5],
        format_func=lambda x: f"G{x} — {'None' if x==0 else ['Minor','Moderate','Strong','Severe','Extreme'][x-1]}",
    )
    xclass_flag = st.checkbox("X-class flare ≤72h")
    mclass_flag = st.checkbox("M-class flare ≤72h")

    st.markdown("---")
    section_label("CME Parameters")
    cme_speed = st.slider("CME Speed (km/s)", 0, 3000, 0,
                          help="Set 0 for no recent CME")
    cme_angle = st.slider("CME Half-angle (°)", 0, 90, 30)

    st.markdown("---")
    ibm_bob_badge()
    st.caption("August AI Builders Challenge")

cme_score = cme_speed * math.cos(math.radians(cme_angle)) if cme_speed > 0 else 0.0

# ── Model + prediction (before hero strip so receipt is artifact-backed) ───────
model, model_name, model_meta = _load_model()
model_loaded = model is not None

if model_loaded:
    X_single, feat_names = build_single_feature_vector(
        kp=kp_input, f10_7=flux_input,
        launch_hour=hour_input,
        day_of_year=datetime.now().timetuple().tm_yday,
        cme_score=cme_score,
        gst_level=gst_input,
        xclass_72h=int(xclass_flag),
        mclass_72h=int(mclass_flag),
        feature_names=model_meta.get("feature_names"),
    )
    try:
        col = positive_class_column(model)
        prob_go = float(model.predict_proba(X_single)[0][col])
    except Exception:
        # An unavailable prediction is reported as unavailable, never as a
        # coin-flip that renders like a real model output.
        prob_go = None
else:
    prob_go   = None
    feat_names = model_meta.get("feature_names") or [
        "kp_3d_avg","kp_7d_avg","flux_3d_avg","flux_7d_avg",
        "kp_lag1","kp_lag3","kp_lag7","xclass_72h","mclass_72h",
        "cme_arrival_score","gst_level","day_sin","day_cos","hour_sin","hour_cos",
    ]
    X_single = None

_banner_prov = load_provenance()
_banner_artifacts_ok = bool(_banner_prov and not _banner_prov.get("note"))
_banner_model_sha = (load_best_model_metadata() or {}).get("sha256")
_banner_inputs = {
    "Kp Index": f"{kp_input:.1f}",
    "F10.7 Flux": f"{flux_input:.0f}",
    "Launch Hour": f"{hour_input:02d}:00",
    "Storm Level": f"G{gst_input}",
    "CME Speed": str(cme_speed),
    "X-flare 72h": "YES" if xclass_flag else "NO",
    "M-flare 72h": "YES" if mclass_flag else "NO",
}
_banner_pkg = build_evidence_package(
    inputs=_banner_inputs,
    source="NASA DONKI / NOAA SWPC",
    model_name=model_name,
    model_sha256=_banner_model_sha,
    score=prob_go if prob_go is not None else None,
    artifacts_ok=_banner_artifacts_ok,
)

# ═══════════════════════════════════════════════════════════════════════════════
# HERO HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div style="padding:1.2rem 0 0.4rem;" aria-label="Dashboard title">
      <div style="font-family:'Orbitron',monospace;font-size:clamp(1.1rem,2.5vw,1.9rem);
                  font-weight:800;letter-spacing:0.1em;color:#E8EDF5;line-height:1.15;">
        AEVION <span style="color:#00D4FF;">SPACEOPS</span>
      </div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:0.78rem;
                  color:#8892A4;letter-spacing:0.06em;margin-top:6px;">
        AI mission-risk decisions with evidence, provenance, and human authority
      </div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;
                  color:#4A5568;letter-spacing:0.2em;margin-top:4px;">
        NASA DONKI · SPACE-WEATHER MODEL AS AN INPUT · HUMAN MISSION AUTHORITY
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_artifact_receipt_banner(
    st,
    model_name=model_name,
    model_sha256=_banner_model_sha,
    provenance=_banner_prov,
    receipt_sha256=_banner_pkg.get("receipt_sha256"),
    verification=_banner_pkg.get("verification"),
)

if model_loaded:
    st.warning("Prototype model artifact: generated from synthetic test data; not operationally qualified.")

prediction_available = prob_go is not None
verdict_txt = (
    "UNAVAILABLE" if not prediction_available
    else "GO" if prob_go >= 0.65 else "HOLD" if prob_go >= 0.40 else "SCRUB"
)
gauge_color = (
    "#4A5568" if not prediction_available
    else "#00FF41" if prob_go >= 0.65 else "#FFD700" if prob_go >= 0.40 else "#FF4444"
)
verdict_cls = {
    "GO":   "swl-verdict-go",
    "HOLD": "swl-verdict-hold",
    "SCRUB":"swl-verdict-scrub",
}.get(verdict_txt, "swl-verdict-hold")
prob_line = (
    "Prototype model score = UNAVAILABLE"
    if not prediction_available
    else f"Prototype model score = {prob_go:.3f}"
)

# ── Live weather fetch ────────────────────────────────────────────────────────
with st.spinner(""):
    weather  = _fetch_weather(nasa_api_key)
summary  = summarise_weather(weather)

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 1 — LIVE CONDITIONS STATUS BAR
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Live Space Weather — NASA DONKI")

c1, c2, c3, c4, c5 = st.columns(5)
orb_color = summary["alert_color"]
orb_map   = {"green":"go","orange":"hold","red":"scrub"}
orb_cls   = f"swl-orb-{orb_map.get(orb_color,'blue')}"

with c1:
    st.metric("X-class Flares",
              summary["x_flare_count"],
              delta=None,
              help="X-class solar flares in past 72 hours")
with c2:
    st.metric("M-class Flares", summary["m_flare_count"],
              help="M-class flares in past 72 hours")
with c3:
    st.metric("CMEs", summary["cme_count"],
              help="Coronal mass ejections in past 72 hours")
with c4:
    st.metric("Geomag Storm", summary["gst_label"],
              help="Maximum geomagnetic storm level")
with c5:
    alert_label = {
        "green": "NOMINAL",
        "orange": "ELEVATED",
        "red": "STORM",
    }[orb_color]
    st.markdown(
        f'<div style="padding-top:0.55rem;">'
        f'<div style="font-size:0.62rem;letter-spacing:0.14em;text-transform:uppercase;'
        f'color:#4A5568;margin-bottom:6px;">STATUS</div>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span class="swl-orb {orb_cls} anim-pulse-go"></span>'
        f'<span style="font-family:var(--font-display,monospace);font-size:0.85rem;'
        f'font-weight:700;color:{gauge_color};">{alert_label}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div style="font-family:var(--font-mono,monospace);font-size:0.62rem;'
    f'color:#4A5568;margin:2px 0 8px;letter-spacing:0.06em;">'
    f'Data: NASA DONKI · Fetched {weather.get("fetched_at","—")[:19].replace("T"," ")} UTC · '
    f'Refreshes every 15 min</div>',
    unsafe_allow_html=True,
)

st.markdown('<div aria-hidden="true" style="border-top:1px solid #1C2640;margin:0.8rem 0;"></div>',
            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 2 — LAUNCH PROBABILITY GAUGE + INPUTS SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
col_gauge, col_params, col_verdict = st.columns([1.2, 1.4, 1])

with col_gauge:
    section_label("Prototype GO Score")
    st.caption(
        "Prototype GO Score — a model score, NOT a calibrated launch-success "
        "probability. The training label is synthetic and independent of the "
        "space-weather features."
    )
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(prob_go * 100, 1),
        number={"suffix":"%", "font":{"size":34, "color":gauge_color,
                                      "family":"Orbitron, monospace"}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickcolor": "#4A5568",
                "tickfont": {"family":"IBM Plex Mono", "size":9},
            },
            "bar":  {"color": gauge_color, "thickness": 0.22},
            "bgcolor": "#0D1220",
            "bordercolor": "#1C2640",
            "borderwidth": 1,
            "steps": [
                {"range": [0,  40], "color": "rgba(255,68,68,0.07)"},
                {"range": [40, 65], "color": "rgba(255,215,0,0.06)"},
                {"range": [65,100], "color": "rgba(0,255,65,0.07)"},
            ],
            "threshold": {
                "line":      {"color": "#4A5568", "width": 1},
                "thickness": 0.6,
                "value":     65,
            },
        },
    ))
    fig_gauge.update_layout(
        **plotly_dark_layout(height=240, margin=dict(l=20, r=20, t=16, b=10))
    )
    st.plotly_chart(fig_gauge, use_container_width=True,
                    config={"displayModeBar": False})

with col_params:
    section_label("Input Parameters")
    params_data = [
        {"Parameter": "Kp Index",     "Value": f"{kp_input:.1f}",  "Unit": "0–9"},
        {"Parameter": "F10.7 Flux",   "Value": f"{flux_input:.0f}","Unit": "sfu"},
        {"Parameter": "Launch Hour",  "Value": f"{hour_input:02d}:00",  "Unit": "UTC"},
        {"Parameter": "Storm Level",  "Value": f"G{gst_input}",    "Unit": "NOAA"},
        {"Parameter": "CME Speed",    "Value": str(cme_speed),     "Unit": "km/s"},
        {"Parameter": "X-flare 72h",  "Value": "YES" if xclass_flag else "NO", "Unit": "—"},
        {"Parameter": "M-flare 72h",  "Value": "YES" if mclass_flag else "NO", "Unit": "—"},
    ]
    telemetry_table(params_data, ["Parameter","Value","Unit"])
    if not model_loaded:
        st.caption("⚠️ Demo mode — train models in notebook 04 for live predictions")

with col_verdict:
    section_label("Mission Verdict")
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'justify-content:center;height:180px;gap:16px;">'
        f'<div class="swl-verdict {verdict_cls}" style="font-size:1.1rem;padding:0.6rem 1.4rem;">'
        f'<span class="swl-orb {orb_cls}"></span>{verdict_txt}</div>'
        f'<div style="font-family:var(--font-mono,monospace);font-size:0.68rem;'
        f'color:#4A5568;text-align:center;">{prob_line}</div>'
        f'<div style="font-family:var(--font-mono,monospace);font-size:0.62rem;'
        f'color:#4A5568;text-align:center;">SELECTED MODEL: {model_name or "UNAVAILABLE"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div aria-hidden="true" style="border-top:1px solid #1C2640;margin:0.8rem 0;"></div>',
            unsafe_allow_html=True)

# ── Evidence-gated mission decision ───────────────────────────────────────────
# The model score is an input. What the product emits is a policy state with the
# evidence that produced it, and a human holds the decision.
section_label("Mission Decision — Evidence Gated")
render_decision_chain(st, active="POLICY CHECK")

_prov = _banner_prov
_artifacts_ok = _banner_artifacts_ok
_model_sha = _banner_model_sha
_decision = policy_check(prob_go if prediction_available else None, _artifacts_ok)
render_policy_state(st, _decision)

_pkg = _banner_pkg
render_evidence_drawer(st, _pkg)
st.caption(HUMAN_AUTHORITY_NOTICE)

st.markdown('<div aria-hidden="true" style="border-top:1px solid #1C2640;margin:0.8rem 0;"></div>',
            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 3 — KP TIME SERIES
# ═══════════════════════════════════════════════════════════════════════════════
col_ts, col_fi = st.columns([1.6, 1])

with col_ts:
    section_label("Historical Kp Index · Launch Events")
    kp_hist = load_kp_history()
    kp_hist["date"] = pd.to_datetime(kp_hist["date"], utc=True)
    mask = (
        (kp_hist["date"] >= pd.Timestamp(start_date, tz="UTC")) &
        (kp_hist["date"] <= pd.Timestamp(end_date,   tz="UTC"))
    )
    view = kp_hist[mask] if mask.any() else kp_hist.tail(90)

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=view["date"], y=view["kp_mean"],
        name="Kp Index",
        fill="tozeroy",
        line=dict(color="#00D4FF", width=1.5),
        fillcolor="rgba(0,212,255,0.06)",
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Kp: %{y:.2f}<extra></extra>",
    ))
    for lvl, color_, label_ in [(5,"#FF6B35","G1 Storm"), (7,"#FF4444","G3 Severe")]:
        fig_ts.add_hline(
            y=lvl, line_dash="dot", line_color=color_,
            annotation_text=label_,
            annotation_position="top right",
            annotation_font=dict(color=color_, size=10, family="IBM Plex Mono"),
        )

    launches_view = view.dropna(subset=["launch_go"])
    go_ev    = launches_view[launches_view["launch_go"] == 1]
    scrub_ev = launches_view[launches_view["launch_go"] == 0]

    if not go_ev.empty:
        fig_ts.add_trace(go.Scatter(
            x=go_ev["date"], y=[0.4]*len(go_ev), mode="markers",
            name="GO", marker=dict(symbol="triangle-up", size=9, color="#00FF41",
                                   line=dict(color="#080B14", width=1)),
            hovertemplate="<b>GO</b><br>%{x|%Y-%m-%d}<extra></extra>",
        ))
    if not scrub_ev.empty:
        fig_ts.add_trace(go.Scatter(
            x=scrub_ev["date"], y=[0.2]*len(scrub_ev), mode="markers",
            name="SCRUB", marker=dict(symbol="x", size=8, color="#FF4444"),
            hovertemplate="<b>SCRUB</b><br>%{x|%Y-%m-%d}<extra></extra>",
        ))

    fig_ts.update_layout(**plotly_dark_layout(
        height=300,
        xaxis_title="Date",
        yaxis_title="Kp Index",
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10)),
    ))
    st.plotly_chart(fig_ts, use_container_width=True,
                    config={"displayModeBar": False})

with col_fi:
    section_label("Feature Importance")
    meta = load_best_model_metadata()
    fi_names = meta.get("feature_names") or feat_names

    # Importances come from the fitted estimator or are declared UNAVAILABLE.
    # The previous synthetic fallback published invented numbers under a real
    # axis label, which is a fabricated measurement.
    fi_state = feature_importance_state(model, fi_names)

    if fi_state["status"] != "OK":
        st.info(
            "Feature Importance UNAVAILABLE — no importance vector could be "
            "derived from the loaded model, so none is shown."
        )
        vals, labels = None, None
    else:
        _v = np.asarray(fi_state["values"], dtype=float)
        idx    = np.argsort(_v)[::-1][:10]
        vals   = _v[idx]
        labels = [fi_state["names"][i] for i in idx]

    if labels is not None:
        fig_fi = go.Figure(go.Bar(
            x=vals, y=labels, orientation="h",
            marker=dict(
                color=vals,
                colorscale=[[0,"#1C2640"],[0.4,"#00D4FF"],[1.0,"#00FF41"]],
                showscale=False,
                line=dict(color="#0D1220", width=0.5),
            ),
            hovertemplate="<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>",
        ))
        fig_fi.update_layout(**plotly_dark_layout(
            height=300,
            xaxis_title="Importance",
            yaxis=dict(autorange="reversed", gridcolor="#1C2640",
                       linecolor="#1C2640", tickcolor="#4A5568"),
        ))
        st.plotly_chart(fig_fi, use_container_width=True,
                        config={"displayModeBar": False})
        st.caption(f"Source: {fi_state['source']}")

st.markdown('<div aria-hidden="true" style="border-top:1px solid #1C2640;margin:0.8rem 0;"></div>',
            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 4 — SHAP EXPLANATION + DATA PROVENANCE
# ═══════════════════════════════════════════════════════════════════════════════
col_shap, col_prov = st.columns([1, 1])

with col_shap:
    section_label("SHAP Explanation · Current Prediction")
    shap_computed = False

    _exp = explainer_state(model)
    if _exp["available"] and X_single is not None:
        explainer = _load_explainer(model_name)
        if explainer is not None:
            try:
                sv = explainer.shap_values(X_single)
                if isinstance(sv, list):
                    sv = sv[1]
                top_shap = shap_top_n(sv[0], feat_names, n=7)
                max_abs  = max(abs(d["shap_value"]) for d in top_shap) or 1.0
                shap_bar_chart(top_shap, max_abs=max_abs)
                shap_computed = True
            except Exception:
                pass

    if shap_computed:
        st.caption("▲ Green = increases the score · ▼ Red = decreases it")
    else:
        # No hardcoded SHAP vector: those numbers were never computed from this
        # model, and presenting them as an explanation is a fabricated attribution.
        st.info(
            f"SHAP explanation UNAVAILABLE — {_exp['reason']}. "
            "No attribution values are shown."
        )

with col_prov:
    section_label("Data Provenance")
    prov = load_provenance()
    if "note" not in prov:
        prov_rows = [
            {"Field": k, "Value": str(v)[:60]}
            for k, v in prov.items()
            if k not in ("schema_version",)
        ]
        telemetry_table(prov_rows, ["Field","Value"])
    else:
        st.info(prov["note"])

    st.markdown("<br>", unsafe_allow_html=True)
    section_label("Model Metadata")
    metrics_sum = load_metrics_summary()
    if "note" not in metrics_sum:
        # Champion identity comes from the shared selector so HOME, Model Lab
        # and the Prediction Explorer cannot disagree about the served model.
        best_name = load_selected_model_name() or metrics_sum.get("best_model", "—")
        st.markdown(
            f'<div style="font-family:var(--font-mono,monospace);font-size:0.72rem;'
            f'color:#4A5568;margin-bottom:8px;">Best model: '
            f'<span style="color:#00D4FF;">{best_name}</span></div>',
            unsafe_allow_html=True,
        )
        for m in metrics_sum.get("metrics", []):
            with st.expander(m.get("model","?"), expanded=False):
                mrows = [
                    {"Metric": k.upper(), "Score": f"{v:.4f}"}
                    for k, v in m.items()
                    if k != "model" and isinstance(v, (int, float))
                ]
                if mrows:
                    telemetry_table(mrows, ["Metric","Score"], color_col="Score")
    else:
        st.info(metrics_sum["note"])

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="text-align:center;padding:1.5rem 0 0.5rem;'
    'font-family:var(--font-mono,monospace);font-size:0.65rem;'
    'color:#4A5568;letter-spacing:0.1em;">'
    'SPACE WEATHER LAUNCH PROBABILITY DASHBOARD · '
    'AUGUST AI BUILDERS CHALLENGE WITH IBM BOB · '
    'NASA DONKI / NOAA SWPC'
    '</div>',
    unsafe_allow_html=True,
)
