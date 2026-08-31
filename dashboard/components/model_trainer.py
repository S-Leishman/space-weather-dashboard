"""
Model training pipeline: Logistic Regression, Random Forest, XGBoost.
IBM Bob generated — Phase 4.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, log_loss,
    confusion_matrix,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import xgboost as xgb

warnings.filterwarnings("ignore", category=UserWarning)

MIN_CLASS_SUPPORT = 2


class ArtifactIsolationError(RuntimeError):
    """Raised when train_all/_save_model would write into the packaged
    dashboard/models/ directory (i.e. contamination of production artifacts
    during a test or ad-hoc run)."""
    pass

MODELS_DIR = Path(__file__).parent.parent / "models"
# Captured at import so a monkeypatch of MODELS_DIR cannot move the guard's
# notion of "the packaged production artifact directory".
PACKAGED_MODELS_DIR = (Path(__file__).parent.parent / "models").resolve()
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
PROC_DIR   = Path(__file__).parent.parent / "data" / "processed"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
_PACKAGED_MODELS_DIR = PACKAGED_MODELS_DIR  # backwards-compatible alias

FEATURE_COLS = [
    "kp_3d_avg", "kp_7d_avg",
    "flux_3d_avg", "flux_7d_avg",
    "kp_lag1", "kp_lag3", "kp_lag7",
    "xclass_72h", "mclass_72h",
    "cme_arrival_score",
    "gst_level",
    "day_sin", "day_cos",
    "hour_sin", "hour_cos",
]


def _running_under_pytest() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def _resolve_models_dir(models_dir: Path | None) -> Path:
    """Destination for training artifacts.

    An explicit directory always wins. Otherwise a run under pytest is given a
    throwaway directory, so an un-isolated test can never silently overwrite the
    shipped models; only a real run writes to the packaged directory.
    """
    if models_dir is not None:
        return Path(models_dir)
    if _running_under_pytest():
        return Path(tempfile.mkdtemp(prefix="swl-models-"))
    return MODELS_DIR


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def positive_class_column(model) -> int:
    """
    Index of the column of ``predict_proba`` that holds P(class == 1).

    Never assume column 1: it is only correct when ``classes_ == [0, 1]``.
    """
    classes = list(getattr(model, "classes_", [0, 1]))
    if 1 in classes:
        return classes.index(1)
    return len(classes) - 1


def _evaluate(model, X_test: np.ndarray, y_test: np.ndarray, label: str) -> dict:
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, positive_class_column(model)]

    n_test = int(len(y_test))
    n_pos  = int((y_test == 1).sum())
    n_neg  = int((y_test == 0).sum())

    # A ranking metric needs both classes present and some spread in the scores.
    # Without those guards a degenerate model silently reports a plausible number.
    auc: float | None = None
    auc_note = None
    if n_pos == 0 or n_neg == 0:
        auc_note = f"undefined: validation split contains only one class (pos={n_pos}, neg={n_neg})"
    elif n_pos < MIN_CLASS_SUPPORT or n_neg < MIN_CLASS_SUPPORT:
        auc_note = (
            f"insufficient class support: need ≥{MIN_CLASS_SUPPORT} of each class "
            f"(pos={n_pos}, neg={n_neg}) for a stable ROC-AUC"
        )
    elif float(np.ptp(y_proba)) == 0.0:
        auc_note = (
            f"degenerate: model returns a constant probability ({y_proba[0]:.4f}) "
            "for every row, so ROC-AUC is 0.5 by construction, not by skill"
        )
        auc = round(float(roc_auc_score(y_test, y_proba)), 4)
    else:
        auc = round(float(roc_auc_score(y_test, y_proba)), 4)

    metrics = {
        "model": label,
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   auc,
        "log_loss":  round(log_loss(y_test, y_proba, labels=[0, 1]), 4),
        "n_validation": n_test,
        "n_validation_positive": n_pos,
        "n_validation_negative": n_neg,
        "proba_column": positive_class_column(model),
    }
    if auc_note:
        metrics["roc_auc_note"] = auc_note
    print(f"  [{label}] Acc={metrics['accuracy']}  F1={metrics['f1']}  "
          f"AUC={metrics['roc_auc']}  n={n_test} (pos={n_pos}, neg={n_neg})")
    if auc_note:
        print(f"      ! {auc_note}")
    return metrics


def cross_validated_auc(model_factory, X: np.ndarray, y: np.ndarray,
                        n_splits: int = 5, random_state: int = 42) -> dict:
    """
    Stratified k-fold ROC-AUC over the whole labelled set.

    A single small holdout cannot support a performance claim; this gives a
    mean and spread across folds so the spread is visible alongside the number.
    """
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    splits = min(n_splits, n_pos, n_neg)
    if splits < 2:
        return {"cv_roc_auc_mean": None, "cv_note": "insufficient class support for cross-validation"}

    skf = StratifiedKFold(n_splits=splits, shuffle=True, random_state=random_state)
    fold_aucs = []
    for train_idx, test_idx in skf.split(X, y):
        m = model_factory()
        m.fit(X[train_idx], y[train_idx])
        proba = m.predict_proba(X[test_idx])[:, positive_class_column(m)]
        if len(set(y[test_idx])) < 2:
            continue
        fold_aucs.append(float(roc_auc_score(y[test_idx], proba)))
    if not fold_aucs:
        return {"cv_roc_auc_mean": None, "cv_note": "no fold contained both classes"}
    return {
        "cv_roc_auc_mean": round(float(np.mean(fold_aucs)), 4),
        "cv_roc_auc_std":  round(float(np.std(fold_aucs)), 4),
        "cv_folds":        len(fold_aucs),
        "cv_n_total":      int(len(y)),
    }


def _portable_model_path(dest: Path) -> str:
    """
    Path to record in metadata for a saved artifact.

    Artifacts inside the repository are recorded repository-relative with
    forward slashes: an absolute path would publish the build machine's
    username and directory layout in a public repository, and would not
    resolve for anyone who clones it. Artifacts written outside the
    repository (isolated test runs) keep their absolute path, which is the
    only form that identifies them unambiguously.
    """
    try:
        return dest.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(dest)


def _save_model(model, name: str, metadata: dict, models_dir: Path | None = None) -> Path:
    dest_dir = Path(models_dir) if models_dir is not None else MODELS_DIR
    # Contamination guard. Under pytest, writing into the packaged production
    # artifact directory is refused before any bytes change — that is the exact
    # mechanism that previously overwrote shipped models during a test run.
    if _running_under_pytest() and dest_dir.resolve() == PACKAGED_MODELS_DIR:
        raise ArtifactIsolationError(
            f"Refusing to write into the packaged artifact directory "
            f"({PACKAGED_MODELS_DIR}) during a test run. Pass an explicit "
            f"models_dir for isolated runs."
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name}.joblib"
    joblib.dump(model, dest)
    meta_path = dest_dir / f"{name}_metadata.json"
    metadata["model_file"] = _portable_model_path(dest)
    metadata["sha256"] = _sha256(dest)
    metadata["saved_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(metadata, indent=2))
    print(f"  saved → {dest}  sha256={metadata['sha256'][:16]}…")
    return dest


def load_features(path: Path | None = None) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load labeled rows from the feature Parquet and return X, y, feature_names."""
    if path is None:
        candidates = sorted(PROC_DIR.glob("features_v*.parquet"), reverse=True)
        if not candidates:
            raise FileNotFoundError("No features_v*.parquet found in data/processed/")
        path = candidates[0]

    df = pd.read_parquet(path)
    df = df.dropna(subset=["launch_go"])

    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].fillna(df[available].median()).values
    y = df["launch_go"].astype(int).values
    return X, y, available


