"""
Studaxis — Collapsible Sidebar Navigation Component
════════════════════════════════════════════════════════════════════
Fixed glass sidebar with JavaScript toggle (localStorage), matching
the Flash UI reference pattern.

Navigation: Dashboard, Chat, Flashcards, Quiz, Insights, Panic Mode,
            Conflicts, Sync Status, Settings, Profile
"""

from __future__ import annotations

import streamlit as st


def _get_current_page() -> str:
    """Get current page from URL query params. Backward-compatible with older Streamlit."""
    if hasattr(st, "query_params"):
        q = st.query_params
        page = q.get("page") if hasattr(q, "get") else None
        if isinstance(page, list):
            page = page[0] if page else None
        if page:
            return page
    try:
        raw = st.experimental_get_query_params()
        if raw and "page" in raw:
            v = raw["page"]
            return v[0] if isinstance(v, list) else v
    except Exception:
        pass
    return "dashboard"


def _get_nav_items(conflicts_count: int = 0) -> list[dict]:
    """Return navigation items with icons."""
    return [
        {"id": "dashboard", "label": "Dashboard", "icon": "fa-solid fa-border-all", "section": "core"},
        {"id": "chat", "label": "AI Chat", "icon": "fa-solid fa-robot", "section": "core"},
        {"id": "flashcards", "label": "Flashcards", "icon": "fa-solid fa-layer-group", "section": "core"},
        {"id": "quiz", "label": "Quiz", "icon": "fa-solid fa-clipboard-question", "section": "core"},
        {"id": "insights", "label": "Insights", "icon": "fa-solid fa-chart-line", "section": "analytics"},
        {"id": "panic_mode", "label": "Panic Mode", "icon": "fa-solid fa-fire", "section": "analytics", "class": "panic-mode"},
        {"id": "conflicts", "label": "Conflicts", "icon": "fa-solid fa-code-compare", "section": "system", "badge": conflicts_count, "badge_type": "error"},
        {"id": "sync_status", "label": "Sync Status", "icon": "fa-solid fa-arrows-rotate", "section": "system"},
        {"id": "settings", "label": "Settings", "icon": "fa-solid fa-gear", "section": "footer"},
        {"id": "profile", "label": "Profile", "icon": "fa-solid fa-user", "section": "footer"},
    ]


def _build_nav_section(items: list[dict], current_page: str, label: str) -> str:
    """Build HTML for a nav section."""
    lines = []
    if label:
        lines.append(f'<div class="nav-label">{label}</div>')
    for i in items:
        active = "active" if current_page == i["id"] else ""
        extra = i.get("class", "")
        badge = ""
        if i.get("badge"):
            badge = f'<span class="nav-badge">{i["badge"]}</span>'
        lines.append(
            f'<a href="?page={i["id"]}" target="_self" class="nav-item {active} {extra}" title="{i["label"]}">'
            f'<i class="{i["icon"]}"></i><span class="label">{i["label"]}</span>{badge}'
            "</a>"
        )
    return f'<div class="nav-section">{"".join(lines)}</div>'


def _build_footer_html(items: list[dict], current_page: str) -> str:
    """Build HTML for footer nav items (no section label)."""
    lines = []
    for i in items:
        active = "active" if current_page == i["id"] else ""
        lines.append(
            f'<a href="?page={i["id"]}" target="_self" class="nav-item {active}" title="{i["label"]}">'
            f'<i class="{i["icon"]}"></i><span class="label">{i["label"]}</span>'
            "</a>"
        )
    return "".join(lines)


