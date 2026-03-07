import streamlit as st
from ui.components.page_chrome import render_background_blobs


def show_auth() -> None:
    # Decorative background blobs
    render_background_blobs()

    # Glass card header
    st.markdown(
        """
        <div class="auth-root">
          <div class="auth-card">
            <div class="auth-logo" aria-hidden="true">🎓</div>
            <h1 class="auth-title">Welcome back</h1>
            <p class="auth-subtitle">Sign in to continue your learning journey</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Form fields — native Streamlit widgets (unmodified)
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="auth-actions-primary">', unsafe_allow_html=True)
        if st.button("Sign In", use_container_width=True):
            if username and password:
                st.session_state.user_logged_in = True
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Please enter username and password.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="auth-actions-secondary">', unsafe_allow_html=True)
        if st.button("Back", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
