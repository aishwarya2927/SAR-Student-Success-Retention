import os

os.environ["HF_HUB_DISABLE_XET"] = "1"

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_folder="./model_cache"
)

db = Chroma(
    persist_directory="vector_store/chroma_db",
    embedding_function=embedding_model
)

query = "student has attendance issues"

results = db.similarity_search(
    query,
    k=3
)

for i, doc in enumerate(results, start=1):
    print(f"\nResult {i}")
    print("-" * 40)
    print(doc.page_content)