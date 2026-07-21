import os

os.environ["HF_HUB_DISABLE_XET"] = "1"

db = None

RISK_FACTOR_QUERIES = {
    "semester": "career counselling and placement guidance",
    "internal_marks_avg": "academic mentoring and study improvement",
    "hackathon_count": "hackathons, internships and career development",
    "backlog_count": "support for students with academic backlogs",
    "attendance_drop": "attendance counselling and mentoring",
    "gpa_trend": "study skills and tutoring"
}


def get_vector_db():
    global db

    if db is None:
        from langchain_community.vectorstores import Chroma
        from llm.gemini_embeddings import GeminiEmbeddings

        embedding_model = GeminiEmbeddings()

        db = Chroma(
            persist_directory="vector_store/chroma_db_gemini",
            embedding_function=embedding_model
        )

    return db


def search_support_resources(risk_factor: str):
    query = RISK_FACTOR_QUERIES.get(risk_factor)

    if query is None:
        return []

    try:
        vector_db = get_vector_db()
        results = vector_db.similarity_search(query, k=3)
        return [doc.page_content for doc in results]

    except Exception as e:
        print(f"Resource Retrieval Error: {e}")
        return []