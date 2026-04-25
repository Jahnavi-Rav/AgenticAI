import math
from typing import List, Dict, Any


MIN_SCORE = 0.35
MAX_EXPANDED_QUERIES = 4
SOURCE_OVERFIT_LIMIT = 2


DOCUMENTS = [
    {
        "source": "memory_notes.txt",
        "text": "Agents use memory to remember user preferences, prior conversations, and task history."
    },
    {
        "source": "rag_notes.txt",
        "text": "RAG systems retrieve relevant chunks from documents and use them as grounded context."
    },
    {
        "source": "vector_notes.txt",
        "text": "Vector search uses embeddings to find semantically similar text."
    },
    {
        "source": "memory_notes.txt",
        "text": "Long-term memory can store facts, summaries, and user preferences."
    },
    {
        "source": "memory_notes.txt",
        "text": "Memory retrieval should avoid irrelevant recall and privacy leaks."
    },
]


QUERY_EXPANSIONS = {
    "remember": ["memory", "recall", "stored facts"],
    "search": ["retrieval", "vector search", "document lookup"],
    "documents": ["chunks", "sources", "context"],
}


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


def expand_query(query: str) -> List[str]:
    """
    Handles query drift:
    - Always keeps original query first
    - Limits number of expansions
    """

    expanded = [query]
    words = query.lower().split()

    for word in words:
        if word in QUERY_EXPANSIONS:
            for extra in QUERY_EXPANSIONS[word]:
                expanded.append(f"{query} {extra}")

    return expanded[:MAX_EXPANDED_QUERIES]


def keyword_score(query: str, text: str) -> float:
    query_words = set(query.lower().split())
    text_words = set(text.lower().split())

    if not query_words:
        return 0.0

    return len(query_words & text_words) / len(query_words)


def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    query_vector = embed(query)
    results = []

    for i, doc in enumerate(DOCUMENTS):
        vector_score = cosine_similarity(query_vector, embed(doc["text"]))

        results.append({
            "id": i,
            "source": doc["source"],
            "text": doc["text"],
            "vector_score": vector_score,
        })

    results.sort(key=lambda x: x["vector_score"], reverse=True)
    return results[:top_k]


def remove_duplicates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []

    for result in results:
        key = (result["source"], result["text"])

        if key not in seen:
            seen.add(key)
            unique.append(result)

    return unique


def rerank(original_query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Handles source overfitting:
    - Penalizes too many results from the same source
    """

    source_counts = {}

    for result in results:
        source = result["source"]
        source_counts[source] = source_counts.get(source, 0) + 1

    reranked = []

    for result in results:
        k_score = keyword_score(original_query, result["text"])
        v_score = result["vector_score"]

        source_penalty = 0.0
        if source_counts[result["source"]] > SOURCE_OVERFIT_LIMIT:
            source_penalty = 0.10

        final_score = (0.65 * v_score) + (0.35 * k_score) - source_penalty

        result["keyword_score"] = round(k_score, 3)
        result["final_score"] = round(final_score, 3)
        result["source_penalty"] = source_penalty

        reranked.append(result)

    reranked.sort(key=lambda x: x["final_score"], reverse=True)
    return reranked


def advanced_search(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if not query.strip():
        return []

    expanded_queries = expand_query(query)

    all_results = []

    for expanded_query in expanded_queries:
        results = retrieve(expanded_query)
        all_results.extend(results)

    unique_results = remove_duplicates(all_results)
    reranked_results = rerank(query, unique_results)

    final_results = [
        r for r in reranked_results
        if r["final_score"] >= MIN_SCORE
    ]

    return final_results[:top_k]


if __name__ == "__main__":
    queries = [
        "How do agents remember?",
        "How does search work in documents?",
        "pizza toppings",
        "",
    ]

    for query in queries:
        print("\n====================")
        print("Query:", query)

        results = advanced_search(query)

        if not results:
            print("No relevant results found.")
            continue

        for result in results:
            print({
                "source": result["source"],
                "text": result["text"],
                "vector_score": round(result["vector_score"], 3),
                "keyword_score": result["keyword_score"],
                "source_penalty": result["source_penalty"],
                "final_score": result["final_score"],
            })