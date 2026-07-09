import os
os.environ["HF_HUB_DISABLE_XET"] = "1"

import shutil
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from llm.gemini_embeddings import GeminiEmbeddings

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCE_FOLDER = BASE_DIR / "resources"
PLACEMENT_FOLDER = BASE_DIR / "resources" / "placement"
PERSIST_DIR = BASE_DIR / "vector_store" / "chroma_db_gemini"

if PERSIST_DIR.exists():
    deleted = False
    for attempt in range(5):
        try:
            shutil.rmtree(PERSIST_DIR)
            print(f"Cleared existing collection at {PERSIST_DIR}")
            deleted = True
            break
        except PermissionError:
            print(f"Folder locked, retrying in 3s... (attempt {attempt + 1}/5)")
            time.sleep(3)

    if not deleted:
        print("\nCould not delete the old collection automatically.")
        print("Close VS Code and any running Python processes, pause OneDrive sync, then run:")
        print(f'  Remove-Item -Recurse -Force "{PERSIST_DIR}"')
        print("Then re-run this script.")
        raise SystemExit(1)

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

texts = []
metadatas = []

for file in RESOURCE_FOLDER.glob("*.md"):
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    for chunk in splitter.split_text(content):
        texts.append(chunk)
        metadatas.append({"category": "general_support", "source": file.stem})

if PLACEMENT_FOLDER.exists():
    for file in PLACEMENT_FOLDER.glob("*.md"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        company_name = file.stem.strip().lower()
        for chunk in splitter.split_text(content):
            texts.append(chunk)
            metadatas.append({"category": "placement", "company": company_name})

general_count = sum(1 for m in metadatas if m["category"] == "general_support")
placement_count = sum(1 for m in metadatas if m["category"] == "placement")
print(f"Loaded {len(texts)} total chunks ({general_count} general_support, {placement_count} placement)")

embedding_model = GeminiEmbeddings()

db = Chroma.from_texts(
    texts=texts,
    embedding=embedding_model,
    metadatas=metadatas,
    persist_directory=str(PERSIST_DIR)
)

print("Knowledge base created successfully with Gemini embeddings (general + placement)!")