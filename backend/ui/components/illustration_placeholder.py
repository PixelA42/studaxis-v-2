"""Illustration placeholder component."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_illustration(
    *,
    ratio: str = "4:3",
    label: str = "Illustration Placeholder",
) -> None:
    """Render a decorative illustration placeholder with a dashed border."""
    ratio_class = (
        "performance-illustration--sixteen-nine"
        if ratio == "16:9"
        else "performance-illustration--four-three"
    )

    st.markdown(
        f'<div class="performance-illustration {ratio_class}"'
        f' aria-hidden="true"'
        f' title="{escape(label, quote=True)}">'
        "</div>",
        unsafe_allow_html=True,
    )
