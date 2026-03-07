"""
Studaxis — Profile Page
════════════════════════════════════════════════════════════════════
User profile management and preferences display.
"""

from __future__ import annotations

import streamlit as st

from profile_store import UserProfile, load_profile, save_profile
from ui.components.page_chrome import render_background_blobs, render_page_root_close, render_page_root_open


def show_profile() -> None:
    """Render the user profile page."""
    theme = st.session_state.get("theme", "light")
    profile_name = st.session_state.get("profile_name", "Student")
    profile_mode = st.session_state.get("profile_mode", "solo")
    class_code = st.session_state.get("class_code")
    
    render_background_blobs()
    render_page_root_open("profile", theme)
    
    st.markdown(
        f"""
        <div class="dashboard-header-card" role="banner" style="margin-bottom: 24px;">
            <div class="dashboard-header-left">
                <div class="dashboard-avatar" style="width: 64px; height: 64px; font-size: 28px;">
                    {profile_name[0].upper() if profile_name else 'S'}
                </div>
                <div class="dashboard-welcome-text">
                    <span class="dashboard-welcome-name" style="font-size: 24px;">{profile_name}</span>
                    <span class="dashboard-welcome-sub">
                        {'Solo Learner' if profile_mode == 'solo' else 'Class Linked'}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("### Profile Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            """
            <div class="dashboard-stat-card" style="margin-bottom: 16px;">
                <span class="dashboard-stat-icon">👤</span>
                <span class="dashboard-stat-label">Display Name</span>
                <span class="dashboard-stat-number" style="font-size: 20px;">""" + profile_name + """</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        mode_display = "Solo Mode" if profile_mode == "solo" else "Class Linked"
        if profile_mode == "teacher_linked_provisional":
            mode_display = "Class Linked (Pending)"
        
        st.markdown(
            f"""
            <div class="dashboard-stat-card" style="margin-bottom: 16px;">
                <span class="dashboard-stat-icon">📚</span>
                <span class="dashboard-stat-label">Learning Mode</span>
                <span class="dashboard-stat-number" style="font-size: 20px;">{mode_display}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    if class_code:
        st.markdown(
            f"""
            <div class="dashboard-stat-card" style="margin-bottom: 16px;">
                <span class="dashboard-stat-icon">🔗</span>
                <span class="dashboard-stat-label">Class Code</span>
                <span class="dashboard-stat-number" style="font-size: 18px; font-family: 'JetBrains Mono', monospace;">{class_code}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown("---")
    st.markdown("### Edit Profile")
    
    new_name = st.text_input(
        "Update display name",
        value=profile_name,
        key="profile_name_edit",
    )
    
    col_save, col_back, _ = st.columns([1, 1, 2])
    
    with col_save:
        if st.button("Save Changes", type="primary", use_container_width=True):
            if new_name.strip():
                st.session_state.profile_name = new_name.strip()
                profile = UserProfile(
                    profile_name=new_name.strip(),
                    profile_mode=profile_mode,
                    class_code=class_code,
                    user_role=st.session_state.get("user_role", "student"),
                )
                save_profile(profile)
                st.success("Profile updated successfully!")
                st.rerun()
            else:
                st.error("Name cannot be empty.")
    
    with col_back:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    
    render_page_root_close()
