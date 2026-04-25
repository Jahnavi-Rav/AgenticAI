import math
from typing import List, Dict, Any


CHUNK_SIZE = 40
CHUNK_OVERLAP = 8
MIN_SIMILARITY = 0.35


def embed(text: str) -> List[float]:
    vector = [0.0] * 20

    for word in text.lower().split():
        index = sum(ord(c) for c in word) % len(vector)
        vector[index] += 1.0

    return vector


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def chunk_text(text: str) -> List[str]:
    words = text.split()

    if not words:
        return []

    if CHUNK_OVERLAP >= CHUNK_SIZE:
        raise ValueError("Bad chunking: overlap must be smaller than chunk size.")

    chunks = []
    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def remove_duplicate_chunks(chunks: List[str]) -> List[str]:
    seen = set()
    unique = []

    for chunk in chunks:
        normalized = " ".join(chunk.lower().split())

        if normalized not in seen:
            seen.add(normalized)
            unique.append(chunk)

    return unique


class SemanticSearch:
    def __init__(self):
        self.index: List[Dict[str, Any]] = []

    def add_document(self, doc_id: str, text: str) -> None:
        chunks = chunk_text(text)
        chunks = remove_duplicate_chunks(chunks)

        for i, chunk in enumerate(chunks):
            self.index.append({
                "doc_id": doc_id,
                "chunk_id": i,
                "text": chunk,
                "embedding": embed(chunk),
            })

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        query_embedding = embed(query)
        results = []

        for item in self.index:
            score = cosine_similarity(query_embedding, item["embedding"])

            if score >= MIN_SIMILARITY:
                results.append({
                    "score": round(score, 3),
                    "doc_id": item["doc_id"],
                    "chunk_id": item["chunk_id"],
                    "text": item["text"],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


if __name__ == "__main__":
    search_engine = SemanticSearch()

    document = """
    AI agents can use tools, memory, planning, and feedback.
    Agents break goals into subtasks and use tools like calculators or search.
    Vector search helps agents retrieve relevant memories and documents.
    Vector search helps agents retrieve relevant memories and documents.
    Prompt injection is a security risk where user input tries to override instructions.
    """

    search_engine.add_document("doc_1", document)

    queries = [
        "How do agents remember documents?",
        "What is prompt injection?",
        "Best pizza toppings",
        "",
    ]

    for query in queries:
        print("\nQuery:", query)

        results = search_engine.search(query)

        if not results:
            print("No relevant matches found.")
            continue

        for result in results:
            print(result)