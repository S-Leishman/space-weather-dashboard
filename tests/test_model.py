"""
Unit tests for dashboard/components/model_trainer.py
IBM Bob generated — Phase 6.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components.model_trainer import (
    FEATURE_COLS,
    _evaluate,
    _save_model,
    load_features,
    train_all,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolate_model_artifacts(tmp_path, monkeypatch):
    models_dir = tmp_path / "generated-models"
    models_dir.mkdir()
    monkeypatch.setattr("dashboard.components.model_trainer.MODELS_DIR", models_dir)


@pytest.fixture
def synthetic_xy():
    """Small balanced dataset for fast training tests."""
    rng = np.random.default_rng(42)
    n = 120
    X = rng.standard_normal((n, len(FEATURE_COLS)))
    y = rng.choice([0, 1], size=n)
    return X, y


@pytest.fixture
def trained_results(synthetic_xy):
    """Full train_all output — reused across multiple tests."""
    X, y = synthetic_xy
    return train_all(X, y, FEATURE_COLS, test_size=0.25, random_state=0)


@pytest.fixture
def tmp_models_dir(tmp_path):
    d = tmp_path / "models"
    d.mkdir()
    return d


# ─── Happy path ───────────────────────────────────────────────────────────────

def test_train_all_returns_three_models(synthetic_xy):
    """train_all must return logistic_regression, random_forest, and xgboost."""
    X, y = synthetic_xy
    results = train_all(X, y, FEATURE_COLS, test_size=0.25, random_state=0)
    assert set(results["models"].keys()) == {"logistic_regression", "random_forest", "xgboost"}


def test_metrics_have_required_keys(trained_results):
    """Every metrics entry must contain all six required metric names."""
    required = {"model", "accuracy", "precision", "recall", "f1", "roc_auc", "log_loss"}
    for entry in trained_results["metrics"]:
        assert required.issubset(set(entry.keys())), f"Missing keys in {entry}"


def test_roc_auc_in_valid_range(trained_results):
    """ROC-AUC must be between 0 and 1 for all three models."""
    for m in trained_results["metrics"]:
        assert 0.0 <= m["roc_auc"] <= 1.0


def test_save_model_creates_files(synthetic_xy, tmp_models_dir):
    """_save_model writes .joblib and *_metadata.json files."""
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=100).fit(*synthetic_xy)

    with patch("dashboard.components.model_trainer.MODELS_DIR", tmp_models_dir):
        import dashboard.components.model_trainer as mt
        orig = mt.MODELS_DIR
        mt.MODELS_DIR = tmp_models_dir
        _save_model(clf, "test_lr", {"name": "test_lr", "accuracy": 0.9})
        mt.MODELS_DIR = orig

    assert (tmp_models_dir / "test_lr.joblib").exists()
    assert (tmp_models_dir / "test_lr_metadata.json").exists()
    meta = json.loads((tmp_models_dir / "test_lr_metadata.json").read_text())
    assert "sha256" in meta
    assert len(meta["sha256"]) == 64


# ─── Edge case ────────────────────────────────────────────────────────────────

def test_evaluate_perfect_predictor():
    """_evaluate with a perfect mock predictor returns 1.0 across all metrics."""
    y_true = np.array([0, 0, 1, 1, 1])
    y_pred = np.array([0, 0, 1, 1, 1])
    y_proba = np.array([0.05, 0.05, 0.95, 0.95, 0.95])

    mock_model = type("M", (), {
        "predict":       lambda self, X: y_pred,
        "predict_proba": lambda self, X: np.column_stack([1-y_proba, y_proba]),
    })()

    metrics = _evaluate(mock_model, np.zeros((5, 2)), y_true, "perfect")
    assert metrics["accuracy"]  == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"]    == 1.0
    assert metrics["f1"]        == 1.0
    assert metrics["roc_auc"]   == 1.0


def test_train_all_single_class_edge():
    """train_all on nearly all-one-class data must not crash (balanced fallback)."""
    rng = np.random.default_rng(7)
    X = rng.standard_normal((60, 4))
    y = np.array([1]*55 + [0]*5)
    # Should complete without exception
    results = train_all(X, y, FEATURE_COLS[:4], test_size=0.25, random_state=7)
    assert len(results["metrics"]) == 3


# ─── Error condition ──────────────────────────────────────────────────────────

def test_load_features_raises_when_no_parquet(tmp_path):
    """load_features raises FileNotFoundError when data/processed is empty."""
    with patch("dashboard.components.model_trainer.PROC_DIR", tmp_path):
        import dashboard.components.model_trainer as mt
        orig = mt.PROC_DIR
        mt.PROC_DIR = tmp_path
        with pytest.raises(FileNotFoundError):
            load_features()
        mt.PROC_DIR = orig
