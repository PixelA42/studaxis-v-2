import sys
from pathlib import Path

# Ensure backend is on path for imports (when run from repo root or backend/ai_chat)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from functools import lru_cache
from utils.local_storage import LocalStorage

from langchain_core.prompts import ChatPromptTemplate
from typing import Any

# Try to import OllamaLLM; use fallback if version incompatible
OllamaLLM: Any = None
try:
    from langchain_ollama import OllamaLLM  # type: ignore[assignment]
except ImportError:
    try:
        from langchain_community.llms import Ollama as OllamaLLM  # type: ignore[assignment]
    except ImportError:
        pass

# Root directory (backend when running from backend, or repo root for shared data)
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = ROOT_DIR / "data"

LLM_MODEL: str = "llama3.2:3b"

# Approximate chars-per-token ratio for budget estimation
_CHARS_PER_TOKEN = 4
# Max tokens for llama3.2:3b context window (conservative)
_MAX_CONTEXT_TOKENS = 3800
_NUM_PREDICT = 512
# Reserve for prompt template + question + generation
_RESERVED_TOKENS = _NUM_PREDICT + 400
_CONTEXT_BUDGET_TOKENS = _MAX_CONTEXT_TOKENS - _RESERVED_TOKENS
_CONTEXT_BUDGET_CHARS = _CONTEXT_BUDGET_TOKENS * _CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# Lazy-initialised singletons (nothing heavy runs at import time)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_vector_store():
    """Build / open the Chroma vector store on first use."""
    from ai_chat.vector import build_vector_store, COLLECTION_NAME, CHROMA_DIR
    print("[info] Initializing vector store for RAG...")
    vs = build_vector_store(rebuild=False)
    print(f"[debug] Using collection: {COLLECTION_NAME}")
    print(f"[debug] Vector store persistence: {CHROMA_DIR}")
    return vs


@lru_cache(maxsize=1)
def _get_llm(temperature: float = 0.5) -> Any:
    """Create the OllamaLLM on first use."""
    if OllamaLLM is None:
        raise RuntimeError(
            "Neither langchain_ollama nor langchain_community.llms.Ollama available. "
            "Run: pip install --upgrade langchain-ollama"
        )
    return OllamaLLM(model=LLM_MODEL, temperature=temperature, num_predict=_NUM_PREDICT)


# Public accessors kept for grader.py and ai_integration_layer.py
vector_store: Any = None  # populated on first access via property-like helpers


def _ensure_initialized() -> None:
    """Trigger lazy init so module-level `vector_store` / `llm` are set."""
    global vector_store, llm
    if vector_store is None:
        vector_store = _get_vector_store()
    if llm is None:
        llm = _get_llm()


llm: Any = None  # populated on first access

# Default storage (CLI / fallback); API callers pass user_id to ask_ai().
_default_storage: LocalStorage = LocalStorage(base_path=str(ROOT_DIR), user_id="student_001")

prompt: ChatPromptTemplate = ChatPromptTemplate.from_template("""
You are Studaxis, a friendly AI study-buddy tutor.
Use the CONTEXT below to answer. If the context is insufficient, use your own knowledge and note [Model Knowledge].
Be conversational: short question → short answer; deep question → detailed explanation with analogies.
Add an exam tip only when genuinely helpful.

CONTEXT:
{context}

{textbook_context}

QUESTION:
{question}

Answer:""")


