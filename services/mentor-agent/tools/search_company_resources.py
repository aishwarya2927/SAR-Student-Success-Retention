import os

os.environ["HF_HUB_DISABLE_XET"] = "1"

db = None

KNOWN_COMPANIES = {
    "google", "microsoft", "amazon", "meta", "apple", "adobe", "salesforce",
    "oracle", "ibm", "phonepe", "paytm", "razorpay", "flipkart", "meesho",
    "zomato", "swiggy", "cred", "zepto", "tcs", "infosys", "wipro",
    "accenture", "capgemini", "deloitte", "cognizant", "ltimindtree",
    "tech_mahindra", "jpmorgan_chase", "morgan_stanley", "goldman_sachs",
    "barclays", "deutsche_bank", "hsbc", "nvidia", "intel", "qualcomm",
    "cisco", "samsung", "isro", "drdo", "nic", "rbi"
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


def search_company_resources(company: str, k: int = 3):
    """Single-company lookup. Returns (results, is_curated)."""
    if not company:
        return [], False

    company_key = company.strip().lower().replace(" ", "_")

    if company_key not in KNOWN_COMPANIES:
        return [], False

    try:
        vector_db = get_vector_db()
        results = vector_db.similarity_search(
            query=f"{company} placement eligibility selection process preparation",
            k=k,
            filter={"company": company_key}
        )
        return [doc.page_content for doc in results], True

    except Exception as e:
        print(f"Company Resource Retrieval Error: {e}")
        return [], False


def search_multiple_company_resources(companies: list[str], k: int = 3):
    """
    Looks up each company independently, returns a dict:
    { "Google": {"context": [...], "is_curated": True}, "Microsoft": {...} }
    """
    results = {}
    for company in companies:
        context, is_curated = search_company_resources(company, k=k)
        results[company] = {"context": context, "is_curated": is_curated}
    return results