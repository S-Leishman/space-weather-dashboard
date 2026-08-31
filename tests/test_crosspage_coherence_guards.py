"""
Cross-page coherence GUARDS — IBM-P0-CROSSPAGE-COHERENCE-002.

Complements tests/test_crosspage_coherence.py (co-authored with the worker).
This file carries the pins that file does not: the owner's exact-label
contracts (P0-E), the synthetic-SHAP label contract (P0-C), About claim
ceilings, protected candour, and the helper-layer identity guards a6/a7/a8.

Truth vocabulary: any score surfaced here is a PROTOTYPE score from a model
trained on synthetic labels — never a calibrated launch-success probability.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = PRODUCT_ROOT / "dashboard"
PAGES = DASHBOARD / "pages"

PAGE_HOME = DASHBOARD / "app.py"
PAGE_PIPELINE = PAGES / "1_\U0001f4e1_Data_Pipeline.py"
PAGE_MODEL_LAB = PAGES / "2_\U0001f9ec_Model_Lab.py"
PAGE_PREDICTION = PAGES / "3_\U0001f52c_Prediction_Explorer.py"
PAGE_ABOUT = PAGES / "4_⬡_About.py"
UTILS = DASHBOARD / "components" / "utils.py"

ALL_PAGES = [PAGE_HOME, PAGE_PIPELINE, PAGE_MODEL_LAB, PAGE_PREDICTION, PAGE_ABOUT]


def src(p: Path) -> str:
    assert p.exists(), f"page missing: {p}"
    return p.read_text(encoding="utf-8")


# ── P0-E: prototype score labelling (owner's exact wording) ──────────────────


def test_g1_go_score_labelled_prototype_go_score():
    """'Launch Probability' invites a judge to read 0.899 as a calibrated
    real-world probability. It is a prototype-model score on a synthetic label."""
    for page in (PAGE_HOME, PAGE_PREDICTION):
        text = src(page)
        assert not re.search(r'section_label\(\s*["\']Launch Probability["\']', text), (
            f"{page.name} still labels the readout 'Launch Probability'"
        )
        assert "Prototype GO Score" in text, (
            f"{page.name} must label the readout 'Prototype GO Score'"
        )


def test_g2_probability_line_is_relabelled():
    for page in (PAGE_HOME, PAGE_PREDICTION):
        text = src(page)
        assert "p(GO) = " not in text, (
            f"{page.name} still renders 'p(GO) = ', which reads as a probability"
        )
        assert "Prototype model score" in text, (
            f"{page.name} must render 'Prototype model score = ...'"
        )


# ── P0-C: SHAP claim coherence ───────────────────────────────────────────────


def test_g3_synthetic_shap_unlabelled_is_banned():
    """A synthetic SHAP-like vector may render only under the unmissable label."""
    text = src(PAGE_PREDICTION)
    if re.search(r"demo_shap|Synthetic SHAP", text, re.I):
        assert "SYNTHETIC DEMONSTRATION" in text and "NOT MODEL EXPLANATION" in text, (
            "Prediction Explorer renders a synthetic SHAP-like vector without the "
            "required 'SYNTHETIC DEMONSTRATION - NOT MODEL EXPLANATION' label."
        )


def test_g4_home_reports_shap_state_honestly():
    """HOME and the Explorer must both derive SHAP display from one state
    (explainer_state) so the pages cannot disagree."""
    home, pred = src(PAGE_HOME), src(PAGE_PREDICTION)
    assert "explainer_state" in home and "explainer_state" in pred, (
        "Both prediction-bearing pages must route SHAP display through "
        "explainer_state so HOME and the Explorer cannot disagree about it."
    )


# ── P0-D: About claim ceilings (owner's banned list) ─────────────────────────

BANNED_ABOUT_CLAIMS = [
    "AI system reduces risk of launching into",
    "Mission planners can model hypothetical launch windows in real time",
    "The best model is explained using",
]


@pytest.mark.parametrize("claim", BANNED_ABOUT_CLAIMS)
def test_g5_about_banned_claims_absent(claim):
    assert claim not in src(PAGE_ABOUT), (
        f"ABOUT asserts an unsupported current capability: {claim!r}. The label "
        "is synthetic and independent of the space-weather features, so model "
        "skill is expected near random."
    )


def test_g6_about_required_hedged_wording_present():
    text = src(PAGE_ABOUT)
    for required in (
        "evidence-aware launch scenario analysis",
        "interactively explore hypothetical launch scenarios",
    ):
        if required not in text:
            # The worker's rewrite may have chosen different hedged wording;
            # the alternative must still be a hedge, not a capability claim.
            assert "Prototype explores" in text or "could be incorporated" in text, (
                f"ABOUT lacks the required hedged wording: {required!r}"
            )


def test_g7_judging_table_distinguishes_maturity():
    text = src(PAGE_ABOUT)
    low = text.lower()
    for marker in ("implemented", "prototype", "future"):
        assert marker in low, f"About lacks a {marker} maturity marker"
    assert "not operationally qualified" in low or "not qualified" in low, (
        "About must mark future work as NOT OPERATIONALLY QUALIFIED"
    )


# ── Protected candour (regressions here would be silent truth loss) ─────────


def test_g8_missing_raw_artifacts_stay_visible():
    """Raw DONKI/SWPC artifacts genuinely are absent. The page must keep
    saying so — suppressing the notice turns a visible contradiction into a
    silent one."""
    text = src(PAGE_PIPELINE)
    assert "MISSING" in text, "Data Pipeline must still be able to report MISSING"
    assert "ingest manifest" in text.lower(), (
        "The ingest-manifest notice must not be suppressed"
    )


def test_g9_home_keeps_artifact_backed_provenance_render():
    text = src(PAGE_HOME)
    assert "load_provenance()" in text, (
        "HOME must render provenance from the artifact, not a static summary"
    )


def test_g10_non_operational_disclaimer_survives():
    assert "not operationally qualified" in src(PAGE_PREDICTION).lower(), (
        "Prediction Explorer must keep the non-operational disclaimer"
    )


def test_g11_no_synthetic_probability_formula_in_prediction_page():
    """The no-model demo path once fabricated a probability from a hardcoded
    formula. Deletion is the contract: no model artifact -> UNAVAILABLE, never
    a plausible number from arithmetic."""
    text = src(PAGE_PREDICTION)
    assert "Demo mode shows synthetic outputs" not in text, (
        "The synthetic demo path is banned."
    )
    for banned in ("0.75 - raw", "0.75 - raw2", "raw = kp * 0.12", "raw2 = kp_val"):
        assert banned not in text, f"synthetic probability formula remnant: {banned!r}"


# ── P0-F: helper-layer identity guards ───────────────────────────────────────

_UTILS_SYMBOL_RE = (
    r"(?<![\w.])(explainer_state|load_active_model|load_selected_model_name"
    r"|positive_class_column|feature_importance_state|load_provenance"
    r"|load_metrics_summary|load_best_model_metadata|build_single_feature_vector"
    r"|shap_top_n)\b"
)


def test_g12_every_utils_symbol_a_page_uses_is_imported_by_that_page():
    """
    The migration defect class: call sites moved to shared symbols without
    updating the importing page's import block, so the page raises NameError at
    render while every other page works. Module-alias usage (utils.X) is
    excluded by the (?<![\\w.]) guard; plain-name usage must trace to an import.
    RED provenance: live 2026-08-31 — Explorer referenced load_active_model/
    explainer_state/positive_class_column without importing them until 1bc0f06.
    """
    import ast

    offenders = []
    for page in ALL_PAGES:
        text = src(page)
        imported = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ImportFrom) and node.module == "dashboard.components.utils":
                imported.update(a.name for a in node.names)
        for m in re.finditer(_UTILS_SYMBOL_RE, text):
            name = m.group(1)
            if name not in imported:
                line = text[: m.start()].count("\n") + 1
                offenders.append(f"{page.name}:{line} -> {name} referenced but not imported")
    assert not offenders, (
        "Page(s) reference dashboard.components.utils symbols without importing "
        "them (NameError at render):\n  " + "\n  ".join(offenders)
    )


def test_g13_explainer_state_is_never_cache_wrapped():
    """
    st.cache_resource deliberately EXCLUDES underscore-prefixed arguments from
    the cache key. A cache-wrapped explainer factory can return an explainer
    bound to a different model than the one being explained — a wrong-model
    explanation on a product whose thesis is model identity and provenance.
    """
    text = src(UTILS)
    m = re.search(r"^def explainer_state", text, re.M)
    assert m, "utils.explainer_state must exist"
    prev_line = text[: m.start()].rstrip().splitlines()[-1]
    assert "cache_resource" not in prev_line, (
        "explainer_state is cache-wrapped; explanation availability must be "
        "computed per call so it can never describe a stale model."
    )


def test_g14_positive_class_column_fails_closed_when_class_1_absent():
    """
    Guessing a probability column is how an UNKNOWN positive-class identity
    becomes 'assume column 1'. A missing class 1 is not a mapping problem to
    paper over — it is a model-identity failure and must raise. RED against the
    fallback-to-last-column implementation; GREEN once it fails closed.
    """
    from dashboard.components.utils import positive_class_column

    try:
        positive_class_column(object())
        raised_missing = False
    except Exception:
        raised_missing = True
    assert raised_missing, (
        "A model without classes_ raised nothing: positive_class_column assumed "
        "a default class layout instead of failing closed."
    )

    class _NonBinary:
        classes_ = [0, 2]

    try:
        positive_class_column(_NonBinary())
        raised_absent = False
    except Exception:
        raised_absent = True
    assert raised_absent, (
        "Absent positive class silently fell back to the last column instead of "
        "failing closed."
    )