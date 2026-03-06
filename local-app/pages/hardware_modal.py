"""
Hardware Warning Modal UI

Pure UI component that renders the glassmorphism hardware warning modal.
It expects hardware specs and optimization tips computed elsewhere.
"""

from typing import Dict, List, Optional, Tuple

import streamlit as st

from pages.hardware_validator import HardwareValidator


def _ensure_modal_state() -> None:
    if "hardware_modal_open" not in st.session_state:
        st.session_state.hardware_modal_open = True


def render_hardware_warning_modal(
    specs: Dict,
    tips: List[str],
    theme: str = "light",
) -> Tuple[bool, Optional[str]]:
    """
    Render the hardware warning modal.

    Args:
        specs: Dict from HardwareValidator._gather_specs().
        tips: Optimization tips from HardwareValidator.get_optimization_tips().
        theme: "light" or "dark" (for future theme-aware styling hooks).

    Returns:
        modal_visible: True if modal is currently shown.
        action: "continue" | "optimize" | None
    """
    _ensure_modal_state()

    if not st.session_state.get("hardware_modal_open", True):
        return False, None

    ram_gb = specs.get("ram_gb")
    disk_free_gb = specs.get("disk_free_gb")

    ram_min = HardwareValidator.MIN_RAM_GB
    disk_min = HardwareValidator.MIN_DISK_GB

    # Determine severity styling for specs
    ram_class = "hardware-specs-metric-value"
    if ram_gb is not None and ram_gb < ram_min:
        ram_class += " hardware-specs-metric-value--danger"

    disk_class = "hardware-specs-metric-value"
    if disk_free_gb is not None and disk_free_gb < disk_min:
        disk_class += " hardware-specs-metric-value--danger"

    # Headline + subtitle copy aligned with requirements tone
    headline = "Your laptop just meets Studaxis requirements"
    subtitle = (
        "Studaxis will run on this device, but some actions may feel slower on 4 GB RAM. "
        "You can still continue, or apply a few safe optimizations first."
    )

    with st.container():
        st.markdown(
            """
            <div class="hardware-modal-backdrop">
              <div class="hardware-modal-gradient"></div>
              <div class="hardware-modal-card" role="dialog" aria-modal="true" aria-labelledby="hardware-modal-title">
                <div class="hardware-modal-heading-row">
                  <div class="hardware-modal-icon" aria-hidden="true">⚠️</div>
                  <div>
                    <h2 id="hardware-modal-title" class="hardware-modal-title">
                      {headline}
                    </h2>
                    <p class="hardware-modal-subtitle">
                      {subtitle}
                    </p>
                  </div>
                </div>
                <div class="hardware-specs-grid">
                  <div>
                    <div class="hardware-specs-metric-label">RAM</div>
                    <div class="{ram_class}">
                      {ram_gb} GB &nbsp; / &nbsp; minimum {ram_min} GB
                    </div>
                  </div>
                  <div>
                    <div class="hardware-specs-metric-label">Disk space (free)</div>
                    <div class="{disk_class}">
                      {disk_free_gb} GB &nbsp; / &nbsp; minimum {disk_min} GB
                    </div>
                  </div>
                </div>
                <div>
                  <div class="hardware-tips-title">Optimization tips for this laptop</div>
                  <ul class="hardware-tips-list">
                    {tips_html}
                  </ul>
                </div>
              </div>
            </div>
            """.format(
                headline=headline,
                subtitle=subtitle,
                ram_class=ram_class,
                disk_class=disk_class,
                ram_gb=ram_gb,
                ram_min=ram_min,
                disk_free_gb=disk_free_gb,
                disk_min=disk_min,
                tips_html="".join(f"<li>{tip}</li>" for tip in tips) or "<li>No extra tips needed for this device.</li>",
            ),
            unsafe_allow_html=True,
        )

        action: Optional[str] = None

        with st.container():
            st.markdown('<div class="hardware-modal-buttons">', unsafe_allow_html=True)
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button(
                    "Continue anyway",
                    key="hardware_modal_continue",
                    use_container_width=True,
                ):
                    st.session_state.hardware_modal_open = False
                    action = "continue"
            with col2:
                if st.button(
                    "Optimize settings",
                    key="hardware_modal_optimize",
                    use_container_width=True,
                ):
                    st.session_state.hardware_modal_open = False
                    action = "optimize"
            st.markdown("</div>", unsafe_allow_html=True)

    return True, action

