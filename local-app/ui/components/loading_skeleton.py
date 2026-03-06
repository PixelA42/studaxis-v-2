"""Loading-skeleton and lazy-card components."""
from __future__ import annotations

from html import escape

import streamlit as st

_SKELETON_CARD = (
    '<div class="performance-skeleton-card">'
    '<div class="performance-skeleton-row performance-skeleton-row--sm"></div>'
    '<div class="performance-skeleton-row performance-skeleton-row--lg"></div>'
    '<div class="performance-skeleton-row performance-skeleton-row--md"></div>'
    "</div>"
)

_SKELETON_LIST_ITEM = (
    '<div class="performance-skeleton-list__item">'
    '<div class="performance-skeleton-avatar"></div>'
    "<div>"
    '<div class="performance-skeleton-row performance-skeleton-row--md"></div>'
    '<div class="performance-skeleton-row performance-skeleton-row--sm"></div>'
    "</div></div>"
)


def render_stats_skeleton() -> None:
    """Render a 3-card grid skeleton placeholder."""
    st.markdown(
        '<div class="performance-skeleton-grid" role="status"'
        ' aria-busy="true" aria-label="Loading dashboard statistics">'
        f"{_SKELETON_CARD}{_SKELETON_CARD}{_SKELETON_CARD}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_chart_skeleton() -> None:
    """Render a chart-area skeleton placeholder."""
    st.markdown(
        '<div class="performance-skeleton-chart" role="status"'
        ' aria-busy="true" aria-label="Loading chart">'
        '<div class="performance-skeleton-row performance-skeleton-row--sm"></div>'
        '<div class="performance-skeleton-row performance-skeleton-row--md"></div>'
        '<div class="performance-skeleton-chart__plot"></div>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_list_skeleton() -> None:
    """Render a 3-item list skeleton placeholder."""
    st.markdown(
        '<div class="performance-skeleton-list" role="status"'
        ' aria-busy="true" aria-label="Loading list">'
        f"{_SKELETON_LIST_ITEM}{_SKELETON_LIST_ITEM}{_SKELETON_LIST_ITEM}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_lazy_card(
    title: str,
    description: str = "Loading data...",
    ratio: str = "4:3",
) -> None:
    """Render a loading card with spinner and illustration placeholder."""
    ratio_class = (
        "performance-illustration--sixteen-nine"
        if ratio == "16:9"
        else "performance-illustration--four-three"
    )

    st.markdown(
        '<div class="performance-loading-card" role="status" aria-busy="true">'
        '<div class="performance-loading-card__head"><div>'
        f'<h3 class="performance-loading-card__title">{escape(title)}</h3>'
        f'<p class="performance-loading-card__desc">{escape(description)}</p>'
        '</div><span class="performance-loading-spinner" aria-hidden="true"></span></div>'
        f'<div class="performance-illustration {ratio_class}" aria-hidden="true"></div>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_chat_typing_skeleton() -> None:
    """Render the chat typing-indicator skeleton with 3 shimmer lines."""
    st.markdown(
        '<div class="chat-skeleton-wrap" role="status" aria-busy="true"'
        ' aria-label="AI Tutor is generating a response">'
        '<div class="chat-skeleton-bubble">'
        '<div class="chat-skeleton-line"></div>'
        '<div class="chat-skeleton-line"></div>'
        '<div class="chat-skeleton-line"></div>'
        "</div></div>",
        unsafe_allow_html=True,
    )