def render_sidebar(
    current_page: str = "dashboard",
    profile_name: str | None = None,
    conflicts_count: int = 0,
    sync_status: str = "offline",
    theme: str = "light",
) -> None:
    """
    Render the collapsible sidebar using JavaScript + localStorage for toggle.
    Matches Flash UI reference: toggle button middle-right, dynamic --sidebar-width.
    """
    nav_items = _get_nav_items(conflicts_count)
    core = [i for i in nav_items if i["section"] == "core"]
    analytics = [i for i in nav_items if i["section"] == "analytics"]
    system = [i for i in nav_items if i["section"] == "system"]
    footer = [i for i in nav_items if i["section"] == "footer"]

    core_html = _build_nav_section(core, current_page, "Core Tools")
    analytics_html = _build_nav_section(analytics, current_page, "Analytics")
    system_html = _build_nav_section(system, current_page, "System")
    footer_html = _build_footer_html(footer, current_page)

    custom_html = f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<style>
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stApp {{background: #f0f2f5;}}
    
    :root {{  /* double curly braces for f-string escaping */
        --alabaster-base: rgba(252, 252, 252, 0.82);
        --accent-blue: #00A8E8;
        --text-primary: #1a1a1a;
        --text-secondary: rgba(26, 26, 26, 0.5);
        --glass-border: rgba(255, 255, 255, 0.4);
        --sidebar-width: 260px;
        --transition-smooth: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    }}

    .block-container {{
        padding-top: 40px !important;
        padding-left: calc(var(--sidebar-width) + 60px) !important;
        max-width: 100% !important;
        transition: padding-left 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    }}

    .sidebar {{
        position: fixed;
        left: 20px;
        top: 20px;
        bottom: 20px;
        width: var(--sidebar-width);
        background: var(--alabaster-base);
        backdrop-filter: blur(20px) saturate(160%);
        -webkit-backdrop-filter: blur(20px) saturate(160%);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.05);
        display: flex;
        flex-direction: column;
        z-index: 1000;
        font-family: 'Inter', sans-serif;
        transition: var(--transition-smooth);
    }}

    .sidebar-toggle {{
        position: absolute;
        right: -14px;
        top: 50%;
        transform: translateY(-50%);
        width: 28px;
        height: 28px;
        background: white;
        border: 1px solid var(--glass-border);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 1001;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        color: var(--text-primary);
        transition: var(--transition-smooth);
    }}
    .sidebar-toggle:hover {{
        background: var(--accent-blue);
        color: white;
        transform: translateY(-50%) scale(1.1);
    }}

    .nav-header {{ padding: 32px 24px; display: flex; align-items: center; gap: 16px; overflow: hidden; white-space: nowrap; transition: var(--transition-smooth);}}
    .logo-mark {{
        min-width: 32px; height: 32px; background: var(--accent-blue);
        border-radius: 8px; display: flex; align-items: center; justify-content: center;
        color: white; font-weight: 800; font-size: 18px;
        box-shadow: 0 4px 12px rgba(0, 168, 232, 0.3);
    }}
    .logo-text {{ font-weight: 700; font-size: 20px; color: var(--text-primary); transition: opacity 0.2s; }}
    
    .nav-section {{ padding: 0 12px; margin-bottom: 24px; overflow: hidden; }}
    .nav-label {{
        font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase;
        color: var(--text-secondary); margin-bottom: 12px; padding-left: 16px; letter-spacing: 2px;
        transition: opacity 0.2s; white-space: nowrap;
    }}
    
    .nav-item {{
        display: flex; align-items: center; padding: 12px 16px; margin: 4px 0;
        border-radius: 14px; color: var(--text-secondary); text-decoration: none;
        transition: var(--transition-smooth); position: relative; overflow: hidden;
    }}
    .nav-item i {{ font-size: 18px; min-width: 24px; text-align: center; margin-right: 16px; transition: var(--transition-smooth); }}
    .nav-item .label {{ font-weight: 500; font-size: 15px; white-space: nowrap; transition: opacity 0.2s; }}
    .nav-badge {{ font-size: 10px; background: #FA5C5C; color: white; padding: 2px 6px; border-radius: 999px; margin-left: auto; }}
    
    .nav-item:hover {{ background: rgba(255, 255, 255, 0.5); color: var(--text-primary); transform: translateY(-1px); }}
    .nav-item.active {{ background: white; color: var(--text-primary); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03); }}
    .nav-item.active::before {{ 
        content: ''; position: absolute; left: 0; top: 25%; height: 50%; width: 4px;
        background: var(--accent-blue); border-radius: 0 4px 4px 0;
    }}
    .nav-item.active .label {{ font-weight: 700; }}
    .nav-item.active i {{ color: var(--accent-blue); }}
    
    .panic-mode:hover {{ background: rgba(255, 68, 68, 0.1) !important; color: #ff4444 !important; }}
    .nav-footer {{ margin-top: auto; padding: 20px 12px; border-top: 1px solid rgba(0,0,0,0.03); overflow: hidden; }}
    a:hover {{ text-decoration: none !important; }} 

    .sidebar.collapsed {{ --sidebar-width: 80px; }}
    .sidebar.collapsed .logo-text,
    .sidebar.collapsed .nav-label,
    .sidebar.collapsed .label {{ opacity: 0; display: none; }}
    .sidebar.collapsed .nav-badge {{ display: none; }}
    .sidebar.collapsed .nav-header {{ padding: 32px 0; justify-content: center; }}
    .sidebar.collapsed .nav-item {{ justify-content: center; padding: 12px 0; }}
    .sidebar.collapsed .nav-item i {{ margin-right: 0; font-size: 20px; }}
    .sidebar.collapsed .sidebar-toggle i {{ transform: rotate(180deg); }}
</style>

<nav class="sidebar" id="sidebar">
    <div class="sidebar-toggle" onclick="toggleSidebar()">
        <i class="fa-solid fa-chevron-left"></i>
    </div>

    <div class="nav-header">
        <div class="logo-mark">S</div>
        <span class="logo-text">Studaxis</span>
    </div>

    {core_html}
    {analytics_html}
    {system_html}
    <div class="nav-footer">{footer_html}</div>
</nav>

<script>
    const sidebar = document.getElementById('sidebar');
    const root = document.documentElement;
    // Always start with sidebar expanded by default
    sidebar.classList.remove('collapsed');
    root.style.setProperty('--sidebar-width', '260px');
    // reset stored state so subsequent loads default open
    localStorage.setItem('sidebarState', 'expanded');
    // Only toggle on button click
    function toggleSidebar() {{
        sidebar.classList.toggle('collapsed');
        if (sidebar.classList.contains('collapsed')) {{
            localStorage.setItem('sidebarState', 'collapsed');
            root.style.setProperty('--sidebar-width', '80px');
        }} else {{
            localStorage.setItem('sidebarState', 'expanded');
            root.style.setProperty('--sidebar-width', '260px');
        }}
    }}
</script>
"""
    # Streamlit can escape HTML after the first line; collapse to single line to fix
    custom_html = custom_html.replace("\n", " ")
    st.markdown(custom_html, unsafe_allow_html=True)


def get_current_page() -> str:
    """Get current page from URL. Use this in main app for routing."""
    return _get_current_page()


def render_hero_header(
    title: str = "Welcome back",
    name: str | None = None,
    subtitle: str = "AI-powered offline tutor that works anywhere, anytime",
    show_cta: bool = False,
    cta_text: str = "Get Started →",
    theme: str = "light",
) -> bool:
    """Render the hero header section above the dashboard. Renders nothing if name is null (caller should redirect)."""
    if not name:
        return False
    theme_class = "theme-dark" if theme == "dark" else ""
    hero_html = (
        f'<div class="hero-wrapper {theme_class}">'
        '<div class="hero-orb hero-orb-1"></div>'
        '<div class="hero-orb hero-orb-2"></div>'
        '<div class="hero-content">'
        f'<h1 class="hero-title">{title}, <span class="highlight">{name}</span></h1>'
        f'<p class="hero-subtitle">{subtitle}</p>'
        '</div>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(hero_html, width="stretch")
    else:
        st.markdown(hero_html, unsafe_allow_html=True)
    if show_cta:
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            if st.button(cta_text, type="primary", use_container_width=True):
                return True
    return False


def render_compact_header(
    name: str | None = None,
    streak: int = 0,
    mode: str = "Solo Mode",
    connectivity: str = "offline",
    theme: str = "light",
) -> None:
    """Render a compact header bar for non-dashboard pages. Renders nothing if name is null (caller should redirect)."""
    if not name:
        return
    theme_class = "theme-dark" if theme == "dark" else ""
    initials = name[0].upper()
    conn = "● Online" if connectivity == "online" else "○ Offline"
    streak_s = "s" if streak != 1 else ""
    st.markdown(
        f'<div class="dashboard-header-card {theme_class}">'
        f'<div class="dashboard-header-left"><div class="dashboard-avatar">{initials}</div>'
        f'<div class="dashboard-welcome-text"><span class="dashboard-welcome-name">Welcome, {name}</span>'
        f'<span class="dashboard-welcome-sub">Personal Mastery · AI Tutor ready</span></div></div>'
        f'<div class="dashboard-header-right">'
        f'<span class="dashboard-streak-pill">🔥 <span class="streak-count">{streak}</span> day{streak_s}</span>'
        f'<span class="dashboard-mode-badge">{mode}</span>'
        f'<span class="status-pill">{conn}</span></div></div>',
        unsafe_allow_html=True,
    )


def inject_sidebar_layout_css() -> None:
    """Inject layout CSS. Sidebar-specific styles are in render_sidebar."""
    css = """
    <style>
        header[data-testid="stHeader"] { display: none; }
        section[data-testid="stSidebar"] { display: none !important; }
        .stApp { background: #F8FAFC; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


__all__ = [
    "render_sidebar",
    "render_hero_header",
    "render_compact_header",
    "inject_sidebar_layout_css",
    "get_current_page",
]
