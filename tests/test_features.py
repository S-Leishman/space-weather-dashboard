"""
Unit tests for dashboard/components/features.py
IBM Bob generated — Phase 6.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components.features import build_feature_matrix, save_features


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def synthetic_master():
    """Minimal daily master DataFrame for testing."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2024-01-01", "2024-03-31", freq="D", tz="UTC")
    return pd.DataFrame({
        "date":              dates,
        "kp_mean":           rng.uniform(0, 9, len(dates)),
        "f10_7":             rng.uniform(70, 200, len(dates)),
        "launch_go":         np.where(rng.random(len(dates)) < 0.15,
                                      rng.choice([0,1], len(dates)), np.nan),
        "launch_window_utc": [f"{rng.integers(0,24):02d}:00" for _ in dates],
    })


@pytest.fixture
def tmp_proc_dir(tmp_path):
    d = tmp_path / "processed"
    d.mkdir()
    return d


# ─── Happy path ───────────────────────────────────────────────────────────────

def test_build_feature_matrix_shape(synthetic_master):
    """Feature matrix has expected columns and no more rows than master."""
    features = build_feature_matrix(synthetic_master)
    assert len(features) == len(synthetic_master)
    # Must have at least the cyclical columns
    assert "day_sin" in features.columns
    assert "day_cos" in features.columns
    assert "hour_sin" in features.columns
    assert "hour_cos" in features.columns


def test_rolling_averages_are_finite(synthetic_master):
    """kp_3d_avg and kp_7d_avg should be finite floats."""
    features = build_feature_matrix(synthetic_master)
    assert features["kp_3d_avg"].notna().all()
    assert features["kp_7d_avg"].notna().all()


def test_cyclical_encoding_bounds(synthetic_master):
    """sin/cos encodings are always in [-1, 1]."""
    features = build_feature_matrix(synthetic_master)
    for col in ("day_sin", "day_cos", "hour_sin", "hour_cos"):
        vals = features[col].dropna().values
        assert (vals >= -1.0).all() and (vals <= 1.0).all(), f"{col} out of range"


def test_save_features_writes_parquet_and_provenance(synthetic_master, tmp_proc_dir, monkeypatch):
    """save_features writes a parquet file and a valid FEATURE_PROVENANCE.json."""
    monkeypatch.setattr("dashboard.components.features.PROC_DIR", tmp_proc_dir)
    features = build_feature_matrix(synthetic_master)
    prov = save_features(features, version=99)

    assert (tmp_proc_dir / "features_v99.parquet").exists()
    assert (tmp_proc_dir / "FEATURE_PROVENANCE.json").exists()
    assert prov["ibm_bob_assisted"] is True
    assert prov["row_count"] == len(features)
    assert len(prov["sha256"]) == 64


# ─── Edge case ────────────────────────────────────────────────────────────────

def test_build_feature_matrix_empty_event_dfs(synthetic_master):
    """Passing empty event DataFrames must not crash and should zero-fill flags."""
    features = build_feature_matrix(
        synthetic_master,
        flr_df=pd.DataFrame(),
        cme_df=pd.DataFrame(),
        gst_df=pd.DataFrame(),
    )
    assert (features["xclass_72h"] == 0).all()
    assert (features["mclass_72h"] == 0).all()
    assert (features["cme_arrival_score"] == 0.0).all()
    assert (features["gst_level"] == 0).all()


def test_lag_features_shift_correctly(synthetic_master):
    """kp_lag1 on row i should equal kp_mean on row i-1."""
    synthetic_master_clean = synthetic_master.copy()
    synthetic_master_clean["launch_window_utc"] = "12:00"
    features = build_feature_matrix(synthetic_master_clean)
    if "kp_lag1" in features.columns and len(features) > 2:
        # Row 2 lag1 should equal row 1 kp_mean
        expected = synthetic_master_clean.iloc[1]["kp_mean"]
        actual   = features.iloc[2]["kp_lag1"]
        assert math.isclose(expected, actual, rel_tol=1e-6)


# ─── Error condition ──────────────────────────────────────────────────────────

def test_build_feature_matrix_missing_kp_col():
    """Master without kp_mean column should still run, filling rolling cols with NaN."""
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC"),
        "launch_go": [1]*10,
    })
    features = build_feature_matrix(df)
    assert "kp_3d_avg" in features.columns
    # All NaN because source column absent
    assert features["kp_3d_avg"].isna().all()
