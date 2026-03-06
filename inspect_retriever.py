from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

ROOT_DIR = Path(__file__).resolve().parent
CHROMA_DIR = ROOT_DIR / 'data' / 'chromadb'
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
vs = Chroma(persist_directory=str(CHROMA_DIR), embedding_function=emb)
retr = vs.as_retriever(search_kwargs={'k':4})

print('Retriever type:', type(retr))
print('\nMethods:')
for m in sorted([m for m in dir(retr) if not m.startswith('_')]):
    print(m)

# Try retrieve methods if available
for name in ('get_relevant_documents','get_relevant_texts','retrieve','search'):
    if hasattr(retr, name):
        print(f"\nFound method: {name}")
        break
