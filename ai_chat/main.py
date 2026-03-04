import sys
from pathlib import Path

# Ensure the parent directory is in the path for imports
ROOT_DIR_TEMP: Path = Path(__file__).resolve().parent.parent
if str(ROOT_DIR_TEMP) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR_TEMP))

from local_app.utils.local_storage import LocalStorage
from ai_chat.vector import build_vector_store, COLLECTION_NAME, CHROMA_DIR, EMBEDDING_MODEL

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from typing import Any

# Try to import OllamaLLM; use fallback if version incompatible
try:
    from langchain_ollama import OllamaLLM
except ImportError as e:
    print(f"[warning] Could not import langchain_ollama: {e}")
    print("[info] Using langchain_community.llms.Ollama as fallback...")
    try:
        from langchain_community.llms import Ollama as OllamaLLM
    except ImportError:
        print("❌ Neither langchain_ollama nor langchain_community.llms.Ollama available")
        OllamaLLM = None

# Root directory
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

DATA_DIR: Path = ROOT_DIR / "data"

LLM_MODEL: str = "llama3.2:3b"

# Initialize and load embeddings
embeddings: HuggingFaceEmbeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)

# Build or load vector store with textbook embeddings
print("[info] Initializing vector store for RAG...")
vector_store: Chroma = build_vector_store(rebuild=False)

print(f"[debug] Using collection: {COLLECTION_NAME}")
print(f"[debug] Vector store persistence: {CHROMA_DIR}")

# Local session storage
storage: LocalStorage = LocalStorage(base_path=str(DATA_DIR))

# Ollama LLM - with fallback handling
if OllamaLLM is None:
    print("❌ ERROR: Could not initialize the LLM. Please fix the version compatibility:")
    print("   Try: pip install --upgrade langchain-community langchain-core langchain-ollama")
    sys.exit(1)

llm: Any = OllamaLLM(
    model=LLM_MODEL,
    temperature=0.5,
    num_predict=512
)

prompt: ChatPromptTemplate = ChatPromptTemplate.from_template("""
You are an expert competitive exam tutor with deep subject knowledge.

PRIORITY HIERARCHY FOR ANSWERING:
1. **PRIMARY SOURCE**: Use retrieved context material (these are the most relevant chunks from textbooks matched to the question via semantic search)
2. **SECONDARY SOURCE**: If retrieved context is incomplete, supplement with textbook reference material
3. **TERTIARY SOURCE**: Only if both retrieved and textbook are insufficient and looks incomplete, use your general knowledge (CLEARLY MARK with [Model Knowledge])

CRITICAL INSTRUCTION:
- Prioritize the RETRIEVED CONTEXT sections - these are semantically matched to the question
- Answer using information from retrieved chunks first
- Textbook reference is for additional context if needed
- If neither source covers the topic, supplement with general knowledge but explicitly mark it
- respond to the brief of the question, avoid unnecessary verbosity, and focus on clarity and accuracy.
- if the question is ambiguous, provide a concise answer based on the most relevant retrieved context and textbook material, and note any assumptions made.
- if the answer looks incomplete based on the retrieved and textbook material, use your general knowledge to fill in gaps but clearly mark it as [Model Knowledge].
                                                                                                                           
RETRIEVED CONTEXT (Semantically Matched to Question):
{context}

TEXTBOOK REFERENCE (Full material for reference):
{textbook_context}

USER QUESTION:
{question}

RESPONSE FORMAT:
Provide a structured answer:
1. **Direct Answer** - From retrieved context primarily
2. **Key Concepts** - Properly identify which source this comes from
3. **Formulas/Definitions** - If applicable, from retrieved and textbook sources
4. **Exam Strategic Tips** - Your expert knowledge enhanced with source materials
5. **Important Notes** - Mark if you're adding information beyond provided sources [Model Knowledge]

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

    # Find all text files
    files: list[Path] = list(books_dir.glob("*.txt"))
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
        
        # Truncate to reasonable length for context window
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...textbook content truncated...]"
            print(f"[debug] Loaded textbook: {chosen.name} ({len(chosen.read_text(encoding='utf-8'))} chars, truncated to {max_chars})")
        else:
            print(f"[debug] Loaded textbook: {chosen.name} ({len(text)} chars)")
        
        return text
        
    except Exception as e:
        print(f"[debug] Failed to read textbook file {chosen.name}: {e}")
        return ""


def get_retriever(subject: str | None = None) -> Any:
    """
    Get a retriever from the vector store with optional subject filtering.
    
    Uses semantic search to find the most relevant chunks from embedded textbooks.
    
    Args:
        subject: Optional subject to filter by (applied as metadata filter)
        
    Returns:
        A retriever object configured for optimal semantic search
    """
    search_kwargs: dict[str, Any] = {
        "k": 8,  # Increased from 4 to get more relevant chunks
    }
    
    # Add subject filter if specified
    if subject:
        search_kwargs["filter"] = {"subject": subject.lower()}
        print(f"[debug] Retriever filtering by subject: {subject}")
    
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    return retriever


def ask_ai(question: str, subject: str | None = None) -> str:
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
            # Join chunks with clear separators and source attribution
            context = "\n\n---NEXT CHUNK---\n\n".join(valid_chunks)
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
    
    # ============ STEP 4: PREPARE CONTEXT FOR LLM ============
    # Prioritize retrieved context as primary
    final_context: str = context if retrieved_context_available else "[No relevant chunks found - using textbook]\n" + (textbook_ctx if textbook_available else "[No textbook material]")
    final_textbook: str = textbook_ctx if textbook_available else "[Textbook reference not available]"
    
    # ============ STEP 5: CREATE RAG CHAIN ============
    chain: Any = prompt | llm

    # ============ STEP 6: SAVE USER MESSAGE ============
    try:
        storage.add_chat_message("user", question, subject or "General")
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
        storage.add_chat_message("assistant", str(response), subject or "General")
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
    stats: dict[str, Any] | None = storage.load_user_stats()
    if not stats:
        stats = storage.initialize_user_stats("local_user")
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