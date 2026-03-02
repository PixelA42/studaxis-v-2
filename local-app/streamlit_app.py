"""
Studaxis - Main Streamlit Application
Offline-First AI Tutor for Low-Connectivity Learning
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from hardware_validator import HardwareValidator
from utils.local_storage import LocalStorage
from utils.ollama_client import OllamaClient
from utils.content_downloader import ContentDownloader


# Page configuration
st.set_page_config(
    page_title="Studaxis - AI Tutor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for light theme (default)
def load_custom_css():
    st.markdown("""
    <style>
    /* Light theme variables (default) */
    :root {
        --bg-primary: #f8fafc;
        --bg-secondary: #ffffff;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --accent: #2563eb;
        --accent-hover: #1d4ed8;
        --border-color: #e2e8f0;
    }
    
    /* Main container */
    .main {
        background-color: var(--bg-primary);
        color: var(--text-primary);
    }
    
    /* Cards */
    .stCard {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Buttons */
    .stButton>button {
        background: var(--accent);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s;
        font-weight: 500;
    }
    
    .stButton>button:hover {
        background: var(--accent-hover);
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }
    
    /* Streak badge */
    .streak-badge {
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: var(--text-primary);
        font-weight: 600;
    }
    
    /* Input fields */
    .stTextInput>div>div>input {
        background-color: var(--bg-secondary);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }
    
    /* Dividers */
    hr {
        border-color: var(--border-color);
    }
    </style>
    """, unsafe_allow_html=True)


# Initialize session state
def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.user_id = "student_001"  # TODO: Implement proper auth
        st.session_state.storage = LocalStorage()
        st.session_state.downloader = ContentDownloader(base_path=".")
        st.session_state.current_page = "Dashboard"
        st.session_state.theme = "light"
        
        # Load or create user stats
        stats = st.session_state.storage.load_user_stats()
        if not stats:
            stats = st.session_state.storage.initialize_user_stats(st.session_state.user_id)
        st.session_state.user_stats = stats
        
        st.session_state.initialized = True


# Hardware validation on first run
def run_hardware_check():
    """Run hardware validation and display results"""
    if 'hardware_checked' not in st.session_state:
        validator = HardwareValidator()
        is_valid, message, specs = validator.validate()
        
        st.session_state.hardware_valid = is_valid
        st.session_state.hardware_message = message
        st.session_state.hardware_specs = specs
        st.session_state.hardware_checked = True
        
        # Save hardware info to user stats
        st.session_state.storage.update_user_stats({
            'hardware_info': {
                'ram_gb': specs['ram_gb'],
                'cpu_model': specs['cpu_model'],
                'disk_space_gb': specs['disk_free_gb']
            }
        })


# Sidebar navigation
def render_sidebar():
    """Render sidebar with navigation and stats"""
    with st.sidebar:
        st.title("📚 Studaxis")
        st.caption("Offline-First AI Tutor")
        
        st.divider()
        
        # Streak display
        streak = st.session_state.user_stats['streak']['current']
        st.markdown(f"""
        <div class="streak-badge">
            🔥 {streak} Day Streak
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Navigation
        st.subheader("Navigation")
        pages = {
            "🏠 Dashboard": "Dashboard",
            "💬 Chat": "Chat",
            "📝 Quiz": "Quiz",
            "🗂️ Flashcards": "Flashcards",
            "⚡ Panic Mode": "Panic Mode",
            "⚙️ Settings": "Settings"
        }
        
        for label, page in pages.items():
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
        
        st.divider()
        
        # Quick stats
        st.subheader("Quick Stats")
        quiz_stats = st.session_state.user_stats['quiz_stats']
        st.metric("Quizzes Attempted", quiz_stats['total_attempted'])
        st.metric("Average Score", f"{quiz_stats['average_score']:.1f}/10")
        
        st.divider()
        
        # Sync status
        st.caption("🔄 Last sync: Never")  # TODO: Implement sync
        st.caption("📶 Status: Offline")


# Dashboard page
def render_dashboard():
    """Render main dashboard with bento grid"""
    st.title("Welcome to Studaxis! 👋")
    st.caption("Your offline-first AI learning companion")
    
    # Hardware status
    if not st.session_state.hardware_valid:
        st.warning(st.session_state.hardware_message)
    
    # Bento grid layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("💬 AI Chat")
        st.write("Ask questions and get instant answers from your AI tutor")
        if st.button("Start Chat", key="dash_chat"):
            st.session_state.current_page = "Chat"
            st.rerun()
    
    with col2:
        st.subheader("📝 Take Quiz")
        st.write("Test your knowledge with AI-graded assessments")
        if st.button("Start Quiz", key="dash_quiz"):
            st.session_state.current_page = "Quiz"
            st.rerun()
    
    with col3:
        st.subheader("🗂️ Flashcards")
        st.write("Review concepts with spaced repetition")
        if st.button("Review Cards", key="dash_flash"):
            st.session_state.current_page = "Flashcards"
            st.rerun()
    
    st.divider()
    
    # Recent activity
    st.subheader("Recent Activity")
    chat_history = st.session_state.user_stats.get('chat_history', [])
    if chat_history:
        for msg in chat_history[-3:]:
            st.caption(f"{msg['timestamp'][:10]} - {msg['topic']}")
    else:
        st.info("No recent activity. Start learning!")


# Chat page (placeholder)
def render_chat():
    """Render chat interface"""
    st.title("💬 AI Chat")
    st.caption("Ask questions about your textbooks")
    
    st.info("🚧 Chat interface coming soon! (Day 2)")
    
    # Placeholder
    user_input = st.text_input("Ask a question...")
    if st.button("Send"):
        st.write("Response will appear here")


# Quiz page
def render_quiz():
    """Render quiz interface with cloud download + offline quiz-taking."""
    st.title("📝 Quiz")
    st.caption("Download assigned quizzes or take cached ones offline")

    # ── Sync / Download section ─────────────────────────────────────────────
    st.subheader("📥 Quiz Library")

    sync_col, stats_col = st.columns([2, 1])

    with stats_col:
        cache_stats = st.session_state.downloader.get_cache_stats()
        st.metric("Cached Quizzes", cache_stats["quiz_count"])
        st.metric("Cache Size", f"{cache_stats['total_size_kb']} KB")

    with sync_col:
        if st.button("🔄 Sync Quizzes from Cloud", use_container_width=True):
            with st.spinner("Connecting to cloud..."):
                result = st.session_state.downloader.sync_quizzes(
                    user_id=st.session_state.user_id
                )
                if result["downloaded"] > 0:
                    st.success(
                        f"✅ Downloaded {result['downloaded']} new quiz(es), "
                        f"{result['cached']} already cached"
                    )
                elif result["cached"] > 0:
                    st.info(f"📦 {result['cached']} quiz(es) available from cache (no new content)")
                else:
                    st.warning("No quizzes available. Ask your teacher to publish one!")

        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.session_state.downloader.clear_cache()
            st.success("Cache cleared")
            st.rerun()

    st.divider()

    # ── Available quizzes list ──────────────────────────────────────────────
    cached_quizzes = st.session_state.downloader.list_cached_quizzes()

    if not cached_quizzes:
        st.info(
            "📭 No quizzes available yet. Click **Sync Quizzes from Cloud** "
            "when you have internet, or ask your teacher to assign a quiz."
        )
        return

    st.subheader("📋 Available Quizzes")

    for i, quiz in enumerate(cached_quizzes):
        quiz_id = quiz.get("quiz_id", f"quiz_{i}")
        title = quiz.get("title", quiz.get("quiz_title", "Untitled Quiz"))
        topic = quiz.get("topic", quiz.get("subject", "General"))
        difficulty = quiz.get("difficulty", "Medium")
        q_count = len(quiz.get("questions", []))

        with st.expander(f"📖 {title}  —  {topic} · {difficulty} · {q_count}Q"):
            st.write(f"**Quiz ID:** `{quiz_id}`")
            st.write(f"**Subject:** {topic}")
            st.write(f"**Difficulty:** {difficulty}")
            st.write(f"**Questions:** {q_count}")

            time_limit = quiz.get("time_limit_minutes", 0)
            if time_limit:
                st.write(f"**Time Limit:** {time_limit} minutes")

            if st.button(f"▶️ Start Quiz", key=f"start_{quiz_id}", use_container_width=True):
                st.session_state.active_quiz = quiz
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.current_page = "Quiz"
                st.rerun()

    st.divider()

    # ── Active quiz-taking UI ───────────────────────────────────────────────
    if "active_quiz" in st.session_state and not st.session_state.get("quiz_submitted", False):
        quiz = st.session_state.active_quiz
        title = quiz.get("title", quiz.get("quiz_title", "Untitled Quiz"))
        questions = quiz.get("questions", [])

        st.subheader(f"🎯 Taking: {title}")
        st.progress(
            len(st.session_state.quiz_answers) / max(len(questions), 1),
            text=f"Answered {len(st.session_state.quiz_answers)}/{len(questions)}"
        )

        for idx, q in enumerate(questions):
            q_text = q.get("question_text", q.get("question", ""))
            q_type = q.get("question_type", "mcq")
            q_key = f"q_{idx}"

            st.markdown(f"**Q{idx + 1}.** {q_text}")

            if q_type == "mcq":
                options = q.get("options", [])
                if options:
                    answer = st.radio(
                        f"Select answer for Q{idx + 1}",
                        options,
                        key=q_key,
                        index=None,
                        label_visibility="collapsed",
                    )
                    if answer:
                        st.session_state.quiz_answers[q_key] = answer

            elif q_type == "true_false":
                answer = st.radio(
                    f"Select answer for Q{idx + 1}",
                    ["True", "False"],
                    key=q_key,
                    index=None,
                    label_visibility="collapsed",
                )
                if answer:
                    st.session_state.quiz_answers[q_key] = answer

            elif q_type in ("subjective", "fill_blank"):
                answer = st.text_input(
                    f"Your answer for Q{idx + 1}",
                    key=q_key,
                    label_visibility="collapsed",
                    placeholder="Type your answer...",
                )
                if answer:
                    st.session_state.quiz_answers[q_key] = answer

            st.markdown("---")

        # Submit button
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            if st.button("✅ Submit Quiz", use_container_width=True, type="primary"):
                st.session_state.quiz_submitted = True
                st.rerun()
        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                del st.session_state.active_quiz
                st.session_state.quiz_answers = {}
                st.rerun()

    # ── Results display ─────────────────────────────────────────────────────
    elif st.session_state.get("quiz_submitted", False) and "active_quiz" in st.session_state:
        quiz = st.session_state.active_quiz
        questions = quiz.get("questions", [])
        answers = st.session_state.quiz_answers
        quiz_id = quiz.get("quiz_id", "unknown")
        topic = quiz.get("topic", quiz.get("subject", "General"))
        title = quiz.get("title", quiz.get("quiz_title", "Untitled Quiz"))

        # Grade the quiz
        correct = 0
        total = len(questions)
        results = []

        for idx, q in enumerate(questions):
            q_key = f"q_{idx}"
            student_answer = answers.get(q_key, "")
            correct_answer = q.get("correct_answer", q.get("answer", ""))

            # Simple string comparison for MCQ/true-false
            is_correct = (
                student_answer.strip().lower() == correct_answer.strip().lower()
                if student_answer and correct_answer
                else False
            )
            if is_correct:
                correct += 1

            results.append({
                "question": q.get("question_text", q.get("question", "")),
                "your_answer": student_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            })

        accuracy = round(correct / max(total, 1) * 100, 1)

        # Save attempt
        st.session_state.storage.record_quiz_attempt(
            quiz_id=quiz_id,
            score=correct,
            total_questions=total,
            topic=topic,
            answers=answers,
        )

        # Display results
        st.subheader(f"📊 Results: {title}")

        r1, r2, r3 = st.columns(3)
        r1.metric("Score", f"{correct}/{total}")
        r2.metric("Accuracy", f"{accuracy}%")
        r3.metric("Topic", topic)

        # Colour-coded feedback
        if accuracy >= 80:
            st.success(f"🎉 Excellent! You scored {accuracy}%")
        elif accuracy >= 60:
            st.info(f"👍 Good effort! {accuracy}% — review the ones you missed.")
        else:
            st.warning(f"📚 Keep studying! {accuracy}% — review explanations below.")

        # Question-by-question review
        st.subheader("📝 Review Answers")
        for idx, r in enumerate(results):
            icon = "✅" if r["is_correct"] else "❌"
            with st.expander(f"{icon} Q{idx + 1}: {r['question'][:80]}"):
                st.write(f"**Your answer:** {r['your_answer'] or '(not answered)'}")
                st.write(f"**Correct answer:** {r['correct_answer']}")
                if r["explanation"]:
                    st.info(f"💡 {r['explanation']}")

        # Actions
        col_retry, col_back = st.columns(2)
        with col_retry:
            if st.button("🔁 Retake Quiz", use_container_width=True):
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.rerun()
        with col_back:
            if st.button("📋 Back to Library", use_container_width=True):
                for key in ("active_quiz", "quiz_answers", "quiz_submitted"):
                    st.session_state.pop(key, None)
                st.rerun()


# Flashcards page (placeholder)
def render_flashcards():
    """Render flashcard interface"""
    st.title("🗂️ Flashcards")
    st.caption("Spaced repetition learning")
    
    st.info("🚧 Flashcard system coming soon! (Day 2)")


# Panic Mode page (placeholder)
def render_panic_mode():
    """Render panic mode (exam simulator)"""
    st.title("⚡ Panic Mode")
    st.caption("Exam simulator - distraction-free environment")
    
    st.warning("⚠️ Panic Mode will hide all UI elements and start a timed exam")
    
    if st.button("Start Exam"):
        st.info("🚧 Panic Mode coming soon! (Day 3)")


# Settings page
def render_settings():
    """Render settings page"""
    st.title("⚙️ Settings")
    
    # Theme toggle
    st.subheader("Appearance")
    theme = st.radio("Theme", ["Light", "Dark"], index=0)
    if theme != st.session_state.theme.capitalize():
        st.session_state.theme = theme.lower()
        st.info("Theme will be applied on next reload")
    
    # Difficulty
    st.subheader("Learning Preferences")
    difficulty = st.selectbox(
        "Difficulty Level",
        ["Beginner", "Intermediate", "Expert"],
        index=0
    )
    
    # Language
    language = st.selectbox(
        "Language",
        ["English", "Hinglish"],
        index=0
    )
    
    if st.button("Save Preferences"):
        st.session_state.storage.update_user_stats({
            'preferences': {
                'difficulty_level': difficulty,
                'theme': st.session_state.theme,
                'language': language
            }
        })
        st.success("✅ Preferences saved!")
    
    st.divider()
    
    # Hardware info
    st.subheader("System Information")
    specs = st.session_state.hardware_specs
    st.write(f"**RAM:** {specs['ram_gb']}GB")
    st.write(f"**CPU:** {specs['cpu_model']}")
    st.write(f"**Disk:** {specs['disk_free_gb']}GB free")


# Main app
def main():
    """Main application entry point"""
    load_custom_css()
    initialize_session_state()
    run_hardware_check()
    
    # Render sidebar
    render_sidebar()
    
    # Render current page
    page = st.session_state.current_page
    
    if page == "Dashboard":
        render_dashboard()
    elif page == "Chat":
        render_chat()
    elif page == "Quiz":
        render_quiz()
    elif page == "Flashcards":
        render_flashcards()
    elif page == "Panic Mode":
        render_panic_mode()
    elif page == "Settings":
        render_settings()


if __name__ == "__main__":
    main()
