import json
import os
from pathlib import Path
from typing import Any
import zipfile
import re

os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ.pop("TORCH_LOGS", None)

import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
# additional loaders may not exist in all environments; wrap imports
try:
    from langchain_community.document_loaders import Docx2txtLoader
except ImportError:
    Docx2txtLoader = None

try:
    from langchain_community.document_loaders import UnstructuredMarkdownLoader
except ImportError:
    UnstructuredMarkdownLoader = None

try:
    from langchain_community.document_loaders import UnstructuredPowerPointLoader
except ImportError:
    UnstructuredPowerPointLoader = None

try:
    from langchain_community.document_loaders import UnstructuredExcelLoader
except ImportError:
    UnstructuredExcelLoader = None

# loader for youtube transcripts
try:
    from langchain_community.document_loaders import YoutubeLoader
except ImportError:
    YoutubeLoader = None

# Root directory: backend when running from backend (backend/data); use parent.parent for repo root if you want shared data
# Here we use backend so DATA_DIR = backend/data; set ROOT_DIR = _here.parent.parent.parent for repo root data
_here: Path = Path(__file__).resolve().parent
ROOT_DIR: Path = _here.parent
DATA_DIR: Path = ROOT_DIR / "data"
TEXTBOOK_DIR: Path = DATA_DIR / "sample_textbooks"
CHROMA_DIR: Path = DATA_DIR / "chromadb"

EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME: str = "studaxis_textbooks"


