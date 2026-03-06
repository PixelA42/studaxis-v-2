import streamlit as st
from ui.components.page_chrome import render_background_blobs


def show_landing() -> None:
    # Decorative background blobs
    render_background_blobs(["warm-tr", "blue-bl", "warm-center"])

    # Hero glass card
    st.markdown(
        """
        <div class="landing-root">
          <div class="landing-card">
            <h1 class="landing-headline">
              organize <span class="landing-highlight">everything</span><br>
              in your <span class="landing-blue">learning<span class="landing-blue-underline"></span></span>
            </h1>
            <p class="landing-subtitle">
              AI-powered offline tutor that works anywhere, anytime —<br>
              even at 0 kbps.
            </p>
            <div class="landing-badge-row">
              <span class="landing-badge">⚡ 100% Offline</span>
              <span class="landing-badge">🤖 Llama 3.2 on-device</span>
              <span class="landing-badge">📚 RAG-grounded</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # CTA button — wrapped in scoped div for landing-specific button style
    st.markdown('<div class="landing-cta">', unsafe_allow_html=True)
    if st.button("Get Started →", use_container_width=True):
        if st.session_state.get("user_logged_in", False):
            st.session_state.page = "dashboard"
        else:
            st.session_state.page = "auth"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
