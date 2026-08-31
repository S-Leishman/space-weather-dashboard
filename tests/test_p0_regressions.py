"""
P0 regression controls — IBM-P0-IMPLEMENT-001.

Contract: these tests fail on the demonstrated defects
(champion/artifact mismatch, fabricated DEMO_METRICS, fabricated feature
importances, AUC published on insufficient class support, un-isolated
train_all() artifact writes, raw-JS emitted markup).

Discipline record (truth about the RED phase, see IBM-P0-IMPLEMENT-001.json):
- live RED before the fix: champion selector, metric-support refusal,
  artifact-isolation kwarg/guard, DEMO_METRICS and importance source contracts.
- GREEN on arrival: Test A emitter check — the <script>->CSS repair landed in
  theme.py before this suite existed; the initial full-file token scan false-
  positivied on an incident-note CSS comment inside <style>, so the checker was
  refined (style-block comment stripping) rather than the product; the
  negative-control below pins that the assertions still catch the historical
  leak. Rendered behavior is separately evidenced by RENDER_VERIFY receipts.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components import model_trainer as mt
from dashboard.components import theme
from dashboard.components import utils as du

APP_PY = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
MODEL_LAB = (ROOT / "dashboard" / "pages" / "2_🧬_Model_Lab.py").read_text(encoding="utf-8")

RAW_JS_TOKENS = ["<script", "STAR_COUNT", "function resize", "window.innerWidth", "canvas.width"]


def raw_js_violations(markup: str) -> list[str]:
    """Violations = a <script> ELEMENT or script BODY text on the HTML/text
    render path. Inside <style> blocks, CSS comments are inert — strip them
    first, and flag only script-body tokens (a "<script" literal in CSS is
    invalid-CSS garbage, not executable markup)."""
    style_chunks = re.findall(r"<style\b.*?</style>", markup, flags=re.S | re.I)
    html_rest = re.sub(r"<style\b.*?</style>", "", markup, flags=re.S | re.I)
    violations = {t for t in RAW_JS_TOKENS if t.lower() in html_rest.lower()}
    for chunk in style_chunks:
        bare = re.sub(r"/\*.*?\*/", "", chunk, flags=re.S)
        violations.update(t for t in RAW_JS_TOKENS[1:] if t.lower() in bare.lower())
    return sorted(violations)


@pytest.fixture
def isolated_models_dir(tmp_path, monkeypatch):
    d = tmp_path / "models"
    d.mkdir()
    monkeypatch.setattr("dashboard.components.model_trainer.MODELS_DIR", d)
    return d


@pytest.fixture
def packaged_hashes():
    return {p.name: p.read_bytes() for p in sorted(PACKAGED_MODELS.glob("*.joblib"))}


PACKAGED_MODELS = ROOT / "dashboard" / "models"


# ─── TEST A — render body leak ────────────────────────────────────────────────

def test_a_inject_design_system_emits_no_script(monkeypatch):
    """Streamlit strips <script> but renders its body; the emitter must not
    emit one at all. Asserted on the EMITTED MARKUP, not on file contents."""
    captured = []
    monkeypatch.setattr(theme.st, "markdown", lambda html, **kw: captured.append(html))
    theme.inject_design_system()
    emitted = "".join(captured)
    assert raw_js_violations(emitted) == [], f"raw JS in emitted markup: {raw_js_violations(emitted)[:3]}"


def test_a_checker_control_flags_historical_leak():
    """Negative control (synthetic): the same assertion set that passes on the
    live emitter flags the historical starfield-script string. Recorded as a
    control, not as a claim about current source."""
    historical = (
        '<div id="starfield-canvas"></div>'
        "<script>var STAR_COUNT = 220; function resize() { "
        "canvas.width = window.innerWidth; } window.addEventListener('resize', resize);</script>"
    )
    assert set(raw_js_violations(historical)) >= {"<script", "STAR_COUNT", "function resize", "window.innerWidth"}


# ─── TEST B — metric coherence ────────────────────────────────────────────────

def _stub_model(y_pred, y_proba):
    return type("M", (), {
        "predict": lambda self, X: np.asarray(y_pred),
        "predict_proba": lambda self, X: np.column_stack([1 - np.asarray(y_proba), y_proba]),
    })()


def test_b_valid_two_class_support_recorded():
    y = np.array([0, 1, 0, 1, 1])
    proba = np.array([0.1, 0.9, 0.2, 0.8, 0.7])
    m = mt._evaluate(_stub_model(np.array([0, 1, 0, 1, 1]), proba),
                     np.zeros((5, 2)), y, "coherent")
    assert m["roc_auc"] is not None and 0.0 <= m["roc_auc"] <= 1.0
    assert m["n_validation_positive"] == 3 and m["n_validation_negative"] == 2
    assert m.get("proba_column") is not None


def test_b_single_class_auc_not_published():
    y = np.zeros(8, dtype=int)
    proba = np.full(8, 0.3)
    m = mt._evaluate(_stub_model(np.zeros(8, dtype=int), proba),
                     np.zeros((8, 2)), y, "single_class")
    assert m["roc_auc"] is None, "AUC must be refused, not measured, on single-class validation"
    assert m.get("roc_auc_note") and "undefined" in m["roc_auc_note"]


def test_b_pathological_split_auc_refused(isolated_models_dir):
    """The exact defect-era fixture (tests/test_model.py:122): labels
    [1]*55+[0]*5, rng default_rng(7), 60x4, test_size=0.25, random_state=7
    yields n_validation=15 at 14 positive / 1 negative. With fewer than two of
    one class in the split, ROC-AUC must be REFUSED (None + note), never
    published as a measured number (the defect shipped 0.1429)."""
    rng = np.random.default_rng(7)
    X = rng.standard_normal((60, 4))
    y = np.array([1] * 55 + [0] * 5)
    results = mt.train_all(X, y, mt.FEATURE_COLS[:4], test_size=0.25, random_state=7)
    rf = next(m for m in results["metrics"] if m["model"] == "random_forest")
    assert rf["n_validation_positive"] == 14 and rf["n_validation_negative"] == 1
    assert rf["roc_auc"] is None, (
        f"expected refused AUC on 14/1 split, got measured {rf.get('roc_auc')} "
        f"with note {rf.get('roc_auc_note')}"
    )
    assert "insufficient class support" in (rf.get("roc_auc_note") or "")


# ─── TEST C — artifact isolation ──────────────────────────────────────────────

def test_c_train_all_with_explicit_dir_leaves_packaged_untouched(packaged_hashes, tmp_path):
    out = tmp_path / "trained"
    rng = np.random.default_rng(42)
    X = rng.standard_normal((120, len(mt.FEATURE_COLS)))
    y = rng.choice([0, 1], size=120)
    mt.train_all(X, y, mt.FEATURE_COLS, test_size=0.25, random_state=0, models_dir=out)
    # new artifacts exist ONLY in the explicit destination
    assert len(list(out.glob("*.joblib"))) == 3
    out_meta = json.loads((out / "xgboost_metadata.json").read_text())
    assert (Path(out_meta["model_file"]).parent == out)
    # packaged production artifacts byte-identical
    after = {p.name: p.read_bytes() for p in sorted(PACKAGED_MODELS.glob("*.joblib"))}
    assert packaged_hashes == after, "packaged dashboard/models/*.joblib changed during isolated training"


def test_c_packaged_write_under_pytest_raises():
    """The historical contamination mechanism: a test-module train_all without
    isolation writing straight into dashboard/models/. Under pytest, an
    implicit write there must raise ArtifactIsolationError BEFORE any bytes
    change. Attribute access is the RED tripwire: before the fix this test
    errors on the missing guard without touching packaged files."""
    before = {p.name: p.read_bytes() for p in sorted(PACKAGED_MODELS.glob("*.joblib"))}
    clf = LogisticRegression().fit(np.zeros((4, 2)), np.array([0, 0, 1, 1]))
    with pytest.raises(mt.ArtifactIsolationError):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("dashboard.components.model_trainer.MODELS_DIR", PACKAGED_MODELS)
            mt._save_model(clf, "probe_probe_probe", {"name": "probe_probe_probe"})
    after = {p.name: p.read_bytes() for p in sorted(PACKAGED_MODELS.glob("*.joblib"))}
    assert before == after, "packaged models changed despite isolation guard"


# ─── Champion / serialized-artifact coherence ─────────────────────────────────

def _coherent_model_dir(tmp_path, best_model: str | None) -> Path:
    d = tmp_path / "models" if best_model is None else tmp_path / f"models_rc_{best_model}"
    d.mkdir()
    X = np.zeros((4, 2))
    y = np.array([0, 0, 1, 1])
    for name in ["xgboost", "random_forest", "logistic_regression"]:
        try:  # xgboost stub only needed if installed; LR fallback stubs are fine
            from xgboost import XGBClassifier
            m = XGBClassifier(n_estimators=2, max_depth=1).fit(X, y)
        except Exception:
            m = LogisticRegression().fit(X, y)
        joblib.dump(m, d / f"{name}.joblib")
    summary = {"best_model": best_model, "metrics": []}
    (d / "metrics_summary.json").write_text(json.dumps(summary))
    return d


def test_champion_selector_prefers_metrics_summary(tmp_path):
    """Selection authority is metrics_summary.json best_model, not a for-loop
    order — the app previously served xgboost while the artifacts' own
    validation regime selected logistic_regression."""
    d = _coherent_model_dir(tmp_path, "logistic_regression")
    assert du.load_selected_model_name(d) == "logistic_regression"


def test_champion_selector_none_when_summary_missing_or_incoherent(tmp_path):
    d = _coherent_model_dir(tmp_path, None)
    assert du.load_selected_model_name(d) is None
    d2 = _coherent_model_dir(tmp_path, "random_forest")
    (d2 / "random_forest.joblib").unlink()
    assert du.load_selected_model_name(d2) is None


def test_app_delegates_selection_to_coherent_selector():
    """Source contract pinning the seam; rendered behavior is covered by the
    separate browser verification receipts."""
    assert "load_selected_model_name" in APP_PY


# ─── Claim-integrity source contracts ─────────────────────────────────────────

def test_no_fabricated_demo_metrics_block():
    assert "DEMO_METRICS" not in MODEL_LAB, "fabricated metrics fallback must not ship"
    assert "NOT_EVALUATED" in MODEL_LAB, "missing-metrics state must be explicit"


def test_no_fabricated_feature_importances():
    assert "0.19,0.15,0.13" not in APP_PY
    assert "UNAVAILABLE" in APP_PY
    assert "feature_importance_state" in APP_PY


def test_importance_state_never_invents_values():
    from sklearn.ensemble import RandomForestClassifier
    rng = np.random.default_rng(0)
    X = rng.standard_normal((40, 3))
    y = rng.choice([0, 1], 40)
    rf = RandomForestClassifier(n_estimators=5).fit(X, y)
    ok = du.feature_importance_state(rf, ["a", "b", "c"])
    assert ok["status"] == "OK" and len(ok["values"]) == 3
    # feature-name mismatch and importance-less estimators must be UNAVAILABLE
    mismatch = du.feature_importance_state(rf, ["a", "b"])
    assert mismatch["status"] == "UNAVAILABLE" and not mismatch["values"]
    lr = LogisticRegression().fit(X, y)
    lr_state = du.feature_importance_state(lr, ["a", "b", "c"])
    assert lr_state["status"] in {"OK", "UNAVAILABLE"}  # coef_-based, never invented