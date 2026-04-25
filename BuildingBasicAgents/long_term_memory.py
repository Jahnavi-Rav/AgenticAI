from typing import List, Dict, Any
import math
import re
import time


SENSITIVE_PATTERNS = [
    r"password\s*[:=]\s*\S+",
    r"api[_\s-]?key\s*[:=]\s*\S+",
    r"secret\s*[:=]\s*\S+",
    r"token\s*[:=]\s*\S+",
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-like
]

MIN_RECALL_SCORE = 0.75
MAX_MEMORY_ITEMS = 20


class LongTermMemory:
    def __init__(self):
        self.memories: List[Dict[str, Any]] = []

    def embed(self, text: str) -> List[float]:
        """
        Simple fake embedding for learning.
        Real systems use embedding models.
        """
        words = text.lower().split()
        vector = [0.0] * 10

        for word in words:
            index = sum(ord(c) for c in word) % 10
            vector[index] += 1.0

        return vector

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def contains_sensitive_info(self, text: str) -> bool:
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def is_confirmed_fact(self, text: str) -> bool:
        """
        Prevents false memories.
        Store only clear user facts/preferences.
        """
        safe_starts = [
            "user likes",
            "user prefers",
            "user is",
            "user wants",
            "user lives",
            "user works",
            "user dislikes",
        ]

        lowered = text.lower().strip()
        return any(lowered.startswith(start) for start in safe_starts)

    def add_memory(self, text: str) -> bool:
        if not text.strip():
            print("Blocked: empty memory.")
            return False

        if self.contains_sensitive_info(text):
            print("Blocked: privacy leak risk.")
            return False

        if not self.is_confirmed_fact(text):
            print("Blocked: possible false memory. Store only confirmed user facts.")
            return False

        embedding = self.embed(text)

        memory = {
            "text": text,
            "embedding": embedding,
            "created_at": time.time(),
        }

        self.memories.append(memory)

        if len(self.memories) > MAX_MEMORY_ITEMS:
            self.memories = self.memories[-MAX_MEMORY_ITEMS:]

        print("Memory saved.")
        return True

    def search_memory(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        query_embedding = self.embed(query)
        results = []

        for memory in self.memories:
            score = self.cosine_similarity(query_embedding, memory["embedding"])

            if score >= MIN_RECALL_SCORE:
                results.append({
                    "text": memory["text"],
                    "score": round(score, 3),
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]


if __name__ == "__main__":
    memory = LongTermMemory()

    # Good memories
    memory.add_memory("User likes budget travel")
    memory.add_memory("User prefers vegetarian food")
    memory.add_memory("User is learning Agentic AI")

    # Edge cases
    memory.add_memory("User password: hello123")          # privacy leak blocked
    memory.add_memory("Maybe the user likes stocks")      # false memory blocked
    memory.add_memory("")                                 # empty blocked

    print("\nRecall results:")
    results = memory.search_memory("cheap travel and food")

    if results:
        for item in results:
            print(item)
    else:
        print("No relevant memories found.")