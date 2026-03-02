"""
Studaxis - Teacher Dashboard
Glassmorphism UI | AWS Hackathon 2026
Teacher analytics, student progress monitoring, and AI quiz generation.
"""

import streamlit as st
import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any
import requests
from dotenv import load_dotenv
from utils.appsync_s3_broker import (
    AppSyncQLClient,
    S3PresignedURLClient,
    load_quiz_with_presigned_url,
    display_quiz_content
)
from utils.bedrock_client import (
    test_bedrock_connection,
    generate_quiz as bedrock_generate_quiz,
    generate_lesson_summary,
)
from utils.export_helpers import (
    quiz_to_docx, quiz_to_pdf,
    notes_to_docx, notes_to_pdf,
)
from utils.content_uploader import ContentUploader

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# AWS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

s3_client = boto3.client('s3')
dynamodb: Any = boto3.resource('dynamodb')

STUDENT_STATS_BUCKET = os.getenv('STUDENT_STATS_BUCKET', 'studaxis-student-stats-2026')
SYNC_TABLE_NAME = os.getenv('SYNC_TABLE_NAME', 'studaxis-student-sync')
QUIZ_INDEX_TABLE = os.getenv('QUIZ_INDEX_TABLE', 'studaxis-quiz-index')

# AppSync + S3 Broker Configuration
APPSYNC_ENDPOINT = os.getenv('APPSYNC_ENDPOINT', 'https://your-appsync-id.appsync-api.ap-south-1.amazonaws.com/graphql')
APPSYNC_API_KEY = os.getenv('APPSYNC_API_KEY', 'your-api-key-here')
S3_PAYLOADS_BUCKET = os.getenv('S3_PAYLOADS_BUCKET', 'studaxis-payloads')
S3_REGION = os.getenv('S3_REGION', 'ap-south-1')

# ─────────────────────────────────────────────────────────────────────────────
# DEMO MODE: Mock Data Generator
# ─────────────────────────────────────────────────────────────────────────────

def get_demo_student_stats():
    """Generate realistic demo student data for hackathon presentations"""
    return pd.DataFrame({
        'student_id': ['STU001', 'STU002', 'STU003', 'STU004', 'STU005', 'STU006', 'STU007', 'STU008'],
        'last_sync': ['2025-03-02 14:32', '2025-03-02 13:15', '2025-03-01 18:45', '2025-03-02 09:20', 
                      '2025-02-28 16:10', '2025-03-02 15:00', '2025-03-01 22:30', '2025-02-27 10:00'],
        'total_quizzes': [12, 15, 8, 18, 5, 14, 11, 9],
        'avg_score': [87.5, 92.3, 61.2, 88.1, 52.8, 79.4, 85.6, 68.9],
        'current_streak': [12, 15, 0, 18, 0, 10, 11, 3],
        'connectivity_status': ['online', 'online', 'offline', 'online', 'offline', 'online', 'online', 'offline']
    })

def get_demo_sync_metadata():
    """Generate demo sync status data"""
    return pd.DataFrame({
        'student_id': ['STU001', 'STU002', 'STU003', 'STU004', 'STU005', 'STU006', 'STU007', 'STU008'],
        'device_id': ['DEV-001', 'DEV-002', 'DEV-003', 'DEV-004', 'DEV-005', 'DEV-006', 'DEV-007', 'DEV-008'],
        'last_sync_timestamp': ['2025-03-02T14:32:15Z', '2025-03-02T13:15:22Z', '2025-03-01T18:45:10Z', 
                                '2025-03-02T09:20:45Z', '2025-02-28T16:10:30Z', '2025-03-02T15:00:05Z',
                                '2025-03-01T22:30:18Z', '2025-02-27T10:00:00Z'],
        'sync_status': ['online', 'online', 'offline', 'online', 'offline', 'online', 'online', 'offline']
    })

def get_demo_topic_performance():
    """Generate demo topic performance data"""
    return pd.DataFrame({
        'Topic': ['Algebra', 'Geometry', 'Statistics', 'Trigonometry', 'Calculus'],
        'Avg Score': [82.5, 78.3, 85.1, 74.2, 80.8],
        'Students Completed': [45, 42, 48, 38, 41]
    })

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Studaxis — Teacher Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Studaxis Teacher Dashboard v1.0 — Real-time student progress insights"
    }
)

