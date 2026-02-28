"""
Shared Constants for Studaxis
Used by both local app and AWS infrastructure
"""

# Model Configuration
OLLAMA_MODEL = "llama3:3b"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Quantization levels by RAM
QUANTIZATION_MAP = {
    8: "Q4_K_M",   # 8GB+ RAM - Best quality
    6: "Q3_K_S",   # 6-8GB RAM - Balanced
    4: "Q2_K"      # 4-6GB RAM - Optimized for low RAM
}

# Hardware Requirements
MIN_RAM_GB = 4.0
MIN_DISK_GB = 2.0
RECOMMENDED_RAM_GB = 6.0

# Storage Limits
MAX_CHAT_HISTORY = 50
MAX_CONTEXT_TOKENS = 4096
MAX_TEXTBOOKS = 10
MAX_EMBEDDINGS_SIZE_MB = 500

# Sync Configuration
SYNC_RETRY_ATTEMPTS = 3
SYNC_RETRY_DELAY_SECONDS = 5
SYNC_TIMEOUT_SECONDS = 30
TARGET_SYNC_PAYLOAD_KB = 5
MAX_SYNC_PAYLOAD_KB = 50

# Grading Configuration
MAX_QUIZ_SCORE = 10.0
SCORE_GRANULARITY = 0.5
GRADING_TEMPERATURE = 0.3  # Lower for consistent grading

# Difficulty Levels
DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Expert"]

# System Prompts by Difficulty
SYSTEM_PROMPTS = {
    "Beginner": """You are a patient and encouraging AI tutor. Use simple vocabulary, 
    provide step-by-step explanations, and give plenty of examples. Assume the student 
    is learning this concept for the first time.""",
    
    "Intermediate": """You are a knowledgeable AI tutor. Use standard academic vocabulary, 
    provide clear explanations with relevant examples, and connect concepts to prior knowledge.""",
    
    "Expert": """You are an advanced AI tutor. Use precise technical terminology, 
    provide concise explanations, and focus on deeper insights and connections between concepts."""
}

# Grading Prompt Template
GRADING_PROMPT_TEMPLATE = """You are an AI grader. Grade the following answer:

Question: {question}

Correct Answer: {correct_answer}

Student Answer: {student_answer}

Provide:
1. Score out of {max_score} (use {granularity} increments)
2. Specific feedback on what was correct/incorrect
3. List of errors with corrections (Red Pen style)

Format your response as:
SCORE: [number]
FEEDBACK: [your feedback]
ERRORS:
- [error 1]: [correction]
- [error 2]: [correction]
"""

# RAG Configuration
RAG_TOP_K = 3  # Number of chunks to retrieve
RAG_CHUNK_SIZE = 500  # Characters per chunk
RAG_CHUNK_OVERLAP = 50  # Overlap between chunks

# RAG Prompt Template
RAG_PROMPT_TEMPLATE = """Context from textbook:
{context}

Question: {query}

Answer the question using ONLY the information from the context above. 
Include source references [Source N] in your answer. If the context doesn't 
contain enough information, say so clearly."""

# UI Configuration
THEMES = {
    "dark": {
        "bg_primary": "#0a0a0f",
        "bg_secondary": "#1a1a2e",
        "text_primary": "#e2e8f0",
        "text_secondary": "#94a3b8",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb"
    },
    "light": {
        "bg_primary": "#f8fafc",
        "bg_secondary": "#ffffff",
        "text_primary": "#1e293b",
        "text_secondary": "#64748b",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8"
    }
}

# Panic Mode Configuration
PANIC_MODE_DURATIONS = [15, 30, 60]  # Minutes
PANIC_MODE_QUESTION_COUNT = 5

# Flashcard Configuration
FLASHCARD_REVIEW_INTERVALS = {
    "Easy": 7,      # Days until next review
    "Medium": 3,
    "Hard": 1
}

# AWS Configuration (defaults)
AWS_REGION = "ap-south-1"
S3_BUCKET_STUDENT = "studaxis-student-stats"
S3_BUCKET_CONTENT = "studaxis-content"

# Bedrock Configuration
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
BEDROCK_REGION = "us-east-1"

# Quiz Types
QUIZ_TYPES = ["mcq", "subjective", "true_false", "fill_blank"]

# Language Support
SUPPORTED_LANGUAGES = ["English", "Hinglish"]

# File Paths (relative to project root)
DATA_DIR = "data"
CHROMADB_DIR = "data/chromadb"
USER_STATS_FILE = "data/user_stats.json"
BACKUP_DIR = "data/backups"
TEXTBOOKS_DIR = "data/sample_textbooks"

# Error Messages
ERROR_MESSAGES = {
    "ollama_not_found": "Ollama not found. Please install from https://ollama.com/download",
    "model_not_available": "Model not available. Run: ollama pull {model}",
    "low_ram": "RAM below minimum requirement. System may be unstable.",
    "low_disk": "Disk space below minimum requirement. Free up space.",
    "sync_failed": "Sync failed. Will retry when connection is available.",
    "grading_failed": "AI grading failed. Please try again.",
    "rag_failed": "Could not retrieve relevant content. Try rephrasing your question."
}

# Success Messages
SUCCESS_MESSAGES = {
    "sync_complete": "✅ Sync complete",
    "quiz_submitted": "✅ Quiz submitted and graded",
    "preferences_saved": "✅ Preferences saved",
    "content_downloaded": "✅ Content downloaded"
}

# Feature Flags (for phased rollout)
FEATURES = {
    "cloud_sync": True,
    "hinglish": True,
    "panic_mode": True,
    "flashcards": True,
    "voice_input": False,  # Phase 2
    "video_caching": False,  # Phase 2
    "peer_sync": False  # Phase 3
}

# Validation Patterns
PATTERNS = {
    "user_id": r"^[a-zA-Z0-9_-]{3,50}$",
    "quiz_id": r"^quiz_[a-zA-Z0-9_-]{8,}$",
    "timestamp": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
}

# API Timeouts
TIMEOUTS = {
    "ollama_inference": 30,
    "bedrock_generation": 60,
    "appsync_sync": 30,
    "s3_upload": 60
}
