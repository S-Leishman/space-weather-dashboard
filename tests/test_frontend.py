"""
Frontend tests: accessibility assertions, component smoke tests, and theme system.
IBM Bob generated — Frontend Phase.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_st(monkeypatch):
    """Minimal Streamlit mock so theme helpers run without a Streamlit session."""
    st_mock = MagicMock()
    st_mock.markdown = MagicMock()
    st_mock.caption  = MagicMock()
    monkeypatch.setattr("streamlit.markdown", st_mock.markdown)
    monkeypatch.setattr("streamlit.caption",  st_mock.caption)
    return st_mock


# ── Design token tests ────────────────────────────────────────────────────────

def test_css_file_exists():
    """The design system CSS file must exist and be non-empty."""
    css_path = ROOT / "dashboard" / "assets" / "css" / "space_theme.css"
    assert css_path.exists(), f"CSS not found at {css_path}"
    content = css_path.read_text(encoding="utf-8")
    assert len(content) > 500, "CSS file appears empty or truncated"


def _read_css() -> str:
    return (ROOT / "dashboard" / "assets" / "css" / "space_theme.css").read_text(encoding="utf-8")


def test_css_contains_required_tokens():
    """CSS must define all required design tokens."""
    css = _read_css()
    required_tokens = [
        "--bg-deep",
        "--color-go",
        "--color-scrub",
        "--color-blue",
        "--font-display",
        "--font-mono",
    ]
    for token in required_tokens:
        assert token in css, f"Missing CSS token: {token}"


def test_css_has_starfield_canvas():
    """CSS must define the starfield canvas positioning."""
    assert "#starfield-canvas" in _read_css()


def test_css_has_reduced_motion_query():
    """CSS must respect prefers-reduced-motion."""
    assert "prefers-reduced-motion" in _read_css()


def test_css_has_responsive_breakpoints():
    """CSS must include mobile-responsive breakpoints."""
    css = _read_css()
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 480px)" in css


def test_css_has_focus_visible():
    """CSS must define visible keyboard focus indicator (WCAG 2.4.7)."""
    assert "focus-visible" in _read_css()


# ── Theme component tests ─────────────────────────────────────────────────────

def test_section_label_emits_html(mock_st):
    """section_label must call st.markdown with HTML containing the label text."""
    from dashboard.components.theme import section_label
    section_label("TEST SECTION")
    called_html = mock_st.markdown.call_args[0][0]
    assert "TEST SECTION" in called_html
    assert "swl-section-label" in called_html


def test_verdict_badge_go(mock_st):
    """verdict_badge GO must produce correct ARIA label and CSS class."""
    from dashboard.components.theme import verdict_badge
    verdict_badge("GO", css_class="swl-verdict-go")
    html = mock_st.markdown.call_args[0][0]
    assert "GO" in html
    assert "swl-verdict-go" in html
    assert 'aria-label' in html


def test_verdict_badge_scrub(mock_st):
    """verdict_badge SCRUB must produce correct CSS class."""
    from dashboard.components.theme import verdict_badge
    verdict_badge("SCRUB", css_class="swl-verdict-scrub")
    html = mock_st.markdown.call_args[0][0]
    assert "swl-verdict-scrub" in html


def test_ibm_bob_badge_emits_aria(mock_st):
    """IBM Bob badge must include an aria-label."""
    from dashboard.components.theme import ibm_bob_badge
    ibm_bob_badge()
    html = mock_st.markdown.call_args[0][0]
    assert "IBM Bob" in html
    assert "aria-label" in html


def test_plotly_dark_layout_has_required_keys():
    """plotly_dark_layout must return a dict with all required Plotly keys."""
    from dashboard.components.theme import plotly_dark_layout
    layout = plotly_dark_layout()
    assert "paper_bgcolor" in layout
    assert "plot_bgcolor" in layout
    assert "font" in layout
    assert "hoverlabel" in layout
    assert layout["paper_bgcolor"] == "#0D1220"


def test_plotly_dark_layout_merges_kwargs():
    """plotly_dark_layout must merge caller kwargs over defaults."""
    from dashboard.components.theme import plotly_dark_layout
    layout = plotly_dark_layout(height=500, title="Test")
    assert layout["height"] == 500
    assert layout["title"] == "Test"
    assert layout["paper_bgcolor"] == "#0D1220"


# ── SHAP bar chart tests ──────────────────────────────────────────────────────

def test_shap_bar_chart_empty(mock_st):
    """shap_bar_chart with empty list must call st.caption, not crash."""
    from dashboard.components.theme import shap_bar_chart
    shap_bar_chart([])
    mock_st.caption.assert_called_once()


def test_shap_bar_chart_html_structure(mock_st):
    """shap_bar_chart must render role=list and role=meter for accessibility."""
    from dashboard.components.theme import shap_bar_chart
    items = [
        {"feature": "kp_3d_avg",   "shap_value":  0.15},
        {"feature": "gst_level",   "shap_value": -0.08},
    ]
    shap_bar_chart(items)
    html = mock_st.markdown.call_args[0][0]
    assert 'role="list"' in html
    assert 'role="meter"' in html
    assert "shap-bar-pos" in html
    assert "shap-bar-neg" in html


def test_shap_bar_chart_positive_vs_negative_class(mock_st):
    """Positive SHAP must use shap-bar-pos; negative must use shap-bar-neg."""
    from dashboard.components.theme import shap_bar_chart
    items = [
        {"feature": "flux",  "shap_value":  0.2},
        {"feature": "storm", "shap_value": -0.1},
    ]
    shap_bar_chart(items)
    html = mock_st.markdown.call_args[0][0]
    assert "shap-bar-pos" in html
    assert "shap-bar-neg" in html
    assert "shap-pos" in html
    assert "shap-neg" in html


# ── Telemetry table tests ─────────────────────────────────────────────────────

def test_telemetry_table_basic(mock_st):
    """telemetry_table must emit a <table> with correct headers."""
    from dashboard.components.theme import telemetry_table
    rows = [{"Model": "XGBoost", "AUC": "0.9143"}]
    telemetry_table(rows, ["Model","AUC"])
    html = mock_st.markdown.call_args[0][0]
    assert "<table" in html
    assert "Model" in html
    assert "AUC" in html
    assert "XGBoost" in html


def test_telemetry_table_color_col(mock_st):
    """telemetry_table color_col must apply val-hi / val-lo CSS classes."""
    from dashboard.components.theme import telemetry_table
    rows = [
        {"Model": "RF",  "AUC": "0.90"},
        {"Model": "LR",  "AUC": "0.45"},
    ]
    telemetry_table(rows, ["Model","AUC"], color_col="AUC")
    html = mock_st.markdown.call_args[0][0]
    assert "val-hi" in html or "val-mid" in html or "val-lo" in html


def test_telemetry_table_empty_rows(mock_st):
    """telemetry_table with zero rows must not crash."""
    from dashboard.components.theme import telemetry_table
    telemetry_table([], ["Col1","Col2"])
    mock_st.markdown.assert_called_once()


# ── Favicon asset test ────────────────────────────────────────────────────────

def test_favicon_svg_is_valid_xml():
    """favicon.svg must be well-formed XML and contain required elements."""
    import xml.etree.ElementTree as ET
    svg_path = ROOT / "dashboard" / "assets" / "icons" / "favicon.svg"
    assert svg_path.exists(), "favicon.svg not found"
    tree = ET.parse(str(svg_path))
    root = tree.getroot()
    # SVG root element
    assert "svg" in root.tag.lower()


# ── Streamlit config test ─────────────────────────────────────────────────────

def test_streamlit_config_exists():
    """Streamlit config.toml must exist with dark theme settings."""
    config = ROOT / ".streamlit" / "config.toml"
    assert config.exists(), ".streamlit/config.toml not found"
    content = config.read_text()
    assert "dark" in content
    assert "#080B14" in content


# ── Pages exist test ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("page_glob,desc", [
    ("1_*_Data_Pipeline.py", "Data Pipeline page"),
    ("2_*_Model_Lab.py",     "Model Lab page"),
    ("3_*_Prediction_Explorer.py", "Prediction Explorer page"),
    ("4_*_About.py",         "About page"),
])
def test_page_file_exists(page_glob, desc):
    """Each multi-page Streamlit page file must exist."""
    pages_dir = ROOT / "dashboard" / "pages"
    matches = list(pages_dir.glob(page_glob))
    assert matches, f"Missing page file matching '{page_glob}' ({desc})"


# ── Page syntax check ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("page_glob", [
    "1_*_Data_Pipeline.py",
    "2_*_Model_Lab.py",
    "3_*_Prediction_Explorer.py",
    "4_*_About.py",
])
def test_page_is_valid_python(page_glob):
    """Each page file must contain valid Python (parse-able AST)."""
    import ast
    pages_dir = ROOT / "dashboard" / "pages"
    files = list(pages_dir.glob(page_glob))
    assert files, f"No file found for {page_glob}"
    src = files[0].read_text(encoding="utf-8")
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {files[0].name}: {e}")


def test_app_py_is_valid_python():
    """dashboard/app.py must contain valid Python."""
    import ast
    app = ROOT / "dashboard" / "app.py"
    src = app.read_text(encoding="utf-8")
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in app.py: {e}")


def test_theme_py_is_valid_python():
    """dashboard/components/theme.py must contain valid Python."""
    import ast
    src = (ROOT / "dashboard" / "components" / "theme.py").read_text(encoding="utf-8")
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in theme.py: {e}")
