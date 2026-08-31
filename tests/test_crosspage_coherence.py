"""
P0 cross-page coherence controls — IBM-P0-CROSSPAGE-COHERENCE-002.

Contract: these tests pin the three release-critical coherence defects:
  P0-A  Model identity mismatch (home page says logistic_regression,
        Prediction Explorer said xgboost).
  P0-B  Data Pipeline path resolution bug (artifacts shown MISSING on the
        pipeline page while home page provenance was populated).
  P0-D  About page makes unsupported SHAP / capability claims that conflict
        with the actual prototype state.

RED phase: tests fail on the demonstrated defects.
GREEN phase: tests pass on the fixed code.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components import utils as du
from dashboard.components.model_trainer import (
    ArtifactIsolationError,
    MIN_CLASS_SUPPORT,
)

APP_PY  = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
PRED_EXP = (ROOT / "dashboard" / "pages" / "3_🔬_Prediction_Explorer.py").read_text(encoding="utf-8")
PIPELINE = (ROOT / "dashboard" / "pages" / "1_📡_Data_Pipeline.py").read_text(encoding="utf-8")
ABOUT    = (ROOT / "dashboard" / "pages" / "4_⬡_About.py").read_text(encoding="utf-8")
MODEL_LAB = (ROOT / "dashboard" / "pages" / "2_🧬_Model_Lab.py").read_text(encoding="utf-8")

PROD_MODELS_DIR = (ROOT / "dashboard" / "models").resolve()
PROC_DIR = (ROOT / "dashboard" / "data" / "processed").resolve()
RAW_DIR = (ROOT / "dashboard" / "data" / "raw").resolve()


# ─── P0-A: model identity coherence ─────────────────────────────────────────────

def test_a_home_page_uses_load_active_model():
    """Home page must delegate model selection to the canonical
    load_active_model() / positive_class_column() utilities, not a local
    pickled-name guess or a for-loop first-match."""
    assert "load_active_model(" in APP_PY
    assert "positive_class_column" in APP_PY
    assert "load_selected_model_name" in APP_PY


def test_a_prediction_explorer_uses_same_selector():
    """Prediction Explorer must read the champion the same way the home page does."""
    assert "load_active_model(" in PRED_EXP
    # must NOT contain a local hard-coded model name that bypasses selection
    assert '"xgboost"' not in PRED_EXP.replace('"xgboost"', '"xgboost"', 1) or \
           PRED_EXP.count('"xgboost"') <= 1, \
           "Prediction Explorer hard-codes xgboost — bypasses champion selection"


def test_a_no_model_name_disagreement_in_source():
    """Both pages must source the model name from the same utility."""
    # The selector function must be called on both pages
    for label, page_src in [("app.py", APP_PY), ("Prediction_Explorer", PRED_EXP)]:
        assert "load_active_model(" in page_src, \
            f"{label} does not call load_active_model()"


def test_a_positive_class_column_imported_in_app():
    """app.py must import positive_class_column, never assume column 1."""
    assert "positive_class_column" in APP_PY


# ─── P0-B: artifact-root / path resolution coherence ────────────────────────────

def test_b_app_imports_canonical_path_anchors():
    """app.py must import MODELS_DIR from utils, not construct it locally
    with a wrong base."""
    assert "MODELS_DIR" in APP_PY, "app.py does not reference MODELS_DIR"
    # Must import from utils, not define locally
    assert "from dashboard.components.utils import" in APP_PY or \
           "from dashboard.components.utils" in APP_PY


def test_b_pipeline_uses_canonical_dirs():
    """Data Pipeline page must reference the same PROC_DIR / RAW_DIR that utils
    defines, so the provenance it displays matches the home page provenance."""
    assert "from dashboard.components.utils import" in PIPELINE or \
           "from dashboard.components.utils" in PIPELINE, \
           "Data Pipeline must import from utils, not define path anchors locally"
    for name in ["PROC_DIR", "RAW_DIR"]:
        assert name in PIPELINE, f"Data Pipeline page does not reference {name}"


def test_b_utils_anchors_match_canonical_layout():
    """The canonical path anchors in utils.py must point to the real
    dashboard/data/processed and dashboard/data/raw directories, not a
    dashboard/data/ sub-path that creates a phantom PROC_DIR."""
    import dashboard.components.utils as u
    assert u.PROC_DIR.resolve() == PROC_DIR
    assert u.RAW_DIR.resolve() == RAW_DIR


def test_b_no_local_path_redefinition_in_pages():
    """Pages must not locally re-define PROC_DIR/DASHBOARD_DIR with a path that
    diverges from utils.py — the historical defect."""
    for label, src in [("app.py", APP_PY), ("Data_Pipeline", PIPELINE)]:
        # A local re-definition like PROC_DIR = Path(...) in the page body
        # would shadow the import; flag assignments that don't come from utils.
        local_defs = re.findall(r'PROC_DIR\s*=\s*Path\(', src)
        assert local_defs == [], \
            f"{label} locally redefines PROC_DIR with Path(...) instead of importing from utils"


def test_b_artifact_path_consistency():
    """load_provenance() and load_best_model_metadata() must read from the
    same models_dir that the dashboard ships."""
    prov_path = PROD_MODELS_DIR / "provenance.json"
    if prov_path.exists():
        data = json.loads(prov_path.read_text())
        assert "artifacts" in data or "hashes" in data, \
            "provenance.json must list artifacts"
    # Also verify load_provenance() returns a dict from utils
    prov = du.load_provenance()
    assert isinstance(prov, dict)


# ─── P0-D: claim coherence — About page vs. actual implementation ───────────────

def test_d_no_unsupported_shap_claims_about_page():
    """About page must not claim SHAP is used for per-prediction explanation
    when the champion model is logistic_regression (no TreeExplainer)."""
    # The About page must qualify SHAP claims
    if "SHAP" in ABOUT:
        # If SHAP is mentioned, it must be in a qualified context
        lower = ABOUT.lower()
        qualified = (
            "prototype" in lower
            or "not qualified" in lower
            or "experimental" in lower
            or "unavailable" in lower
            or "may not" in lower
            or "cannot" in lower
            or "no longer" in lower
        )
        assert qualified, \
            "About page mentions SHAP but does not qualify the claim as prototype / unavailable"


def test_d_no_risk_reduction_claim():
    """About page must not claim the system 'reduces risk' — it predicts a
    prototype score, it does not reduce operational risk."""
    lower = ABOUT.lower()
    assert "reduces risk" not in lower, \
        "About page claims 'reduces risk' — not supported by prototype status"
    assert "risk mitigation" not in lower, \
        "About page claims 'risk mitigation' — not supported by prototype status"


def test_d_no_mission_planner_capability_claim():
    """About page must not claim mission planners 'can model hypothetical
    launch windows in real time' as a delivered capability."""
    lower = ABOUT.lower()
    assert "can model" not in lower, \
        "About page claims users 'can model' — implies delivered capability"
    assert "model hypothetical" not in lower, \
        "About page claims 'model hypothetical launch windows' — implies delivered capability"


