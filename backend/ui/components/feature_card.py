"""Dashboard feature-card component."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_feature_card(
    *,
    icon: str,
    icon_color: str = "blue",
    title: str,
    description: str,
    meta: str = "",
    variant: str = "",
) -> None:
    """Render a dashboard feature tile with icon chip, title, description, and optional meta."""
    safe_title = escape(title)
    safe_color = escape(icon_color, quote=True)

    variant_class = f" dashboard-feature-card--{escape(variant, quote=True)}" if variant else ""
    meta_html = f'<div class="dashboard-feature-meta">{escape(meta)}</div>' if meta else ""

    st.markdown(
        f'<div class="dashboard-feature-card{variant_class}" role="region" aria-label="{safe_title}">'
        f'<div class="db-icon-chip db-icon-chip--{safe_color}" aria-hidden="true">{escape(icon)}</div>'
        f'<div class="dashboard-feature-title">{safe_title}</div>'
        f'<div class="dashboard-feature-desc">{escape(description)}</div>'
        f"{meta_html}"
        "</div>",
        unsafe_allow_html=True,
    )
