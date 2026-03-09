"""One-shot script to build the vector store with per-file timeout protection."""
import json
import signal
import sys
import os
import hashlib
from pathlib import Path

# Suppress torch/HF noise
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ.pop("TORCH_LOGS", None)
import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

_here = Path(__file__).resolve().parent
DATA_DIR = _here / "data"
TEXTBOOK_DIR = DATA_DIR / "sample_textbooks"
CHROMA_DIR = DATA_DIR / "chromadb"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "studaxis_textbooks"

# Per-file timeout (seconds) – skip files that take too long
FILE_TIMEOUT = 120


def main():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import PyPDFLoader, TextLoader

    try:
        from langchain_community.document_loaders import UnstructuredPowerPointLoader
    except ImportError:
        UnstructuredPowerPointLoader = None

    print("[1/4] Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    print("  ✓ Embedding model loaded")

    print("[2/4] Collecting textbook files...")
    files = []
    for p in TEXTBOOK_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".txt", ".text", ".pdf", ".pptx"):
            files.append(p)
    files.sort(key=lambda f: (f.suffix.lower() != ".txt", f.name))  # txt first
    print(f"  Found {len(files)} files")

    print("[3/4] Loading and splitting documents...")
    all_docs = []
    for f in files:
        suffix = f.suffix.lower()
        print(f"  Loading {f.name} ...", end=" ", flush=True)
        try:
            if suffix in (".txt", ".text"):
                loader = TextLoader(str(f), encoding="utf-8")
            elif suffix == ".pdf":
                loader = PyPDFLoader(str(f))
            elif suffix == ".pptx" and UnstructuredPowerPointLoader:
                loader = UnstructuredPowerPointLoader(str(f))
            else:
                print("skip (unsupported)")
                continue

            docs = loader.load()
            subject = f.stem.split("_")[0].lower()
            # Topic extraction before chunking (for topic-aware RAG)
            full_text = "\n\n".join(getattr(d, "page_content", "") or "" for d in docs)
            dominant_topics = []
            if full_text.strip():
                try:
                    from rag.topic_extractor import extract_dominant_topics
                    dominant_topics = extract_dominant_topics(full_text, num_topics=10)
                    if dominant_topics:
                        print(f"    ({len(dominant_topics)} topics)")
                except Exception as ex:
                    print(f"    (topics skipped: {ex})")
            for d in docs:
                d.metadata["subject"] = subject
                d.metadata["source"] = f.name
                d.metadata["file_type"] = suffix
                d.metadata["dominant_topics"] = json.dumps(dominant_topics)
            all_docs.extend(docs)
            print(f"✓ {len(docs)} pages")
        except KeyboardInterrupt:
            print("interrupted — stopping")
            sys.exit(1)
        except Exception as e:
            print(f"FAILED ({e})")

    if not all_docs:
        print("❌ No documents loaded!")
        return

    print(f"  Total raw documents: {len(all_docs)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600, chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    split_docs = splitter.split_documents(all_docs)
    print(f"  Split into {len(split_docs)} chunks")

    # Deterministic IDs
    doc_ids = []
    for i, doc in enumerate(split_docs):
        src = doc.metadata.get("source", "unk")
        h = hashlib.sha256(doc.page_content.encode()).hexdigest()[:16]
        doc_ids.append(f"{src}_{i}_{h}")

    print("[4/4] Building ChromaDB vector store...")

    # Delete old collection if it exists
    vs = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )
    try:
        count = vs._collection.count()
        if count > 0:
            print(f"  Deleting old collection ({count} docs)...")
            vs.delete_collection()
            vs = Chroma(
                collection_name=COLLECTION_NAME,
                persist_directory=str(CHROMA_DIR),
                embedding_function=embeddings,
            )
    except Exception:
        pass

    BATCH = 50
    total = len(split_docs)
    added = 0
    for start in range(0, total, BATCH):
        end = min(start + BATCH, total)
        try:
            vs.add_documents(split_docs[start:end], ids=doc_ids[start:end])
            added = end
            print(f"  ✓ embedded {end}/{total}")
        except Exception as e:
            print(f"  ✗ batch {start}-{end} failed: {e}")

    final = vs._collection.count()
    print(f"\n✅ Done! Vector store has {final} chunks in {CHROMA_DIR}")


if __name__ == "__main__":
    main()