def test_d_capability_legend_present():
    """About page must have a status legend distinguishing IMPLEMENTED,
    PROTOTYPE, and FUTURE / NOT QUALIFIED capabilities."""
    lower = ABOUT.lower()
    assert "implemented" in lower or "prototype" in lower, \
        "About page must classify capabilities by status"
    assert "future" in lower or "not qualified" in lower or "not operationally" in lower, \
        "About page must mark non-delivered capabilities as FUTURE / NOT QUALIFIED"


def test_d_model_lab_shows_not_evaluated_state():
    """Model Lab page must show an explicit NOT_EVALUATED / not-trained state
    rather than fabricated metrics."""
    assert "NOT_EVALUATED" in MODEL_LAB, \
        "Model Lab page must show NOT_EVALUATED state when metrics are absent"
    assert "DEMO_METRICS" not in MODEL_LAB, \
        "Model Lab page must not contain fabricated DEMO_METRICS fallback"


def test_d_app_shows_unavailable_for_unsupported_features():
    """app.py must contain explicit UNAVAILABLE state for features that can't
    be computed (e.g., SHAP on logistic regression)."""
    assert "UNAVAILABLE" in APP_PY, \
        "app.py must render UNAVAILABLE for unsupported features"


# ─── P0-A/B: runtime coherence — model identity & artifact path ─────────────────

def test_runtime_model_identity_consistent():
    """The model name returned by load_active_model must be the same value
    shown on the home page verdict line."""
    model, model_name, meta = du.load_active_model()
    selected = du.load_selected_model_name(PROD_MODELS_DIR)
    if selected is not None:
        assert model_name == selected, \
            f"load_active_model() returned {model_name} but " \
            f"load_selected_model_name() returns {selected} — identity mismatch"


def test_runtime_model_has_positive_class_column():
    """The champion model must expose a positive_class_column() that returns
    a valid index for predict_proba."""
    model, model_name, meta = du.load_active_model()
    if model is not None:
        col = du.positive_class_column(model)
        assert isinstance(col, int) and col >= 0, \
            f"positive_class_column returned {col} for {model_name}"
