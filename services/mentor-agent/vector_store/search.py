from dotenv import load_dotenv
load_dotenv()

from langchain_community.vectorstores import Chroma
from llm.gemini_embeddings import GeminiEmbeddings

embedding_model = GeminiEmbeddings()

db = Chroma(
    persist_directory="vector_store/chroma_db_gemini",
    embedding_function=embedding_model
)

query = "student has attendance issues"
results = db.similarity_search(query, k=3)

for i, doc in enumerate(results, start=1):
    print(f"\nResult {i}")
    print("-" * 40)
    print(doc.page_content)