def get_textbook_context(subject: str | None = None, max_chars: int = 2000) -> str:
    """Load textbook content from sample_textbooks matching subject (fallback: all samples).
    
    This function loads static textbook material to be used as the PRIMARY source
    for RAG (Retrieval Augmented Generation).

    Returns a string to include as `textbook_context` in the prompt.
    """
    books_dir: Path = ROOT_DIR / "data" / "sample_textbooks"
    
    # Check if directory exists
    if not books_dir.exists():
        print(f"[debug] Textbook directory not found: {books_dir}")
        return ""

    # Find all supported text files
    _TEXTBOOK_GLOBS = ("*.txt", "*.md", "*.csv")
    files: list[Path] = []
    for pattern in _TEXTBOOK_GLOBS:
        files.extend(books_dir.glob(pattern))
    if not files:
        print(f"[debug] No textbook files found in: {books_dir}")
        return ""

    # Try to match by subject keyword in filename
    subject_l: str | None = subject.lower() if subject else None
    chosen: Path | None = None
    
    if subject_l:
        for f in files:
            if subject_l in f.stem.lower():
                chosen = f
                print(f"[debug] Matched textbook by subject '{subject}': {f.name}")
                break

    # Fallback: use first available file if no match found
    if not chosen:
        chosen = files[0]
        if subject_l:
            print(f"[debug] Subject '{subject}' not found in textbook files, using: {chosen.name}")
        else:
            print(f"[debug] Using default textbook: {chosen.name}")

    try:
        text: str = chosen.read_text(encoding="utf-8")
        
        if not text or not text.strip():
            print(f"[debug] Textbook file is empty: {chosen.name}")
            return ""
        
        full_len = len(text)
        # Truncate to reasonable length for context window
        if full_len > max_chars:
            text = text[:max_chars] + "\n[...textbook content truncated...]"
            print(f"[debug] Loaded textbook: {chosen.name} ({full_len} chars, truncated to {max_chars})")
        else:
            print(f"[debug] Loaded textbook: {chosen.name} ({full_len} chars)")
        
        return text
        
    except Exception as e:
        print(f"[debug] Failed to read textbook file {chosen.name}: {e}")
        return ""


def _get_doc_topics_from_store(textbook_id: str) -> list[str]:
    """Get dominant_topics for a textbook from vector store metadata."""
    try:
        _ensure_initialized()
        import json
        # Fetch one chunk for this textbook to read its dominant_topics
        docs = vector_store.similarity_search("concepts", k=1, filter={"source": textbook_id})
        if not docs:
            return []
        meta = getattr(docs[0], "metadata", {}) or {}
        raw = meta.get("dominant_topics", "")
        if not raw:
            return []
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return list(parsed) if isinstance(parsed, list) else []
    except Exception as e:
        print(f"[debug] Could not get doc topics for {textbook_id}: {e}")
        return []


def topic_aware_retrieve(
    query: str,
    subject: str | None = None,
    textbook_id: str | None = None,
    top_k: int = 5,
) -> list[Any]:
    """
    Topic-aware RAG retrieval: map question to topics, dual-query, merge, dedupe.

    Step 1: Map user question to 2-3 dominant topics (when textbook_id and topics available)
    Step 2: Retrieve chunks similar to those topics
    Step 3: Retrieve chunks similar to original question
    Step 4: Merge, deduplicate, return top_k chunks
    """
    _ensure_initialized()
    from rag.topic_extractor import map_question_to_topics

    base_filter: dict[str, Any] = {}
    if textbook_id:
        base_filter["source"] = textbook_id
    elif subject:
        base_filter["subject"] = subject.lower()

    seen_ids: set[str] = set()
    seen_content: set[str] = set()
    merged: list[Any] = []

    def add_unique(doc: Any) -> None:
        c = getattr(doc, "page_content", "") or ""
        if len(c) < 20:
            return
        key = c[:200]
        if key in seen_content:
            return
        seen_content.add(key)
        merged.append(doc)

    # Step 1: Get doc topics and map question to relevant topics
    mapped_topics: list[str] = []
    if textbook_id:
        doc_topics = _get_doc_topics_from_store(textbook_id)
        if doc_topics:
            mapped_topics = map_question_to_topics(query, doc_topics)
            if mapped_topics:
                print(f"[debug] Question mapped to topics: {mapped_topics}")

    # Step 2: Retrieve by topic query (if we have mapped topics)
    if mapped_topics:
        topic_query = ", ".join(mapped_topics)
        try:
            retriever = vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 4,
                    "fetch_k": 10,
                    "filter": base_filter if base_filter else None,
                },
            )
            topic_docs = retriever.invoke(topic_query)
            for d in topic_docs or []:
                add_unique(d)
        except Exception as e:
            print(f"[debug] Topic retrieval failed: {e}")

    # Step 3: Retrieve by original question
    try:
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 4,
                "fetch_k": 10,
                "filter": base_filter if base_filter else None,
            },
        )
        question_docs = retriever.invoke(query.strip())
        for d in question_docs or []:
            add_unique(d)
    except Exception as e:
        print(f"[debug] Question retrieval failed: {e}")

    # Step 4: Return top_k (already deduplicated, order preserved: topic hits first, then question hits)
    return merged[:top_k]


