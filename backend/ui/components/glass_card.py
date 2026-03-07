"""Glass-card and boot-card HTML components."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_glass_card(
    content_html: str,
    *,
    css_class: str = "",
    role: str = "",
    aria_label: str = "",
    aria_busy: bool = False,
) -> None:
    """Render a glassmorphism card wrapping arbitrary *content_html*."""
    classes = f"glass-card {css_class}".strip()
    attrs = ""
    if role:
        attrs += f' role="{escape(role, quote=True)}"'
    if aria_label:
        attrs += f' aria-label="{escape(aria_label, quote=True)}"'
    if aria_busy:
        attrs += ' aria-busy="true"'

    st.markdown(
        f'<div class="{escape(classes, quote=True)}"{attrs}>{content_html}</div>',
        unsafe_allow_html=True,
    )


def render_boot_card(title: str, subtitle: str) -> None:
    """Render the boot-flow glass card shell with *title* and *subtitle*."""
    st.markdown(
        '<div class="boot-root">'
        '<div class="boot-main">'
        '<div class="boot-glass-card" role="status" aria-busy="true">'
        f'<h1 class="boot-title">{escape(title)}</h1>'
        f'<p class="boot-subtitle">{escape(subtitle)}</p>'
        "</div></div></div>",
        unsafe_allow_html=True,
    )
