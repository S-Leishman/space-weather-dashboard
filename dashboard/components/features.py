"""
Feature engineering pipeline for the Space Weather Launch Probability Dashboard.
IBM Bob generated — Phase 3.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROC_DIR = Path(__file__).parent.parent / "data" / "processed"
RAW_DIR  = Path(__file__).parent.parent / "data" / "raw"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cyclical_encode(series: pd.Series, period: float) -> tuple[pd.Series, pd.Series]:
    """Return (sin, cos) cyclical encoding for a numeric series with given period."""
    rad = 2 * math.pi * series / period
    return np.sin(rad), np.cos(rad)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ─── Core transform ───────────────────────────────────────────────────────────

def build_feature_matrix(
    daily_master: pd.DataFrame,
    flr_df: pd.DataFrame | None = None,
    cme_df: pd.DataFrame | None = None,
    gst_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Construct the full feature matrix from a daily master DataFrame.

    Expected columns in daily_master:
        date (datetime64[ns, UTC])
        kp_mean          (float) — daily mean Kp index
        f10_7            (float) — daily F10.7 solar flux
        launch_go        (int)   — target label (1=GO, 0=SCRUB/HOLD), may be NaN
        launch_window_utc (str)  — e.g. "14:00"

    Returns a DataFrame with all engineered features and a 'launch_go' column.
    """
    df = daily_master.copy()

    # Ensure date is UTC datetime
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").reset_index(drop=True)

    # ── Rolling averages ──────────────────────────────────────────────────────
    for col, out in [("kp_mean", "kp"), ("f10_7", "flux")]:
        if col in df.columns:
            df[f"{out}_3d_avg"] = df[col].rolling(3, min_periods=1).mean()
            df[f"{out}_7d_avg"] = df[col].rolling(7, min_periods=1).mean()
        else:
            df[f"{out}_3d_avg"] = np.nan
            df[f"{out}_7d_avg"] = np.nan

    # ── Lag features ─────────────────────────────────────────────────────────
    for lag in [1, 3, 7]:
        if "kp_mean" in df.columns:
            df[f"kp_lag{lag}"] = df["kp_mean"].shift(lag)
        else:
            df[f"kp_lag{lag}"] = np.nan

    # ── Flare flags from DONKI FLR ────────────────────────────────────────────
    df["xclass_72h"] = 0
    df["mclass_72h"] = 0

    if flr_df is not None and not flr_df.empty:
        class_col = next((c for c in flr_df.columns if "class" in c.lower()), None)
        time_col  = next((c for c in flr_df.columns if "begin" in c.lower() or "time" in c.lower()), None)

        if class_col and time_col:
            flr = flr_df[[time_col, class_col]].copy()
            flr["_ts"] = pd.to_datetime(flr[time_col], utc=True, errors="coerce")
            flr["_cls"] = flr[class_col].astype(str).str[0].str.upper()
            flr = flr.dropna(subset=["_ts"])

            for idx, row in df.iterrows():
                window_start = row["date"] - pd.Timedelta(hours=72)
                window_end   = row["date"]
                in_window = flr[(flr["_ts"] >= window_start) & (flr["_ts"] <= window_end)]
                df.at[idx, "xclass_72h"] = int((in_window["_cls"] == "X").any())
                df.at[idx, "mclass_72h"] = int((in_window["_cls"] == "M").any())

    # ── CME arrival probability score ─────────────────────────────────────────
    df["cme_arrival_score"] = 0.0

    if cme_df is not None and not cme_df.empty:
        # Try to extract speed and half-angle from cmeAnalyses nested list
        speeds, half_angles, times = [], [], []
        start_col = next((c for c in cme_df.columns if "start" in c.lower() or "time" in c.lower()), None)
        for _, row in cme_df.iterrows():
            ts_raw = row.get(start_col) if start_col else None
            analyses = row.get("cmeAnalyses") or []
            if isinstance(analyses, list):
                for a in analyses:
                    if isinstance(a, dict):
                        spd = a.get("speed")
                        ha  = a.get("halfAngle")
                        if spd and ts_raw:
                            try:
                                speeds.append(float(spd))
                                half_angles.append(float(ha) if ha else 45.0)
                                times.append(pd.to_datetime(ts_raw, utc=True, errors="coerce"))
                            except (ValueError, TypeError):
                                pass

        if speeds:
            cme_feat = pd.DataFrame({
                "_ts": times,
                "_speed": speeds,
                "_ha": half_angles,
            }).dropna(subset=["_ts"])
            cme_feat["_score"] = cme_feat["_speed"] * np.cos(np.radians(cme_feat["_ha"]))

            for idx, row in df.iterrows():
                window_start = row["date"] - pd.Timedelta(days=5)
                window_end   = row["date"]
                in_window = cme_feat[(cme_feat["_ts"] >= window_start) & (cme_feat["_ts"] <= window_end)]
                if not in_window.empty:
                    df.at[idx, "cme_arrival_score"] = float(in_window["_score"].max())

    # ── Geomagnetic storm level ────────────────────────────────────────────────
    df["gst_level"] = 0

    if gst_df is not None and not gst_df.empty:
        kp_col    = next((c for c in gst_df.columns if "kp" in c.lower()), None)
        time_col  = next((c for c in gst_df.columns if "start" in c.lower() or "time" in c.lower()), None)

        def _kp_to_g(kp_val: float) -> int:
            if kp_val >= 9: return 5
            if kp_val >= 8: return 4
            if kp_val >= 7: return 3
            if kp_val >= 6: return 2
            if kp_val >= 5: return 1
            return 0

        if time_col:
            gst = gst_df.copy()
            gst["_ts"] = pd.to_datetime(gst[time_col], utc=True, errors="coerce")

            # allKpIndex may be nested list of dicts
            if "allKpIndex" in gst.columns:
                gst_scores = []
                for _, row in gst.iterrows():
                    kp_list = row.get("allKpIndex") or []
                    if isinstance(kp_list, list) and kp_list:
                        max_kp = max((float(k.get("kpIndex", 0)) for k in kp_list if isinstance(k, dict)), default=0)
                    else:
                        max_kp = 0
                    gst_scores.append((row["_ts"], _kp_to_g(max_kp)))

                for idx, row in df.iterrows():
                    day_storms = [g for ts, g in gst_scores
                                  if ts and ts.normalize() == row["date"]]
                    if day_storms:
                        df.at[idx, "gst_level"] = max(day_storms)

    # ── Cyclical encodings ────────────────────────────────────────────────────
    df["day_of_year"] = df["date"].dt.day_of_year
    df["day_sin"], df["day_cos"] = _cyclical_encode(df["day_of_year"], 365.25)

    # Launch hour
    def _parse_hour(s: str) -> float:
        try:
            return float(str(s).split(":")[0])
        except (ValueError, AttributeError):
            return 12.0  # default noon

    if "launch_window_utc" in df.columns:
        df["launch_hour"] = df["launch_window_utc"].apply(_parse_hour)
    else:
        df["launch_hour"] = 12.0

    df["hour_sin"], df["hour_cos"] = _cyclical_encode(df["launch_hour"], 24.0)

    # ── Final cleanup ─────────────────────────────────────────────────────────
    feature_cols = [
        "kp_3d_avg", "kp_7d_avg",
        "flux_3d_avg", "flux_7d_avg",
        "kp_lag1", "kp_lag3", "kp_lag7",
        "xclass_72h", "mclass_72h",
        "cme_arrival_score",
        "gst_level",
        "day_sin", "day_cos",
        "hour_sin", "hour_cos",
    ]
    existing_features = [c for c in feature_cols if c in df.columns]
    out_cols = ["date"] + existing_features
    if "launch_go" in df.columns:
        out_cols.append("launch_go")

    result = df[out_cols].copy()
    result[existing_features] = result[existing_features].astype(float)
    return result


# ─── Save + provenance ────────────────────────────────────────────────────────

def save_features(features: pd.DataFrame, version: int = 1) -> dict:
    """Save feature matrix as Parquet and write FEATURE_PROVENANCE.json."""
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"features_v{version}.parquet"
    dest = PROC_DIR / filename
    features.to_parquet(dest, index=False)

    raw_bytes = dest.read_bytes()
    digest = _sha256_bytes(raw_bytes)
    target_col = "launch_go"
    labeled_rows = int(features[target_col].notna().sum()) if target_col in features.columns else 0

    provenance = {
        "filename": filename,
        "sha256": digest,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_count": len([c for c in features.columns if c not in ("date", "launch_go")]),
        "row_count": len(features),
        "labeled_row_count": labeled_rows,
        "ibm_bob_assisted": True,
        "version": version,
        "schema_version": "aevion.feature-provenance.v1",
    }
    prov_path = PROC_DIR / "FEATURE_PROVENANCE.json"
    prov_path.write_text(json.dumps(provenance, indent=2))
    print(f"[features] saved → {dest}  ({len(features)} rows, {provenance['feature_count']} features)")
    print(f"[provenance] sha256={digest[:24]}…")
    print(f"[provenance] {prov_path}")
    return provenance
