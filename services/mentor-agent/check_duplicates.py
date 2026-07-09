from dotenv import load_dotenv
load_dotenv()

from langchain_community.vectorstores import Chroma
from llm.gemini_embeddings import GeminiEmbeddings

embedding_model = GeminiEmbeddings()
db = Chroma(
    persist_directory="vector_store/chroma_db_gemini",
    embedding_function=embedding_model
)

all_data = db.get(include=["documents", "metadatas"])
print("Total chunks in collection:", len(all_data["documents"]))

no_metadata_count = sum(1 for m in all_data["metadatas"] if m is None)
general_count = sum(1 for m in all_data["metadatas"] if m and m.get("category") == "general_support")
placement_count = sum(1 for m in all_data["metadatas"] if m and m.get("category") == "placement")

print(f"No metadata (old/legacy chunks): {no_metadata_count}")
print(f"general_support: {general_count}")
print(f"placement: {placement_count}")

from collections import Counter
counts = Counter(all_data["documents"])
duplicates = {text: count for text, count in counts.items() if count > 1}
print(f"\nDuplicate text chunks: {len(duplicates)}")
if duplicates:
    sample = list(duplicates.items())[0]
    print("Example (appears", sample[1], "times):")
    print(sample[0][:200])