def train_all(
    X: np.ndarray, y: np.ndarray, feature_names: list[str],
    test_size: float = 0.2, random_state: int = 42,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """Train LR, RF, XGBoost and return results dict.

    When ``models_dir`` is supplied, artifacts are written there instead of the
    packaged ``dashboard/models/``. A run under pytest that supplies no explicit
    directory is redirected to a throwaway one, and ``_save_model`` refuses any
    test-time write into the packaged directory, raising
    ``ArtifactIsolationError`` before any bytes change. Together these stop a
    test run from overwriting shipped production models.
    """
    out_dir = _resolve_models_dir(models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    results: dict[str, Any] = {
        "X_train": X_train, "X_test": X_test,
        "y_train": y_train, "y_test": y_test,
        "feature_names": feature_names,
        "metrics": [],
        "models": {},
    }

    # ── 1. Logistic Regression ────────────────────────────────────────────────
    print("\n[Phase 4] Training Logistic Regression …")
    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(
            class_weight="balanced", max_iter=1000,
            random_state=random_state, solver="lbfgs",
        )),
    ])
    lr_pipe.fit(X_train, y_train)
    lr_metrics = _evaluate(lr_pipe, X_test, y_test, "logistic_regression")
    results["metrics"].append(lr_metrics)
    _save_model(lr_pipe, "logistic_regression", {
        "name": "logistic_regression",
        "algorithm": "LogisticRegression (L2, balanced)",
        "feature_names": feature_names,
        "hyperparameters": {"C": 1.0, "max_iter": 1000},
        **{k: v for k, v in lr_metrics.items() if k != "model"},
    }, models_dir=out_dir)
    results["models"]["logistic_regression"] = lr_pipe

    # ── 2. Random Forest + GridSearchCV ──────────────────────────────────────
    print("\n[Phase 4] Training Random Forest (GridSearchCV) …")
    rf_grid = GridSearchCV(
        RandomForestClassifier(class_weight="balanced", random_state=random_state),
        param_grid={
            "n_estimators": [100, 200],
            "max_depth": [None, 8, 16],
            "min_samples_split": [2, 5],
        },
                # n_jobs=1: loky workers were being killed mid-search on this
        # memory-constrained host, surfacing as TerminatedWorkerError.
        cv=cv, scoring="roc_auc", n_jobs=1, verbose=0,
    )
    rf_grid.fit(X_train, y_train)
    rf_best = rf_grid.best_estimator_
    rf_metrics = _evaluate(rf_best, X_test, y_test, "random_forest")
    results["metrics"].append(rf_metrics)
    _save_model(rf_best, "random_forest", {
        "name": "random_forest",
        "algorithm": "RandomForestClassifier",
        "feature_names": feature_names,
        "hyperparameters": rf_grid.best_params_,
        "cv_best_score": round(rf_grid.best_score_, 4),
        **{k: v for k, v in rf_metrics.items() if k != "model"},
    }, models_dir=out_dir)
    results["models"]["random_forest"] = rf_best

    # ── 3. XGBoost ─────────────────────────────────────────────────────────
    print("\n[Phase 4] Training XGBoost …")
    scale_pos = int((y_train == 0).sum()) / max(1, int((y_train == 1).sum()))
    xgb_model = xgb.XGBClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        early_stopping_rounds=20,
        random_state=random_state,
        use_label_encoder=False,
    )
    # Early stopping must never watch the validation split — doing so leaks the
    # split the metrics are then reported on. Carve the watch set out of train.
    can_split_train = min(int((y_train == 0).sum()), int((y_train == 1).sum())) >= 2
    if can_split_train:
        X_fit, X_watch, y_fit, y_watch = train_test_split(
            X_train, y_train, test_size=0.2, stratify=y_train, random_state=random_state
        )
        xgb_model.fit(X_fit, y_fit, eval_set=[(X_watch, y_watch)], verbose=False)
    else:
        xgb_model.set_params(early_stopping_rounds=None)
        xgb_model.fit(X_train, y_train, verbose=False)
    xgb_metrics = _evaluate(xgb_model, X_test, y_test, "xgboost")
    results["metrics"].append(xgb_metrics)
    _save_model(xgb_model, "xgboost", {
        "name": "xgboost",
        "algorithm": "XGBClassifier",
        "feature_names": feature_names,
        "best_iteration": getattr(xgb_model, "best_iteration", None),
        **{k: v for k, v in xgb_metrics.items() if k != "model"},
    }, models_dir=out_dir)
    results["models"]["xgboost"] = xgb_model

    # ── Determine validation champion by ROC-AUC ─────────────────────────────
    best_metric = max(results["metrics"], key=lambda m: (m["roc_auc"] is not None, m["roc_auc"] or 0.0))
    results["best_model_name"] = best_metric["model"]
    results["best_model"]      = results["models"][best_metric["model"]]
    print(f"\n  Validation champion: {best_metric['model']}  AUC={best_metric['roc_auc']}")

    # Save metrics summary — every number below comes from this one run.
    summary_path = out_dir / "metrics_summary.json"
    summary_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": results["metrics"],
        "best_model": best_metric["model"],
        "validation": {
            "n_total_labelled": int(len(y)),
            "n_train": int(len(y_train)),
            "n_validation": int(len(y_test)),
            "n_validation_positive": int((y_test == 1).sum()),
            "n_validation_negative": int((y_test == 0).sum()),
            "test_size": test_size,
            "random_state": random_state,
        },
        "n_features": len(feature_names),
        "feature_names": feature_names,
    }, indent=2))

    return results


def load_model(name: str):
    path = MODELS_DIR / f"{name}.joblib"
    return joblib.load(path)
