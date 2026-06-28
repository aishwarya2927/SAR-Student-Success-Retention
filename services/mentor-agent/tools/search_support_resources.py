
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

def search_support_resources(query: str):
  results = db.similarity_search(
    query,
    k=3
  )

  return [doc.page_content for doc in results]


