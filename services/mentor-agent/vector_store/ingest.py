from dotenv import load_dotenv
load_dotenv()

import os
os.environ["HF_HUB_DISABLE_XET"] = "1"

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from llm.gemini_embeddings import GeminiEmbeddings

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCE_FOLDER = BASE_DIR / "resources"

print("Looking in:", RESOURCE_FOLDER)

documents = []
for file in RESOURCE_FOLDER.glob("*.md"):
    with open(file, "r", encoding="utf-8") as f:
        documents.append(f.read())

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

chunks = []
for document in documents:
    chunks.extend(splitter.split_text(document))

print(f"Loaded {len(documents)} documents")
print(f"Created {len(chunks)} chunks")

embedding_model = GeminiEmbeddings()

db = Chroma.from_texts(
    texts=chunks,
    embedding=embedding_model,
    persist_directory="vector_store/chroma_db_gemini"
)

print("Knowledge base created successfully with Gemini embeddings!")