# ─────────────────────────────────────────────────────────────────────────────
# GLASSMORPHISM DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    /* ── Soft ambient mesh gradient ────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg,
            #fdf6ff 0%, #e8f4f8 25%, #f0faf5 50%, #fff7f0 75%, #f8f0ff 100%);
        background-attachment: fixed;
    }

    /* ── Core glass card ─────────────────────────────────────────────────── */
    .glass-card {
        background: rgba(255, 255, 255, 0.35);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.09);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.45);
        padding: 22px 24px;
        margin-bottom: 18px;
        color: #2d334a;
    }

    /* ── 6 gradient profiles ─────────────────────────────────────────────── */
    .grad-maroon { background: linear-gradient(135deg, #6b0f1a 0%, #b91c28 55%, #e11d3f 100%);
                   color: white !important; border: none; }
    .grad-sage   { background: linear-gradient(135deg, #52796f 0%, #74b49b 60%, #a8d8c2 100%);
                   color: white !important; border: none; }
    .grad-blue   { background: linear-gradient(135deg, #1a203c 0%, #1e3a5f 55%, #0ea5e9 100%);
                   color: white !important; border: none; }
    .grad-sunset { background: linear-gradient(135deg, #c2440e 0%, #ea580c 55%, #fb923c 100%);
                   color: white !important; border: none; }
    .grad-purple { background: linear-gradient(135deg, #6d28d9 0%, #8b5cf6 55%, #c4b5fd 100%);
                   color: white !important; border: none; }
    .grad-slate  { background: linear-gradient(135deg, #64748b 0%, #94a3b8 60%, #cbd5e1 100%);
                   color: white !important; border: none; }

    /* ── Metric display ───────────────────────────────────────────────────── */
    .metric-big   { font-size: 2.4rem; font-weight: 800; line-height: 1;
                    margin: 6px 0 3px; letter-spacing: -1px; }
    .metric-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
                    text-transform: uppercase; opacity: 0.82; }
    .metric-delta-pos { color: #4ade80; font-size: 0.82rem; font-weight: 600; }
    .metric-delta-neg { color: #fb923c; font-size: 0.82rem; font-weight: 600; }
    .score-pill {
        display: inline-block; padding: 3px 12px; border-radius: 999px;
        font-size: 0.72rem; font-weight: 700;
        background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.35);
        margin-top: 5px;
    }

    /* ── Student row ──────────────────────────────────────────────────────── */
    .student-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 14px; margin-bottom: 8px; border-radius: 12px;
        background: rgba(255,255,255,0.45); border: 1px solid rgba(255,255,255,0.6);
    }
    .student-row:hover { background: rgba(255,255,255,0.68); }
    .student-avatar {
        width: 38px; height: 38px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.9rem; flex-shrink: 0; margin-right: 12px;
    }
    .sync-dot-ok   { width:9px;height:9px;border-radius:50%;background:#4ade80;display:inline-block; }
    .sync-dot-warn { width:9px;height:9px;border-radius:50%;background:#fb923c;display:inline-block; }
    .sync-dot-off  { width:9px;height:9px;border-radius:50%;background:#94a3b8;display:inline-block; }

    /* ── Alert strips ─────────────────────────────────────────────────────── */
    .alert-strip { padding: 10px 16px; border-radius: 10px;
                   font-size: 0.82rem; font-weight: 600; margin-bottom: 8px; }
    .alert-warn  { background: rgba(251,146,60,0.15);  color: #9a3412; border-left: 3px solid #fb923c; }
    .alert-ok    { background: rgba(74,222,128,0.15);  color: #155724; border-left: 3px solid #4ade80; }
    .alert-info  { background: rgba(14,165,233,0.15);  color: #0c4a6e; border-left: 3px solid #0ea5e9; }
    .alert-crit  { background: rgba(239,68,68,0.13);   color: #7f1d1d; border-left: 3px solid #ef4444; }

    /* ── Section / card headings ──────────────────────────────────────────── */
    .section-title { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
                     text-transform: uppercase; color: #64748b; margin-bottom: 12px; }
    .card-title    { font-size: 1.02rem; font-weight: 700; color: inherit; margin: 0 0 3px; }
    .card-sub      { font-size: 0.77rem; opacity: 0.75; margin-bottom: 12px; }

    /* ── Tab bar ──────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.3); backdrop-filter: blur(10px);
        border-radius: 14px; padding: 4px 6px;
        border: 1px solid rgba(255,255,255,0.4); gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px; padding: 8px 18px;
        font-weight: 600; font-size: 0.85rem; color: #64748b;
        background: transparent; border: none;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255,255,255,0.75) !important;
        color: #2d334a !important;
        box-shadow: 0 2px 8px rgba(31,38,135,0.08);
    }

    /* ── Sidebar ──────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.35) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255,255,255,0.4) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #2d334a !important; }

    /* ── Streamlit metric cards ────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.45);
        border: 1px solid rgba(255,255,255,0.55);
        border-radius: 16px; padding: 16px 18px !important;
        backdrop-filter: blur(10px);
    }
    [data-testid="stMetricValue"] { color: #2d334a !important; }
    [data-testid="stMetricLabel"] { color: #64748b !important; }
    [data-testid="stMetricDelta"] { font-weight: 600 !important; }

    /* ── Buttons ──────────────────────────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #1e3a5f, #0ea5e9) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; font-weight: 600 !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }

    /* ── Divider ──────────────────────────────────────────────────────────── */
    .glass-divider {
        border: none; height: 1px;
        background: rgba(100,116,139,0.15); margin: 14px 0;
    }
    hr { border-color: rgba(100,116,139,0.12) !important; }

    /* ── Hide default Streamlit chrome ────────────────────────────────────── */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
AVATAR_COLORS = ["#6b0f1a","#1a203c","#6d28d9","#52796f","#c2440e","#0f4c75","#7c3aed","#065f46"]

def avatar_color(name: str) -> str:
    """Get avatar color based on name hash. Handles None/NaN gracefully."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        name = "default"
    name_str = str(name).strip()
    if not name_str:
        name_str = "default"
    return AVATAR_COLORS[sum(ord(c) for c in name_str) % len(AVATAR_COLORS)]

def sync_dot(status) -> str:
    cls = {"online": "sync-dot-ok", "syncing": "sync-dot-warn",
           "offline": "sync-dot-off", "pending": "sync-dot-warn"}
    status_str = str(status) if status is not None and str(status) != 'nan' else 'offline'
    return f'<span class="{cls.get(status_str.lower(), "sync-dot-off")}"></span>'

def transparent_fig(fig, font_color: str = "#2d334a"):
    """Make any Plotly figure background transparent to show glass behind it."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=font_color,
        margin=dict(l=8, r=8, t=40, b=8),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR  — navigation + filters
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:24px;padding:4px 0;">
        <div style="font-size:2rem;">🎓</div>
        <div>
            <div style="font-size:1.1rem;font-weight:800;color:#2d334a;line-height:1.1;">Studaxis</div>
            <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.05em;">Teacher Dashboard · v1.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 🚨 HACKATHON SECRET WEAPON: Demo Mode Toggle
    use_demo_data = st.toggle(
        "**Demo Mode** (Sample Data)",
        value=False,
        help="Show sample student data — useful for exploring the dashboard before students sync."
    )

    if use_demo_data:
        st.markdown('<div class="alert-strip alert-info">Demo mode active — showing sample classroom data</div>',
                    unsafe_allow_html=True)

    st.markdown("<hr class='glass-divider'>", unsafe_allow_html=True)

    school_name = st.text_input("School Name", value="Demo School")
    class_name  = st.selectbox("Select Class", ["Class 10", "Class 11", "Class 12"])
    subject     = st.multiselect(
        "Filter by Subject",
        ["Mathematics", "Science", "English", "History", "Geography"],
        default=["Mathematics"]
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

    st.markdown("<hr class='glass-divider'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.7rem;color:#94a3b8;line-height:1.7;">
        Last refreshed:<br>
        <strong style="color:#64748b;">{datetime.now().strftime('%b %d, %Y  %H:%M')}</strong>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING FUNCTIONS (WITH FALLBACK)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_student_stats_from_s3(bucket_name=STUDENT_STATS_BUCKET):
    """
    Fetch all student_*.json files from S3 bucket.
    Returns empty DataFrame if bucket doesn't exist or has no data.
    """
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='student_')
        
        if 'Contents' not in response:
            return pd.DataFrame()
        
        all_stats = []
        
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):
                try:
                    file_obj = s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                    stats_data = json.loads(file_obj['Body'].read().decode('utf-8'))
                    
                    student_id = obj['Key'].split('_')[1]
                    
                    flattened = {
                        'student_id': student_id,
                        'last_sync': stats_data.get('last_sync_time', 'N/A'),
                        'total_quizzes': len(stats_data.get('quiz_scores', {})),
                        'avg_score': calculate_avg_score(stats_data.get('quiz_scores', {})),
                        'current_streak': stats_data.get('streak', 0),
                        'connectivity_status': stats_data.get('connectivity_status', 'Unknown'),
                    }
                    all_stats.append(flattened)
                except Exception as e:
                    st.warning(f"⚠️ Error reading {obj['Key']}")
                    continue
        
        return pd.DataFrame(all_stats)
    
    except Exception as e:
        # Graceful fallback — don't crash, just return empty
        st.warning(f"⚠️ Could not connect to S3: {e}")
        return pd.DataFrame()

def calculate_avg_score(quiz_scores_dict):
    """Calculate average quiz score from dictionary"""
    if not quiz_scores_dict:
        return 0
    scores = [float(v) for v in quiz_scores_dict.values() if isinstance(v, (int, float))]
    return round(sum(scores) / len(scores), 2) if scores else 0


def call_appsync_mutation(mutation_string, variables, operation_name=None):
    """Call AppSync GraphQL from Streamlit (raw HTTP — bypasses gql introspection)."""
    payload = {
        "query": mutation_string,
        "variables": variables,
    }
    if operation_name:
        payload["operationName"] = operation_name

    try:
        resp = requests.post(
            APPSYNC_ENDPOINT,
            json=payload,
            headers={
                "x-api-key": APPSYNC_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        body = resp.json()

        if "errors" in body:
            st.error(f"AppSync error: {body['errors'][0]}")
            return None

        return body.get("data")
    except requests.exceptions.Timeout:
        st.error("AppSync request timed out (10 s)")
        return None
    except Exception as exc:
        st.error(f"AppSync error: {str(exc)}")
        return None

@st.cache_data(ttl=300)
def fetch_sync_metadata_from_dynamodb():
    """Query DynamoDB 'studaxis-student-sync' for student sync metadata"""
    try:
        table = dynamodb.Table(SYNC_TABLE_NAME)
        response = table.scan()
        items = response.get('Items', [])
        return pd.DataFrame(items)
    except Exception as e:
        st.warning(f"⚠️ DynamoDB connection issue ({SYNC_TABLE_NAME}): {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_quiz_index_from_dynamodb():
    """Query DynamoDB 'studaxis-quiz-index' for quiz metadata"""
    try:
        table = dynamodb.Table(QUIZ_INDEX_TABLE)
        response = table.scan()
        items = response.get('Items', [])
        return pd.DataFrame(items)
    except Exception as e:
        st.warning(f"⚠️ DynamoDB connection issue ({QUIZ_INDEX_TABLE}): {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Choose between real or demo data
# ─────────────────────────────────────────────────────────────────────────────

def get_student_stats(use_demo=False):
    """Returns either real or demo student stats"""
    if use_demo:
        return get_demo_student_stats()
    real_data = fetch_student_stats_from_s3()
    if real_data.empty:
        st.markdown('<div class="alert-strip alert-info">No live data yet — showing sample data. Your students\' results will appear here once their devices sync.</div>',
                    unsafe_allow_html=True)
        return get_demo_student_stats()
    return real_data

def get_sync_metadata(use_demo=False):
    """Returns either real or demo sync metadata"""
    if use_demo:
        return get_demo_sync_metadata()
    
    real_data = fetch_sync_metadata_from_dynamodb()
    
    if real_data.empty:
        return get_demo_sync_metadata()
    
    return real_data

# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:8px;">
    <div style="font-size:0.85rem;color:#64748b;font-weight:500;">Welcome back,</div>
    <h1 style="margin:0;font-size:2rem;font-weight:800;
               background:linear-gradient(90deg,#6b0f1a,#b91c28,#8b5cf6);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               background-clip:text;">
        Teacher Dashboard
    </h1>
    <div style="font-size:0.83rem;color:#94a3b8;margin-top:3px;">
        Live student progress — updates automatically as students complete activities
        &nbsp;·&nbsp;
        <span style="color:#4ade80;font-weight:600;">&#9679;</span>&nbsp;Connected
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Class Overview",
    "Topic Performance",
    "At-Risk Students",
    "Sync Status",
    "Quiz Preview",
    "🤖 AI Generate",
    "📤 Publish & Assign",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CLASS OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown(f'<div class="section-title">Class Overview — {class_name}</div>',
                unsafe_allow_html=True)

    df_stats = get_student_stats(use_demo=use_demo_data)

    if df_stats.empty:
        # ── Glassmorphic empty state ────────────────────────────────────────
        st.markdown("""
        <div class="glass-card grad-purple" style="text-align:center;padding:48px 32px;">
            <div style="font-size:3rem;margin-bottom:16px;">&#9201;</div>
            <h3 style="margin:0 0 10px;">Waiting for Student Activity</h3>
            <p style="opacity:0.85;margin:0 0 8px;">No student data has been received yet.</p>
            <p style="opacity:0.75;font-size:0.88rem;margin:0;">
                Progress will appear here once students complete activities and their devices sync.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">How it works</div>
            <div style="font-size:0.86rem;color:#2d334a;line-height:2;margin-top:8px;">
                <div>&#9312; Students complete quizzes and activities on their devices, even without internet.</div>
                <div>&#9313; Devices sync automatically the moment they connect to a network.</div>
                <div>&#9314; This dashboard updates with their latest scores and progress.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # ── Glassmorphic KPI row ─────────────────────────────────────────────
        avg_class_score = df_stats['avg_score'].mean()
        avg_streak      = df_stats['current_streak'].mean()
        total_quizzes   = df_stats['total_quizzes'].sum()
        online_count    = len(df_stats[df_stats['connectivity_status'] == 'online'])

        kc1, kc2, kc3, kc4 = st.columns(4, gap="medium")

        def kpi(col, gradient, label, value, delta, delta_ok=True):
            delta_cls = "metric-delta-pos" if delta_ok else "metric-delta-neg"
            with col:
                st.markdown(f"""
                <div class="glass-card {gradient}" style="padding:20px 22px 16px;min-height:120px;">
                    <div class="metric-label">{label}</div>
                    <div class="metric-big">{value}</div>
                    <div class="{delta_cls}">{delta}</div>
                </div>
                """, unsafe_allow_html=True)

        kpi(kc1, "grad-maroon", "Total Students",     len(df_stats),             f"▲ {online_count} active now")
        kpi(kc2, "grad-sage",   "Class Average",      f"{avg_class_score:.1f}%", "▲ +3.2 pts this week")
        kpi(kc3, "grad-blue",   "Avg Streak",         f"{avg_streak:.0f} days",  "▲ +1.4 days")
        kpi(kc4, "grad-sunset", "Total Quizzes Done",  total_quizzes,            "Class-wide total")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Table + histogram side-by-side ───────────────────────────────────
        tbl_col, chart_col = st.columns([1.3, 1], gap="medium")

        with tbl_col:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">🏆 Student Performance</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-sub">Sorted by average score · updates automatically when student devices sync</div>',
                        unsafe_allow_html=True)
            df_display = df_stats.sort_values('avg_score', ascending=False).reset_index(drop=True)
            df_display.index = df_display.index + 1
            st.dataframe(
                df_display[['student_id','total_quizzes','avg_score',
                             'current_streak','connectivity_status','last_sync']]
                .rename(columns={
                    'student_id': 'Student ID', 'total_quizzes': 'Quizzes',
                    'avg_score': 'Avg Score (%)', 'current_streak': 'Streak',
                    'connectivity_status': 'Status', 'last_sync': 'Last Sync',
                }),
                use_container_width=True, hide_index=False,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with chart_col:
            st.markdown('<div class="glass-card" style="padding:16px 16px 4px;">', unsafe_allow_html=True)
            if len(df_stats) > 0 and not df_stats['avg_score'].isna().all():
                fig = px.histogram(
                    df_stats, x='avg_score', nbins=10,
                    title="Score Distribution",
                    labels={'avg_score': 'Average Score (%)'},
                    color_discrete_sequence=['#8b5cf6'],
                )
                fig.update_traces(marker_line_color='rgba(255,255,255,0.4)',
                                  marker_line_width=1.5, opacity=0.85)
                fig.update_layout(
                    xaxis=dict(showgrid=False, zeroline=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(100,116,139,0.12)', zeroline=False),
                    bargap=0.08, height=340,
                )
                transparent_fig(fig)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("📊 Insufficient data to display score distribution")
            st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — TOPIC PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Topic-wise Performance Analysis</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="alert-strip alert-info" style="display:inline-block;margin-bottom:14px;">📖 Selected subjects: <strong>{", ".join(subject)}</strong></div>',
                unsafe_allow_html=True)

    topic_data = get_demo_topic_performance()

    if topic_data.empty:
        st.markdown('<div class="alert-strip alert-warn">⚠️ No topic data available.</div>',
                    unsafe_allow_html=True)
    else:
        try:
            TOPIC_COLORS = {
                'Algebra': '#e11d3f', 'Geometry': '#0ea5e9', 'Statistics': '#8b5cf6',
                'Trigonometry': '#fb923c', 'Calculus': '#4ade80',
            }
            bar_col, radar_col = st.columns([1.6, 1], gap="medium")

            with bar_col:
                fig_bar = go.Figure()
                for _, row in topic_data.iterrows():
                    fig_bar.add_trace(go.Bar(
                        x=[row['Topic']], y=[row['Avg Score']], name=row['Topic'],
                        marker=dict(color=TOPIC_COLORS.get(row['Topic'], '#94a3b8'),
                                    opacity=0.87,
                                    line=dict(color='rgba(255,255,255,0.35)', width=1.5)),
                        width=0.55, showlegend=False,
                    ))
                fig_bar.update_layout(
                    title=dict(text="Average Score by Topic", font=dict(size=14), x=0),
                    xaxis=dict(showgrid=False, zeroline=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(100,116,139,0.12)',
                               zeroline=False, range=[0, 105], ticksuffix='%'),
                    height=340, bargap=0.25,
                )
                transparent_fig(fig_bar)
                st.markdown('<div class="glass-card" style="padding:16px 16px 4px;">', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            with radar_col:
                topics = topic_data['Topic'].tolist()
                scores = topic_data['Avg Score'].tolist()
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=scores + [scores[0]], theta=topics + [topics[0]],
                    fill='toself', fillcolor='rgba(14,165,233,0.17)',
                    line=dict(color='#0ea5e9', width=2.5), name='Class',
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=[80]*len(topics) + [80], theta=topics + [topics[0]],
                    fill='toself', fillcolor='rgba(139,92,246,0.07)',
                    line=dict(color='#8b5cf6', width=1.5, dash='dot'), name='Target 80%',
                ))
                fig_radar.update_layout(
                    polar=dict(bgcolor='rgba(0,0,0,0)',
                               radialaxis=dict(range=[0, 100], visible=True,
                                               gridcolor='rgba(100,116,139,0.2)')),
                    legend=dict(x=0.7, y=1.05, font=dict(size=9)),
                    title=dict(text='Topic Radar', font=dict(size=14), x=0),
                    height=340,
                )
                transparent_fig(fig_radar)
                st.markdown('<div class="glass-card" style="padding:16px 16px 4px;">', unsafe_allow_html=True)
                st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📋 Topic Metrics</div>', unsafe_allow_html=True)
            st.dataframe(topic_data, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error rendering topic chart: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — STRUGGLING STUDENTS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Students Who May Need Extra Support</div>', unsafe_allow_html=True)

    df_stats = get_student_stats(use_demo=use_demo_data)

    if df_stats.empty:
        st.markdown('<div class="alert-strip alert-info">No student data available yet.</div>',
                    unsafe_allow_html=True)
    else:
        struggling = df_stats[
            (df_stats['avg_score'] < 60) | (df_stats['current_streak'] == 0)
        ].sort_values('avg_score')

        if struggling.empty:
            st.markdown("""
            <div class="glass-card grad-sage" style="text-align:center;padding:40px 24px;">
                <div style="font-size:2.8rem;margin-bottom:12px;">&#10003;</div>
                <h3 style="margin:0;">All Students on Track</h3>
                <p style="opacity:0.85;margin-top:8px;font-size:0.9rem;">
                    No students below 60% average or with a lapsed activity streak.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-strip alert-warn"><strong>{len(struggling)} student(s)</strong> flagged — average score below 60% or no recent activity</div>',
                        unsafe_allow_html=True)

            for _, row in struggling.iterrows():
                score    = row['avg_score']
                streak   = row['current_streak']
                sid      = row['student_id']
                is_crit  = score < 60
                bar_color = '#ef4444' if is_crit else '#fb923c'
                pct_w     = int(score)
                ac        = avatar_color(sid)
                initials  = sid[:2].upper()
                dot       = sync_dot(row['connectivity_status'])

                st.markdown(f"""
                <div class="glass-card" style="margin-bottom:12px;">
                    <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
                        <div class="student-avatar"
                             style="background:{ac};color:white;width:46px;height:46px;font-size:1rem;">
                            {initials}
                        </div>
                        <div style="flex:1;">
                            <div style="font-weight:700;font-size:1rem;color:#2d334a;">{sid}</div>
                            <div style="font-size:0.75rem;color:#64748b;">
                                Last sync: {row['last_sync']} &nbsp; {dot} {row['connectivity_status']}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.5rem;font-weight:800;color:{bar_color};">{score:.1f}%</div>
                            <div style="font-size:0.72rem;color:#94a3b8;">avg score</div>
                        </div>
                    </div>
                    <div style="background:rgba(100,116,139,0.12);border-radius:999px;height:7px;
                                overflow:hidden;margin-bottom:12px;">
                        <div style="background:{bar_color};width:{pct_w}%;height:100%;border-radius:999px;"></div>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;
                                font-size:0.82rem;text-align:center;margin-bottom:10px;">
                        <div>
                            <div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;">Quizzes</div>
                            <div style="font-weight:700;">{row['total_quizzes']}</div>
                        </div>
                        <div>
                            <div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;">Streak</div>
                            <div style="font-weight:700;">{streak} 🔥</div>
                        </div>
                        <div>
                            <div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;">Status</div>
                            <div style="font-weight:700;">{row['connectivity_status']}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if is_crit:
                    st.markdown('<div class="alert-strip alert-crit">Score below 60% — consider scheduling a check-in or additional support.</div>',
                                unsafe_allow_html=True)
                if streak == 0:
                    st.markdown('<div class="alert-strip alert-warn">No recent activity — student may benefit from a gentle nudge to re-engage.</div>',
                                unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — SYNC STATUS
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-title">Device Sync Status</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Manual AppSync Sync Actions</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Trigger offline sync mutations from dashboard</div>', unsafe_allow_html=True)

    action_col1, action_col2 = st.columns(2)

    with action_col1:
        if st.button("Sync Quiz Attempt", use_container_width=True):
            mutation = """
            mutation RecordQuizAttempt(
              $userId: String!
              $quizId: String!
              $score: Int!
              $totalQuestions: Int!
              $deviceId: String
              $completedAtLocal: String
            ) {
              recordQuizAttempt(
                userId: $userId
                quizId: $quizId
                score: $score
                totalQuestions: $totalQuestions
                deviceId: $deviceId
                completedAtLocal: $completedAtLocal
              ) {
                attemptId
                userId
                quizId
                score
                totalQuestions
                accuracyPercentage
                syncedAt
              }
            }
            """

            result = call_appsync_mutation(
                mutation,
                {
                    "userId": "STU001",
                    "quizId": "Q123",
                    "score": 7,
                    "totalQuestions": 10,
                    "deviceId": "DEV001",
                    "completedAtLocal": datetime.now(timezone.utc).isoformat(),
                },
                operation_name="RecordQuizAttempt",
            )

            if result:
                st.success(f"Quiz sync successful: {result}")

    with action_col2:
        if st.button("Sync Streak", use_container_width=True):
            streak_mutation = """
            mutation UpdateStreak($userId: String!, $currentStreak: Int!) {
              updateStreak(userId: $userId, currentStreak: $currentStreak) {
                userId
                currentStreak
                syncedAt
              }
            }
            """

            streak_result = call_appsync_mutation(
                streak_mutation,
                {
                    "userId": "STU001",
                    "currentStreak": 5,
                },
                operation_name="UpdateStreak",
            )

            if streak_result:
                st.success(f"Streak sync successful: {streak_result}")

    st.markdown('</div>', unsafe_allow_html=True)

    df_sync = get_sync_metadata(use_demo=use_demo_data)

    if df_sync.empty:
        st.markdown('<div class="alert-strip alert-info">No device data available yet.</div>',
                    unsafe_allow_html=True)
    else:
        status_col    = 'sync_status'
        online_count  = len(df_sync[df_sync[status_col] == 'online'])
        syncing_count = len(df_sync[df_sync[status_col] == 'syncing'])
        offline_count = len(df_sync) - online_count - syncing_count

        sc1, sc2, sc3 = st.columns(3, gap="medium")
        sc1.markdown(f"""
        <div class="glass-card grad-sage" style="text-align:center;padding:22px;">
            <div class="metric-label">Online</div>
            <div class="metric-big">{online_count}</div>
            <div class="score-pill">Synced securely</div>
        </div>
        """, unsafe_allow_html=True)
        sc2.markdown(f"""
        <div class="glass-card grad-sunset" style="text-align:center;padding:22px;">
            <div class="metric-label">Syncing</div>
            <div class="metric-big">{syncing_count}</div>
            <div class="score-pill">Updating progress</div>
        </div>
        """, unsafe_allow_html=True)
        sc3.markdown(f"""
        <div class="glass-card grad-slate" style="text-align:center;padding:22px;">
            <div class="metric-label">Offline</div>
            <div class="metric-big">{offline_count}</div>
            <div class="score-pill">Waiting for connection</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Sync rows list
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Sync Details by Device</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">Updates automatically when student devices reconnect to the internet</div>',
                    unsafe_allow_html=True)
        for _, row in df_sync.iterrows():
            dot    = sync_dot(row.get('sync_status', 'offline'))
            sid    = row.get('student_id', row.get('studentId', 'UNK'))
            if pd.isna(sid):
                sid = 'UNK'
            else:
                sid = str(sid)
            ac     = avatar_color(sid)
            inits  = sid[:3].upper()
            ts     = str(row.get('last_sync_timestamp', row.get('lastSyncTimestamp', 'N/A')))[:19].replace('T', '  ')
            st.markdown(f"""
            <div class="student-row">
                <div style="display:flex;align-items:center;">
                    <div class="student-avatar" style="background:{ac};color:white;">{inits}</div>
                    <div>
                        <div style="font-weight:600;font-size:0.88rem;color:#2d334a;">{sid}</div>
                        <div style="font-size:0.71rem;color:#64748b;">{row.get('device_id', row.get('deviceId', '—'))}</div>
                    </div>
                </div>
                <div style="text-align:right;font-size:0.8rem;">
                    <div style="display:flex;align-items:center;gap:6px;justify-content:flex-end;">
                        {dot} <span style="color:#64748b;">{row.get('sync_status', '—')}</span>
                    </div>
                    <div style="color:#94a3b8;font-size:0.7rem;margin-top:2px;">{ts}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Donut chart
        fig_donut = go.Figure(data=[go.Pie(
            labels=['Online', 'Syncing', 'Offline'],
            values=[online_count, syncing_count, offline_count],
            hole=0.58,
            marker=dict(colors=['#4ade80', '#fb923c', '#94a3b8'],
                        line=dict(color='rgba(255,255,255,0.5)', width=2)),
        )])
        fig_donut.update_traces(textinfo='label+percent', textfont_size=11)
        fig_donut.update_layout(
            title=dict(text='Device Connectivity Breakdown', font=dict(size=14), x=0),
            showlegend=False, height=300,
            annotations=[dict(text=f'<b>{len(df_sync)}</b><br>Devices',
                              x=0.5, y=0.5, font_size=14, showarrow=False,
                              font=dict(color='#2d334a'))],
        )
        transparent_fig(fig_donut)
        st.markdown('<div class="glass-card" style="padding:16px 16px 4px;">', unsafe_allow_html=True)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — LIVE QUIZ CONTENT (AppSync + S3 Broker — logic unchanged)
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-title">Live Quiz Content — AppSync + S3 Broker Pattern</div>',
                unsafe_allow_html=True)

    # Architecture explainer card
    st.markdown("""
    <div class="glass-card grad-blue" style="margin-bottom:18px;">
        <div class="card-title">🔗 How This Works</div>
        <div style="font-size:0.83rem;line-height:2;opacity:0.92;margin-top:6px;">
            <div>① You provide a <strong>quiz ID</strong> → AppSync queries Lambda</div>
            <div>② <strong>ContentDistribution Lambda</strong> generates a presigned S3 URL</div>
            <div>③ Streamlit downloads the quiz JSON directly from S3</div>
            <div>④ Bypasses AppSync's 1MB payload limit — works for large quizzes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Initialize AppSync + S3 clients (unchanged)
    appsync_client   = AppSyncQLClient(endpoint=APPSYNC_ENDPOINT, api_key=APPSYNC_API_KEY)
    s3_broker_client = S3PresignedURLClient(region=S3_REGION)

    # ── Step 1: Quiz ID input ───────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📥 Fetch Quiz from S3</div>', unsafe_allow_html=True)

    col_input, col_button = st.columns([3, 1])
    with col_input:
        st.markdown("**Step 1 — Enter Quiz ID**")
        quiz_id_input = st.text_input(
            "Quiz ID", placeholder="quiz_",
            help="The quiz_id from your Quiz Index DynamoDB table",
            label_visibility="collapsed",
        )
    with col_button:
        st.markdown("**Step 2 — Fetch**")
        fetch_button = st.button("🚀 Get Presigned URL", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 2: Fetch presigned URL (logic unchanged) ────────────────────────
    if fetch_button and quiz_id_input:
        with st.spinner("📡 Querying AppSync for presigned URL…"):
            presigned_url = appsync_client.get_quiz_presigned_url(quiz_id_input)
            if presigned_url:
                st.session_state.presigned_url = presigned_url
                st.markdown(f'<div class="alert-strip alert-ok">✅ Got presigned URL for: <strong>{quiz_id_input}</strong></div>',
                            unsafe_allow_html=True)
                with st.expander("🔗 Presigned URL Details"):
                    st.code(presigned_url, language="url")
                    st.markdown('<div class="alert-strip alert-info">⏱️ This URL expires in 1 hour (3600 seconds)</div>',
                                unsafe_allow_html=True)

    # ── Step 3: Download quiz from S3 (logic unchanged) ─────────────────────
    if 'presigned_url' in st.session_state:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📦 Download Quiz JSON from S3</div>', unsafe_allow_html=True)
        download_col1, download_col2 = st.columns([2, 1])
        with download_col1:
            if st.button("📥 Download Quiz from S3", use_container_width=True):
                with st.spinner("📥 Downloading quiz JSON from S3…"):
                    quiz_data = load_quiz_with_presigned_url(st.session_state.presigned_url)
                    if quiz_data:
                        st.session_state.quiz_data = quiz_data
                        st.markdown('<div class="alert-strip alert-ok">✅ Quiz downloaded successfully!</div>',
                                    unsafe_allow_html=True)
        with download_col2:
            if st.button("🔄 Clear", use_container_width=True):
                for key in ('presigned_url', 'quiz_data'):
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 4: Display quiz content (logic unchanged) ───────────────────────
    st.markdown("<hr class='glass-divider'>", unsafe_allow_html=True)
    if 'quiz_data' in st.session_state and st.session_state.quiz_data:
        display_quiz_content(st.session_state.quiz_data)
    else:
        st.markdown('<div class="alert-strip alert-info">👆 Enter a quiz ID above and click <strong>Get Presigned URL</strong> to load a quiz</div>',
                    unsafe_allow_html=True)

    # ── Architecture explainer ────────────────────────────────────────────────
    st.markdown("<hr class='glass-divider'>", unsafe_allow_html=True)
    st.markdown("""
    <div class="glass-card">
        <div class="card-title">🎯 Why This Architecture Matters for Studaxis</div>
        <div style="font-size:0.85rem;color:#2d334a;line-height:1.8;margin-top:10px;">
            <strong>The Problem:</strong> Edge devices in rural schools have spotty connectivity.
            AppSync has a <strong>1MB payload limit</strong> — but AI-generated quizzes with
            explanations are far larger.<br><br>
            <strong>The Solution (AppSync + S3 Broker):</strong>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px;">
            <div class="alert-strip alert-ok">✅ Student gets presigned URL instantly on 2G</div>
            <div class="alert-strip alert-ok">✅ Downloads quiz directly from S3 when 4G available</div>
            <div class="alert-strip alert-ok">✅ Quiz works 100% offline on-device</div>
            <div class="alert-strip alert-ok">✅ Results sync back up next connection</div>
        </div>
        <div style="font-size:0.78rem;color:#94a3b8;margin-top:10px;">
            This is what makes Studaxis <strong>truly offline-first.</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — AI CONTENT GENERATION (AWS Bedrock / Claude 3 Haiku)
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown('<div class="section-title">AI Content Generation — AWS Bedrock (Claude 3)</div>',
                unsafe_allow_html=True)

    # ── Bedrock settings (sidebar-injected values read here) ─────────────────
    bedrock_region = os.getenv('BEDROCK_REGION', 'ap-south-1')

    # ── Two-column layout: left = controls, right = output ───────────────────
    ctrl_col, out_col = st.columns([1, 1.4], gap="large")

    with ctrl_col:
        # ── Connection test ───────────────────────────────────────────────────
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🔌 Bedrock Connection</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-sub">Region: <strong>{bedrock_region}</strong> &nbsp;·&nbsp; '
            'Requires <code>bedrock:InvokeModel</code> IAM permission and '
            'model access granted in the Bedrock console.</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔍 Test Connection", use_container_width=True, key="btn_test_conn"):
            with st.spinner("Checking Bedrock access…"):
                result = test_bedrock_connection(region=bedrock_region)
            if result["success"]:
                st.markdown(
                    f'<div class="alert-strip alert-ok">✅ {result["message"]}</div>',
                    unsafe_allow_html=True,
                )
                if result["models"]:
                    with st.expander("Available Claude models"):
                        for m in result["models"]:
                            st.code(m, language=None)
            else:
                st.markdown(
                    f'<div class="alert-strip alert-crit">❌ {result["message"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("""
                <div class="alert-strip alert-warn">
                    ⚠️ <strong>Checklist:</strong><br>
                    1. Run <code>aws configure</code> with a key that has <code>bedrock:InvokeModel</code><br>
                    2. In Bedrock Console → Model access → enable Claude 3 Haiku<br>
                    3. Make sure the region matches where model access was granted
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Quiz generation form ──────────────────────────────────────────────
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📝 Quiz Generator</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">Claude 3 Haiku generates structured JSON quizzes</div>',
                    unsafe_allow_html=True)

        quiz_topic      = st.text_input("Topic", placeholder="e.g. Photosynthesis, World War II, Pythagoras Theorem",
                                        key="quiz_topic")
        quiz_difficulty = st.select_slider("Difficulty", options=["easy", "medium", "hard"],
                                           value="medium", key="quiz_diff")
        quiz_num_q      = st.slider("Number of questions", 1, 8, 3, key="quiz_num_q")

        gen_quiz_btn = st.button("🚀 Generate Quiz", use_container_width=True, key="btn_gen_quiz",
                                 disabled=not quiz_topic.strip())
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Lesson summary form ───────────────────────────────────────────────
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📖 Lesson Summary Generator</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">Get key concepts + study notes for any topic</div>',
                    unsafe_allow_html=True)

        summary_topic  = st.text_input("Topic", placeholder="e.g. Mitosis, The French Revolution",
                                       key="summary_topic")
        summary_grade  = st.selectbox("Grade level",
                                      ["Grade 6", "Grade 7", "Grade 8", "Grade 9",
                                       "Grade 10", "Grade 11", "Grade 12", "Undergraduate"],
                                      index=4, key="summary_grade")

        gen_summary_btn = st.button("📚 Generate Notes", use_container_width=True, key="btn_gen_summary",
                                    disabled=not summary_topic.strip())
        st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────── OUTPUT COLUMN ───────────────────────────
    with out_col:

        # ── Quiz generation ───────────────────────────────────────────────────
        if gen_quiz_btn and quiz_topic.strip():
            with st.spinner(f"Generating {quiz_num_q}-question quiz on '{quiz_topic}'…"):
                try:
                    quiz_result = bedrock_generate_quiz(
                        topic=quiz_topic.strip(),
                        difficulty=quiz_difficulty,
                        num_questions=quiz_num_q,
                        region=bedrock_region,
                    )
                    st.session_state["ai_quiz_result"] = quiz_result
                    st.session_state.pop("ai_summary_result", None)   # clear other output
                except Exception as exc:
                    st.session_state["ai_quiz_error"] = str(exc)
                    st.session_state.pop("ai_quiz_result", None)

        if gen_summary_btn and summary_topic.strip():
            with st.spinner(f"Generating study notes for '{summary_topic}'…"):
                try:
                    summary_result = generate_lesson_summary(
                        topic=summary_topic.strip(),
                        grade_level=summary_grade,
                        region=bedrock_region,
                    )
                    st.session_state["ai_summary_result"] = summary_result
                    st.session_state.pop("ai_quiz_result", None)      # clear other output
                except Exception as exc:
                    st.session_state["ai_summary_error"] = str(exc)
                    st.session_state.pop("ai_summary_result", None)

        # ── Render quiz result ────────────────────────────────────────────────
        if "ai_quiz_error" in st.session_state:
            st.markdown(
                f'<div class="alert-strip alert-crit">❌ {st.session_state["ai_quiz_error"]}</div>',
                unsafe_allow_html=True,
            )

        if "ai_quiz_result" in st.session_state:
            q_data = st.session_state["ai_quiz_result"]
            st.markdown(f"""
            <div class="glass-card grad-purple" style="margin-bottom:14px;">
                <div class="card-title">🎓 {q_data.get('quiz_title', 'Generated Quiz')}</div>
                <div class="card-sub">{q_data.get('topic', '')} &nbsp;·&nbsp;
                    Difficulty: <strong>{q_data.get('difficulty', '').capitalize()}</strong></div>
            </div>
            """, unsafe_allow_html=True)

            questions = q_data.get("questions", [])
            for i, q in enumerate(questions, 1):
                options_html = "".join(
                    f'<div style="font-size:0.84rem;padding:3px 0;color:#2d334a;">'
                    f'{"✅ " if opt == q.get("answer") else "&nbsp;&nbsp;&nbsp;"}{opt}</div>'
                    for opt in q.get("options", [])
                )
                explanation = q.get("explanation", "")
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom:10px;">
                    <div style="font-weight:700;font-size:0.9rem;color:#2d334a;margin-bottom:8px;">
                        Q{i}. {q.get('question', '')}
                    </div>
                    {options_html}
                    {'<div style="margin-top:8px;font-size:0.78rem;color:#52796f;border-top:1px solid rgba(100,116,139,0.15);padding-top:7px;">💡 ' + explanation + '</div>' if explanation else ''}
                </div>
                """, unsafe_allow_html=True)

            # Download buttons — Word & PDF
            fname_base = quiz_topic.replace(' ', '_').lower()
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    label="📄 Download as Word",
                    data=quiz_to_docx(q_data),
                    file_name=f"quiz_{fname_base}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    label="📕 Download as PDF",
                    data=quiz_to_pdf(q_data),
                    file_name=f"quiz_{fname_base}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

        # ── Render lesson summary result ──────────────────────────────────────
        if "ai_summary_error" in st.session_state:
            st.markdown(
                f'<div class="alert-strip alert-crit">❌ {st.session_state["ai_summary_error"]}</div>',
                unsafe_allow_html=True,
            )

        if "ai_summary_result" in st.session_state:
            s_data = st.session_state["ai_summary_result"]
            st.markdown(f"""
            <div class="glass-card grad-sage" style="margin-bottom:14px;">
                <div class="card-title">📖 {s_data.get('title', 'Study Notes')}</div>
                <div class="card-sub">{s_data.get('grade_level', '')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Key concepts pills
            concepts = s_data.get("key_concepts", [])
            if concepts:
                pills_html = " ".join(
                    f'<span style="display:inline-block;background:rgba(82,121,111,0.15);'
                    f'border:1px solid rgba(82,121,111,0.3);border-radius:999px;'
                    f'padding:3px 12px;font-size:0.78rem;font-weight:600;color:#52796f;margin:3px 2px;">'
                    f'{c}</span>'
                    for c in concepts
                )
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom:10px;">
                    <div class="card-title" style="font-size:0.78rem;">KEY CONCEPTS</div>
                    <div style="margin-top:8px;">{pills_html}</div>
                </div>
                """, unsafe_allow_html=True)

            # Summary text
            summary_text = s_data.get("summary", "")
            if summary_text:
                st.markdown(f"""
                <div class="glass-card">
                    <div class="card-title">Summary</div>
                    <div style="font-size:0.87rem;color:#2d334a;line-height:1.75;margin-top:8px;">
                        {summary_text.replace(chr(10), '<br>')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Fun fact
            fun_fact = s_data.get("fun_fact", "")
            if fun_fact:
                st.markdown(f"""
                <div class="alert-strip alert-info" style="margin-bottom:14px;">
                    🌟 <strong>Fun Fact:</strong> {fun_fact}
                </div>
                """, unsafe_allow_html=True)

            # Download buttons — Word & PDF
            fname_base_s = summary_topic.replace(' ', '_').lower()
            dl3, dl4 = st.columns(2)
            with dl3:
                st.download_button(
                    label="📄 Download as Word",
                    data=notes_to_docx(s_data),
                    file_name=f"notes_{fname_base_s}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            with dl4:
                st.download_button(
                    label="📕 Download as PDF",
                    data=notes_to_pdf(s_data),
                    file_name=f"notes_{fname_base_s}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

        # ── Empty state ───────────────────────────────────────────────────────
        if (
            "ai_quiz_result"    not in st.session_state
            and "ai_summary_result" not in st.session_state
            and "ai_quiz_error"     not in st.session_state
            and "ai_summary_error"  not in st.session_state
        ):
            st.markdown("""
            <div class="glass-card grad-blue" style="text-align:center;padding:48px 32px;">
                <div style="font-size:3rem;margin-bottom:16px;">🤖</div>
                <h3 style="margin:0 0 10px;">Ready to Generate</h3>
                <p style="opacity:0.85;margin:0 0 8px;">
                    Fill in a topic on the left and click <strong>Generate Quiz</strong>
                    or <strong>Generate Notes</strong>.
                </p>
                <p style="opacity:0.72;font-size:0.83rem;margin:0;">
                    Powered by Claude 3 Haiku via AWS Bedrock
                </p>
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — PUBLISH & ASSIGN QUIZZES
# ─────────────────────────────────────────────────────────────────────────────
with tab7:
    st.markdown('<div class="section-title">Publish & Assign Quizzes to Students</div>',
                unsafe_allow_html=True)

    # Architecture explainer
    st.markdown("""
    <div class="glass-card grad-purple" style="margin-bottom:18px;">
        <div class="card-title">📤 Content Upload Pipeline</div>
        <div style="font-size:0.83rem;line-height:2;opacity:0.92;margin-top:6px;">
            <div>① Generate a quiz in the <strong>AI Generate</strong> tab</div>
            <div>② Publish it here → uploads JSON to <strong>S3</strong> + registers in <strong>DynamoDB</strong></div>
            <div>③ Students auto-download via <strong>ContentDistribution Lambda</strong> on next sync</div>
            <div>④ Quiz works 100% offline — results sync back when connectivity returns</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Initialize uploader
    content_uploader = ContentUploader(
        s3_bucket=S3_PAYLOADS_BUCKET,
        quiz_index_table=QUIZ_INDEX_TABLE,
        region=S3_REGION,
    )

    pub_left, pub_right = st.columns([1, 1.4], gap="large")

    with pub_left:
        # ── Publish Generated Quiz ───────────────────────────────────────
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🚀 Publish Last Generated Quiz</div>', unsafe_allow_html=True)

        has_quiz = "ai_quiz_result" in st.session_state
        if has_quiz:
            q_preview = st.session_state["ai_quiz_result"]
            st.markdown(f"""
            <div class="alert-strip alert-ok">
                ✅ Ready to publish: <strong>{q_preview.get('quiz_title', 'Untitled')}</strong>
                ({len(q_preview.get('questions', []))} questions)
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-strip alert-warn">⚠️ No quiz generated yet — go to <strong>AI Generate</strong> tab first</div>',
                        unsafe_allow_html=True)

        pub_subject = st.selectbox(
            "Subject",
            ["Mathematics", "Science", "English", "History", "Geography", "Computer Science"],
            key="pub_subject",
        )
        pub_difficulty = st.select_slider(
            "Difficulty", options=["Easy", "Medium", "Hard"],
            value="Medium", key="pub_diff",
        )
        pub_time_limit = st.number_input(
            "Time Limit (minutes, 0 = no limit)", min_value=0, max_value=180,
            value=0, step=5, key="pub_time",
        )
        pub_total_marks = st.number_input(
            "Total Marks (0 = auto from questions)", min_value=0, max_value=100,
            value=0, step=1, key="pub_marks",
        )

        # Student assignment
        st.markdown("**Assign to Students** (leave empty → all students)")
        assign_mode = st.radio(
            "Assignment scope", ["All Students", "Specific Students"],
            horizontal=True, key="pub_assign_mode",
        )
        assigned_students = []
        if assign_mode == "Specific Students":
            df_for_assign = get_student_stats(use_demo=use_demo_data)
            if not df_for_assign.empty:
                available_ids = df_for_assign["student_id"].tolist()
                assigned_students = st.multiselect(
                    "Select students", available_ids, key="pub_assigned",
                )
            else:
                assigned_students_text = st.text_input(
                    "Enter student IDs (comma-separated)",
                    placeholder="STU001, STU002, STU003",
                    key="pub_assigned_text",
                )
                if assigned_students_text:
                    assigned_students = [s.strip() for s in assigned_students_text.split(",") if s.strip()]

        publish_btn = st.button(
            "📤 Publish to Cloud",
            use_container_width=True,
            key="btn_publish_quiz",
            disabled=not has_quiz,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with pub_right:
        # ── Publish action ───────────────────────────────────────────────
        if publish_btn and has_quiz:
            with st.spinner("Publishing quiz to S3 + DynamoDB..."):
                result = content_uploader.publish_quiz(
                    quiz_data=st.session_state["ai_quiz_result"],
                    subject=pub_subject,
                    difficulty=pub_difficulty.lower(),
                    assigned_to=assigned_students if assigned_students else None,
                    time_limit_minutes=pub_time_limit,
                    total_marks=pub_total_marks,
                    created_by="teacher",
                )
                if result["success"]:
                    st.session_state["last_publish_result"] = result
                    st.markdown(f"""
                    <div class="glass-card grad-sage" style="text-align:center;padding:30px;">
                        <div style="font-size:2.5rem;margin-bottom:12px;">✅</div>
                        <h3 style="margin:0 0 8px;">Quiz Published Successfully!</h3>
                        <div style="font-size:0.85rem;opacity:0.9;margin-bottom:12px;">
                            Students will receive this quiz on their next sync.
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;text-align:left;">
                            <div class="alert-strip alert-ok">Quiz ID: <strong>{result['quiz_id']}</strong></div>
                            <div class="alert-strip alert-ok">S3 Key: <strong>{result['s3_key']}</strong></div>
                            <div class="alert-strip alert-info">Subject: <strong>{pub_subject}</strong></div>
                            <div class="alert-strip alert-info">Assigned to: <strong>{len(assigned_students) if assigned_students else 'All'} students</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="alert-strip alert-crit">❌ Publish failed: {result['message']}</div>
                    """, unsafe_allow_html=True)

        # ── Published quiz index ─────────────────────────────────────────
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📋 Published Quiz Index</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">All quizzes available for student download</div>',
                    unsafe_allow_html=True)

        if st.button("🔄 Refresh Index", key="btn_refresh_index", use_container_width=True):
            st.cache_data.clear()

        try:
            published = content_uploader.list_published_quizzes()
            if published:
                for pq in published[:20]:  # Show latest 20
                    status_dot = '<span style="color:#4ade80;">●</span>' if pq.get('status') == 'published' else '<span style="color:#94a3b8;">●</span>'
                    assigned_count = len(pq.get('assigned_to', []))
                    assign_label = f"{assigned_count} students" if assigned_count else "All students"
                    st.markdown(f"""
                    <div class="student-row">
                        <div style="flex:1;">
                            <div style="font-weight:600;font-size:0.88rem;color:#2d334a;">
                                {status_dot} {pq.get('title', 'Untitled')}
                            </div>
                            <div style="font-size:0.71rem;color:#64748b;">
                                {pq.get('subject', '—')} · {pq.get('difficulty', '—')} · {pq.get('question_count', '?')}Q · {assign_label}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:0.72rem;color:#94a3b8;">{pq.get('quiz_id', '')}</div>
                            <div style="font-size:0.68rem;color:#b0b8c4;">{str(pq.get('created_at', ''))[:16]}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-strip alert-info">No quizzes published yet. Generate one in the AI tab and publish it here.</div>',
                            unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="alert-strip alert-warn">⚠️ Could not load quiz index: {e}</div>',
                        unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<hr class='glass-divider'>", unsafe_allow_html=True)
st.markdown(f"""
<div class="glass-card" style="text-align:center;padding:18px 24px;">
    <div style="font-size:0.78rem;color:#64748b;line-height:2;">
        <strong style="color:#2d334a;">Studaxis Teacher Dashboard v1.0</strong>
        &nbsp;|&nbsp; Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        <br>
        Demo Mode: <strong>{"Enabled" if use_demo_data else "Disabled"}</strong>
    </div>
</div>
""", unsafe_allow_html=True)
