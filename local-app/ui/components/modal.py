"""Modal backdrop component."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_modal_backdrop(
    content_html: str,
    *,
    modal_id: str = "modal",
    modal_class: str = "",
    aria_label: str = "Dialog",
) -> None:
    """Render a fixed-position error-modal backdrop with inner modal panel."""
    inner_classes = f"error-modal {modal_class}".strip()

    st.markdown(
        f'<div class="error-modal-backdrop" role="dialog" aria-modal="true"'
        f' aria-labelledby="{escape(modal_id, quote=True)}"'
        f' aria-label="{escape(aria_label, quote=True)}">'
        f'<div class="{escape(inner_classes, quote=True)}">'
        f"{content_html}"
        f"</div></div>",
        unsafe_allow_html=True,
    )
