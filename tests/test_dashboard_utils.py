"""
Unit tests for dashboard utility functions.
IBM Bob generated — Phase 6.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components.utils import (
    build_single_feature_vector,
    shap_top_n,
    summarise_weather,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def nominal_weather():
    return {
        "fetched_at": "2024-08-30T12:00:00Z",
        "FLR": [],
        "CME": [],
        "GST": [],
    }


@pytest.fixture
def storm_weather():
    return {
        "fetched_at": "2024-08-30T12:00:00Z",
        "FLR": [{"classType": "X2.5", "beginTime": "2024-08-29T14:00Z"}],
        "CME": [{"startTime": "2024-08-29T14:30Z"}],
        "GST": [{
            "startTime": "2024-08-30T06:00Z",
            "allKpIndex": [{"kpIndex": "8"}, {"kpIndex": "7"}],
        }],
    }


# ─── Happy path ───────────────────────────────────────────────────────────────

def test_summarise_weather_nominal(nominal_weather):
    """Quiet weather should give green alert and zero counts."""
    s = summarise_weather(nominal_weather)
    assert s["x_flare_count"] == 0
    assert s["m_flare_count"] == 0
    assert s["cme_count"]     == 0
    assert s["gst_level"]     == 0
    assert s["alert_color"]   == "green"


def test_summarise_weather_storm(storm_weather):
    """Stormy weather should give red alert and correct counts."""
    s = summarise_weather(storm_weather)
    assert s["x_flare_count"] >= 1
    assert s["cme_count"]     >= 1
    assert s["gst_level"]     >= 3
    assert s["alert_color"]   == "red"


def test_build_single_feature_vector_shape():
    """build_single_feature_vector returns (1, N) array with N=15 default features."""
    X, names = build_single_feature_vector(
        kp=3.5, f10_7=130.0, launch_hour=14, day_of_year=240,
        cme_score=0.0, gst_level=1, xclass_72h=0, mclass_72h=1,
    )
    assert X.shape == (1, 15)
    assert len(names) == 15
    assert X.dtype == float


def test_cyclical_encoding_in_feature_vector():
    """Cyclical encodings in the feature vector respect trig identity sin²+cos²=1."""
    X, names = build_single_feature_vector(
        kp=2.0, f10_7=100.0, launch_hour=6, day_of_year=180,
    )
    vec = dict(zip(names, X[0]))
    assert math.isclose(vec["day_sin"]**2 + vec["day_cos"]**2, 1.0, abs_tol=1e-9)
    assert math.isclose(vec["hour_sin"]**2 + vec["hour_cos"]**2, 1.0, abs_tol=1e-9)


def test_shap_top_n_returns_correct_count():
    """shap_top_n returns exactly n entries sorted by |shap_value| descending."""
    sv = np.array([0.01, -0.5, 0.3, -0.1, 0.8, -0.02, 0.15])
    names = [f"f{i}" for i in range(7)]
    top = shap_top_n(sv, names, n=3)
    assert len(top) == 3
    # First entry should have largest absolute value
    assert top[0]["feature"] == "f4"   # |0.8| is largest
    assert abs(top[0]["shap_value"]) >= abs(top[1]["shap_value"])


# ─── Edge case ────────────────────────────────────────────────────────────────

def test_summarise_weather_missing_keys():
    """summarise_weather handles missing keys without crashing."""
    s = summarise_weather({})
    assert s["x_flare_count"] == 0
    assert s["gst_level"] == 0


def test_shap_top_n_fewer_features_than_n():
    """shap_top_n when n > len(sv) returns all features."""
    sv = np.array([0.1, -0.2, 0.3])
    names = ["a", "b", "c"]
    top = shap_top_n(sv, names, n=10)
    assert len(top) == 3


def test_build_single_feature_vector_custom_names():
    """Passing custom feature_names respects the caller's ordering."""
    custom = ["kp_3d_avg", "flux_3d_avg", "gst_level"]
    X, names = build_single_feature_vector(
        kp=4.0, f10_7=150.0, launch_hour=10, day_of_year=100,
        feature_names=custom,
    )
    assert X.shape == (1, 3)
    assert names == custom


# ─── Error condition ──────────────────────────────────────────────────────────

def test_live_space_weather_handles_api_failure():
    """live_space_weather catches request exceptions and populates error keys."""
    from dashboard.components.utils import live_space_weather
    with patch("requests.get", side_effect=Exception("connection refused")):
        result = live_space_weather(api_key="FAIL", lookback_days=1)
    assert "FLR" in result
    assert result["FLR"] == []
    assert "FLR_error" in result
