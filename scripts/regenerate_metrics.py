"""
Single-run regeneration of the dashboard's dataset, provenance and model metrics.

Every number the UI displays must come from one execution of this script, so the
metrics table, the model artifacts and FEATURE_PROVENANCE.json can never drift
apart. Run:

    python scripts/regenerate_metrics.py

Extracted from notebooks 03 and 04 so it can run headless in CI and in the demo
environment. The label column is a documented synthetic scaffold (see
LABEL_SEMANTICS below) — it carries no operational meaning.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.features import build_feature_matrix, save_features, PROC_DIR
from dashboard.components.model_trainer import (
    MODELS_DIR,
    cross_validated_auc,
    load_features,
    train_all,
)

RANDOM_STATE = 42
DATASET_ID = "swl-challenge-synthetic-v1"
LABEL_SEMANTICS = (
    "launch_go is a synthetic scaffold label drawn independently of the space-weather "
    "features (challenge demo dataset, no real launch outcomes merged). No model can "
    "have genuine predictive skill on it; ROC-AUC near 0.5 is the expected and correct result."
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_daily_master() -> pd.DataFrame:
    """Deterministic synthetic daily master, identical to notebook 03's fallback."""
    rng = np.random.default_rng(RANDOM_STATE)
    dates = pd.date_range("2023-01-01", "2024-08-30", freq="D", tz="UTC")
    master = pd.DataFrame({
        "date": dates,
        "kp_mean": rng.uniform(0, 9, len(dates)),
        "f10_7": rng.uniform(70, 220, len(dates)),
        "launch_go": np.where(rng.uniform(0, 1, len(dates)) < 0.7, 1, 0),
        "launch_window_utc": [f"{rng.integers(0, 24):02d}:00" for _ in dates],
    })
    labelled = rng.random(len(master)) > 0.86
    master.loc[~labelled, "launch_go"] = np.nan
    master.loc[~labelled, "launch_window_utc"] = np.nan
    return master


def main() -> int:
    started = datetime.now(timezone.utc)
    print(f"[regen] start {started.isoformat()}")

    master = build_daily_master()
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    master_path = PROC_DIR / "daily_master.parquet"
    master.to_parquet(master_path, index=False)
    print(f"[regen] daily_master  rows={len(master)}  -> {master_path}")

    features = build_feature_matrix(master)
    provenance = save_features(features, version=1)

    X, y, feature_names = load_features()
    print(f"[regen] labelled rows={len(y)}  GO={int(y.sum())}  SCRUB={int((y == 0).sum())}")

    results = train_all(X, y, feature_names, test_size=0.2, random_state=RANDOM_STATE)

    # Cross-validated AUC over the whole labelled set — the holdout alone is too
    # small to support any claim, so the spread is reported next to it.
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    import xgboost as xgb

    factories = {
        "logistic_regression": lambda: Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(class_weight="balanced", max_iter=1000,
                                      random_state=RANDOM_STATE)),
        ]),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE),
        "xgboost": lambda: xgb.XGBClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=4,
            eval_metric="logloss", random_state=RANDOM_STATE),
    }
    for entry in results["metrics"]:
        entry.update(cross_validated_auc(factories[entry["model"]], X, y,
                                         random_state=RANDOM_STATE))
        print(f"[regen] {entry['model']:20s} cv_auc={entry.get('cv_roc_auc_mean')} "
              f"± {entry.get('cv_roc_auc_std')}")

    summary_path = MODELS_DIR / "metrics_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["metrics"] = results["metrics"]
    summary["dataset_id"] = DATASET_ID
    summary["label_semantics"] = LABEL_SEMANTICS
    summary["regenerated_by"] = "scripts/regenerate_metrics.py"
    summary_path.write_text(json.dumps(summary, indent=2))

    # Provenance: dataset identity, feature manifest hash, model artifact hashes.
    feature_manifest = json.dumps(sorted(feature_names), separators=(",", ":")).encode()
    provenance.update({
        "dataset_id": DATASET_ID,
        "label_semantics": LABEL_SEMANTICS,
        "daily_master_sha256": _sha256_file(master_path),
        "feature_manifest_sha256": hashlib.sha256(feature_manifest).hexdigest(),
        "feature_names": sorted(feature_names),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "scripts/regenerate_metrics.py",
        "training_artifacts": {
            name: _sha256_file(MODELS_DIR / f"{name}.joblib")
            for name in ("logistic_regression", "random_forest", "xgboost")
            if (MODELS_DIR / f"{name}.joblib").exists()
        },
        "validation": summary.get("validation", {}),
    })
    prov_path = PROC_DIR / "FEATURE_PROVENANCE.json"
    prov_path.write_text(json.dumps(provenance, indent=2))
    print(f"[regen] provenance -> {prov_path}")
    print(f"[regen] done in {(datetime.now(timezone.utc) - started).total_seconds():.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
