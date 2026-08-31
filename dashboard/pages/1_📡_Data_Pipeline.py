"""
Page: Data Pipeline Monitor
Displays ingestion status, raw data samples, EDA charts.
IBM Bob generated — Frontend Phase.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.theme import (
    inject_design_system, section_label, telemetry_table, plotly_dark_layout
)
# Canonical anchors. This page previously derived RAW_DIR/PROC_DIR from its own
# location, which resolves one directory too high and made it report every
# artifact MISSING while HOME simultaneously displayed those same artifacts.
from dashboard.components.utils import PROC_DIR, RAW_DIR

st.set_page_config(
    page_title="SWL · Data Pipeline",
    page_icon="📡",
    layout="wide",
)
inject_design_system()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-family:Orbitron,monospace;font-size:1.4rem;font-weight:800;'
    'letter-spacing:0.1em;color:#E8EDF5;padding:0.6rem 0 0.2rem;">'
    'DATA <span style="color:#00D4FF;">PIPELINE</span></div>'
    '<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
    'color:#4A5568;letter-spacing:0.2em;">INGESTION · EDA · PROVENANCE</div>',
    unsafe_allow_html=True,
)
st.markdown('<hr style="border-color:#1C2640;margin:0.6rem 0 1rem;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# INGESTION STATUS
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Ingestion Status")

EVENT_TYPES = ["FLR","CME","GST","SEP"]
col_status = st.columns(len(EVENT_TYPES) + 2)

status_rows = []
for i, etype in enumerate(EVENT_TYPES):
    files = sorted(RAW_DIR.glob(f"donki_{etype.lower()}_*.json"), reverse=True) if RAW_DIR.exists() else []
    found  = bool(files)
    size   = f"{files[0].stat().st_size:,} B" if found else "—"
    ts     = files[0].stat().st_mtime if found else None
    status = "✓ CACHED" if found else "○ MISSING"
    color  = "#00FF41" if found else "#FF4444"
    with col_status[i]:
        st.markdown(
            f'<div style="background:#0D1220;border:1px solid #1C2640;border-radius:6px;'
            f'padding:0.8rem;text-align:center;">'
            f'<div style="font-family:Orbitron,monospace;font-size:0.75rem;'
            f'font-weight:700;color:#8892A4;letter-spacing:0.1em;">{etype}</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.85rem;'
            f'font-weight:600;color:{color};margin:4px 0;">{status}</div>'
            f'<div style="font-size:0.62rem;color:#4A5568;">{size}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    status_rows.append({"Type": etype, "Status": status, "Size": size})

# KP / Flux
for label, glob_name, idx in [("KP_1M","swpc_kp_1m.json",4), ("F10.7","swpc_solar_cycle_indices.json",5)]:
    p = RAW_DIR / glob_name if RAW_DIR.exists() else Path("/nonexistent")
    found = p.exists()
    color = "#00FF41" if found else "#FF4444"
    size  = f"{p.stat().st_size:,} B" if found else "—"
    with col_status[idx]:
        st.markdown(
            f'<div style="background:#0D1220;border:1px solid #1C2640;border-radius:6px;'
            f'padding:0.8rem;text-align:center;">'
            f'<div style="font-family:Orbitron,monospace;font-size:0.75rem;'
            f'font-weight:700;color:#8892A4;letter-spacing:0.1em;">{label}</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.85rem;'
            f'font-weight:600;color:{color};margin:4px 0;">'
            f'{"✓ CACHED" if found else "○ MISSING"}</div>'
            f'<div style="font-size:0.62rem;color:#4A5568;">{size}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Ingest manifest ───────────────────────────────────────────────────────────
manifest_p = RAW_DIR / "ingest_manifest.json" if RAW_DIR.exists() else Path("/nonexistent")
if manifest_p.exists():
    with st.expander("📋 Ingest Manifest", expanded=False):
        manifest = json.loads(manifest_p.read_text())
        st.markdown(
            f'<div style="font-size:0.72rem;color:#4A5568;font-family:IBM Plex Mono,monospace;">'
            f'Ingested: {manifest.get("ingested_at","—")[:19].replace("T"," ")} UTC · '
            f'{manifest.get("start_date","—")} → {manifest.get("end_date","—")}</div>',
            unsafe_allow_html=True,
        )
        mrows = [
            {"Source": k, "SHA-256 (16ch)": v.get("sha256","")[:16]+"…",
             "Path": Path(v.get("path","")).name}
            for k, v in manifest.get("files", {}).items()
        ]
        if mrows:
            telemetry_table(mrows, ["Source","SHA-256 (16ch)","Path"])
else:
    # The MISSING rows above are real and are deliberately not suppressed. They
    # refer to the RAW DONKI/SWPC pulls, which are not committed to the repo.
    # The PROCESSED feature artifact that HOME's provenance record describes is
    # a different artifact and is present — stating both prevents a reader from
    # concluding that one of the two pages is lying.
    st.info(
        "No ingest manifest found — the RAW NASA DONKI / NOAA SWPC pulls listed above "
        "are genuinely absent from this checkout (they are not committed). "
        "Run notebook 01 with a NASA API key to fetch them.\n\n"
        "This is NOT a path-resolution problem: this page and the Home page resolve the "
        "same artifact root (`dashboard/data/`). The PROCESSED feature artifact "
        "described by the Home provenance record is a different artifact class and is "
        "present — see Feature Provenance below."
    )

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE PROVENANCE
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Feature Provenance")

prov_p = PROC_DIR / "FEATURE_PROVENANCE.json" if PROC_DIR.exists() else Path("/nonexistent")
if prov_p.exists():
    prov = json.loads(prov_p.read_text())
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Rows",     prov.get("row_count","—"))
    p2.metric("Features", prov.get("feature_count","—"))
    p3.metric("Labeled",  prov.get("labeled_row_count","—"))
    p4.metric("Version",  f"v{prov.get('version','?')}")

    sha = prov.get("sha256","")
    st.markdown(
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
        f'color:#4A5568;margin:6px 0;">SHA-256: <span style="color:#00D4FF;">{sha}</span></div>'
        f'<div style="font-size:0.62rem;color:#4A5568;">File: {prov.get("filename","—")} · '
        f'Created: {prov.get("created_at","—")[:19].replace("T"," ")} UTC · '
        f'IBM Bob assisted: {prov.get("ibm_bob_assisted","—")}</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("FEATURE_PROVENANCE.json not found. Run notebook 03 to build feature matrix.")

st.markdown('<hr style="border-color:#1C2640;margin:0.8rem 0;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# EDA CHARTS
# ═══════════════════════════════════════════════════════════════════════════════
section_label("Exploratory Data Analysis")

master_p = PROC_DIR / "daily_master.parquet" if PROC_DIR.exists() else Path("/nonexistent")
if master_p.exists():
    master = pd.read_parquet(master_p)
    master["date"] = pd.to_datetime(master["date"], utc=True, errors="coerce")

    col_eda1, col_eda2 = st.columns(2)

    with col_eda1:
        section_label("Kp Index Distribution")
        if "kp_mean" in master.columns:
            fig_kp = go.Figure(go.Histogram(
                x=master["kp_mean"].dropna(),
                nbinsx=30,
                marker=dict(color="#00D4FF", line=dict(color="#080B14", width=0.5)),
                opacity=0.85,
                hovertemplate="Kp %{x:.1f}–%{x:.1f}: %{y} days<extra></extra>",
            ))
            fig_kp.update_layout(**plotly_dark_layout(
                height=250, xaxis_title="Kp Index", yaxis_title="Count",
            ))
            st.plotly_chart(fig_kp, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.info("kp_mean column not in daily master.")

    with col_eda2:
        section_label("F10.7 Solar Flux Distribution")
        if "f10_7" in master.columns:
            fig_flux = go.Figure(go.Histogram(
                x=master["f10_7"].dropna(),
                nbinsx=30,
                marker=dict(color="#FF6B35", line=dict(color="#080B14", width=0.5)),
                opacity=0.85,
                hovertemplate="F10.7 %{x:.0f}: %{y} days<extra></extra>",
            ))
            fig_flux.update_layout(**plotly_dark_layout(
                height=250, xaxis_title="F10.7 (sfu)", yaxis_title="Count",
            ))
            st.plotly_chart(fig_flux, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.info("f10_7 column not in daily master.")

    # Kp over time
    section_label("Kp Index Time Series (full history)")
    if "kp_mean" in master.columns:
        fig_full = go.Figure()
        fig_full.add_trace(go.Scatter(
            x=master["date"], y=master["kp_mean"],
            line=dict(color="#00D4FF", width=1.2),
            fill="tozeroy", fillcolor="rgba(0,212,255,0.05)",
            name="Kp (daily mean)",
            hovertemplate="%{x|%Y-%m-%d}: Kp=%{y:.2f}<extra></extra>",
        ))
        fig_full.add_hline(y=5, line_dash="dot", line_color="#FF6B35",
                           annotation_text="G1 Threshold",
                           annotation_font=dict(color="#FF6B35", size=9))
        fig_full.update_layout(**plotly_dark_layout(
            height=200, xaxis_title="Date", yaxis_title="Kp",
        ))
        st.plotly_chart(fig_full, use_container_width=True,
                        config={"displayModeBar": False})

    # Null analysis
    with st.expander("🔬 Null Analysis", expanded=False):
        null_pct = (master.isnull().sum() / len(master) * 100).round(1)
        null_df  = null_pct.reset_index()
        null_df.columns = ["Column", "Null %"]
        telemetry_table(null_df.to_dict("records"), ["Column","Null %"])

else:
    st.info(
        "Daily master parquet not found. Run notebooks 01 and 02 to ingest and clean data, "
        "then refresh this page."
    )
    # Synthetic demo charts
    section_label("Demo Charts (synthetic data)")
    rng = np.random.default_rng(1)
    dates = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=365, freq="D")
    kp_syn  = rng.uniform(0, 9, 365)
    fl_syn  = rng.uniform(70, 220, 365)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        fig_d = go.Figure(go.Histogram(
            x=kp_syn, nbinsx=25,
            marker=dict(color="#00D4FF", line=dict(color="#080B14", width=0.5)),
            hovertemplate="Kp %{x:.1f}: %{y} days<extra></extra>",
        ))
        fig_d.update_layout(**plotly_dark_layout(
            height=220, xaxis_title="Kp Index (synthetic)", yaxis_title="Count",
        ))
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})
    with col_d2:
        fig_d2 = go.Figure(go.Histogram(
            x=fl_syn, nbinsx=25,
            marker=dict(color="#FF6B35", line=dict(color="#080B14", width=0.5)),
            hovertemplate="F10.7 %{x:.0f}: %{y} days<extra></extra>",
        ))
        fig_d2.update_layout(**plotly_dark_layout(
            height=220, xaxis_title="F10.7 sfu (synthetic)", yaxis_title="Count",
        ))
        st.plotly_chart(fig_d2, use_container_width=True, config={"displayModeBar": False})

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:1rem 0 0;font-family:IBM Plex Mono,monospace;'
    'font-size:0.62rem;color:#4A5568;letter-spacing:0.1em;">'
    'SWL DATA PIPELINE · NASA DONKI API · NOAA SWPC</div>',
    unsafe_allow_html=True,
)