def get_retriever(subject: str | None = None, textbook_id: str | None = None) -> Any:
    """
    Get a retriever from the vector store with optional subject or textbook filtering.
    
    Uses semantic search to find the most relevant chunks from embedded textbooks.
    
    Args:
        subject: Optional subject to filter by (applied as metadata filter)
        textbook_id: Optional textbook filename to filter by (applied as source filter)
        
    Returns:
        A retriever object configured for optimal semantic search
    """
    _ensure_initialized()
    k_val = 3 if textbook_id else 4
    search_kwargs: dict[str, Any] = {
        "k": k_val,
        "fetch_k": 12 if not textbook_id else 8,
    }
    
    # Build filter: textbook_id takes precedence (search within one book only)
    if textbook_id:
        search_kwargs["filter"] = {"source": textbook_id}
        print(f"[debug] Retriever filtering by textbook: {textbook_id}")
    elif subject:
        search_kwargs["filter"] = {"subject": subject.lower()}
        print(f"[debug] Retriever filtering by subject: {subject}")
    
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )
    return retriever


def ask_ai(question: str, subject: str | None = None, user_id: str | None = None) -> str:
    """
    Ask the AI a question and get a response using optimized RAG.
    
    Sources used in priority order:
    1. Retrieved Context from vector store (PRIMARY - semantic search results)
    2. Textbook Reference (SECONDARY - static fallback)
    3. LLM general knowledge (TERTIARY - only if both sources fail)
    
    Args:
        question: The user's question
        subject: Optional subject to filter semantic search by
        
    Returns:
        The AI's response as a string
    """
    print(f"\n[debug] Processing question: {question[:100]}...")
    
    # ============ STEP 1: SEMANTIC SEARCH - PRIMARY SOURCE ============
    print("[debug] Step 1: Performing semantic search on embedded textbooks...")
    retriever = get_retriever(subject)
    
    try:
        docs: list[Any] = retriever.invoke(question)
    except Exception as e:
        print(f"[warning] Error during retrieval: {e}")
        docs = []

    # Process and validate retrieved documents
    context: str = ""
    retrieved_context_available: bool = False
    retrieved_chunk_count: int = 0
    
    if docs and len(docs) > 0:
        valid_chunks: list[str] = []
        
        for i, doc in enumerate(docs):
            if hasattr(doc, 'page_content') and doc.page_content:
                chunk_text: str = doc.page_content.strip()
                
                if chunk_text and len(chunk_text) > 20:  # Filter out very short chunks
                    valid_chunks.append(chunk_text)
                    
                    # Extract metadata for better context
                    source_info: str = ""
                    if hasattr(doc, 'metadata'):
                        source: str = doc.metadata.get("source", "unknown")
                        subject_meta: str = doc.metadata.get("subject", "general")
                        source_info = f"[From {source} - {subject_meta}]"
                    
                    print(f"  ✓ Chunk {i+1}: {chunk_text[:60]}... {source_info}")
        
        if valid_chunks:
            context = "\n\n".join(valid_chunks)
            # Enforce token budget on retrieved context
            if len(context) > _CONTEXT_BUDGET_CHARS:
                context = context[:_CONTEXT_BUDGET_CHARS]
                print(f"[debug] Trimmed retrieved context to {_CONTEXT_BUDGET_CHARS} chars (token budget)")
            retrieved_context_available = True
            retrieved_chunk_count = len(valid_chunks)
            print(f"✅ Retrieved {retrieved_chunk_count} relevant chunks from semantic search")
    
    if not retrieved_context_available:
        print("⚠️  No relevant chunks found in semantic search")
    
    # ============ STEP 2: TEXTBOOK REFERENCE - SECONDARY SOURCE ============
    print("[debug] Step 2: Loading textbook reference as fallback...")
    textbook_ctx: str = get_textbook_context(subject)
    textbook_available: bool = bool(textbook_ctx and textbook_ctx.strip())
    
    if textbook_available:
        print(f"✅ Textbook reference loaded ({len(textbook_ctx)} chars)")
    else:
        print("ℹ️  Textbook reference unavailable for this topic")
    
    # ============ STEP 3: BUILD SOURCE SUMMARY ============
    sources_used: list[str] = []
    if retrieved_context_available:
        sources_used.append(f"retrieved-semantic-search({retrieved_chunk_count}-chunks)")
    if textbook_available:
        sources_used.append("textbook-reference")
    
    sources_msg: str = ", ".join(sources_used) if sources_used else "llm-knowledge-only"
    print(f"[debug] Primary Sources: {sources_msg}")
    
    # ============ STEP 4: PREPARE CONTEXT FOR LLM (with token budget) ============
    if retrieved_context_available:
        final_context = context
        # Only add textbook if we have remaining budget (else redundant — chunks came from textbooks)
        remaining_budget = _CONTEXT_BUDGET_CHARS - len(final_context)
        if textbook_available and remaining_budget > 200:
            final_textbook = textbook_ctx[:remaining_budget]
        else:
            final_textbook = ""
    else:
        final_context = textbook_ctx if textbook_available else "[No study material available]"
        final_textbook = ""
    
    # ============ STEP 5: CREATE RAG CHAIN ============
    _ensure_initialized()
    chain: Any = prompt | llm

    # ============ STEP 6: SAVE USER MESSAGE ============
    _storage = LocalStorage(base_path=str(ROOT_DIR), user_id=user_id) if user_id else _default_storage
    try:
        _storage.add_chat_message("user", question, subject or "General")
    except Exception as e:
        print(f"[warning] Could not save user message: {e}")

    # ============ STEP 7: INVOKE CHAIN WITH OPTIMIZED CONTEXT ============
    print("[debug] Step 7: Invoking LLM with optimized context...")
    try:
        response: str = chain.invoke({
            "context": final_context,  # PRIMARY: Retrieved chunks
            "textbook_context": final_textbook,  # SECONDARY: Textbook reference
            "question": question
        })
    except Exception as e:
        print(f"❌ Error during chain invocation: {e}")
        response = f"Error generating response: {str(e)}"
    
    # ============ STEP 8: SAVE ASSISTANT RESPONSE ============
    try:
        _storage.add_chat_message("assistant", str(response), subject or "General")
    except Exception as e:
        print(f"[warning] Could not save assistant response: {e}")

    print("[debug] RAG query completed successfully\n")
    return response

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎓 STUDAXIS - RAG-Based Exam Tutor")
    print("="*60)
    
    # Load or initialize user stats / chat history
    print("\n[info] Loading user session...")
    stats: dict[str, Any] | None = _default_storage.load_user_stats()
    if not stats:
        stats = _default_storage.initialize_user_stats("local_user")
        print("✅ Initialized new local session.")
    else:
        history: list[Any] = stats.get("chat_history", [])
        if history:
            print(f"✅ Restored chat history ({len(history)} messages)")
            print("📝 Last 5 messages:")
            for m in history[-5:]:
                role: Any = m.get("role")
                content: Any = m.get("content")
                content_preview: str = content[:80] + "..." if len(str(content)) > 80 else content
                print(f"   {role.upper()}: {content_preview}")
    
    print("\n" + "-"*60)
    print("💡 Enter your question or 'exit' to quit")
    print("   (Optional: use 'math' or 'science' to filter by subject)")
    print("-"*60 + "\n")

    while True:
        try:
            q: str = input("You: ").strip()
            
            if not q:
                print("⚠️  Please enter a question.\n")
                continue
            
            if q.lower() == "exit":
                print("\n👋 Exiting and saving session.")
                print("="*60 + "\n")
                break
            
            # Optional: Extract subject if specified (e.g., "math: what is algebra")
            subject: str | None = None
            question_text: str = q
            
            if ":" in q:
                parts: list[str] = q.split(":", 1)
                potential_subject: str = parts[0].strip().lower()
                if potential_subject in ["math", "science", "history", "english"]:
                    subject = potential_subject
                    question_text = parts[1].strip()
            
            # Get AI response using RAG
            print("\n🤔 Processing with RAG...\n")
            response: str = ask_ai(question_text, subject=subject)
            print(f"Tutor: {response}\n")
            print("-"*60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Session interrupted.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            print("-"*60 + "\n")