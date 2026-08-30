"""
Dashboard utility helpers — live NASA DONKI fetch, SHAP top-N, etc.
IBM Bob generated — Phase 5.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

MODELS_DIR = Path(__file__).parent.parent / "models"
PROC_DIR   = Path(__file__).parent.parent / "data" / "processed"
BASE_DONKI = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get"


def live_space_weather(api_key: str = "DEMO_KEY", lookback_days: int = 3) -> dict:
    """Fetch current space weather from DONKI (cached 15 min via Streamlit)."""
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    params = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate":   end.strftime("%Y-%m-%d"),
        "api_key":   api_key,
    }
    result: dict[str, Any] = {"fetched_at": end.isoformat()}
    for etype, endpoint in [("FLR", "/FLR"), ("CME", "/CME"), ("GST", "/GST")]:
        try:
            r = requests.get(BASE_DONKI + endpoint, params=params, timeout=15)
            r.raise_for_status()
            result[etype] = r.json() or []
        except Exception as exc:
            result[etype] = []
            result[f"{etype}_error"] = str(exc)
    return result


def summarise_weather(weather: dict) -> dict:
    """Return a plain-English summary dict from live_space_weather output."""
    flares = weather.get("FLR", [])
    cmes   = weather.get("CME", [])
    gsts   = weather.get("GST", [])

    x_flares = [f for f in flares if isinstance(f, dict)
                and str(f.get("classType","")).startswith("X")]
    m_flares = [f for f in flares if isinstance(f, dict)
                and str(f.get("classType","")).startswith("M")]
    storm_level = 0
    for g in gsts:
        if isinstance(g, dict):
            for kp_entry in (g.get("allKpIndex") or []):
                if isinstance(kp_entry, dict):
                    try:
                        kp_val = float(kp_entry.get("kpIndex", 0))
                        lvl = 0
                        if kp_val >= 9: lvl=5
                        elif kp_val >= 8: lvl=4
                        elif kp_val >= 7: lvl=3
                        elif kp_val >= 6: lvl=2
                        elif kp_val >= 5: lvl=1
                        storm_level = max(storm_level, lvl)
                    except (ValueError, TypeError):
                        pass

    return {
        "x_flare_count": len(x_flares),
        "m_flare_count": len(m_flares),
        "cme_count": len(cmes),
        "gst_level": storm_level,
        "gst_label": f"G{storm_level}" if storm_level > 0 else "None",
        "alert_color": "red" if x_flares or storm_level >= 3
                       else "orange" if m_flares or storm_level >= 1
                       else "green",
    }


def build_single_feature_vector(
    kp: float,
    f10_7: float,
    launch_hour: int,
    day_of_year: int,
    cme_score: float = 0.0,
    gst_level: int = 0,
    xclass_72h: int = 0,
    mclass_72h: int = 0,
    feature_names: list[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    """
    Build a single-row feature vector matching the training schema.
    Returns (X, feature_names).
    """
    import math

    names = feature_names or [
        "kp_3d_avg", "kp_7d_avg",
        "flux_3d_avg", "flux_7d_avg",
        "kp_lag1", "kp_lag3", "kp_lag7",
        "xclass_72h", "mclass_72h",
        "cme_arrival_score",
        "gst_level",
        "day_sin", "day_cos",
        "hour_sin", "hour_cos",
    ]
    day_sin  = math.sin(2 * math.pi * day_of_year / 365.25)
    day_cos  = math.cos(2 * math.pi * day_of_year / 365.25)
    hour_sin = math.sin(2 * math.pi * launch_hour / 24)
    hour_cos = math.cos(2 * math.pi * launch_hour / 24)

    values = {
        "kp_3d_avg":          kp,
        "kp_7d_avg":          kp,
        "flux_3d_avg":        f10_7,
        "flux_7d_avg":        f10_7,
        "kp_lag1":            kp,
        "kp_lag3":            kp,
        "kp_lag7":            kp,
        "xclass_72h":         float(xclass_72h),
        "mclass_72h":         float(mclass_72h),
        "cme_arrival_score":  cme_score,
        "gst_level":          float(gst_level),
        "day_sin":            day_sin,
        "day_cos":            day_cos,
        "hour_sin":           hour_sin,
        "hour_cos":           hour_cos,
    }
    vec = np.array([[values.get(n, 0.0) for n in names]], dtype=float)
    return vec, names


def shap_top_n(shap_values: np.ndarray, feature_names: list[str], n: int = 5) -> list[dict]:
    """Return top-N |SHAP| contributors as list of {feature, shap_value} dicts."""
    sv = np.array(shap_values).flatten()
    idx = np.argsort(np.abs(sv))[::-1][:n]
    return [{"feature": feature_names[i], "shap_value": float(sv[i])} for i in idx]


def load_provenance() -> dict:
    p = PROC_DIR / "FEATURE_PROVENANCE.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"note": "FEATURE_PROVENANCE.json not yet generated — run notebook 03."}


def load_metrics_summary() -> dict:
    p = MODELS_DIR / "metrics_summary.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"note": "metrics_summary.json not yet generated — run notebook 04."}


def load_best_model_metadata() -> dict:
    summary = load_metrics_summary()
    best_name = summary.get("best_model")
    if best_name:
        p = MODELS_DIR / f"{best_name}_metadata.json"
        if p.exists():
            return json.loads(p.read_text())
    return {}


def load_kp_history() -> pd.DataFrame:
    """Load daily Kp history from processed parquet if available."""
    p = PROC_DIR / "daily_master.parquet"
    if p.exists():
        df = pd.read_parquet(p)
        if "kp_mean" in df.columns and "date" in df.columns:
            return df[["date", "kp_mean", "launch_go"]].copy()
    # Fallback: synthetic
    rng = np.random.default_rng(0)
    dates = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=180, freq="D")
    return pd.DataFrame({
        "date": dates,
        "kp_mean": rng.uniform(0, 9, 180),
        "launch_go": np.where(rng.random(180) < 0.14,
                              rng.choice([0, 1], 180, p=[0.3, 0.7]),
                              np.nan),
    })
