"""Boot-splash layout — shared shell for all boot-flow screens."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_boot_splash(title: str, subtitle: str) -> None:
    """Render the boot-root > boot-main > boot-glass-card splash shell."""
    st.markdown(
        '<div class="boot-root">'
        '<div class="boot-main">'
        '<div class="boot-glass-card" role="status" aria-busy="true">'
        f'<h1 class="boot-title">{escape(title)}</h1>'
        f'<p class="boot-subtitle">{escape(subtitle)}</p>'
        "</div></div></div>",
        unsafe_allow_html=True,
    )
