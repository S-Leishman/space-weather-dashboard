"""
Design system injector — loads CSS, injects starfield canvas + CRT overlay.
IBM Bob generated — Frontend Phase.
"""
from __future__ import annotations

from pathlib import Path
import streamlit as st

_CSS_PATH = Path(__file__).parent.parent / "assets" / "css" / "space_theme.css"


def inject_design_system() -> None:
    """Call once at the top of every page to apply the design system."""
    # Load external CSS
    if _CSS_PATH.exists():
        css = _CSS_PATH.read_text(encoding="utf-8")
    else:
        css = ""  # fallback: no crash if file missing during tests

    # Starfield + CRT + CSS injection.
    # NOTE: Streamlit strips <script> elements from st.markdown output but keeps
    # their text content, which renders the script body as visible page text.
    # The starfield is therefore rendered entirely in CSS — no script is emitted.
    html = (
        f"<style>{css}</style>"
        '<div class="crt-overlay" aria-hidden="true"></div>'
        '<div id="starfield-canvas" aria-hidden="true"></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def section_label(text: str) -> None:
    """Render a monospace section eyebrow label."""
    st.markdown(
        f'<div class="swl-section-label" role="heading" aria-level="3">{text}</div>',
        unsafe_allow_html=True,
    )


def verdict_badge(label: str, css_class: str = "swl-verdict-go") -> None:
    """Render a styled verdict badge (GO / HOLD / SCRUB)."""
    orb_map = {
        "swl-verdict-go":   "swl-orb-go",
        "swl-verdict-hold": "swl-orb-hold",
        "swl-verdict-scrub":"swl-orb-scrub",
    }
    orb = orb_map.get(css_class, "swl-orb-blue")
    st.markdown(
        f'<div class="swl-verdict {css_class}" role="status" aria-label="Launch verdict: {label}">'
        f'<span class="swl-orb {orb}"></span>{label}</div>',
        unsafe_allow_html=True,
    )


def ibm_bob_badge() -> None:
    """Render the IBM Bob attribution badge."""
    st.markdown(
        '<span class="ibm-bob-badge" aria-label="Built with IBM Bob">'
        '⬡ Built with IBM Bob</span>',
        unsafe_allow_html=True,
    )


def shap_bar_chart(shap_items: list[dict], max_abs: float | None = None) -> None:
    """
    Render an accessible SHAP contribution chart in pure HTML/CSS.
    Each item: {"feature": str, "shap_value": float}
    """
    if not shap_items:
        st.caption("No SHAP data available.")
        return

    if max_abs is None:
        max_abs = max(abs(d["shap_value"]) for d in shap_items) or 1.0

    rows = []
    for item in shap_items:
        val    = item["shap_value"]
        feat   = item["feature"]
        pct    = int(abs(val) / max_abs * 100)
        is_pos = val >= 0
        bar_cls  = "shap-bar-pos" if is_pos else "shap-bar-neg"
        val_cls  = "shap-pos" if is_pos else "shap-neg"
        sign     = "+" if is_pos else ""
        label_id = feat.replace("_", "-")
        rows.append(
            f'<div class="shap-row" role="listitem" aria-label="{feat}: {sign}{val:.4f}">'
            f'  <span class="shap-feature" id="shap-{label_id}">{feat}</span>'
            f'  <div class="shap-bar-track" role="meter" aria-labelledby="shap-{label_id}"'
            f'       aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">'
            f'    <div class="shap-bar-fill {bar_cls}" style="width:{pct}%"></div>'
            f'  </div>'
            f'  <span class="shap-value {val_cls}" aria-hidden="true">{sign}{val:.4f}</span>'
            f'</div>'
        )
    html = (
        '<div role="list" aria-label="SHAP feature contributions">'
        + "".join(rows)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def telemetry_table(rows: list[dict], columns: list[str],
                    color_col: str | None = None) -> None:
    """
    Render an accessible HTML telemetry table.
    rows: list of dicts keyed by column names.
    color_col: optional column name to apply traffic-light coloring.
    """
    th_cells = "".join(f"<th scope='col'>{c}</th>" for c in columns)
    body_rows = []
    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col, "—")
            if color_col and col == color_col:
                try:
                    fval = float(val)
                    cls = "val-hi" if fval >= 0.8 else "val-mid" if fval >= 0.5 else "val-lo"
                except (ValueError, TypeError):
                    cls = "val-neu"
                cells.append(f"<td class='{cls}'>{val}</td>")
            else:
                cells.append(f"<td>{val}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    html = (
        "<table class='tel-table' role='table'>"
        f"<thead><tr>{th_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    st.markdown(html, unsafe_allow_html=True)


def metric_pill(label: str, value: str) -> str:
    """Return HTML for an inline metric pill."""
    return (
        f"<span class='metric-pill'>{label}: "
        f"<span class='pill-val'>{value}</span></span>"
    )


def plotly_dark_layout(**kwargs) -> dict:
    """Return a Plotly layout dict matching the design system."""
    base = dict(
        paper_bgcolor="#0D1220",
        plot_bgcolor="#080B14",
        font=dict(family="IBM Plex Mono, monospace", color="#8892A4", size=11),
        xaxis=dict(
            gridcolor="#1C2640",
            linecolor="#1C2640",
            tickcolor="#4A5568",
            zerolinecolor="#1C2640",
        ),
        yaxis=dict(
            gridcolor="#1C2640",
            linecolor="#1C2640",
            tickcolor="#4A5568",
            zerolinecolor="#1C2640",
        ),
        legend=dict(
            bgcolor="rgba(13,18,32,0.8)",
            bordercolor="#1C2640",
            borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=12, r=12, t=32, b=12),
        hoverlabel=dict(
            bgcolor="#0D1220",
            bordercolor="#1C2640",
            font=dict(family="IBM Plex Mono", color="#E8EDF5"),
        ),
    )
    base.update(kwargs)
    return base
