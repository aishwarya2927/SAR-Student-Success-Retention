import os
import time
from google import genai
from google.genai import types
from google.genai.errors import ClientError

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _embed_with_retry(client, model, contents, config, max_retries=5):
    for attempt in range(max_retries):
        try:
            return client.models.embed_content(model=model, contents=contents, config=config)
        except ClientError as e:
            if e.code == 429 and attempt < max_retries - 1:
                wait = 20 * (attempt + 1)  # 20s, 40s, 60s, 80s, 100s
                print(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


class GeminiEmbeddings:
    def __init__(self, model="gemini-embedding-001", batch_size=20):
        self.model = model
        self.batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        client = _get_client()
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            result = _embed_with_retry(
                client, self.model, batch,
                types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            all_embeddings.extend([e.values for e in result.embeddings])
            print(f"Embedded {min(i + self.batch_size, len(texts))}/{len(texts)} chunks")

            # Deliberate pause between batches to stay under per-minute quota
            if i + self.batch_size < len(texts):
                time.sleep(15)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        client = _get_client()
        result = _embed_with_retry(
            client, self.model, [text],
            types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        return result.embeddings[0].values