"""Page-level chrome: root wrappers, background blobs, and back button."""
from __future__ import annotations

from html import escape

import streamlit as st

_PAGE_ROOT_MAP: dict[str, str] = {
    "dashboard": "dashboard-root",
    "chat": "chat-root",
    "settings": "settings-root",
}


def render_page_root_open(page_name: str, theme: str = "light") -> None:
    """Emit the opening ``<div>`` for a page root with optional dark-theme class."""
    root_class = _PAGE_ROOT_MAP.get(page_name, f"{escape(page_name, quote=True)}-root")
    theme_class = " theme-dark" if theme == "dark" else ""

    st.markdown(
        f'<div class="{root_class}{theme_class}">',
        unsafe_allow_html=True,
    )


def render_page_root_close() -> None:
    """Emit the closing ``</div>`` for a page root."""
    st.markdown("</div>", unsafe_allow_html=True)


def render_background_blobs(blobs: list[str] | None = None) -> None:
    """Render decorative background gradient blobs."""
    blob_names = blobs if blobs is not None else ["warm-tr", "blue-bl"]
    children = "".join(
        f'<div class="page-blob page-blob--{escape(name, quote=True)}"></div>'
        for name in blob_names
    )

    st.markdown(
        f'<div class="page-blob-layer" aria-hidden="true">{children}</div>',
        unsafe_allow_html=True,
    )


def render_back_button(
    target_page: str = "dashboard",
    label: str = "\u2190 Back to Dashboard",
) -> bool:
    """Render a back-navigation button. Returns ``True`` if clicked (triggers rerun)."""
    if st.button(label, key=f"back_to_{target_page}"):
        st.session_state.page = target_page
        st.rerun()
        return True
    return False
