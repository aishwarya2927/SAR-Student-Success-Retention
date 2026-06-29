
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

RISK_FACTOR_QUERIES = {
    "backlog_count": "support for students with academic backlogs",
    "gpa_trend": "study skills and tutoring for low GPA",
    "attendance_drop": "attendance counselling and mentoring"
}

def search_support_resources(risk_factor: str):

    query = RISK_FACTOR_QUERIES.get(risk_factor)

    if query is None:
        return []

    results = db.similarity_search(
        query,
        k=3
    )

    return [doc.page_content for doc in results]