def build_vector_store(rebuild: bool = False) -> Chroma:
    """
    Build or load vector store with textbook embeddings for RAG.
    
    Args:
        rebuild: If True, rebuild the vector store from scratch
        
    Returns:
        Chroma vector store instance with textbook embeddings
    """
    # Initialize embeddings
    embeddings: HuggingFaceEmbeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    # Load or create vector store
    vector_store: Chroma = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )

    # Check if rebuild is needed
    db_exists: bool = False
    db_empty: bool = True
    
    try:
        # Try to get collection count
        collection_count: int = vector_store._collection.count()
        db_exists = collection_count > 0
        db_empty = collection_count == 0
        print(f"[debug] Vector DB exists with {collection_count} documents")
        
    except Exception as e:
        print(f"[debug] Vector DB not initialized yet or error: {e}")
        db_exists = False
        db_empty = True

    # Skip rebuild if DB exists and has documents (unless rebuild=True)
    if db_exists and not rebuild:
        print("✅ Using existing Vector DB.")
        return vector_store

    print("[info] Building/Rebuilding vector store from textbooks and linked resources...")

    documents: list[Any] = []
    
    if not TEXTBOOK_DIR.exists():
        print(f"❌ Textbook directory not found: {TEXTBOOK_DIR}")
        return vector_store

    # traverse folder including zip contents
    def iter_files(base: Path):
        # walk recursively, unzip .zip files on the fly
        for item in base.iterdir():
            if item.is_dir():
                yield from iter_files(item)
            elif item.suffix.lower() == ".zip":
                # extract to temporary directory
                extract_dir = base / (item.stem + "_unzipped")
                if not extract_dir.exists():
                    try:
                        import zipfile
                        with zipfile.ZipFile(item, 'r') as zf:
                            zf.extractall(extract_dir)
                        print(f"[debug] Extracted {item.name} to {extract_dir}")
                    except Exception as e:
                        print(f"❌ Failed to unzip {item.name}: {e}")
                        continue
                yield from iter_files(extract_dir)
            else:
                yield item

    textbook_files: list[Path] = list(set(iter_files(TEXTBOOK_DIR)))
    if not textbook_files:
        print(f"⚠️  No files found in {TEXTBOOK_DIR}")
        return vector_store

    print(f"[info] Loading {len(textbook_files)} file(s) from textbooks directory...")

    for file in textbook_files:
        try:
            subject: str = file.stem.split("_")[0].lower()

            loader = None
            suffix = file.suffix.lower()
            print(f"[debug] Processing {file.name} (suffix {suffix})")

            # choose loader based on suffix
            if suffix == ".pdf":
                loader = PyPDFLoader(str(file))
            elif suffix in (".txt", ".text"):
                loader = TextLoader(str(file), encoding="utf-8")
            elif suffix == ".md" and UnstructuredMarkdownLoader is not None:
                loader = UnstructuredMarkdownLoader(str(file))
            elif suffix == ".md":
                # Fallback: load markdown as plain text
                loader = TextLoader(str(file), encoding="utf-8")
            elif suffix == ".csv" and CSVLoader is not None:
                loader = CSVLoader(str(file))
            elif suffix in (".pptx", ".ppt") and UnstructuredPowerPointLoader is not None:
                loader = UnstructuredPowerPointLoader(str(file))
            elif suffix in (".xlsx", ".xls") and UnstructuredExcelLoader is not None:
                loader = UnstructuredExcelLoader(str(file))
            elif suffix == ".docx" and Docx2txtLoader is not None:
                loader = Docx2txtLoader(str(file))
            elif suffix == ".doc":
                print(f"[info] .doc format not supported, convert to .docx: {file.name}")
                continue
            else:
                print(f"[debug] Unsupported file type, skipping: {file.name}")
                continue

            if loader is None:
                print(f"[debug] No loader available for {file.name}, skipping")
                continue

            docs: list[Any] = loader.load()

            # for text files, also look for youtube links lines
            if suffix == ".txt" and YoutubeLoader is not None and docs:
                for d in docs:
                    text_content = d.page_content or ""
                    import re
                    urls = re.findall(r'https?://\S+', text_content)
                    for url in urls:
                        if "youtube.com" in url or "youtu.be" in url:
                            try:
                                yloader = YoutubeLoader.from_youtube_url(url)
                                ydocs = yloader.load()
                                for yd in ydocs:
                                    yd.metadata["subject"] = subject
                                    yd.metadata["source"] = url
                                    yd.metadata["file_type"] = "youtube"
                                documents.extend(ydocs)
                                print(f"✓ Loaded youtube transcript from {url}")
                            except Exception as e:
                                print(f"⚠️  Failed to load youtube {url}: {e}")
                        elif "drive.google.com" in url or "docs.google.com" in url:
                            # Placeholder: downloading from Google Drive requires auth/setup
                            print(f"⚠️  Google Drive link found ({url}) – manual download required before embedding.")

            if not docs:
                print(f"⚠️  No content loaded from {file.name}")
                continue

            # Topic extraction BEFORE chunking (for topic-aware RAG)
            full_text = "\n\n".join(getattr(d, "page_content", "") or "" for d in docs)
            dominant_topics: list[str] = []
            if full_text.strip():
                try:
                    from rag.topic_extractor import extract_dominant_topics
                    dominant_topics = extract_dominant_topics(full_text, num_topics=10)
                    if dominant_topics:
                        print(f"  ✓ Extracted {len(dominant_topics)} topics for {file.name}")
                except Exception as ex:
                    print(f"  ⚠️ Topic extraction skipped for {file.name}: {ex}")

            for doc in docs:
                doc.metadata["subject"] = subject
                doc.metadata["source"] = file.name
                doc.metadata["file_type"] = suffix
                doc.metadata["dominant_topics"] = json.dumps(dominant_topics)

            documents.extend(docs)
            print(f"✓ Loaded {len(docs)} documents from {file.name}")

        except Exception as e:
            print(f"❌ Error loading {file.name}: {e}")
            continue

    if not documents:
        print("❌ No documents loaded. Vector store will be empty.")
        return vector_store

    print(f"[info] Total documents loaded: {len(documents)}")
    print("[info] Splitting documents into chunks...")

    # Split documents into chunks — stay within MiniLM-L6-v2's 256-token window
    splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(
        chunk_size=600,   # ~150 tokens, safely within 256-token embedding limit
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    split_docs: list[Any] = splitter.split_documents(documents)
    print(f"✓ Created {len(split_docs)} chunks")

    # Generate deterministic IDs from content hash for deduplication
    import hashlib
    doc_ids: list[str] = []
    for i, doc in enumerate(split_docs):
        source = doc.metadata.get("source", "unknown")
        content_hash = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()[:16]
        doc_ids.append(f"{source}_{i}_{content_hash}")

    # Clear existing collection if rebuilding
    if rebuild and db_exists:
        try:
            print("[info] Clearing existing collection for rebuild...")
            vector_store.delete_collection()
            # Re-create the collection after deletion
            vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                persist_directory=str(CHROMA_DIR),
                embedding_function=embeddings,
            )
        except Exception as e:
            print(f"[warning] Could not delete existing collection: {e}")

    # Add documents to vector store (with deterministic IDs to prevent duplicates)
    print("[info] Adding documents to vector store...")
    try:
        vector_store.add_documents(split_docs, ids=doc_ids)
        print(f"✅ Vector DB built successfully with {len(split_docs)} chunks.")
    except Exception as e:
        print(f"❌ Error adding documents to vector store: {e}")

    return vector_store


if __name__ == "__main__":
    import sys
    
    # Allow --rebuild flag to force rebuild
    rebuild_flag: bool = "--rebuild" in sys.argv or "-r" in sys.argv
    
    if rebuild_flag:
        print("[info] Rebuild flag detected. Will rebuild vector store...")
    
    build_vector_store(rebuild=rebuild_flag)