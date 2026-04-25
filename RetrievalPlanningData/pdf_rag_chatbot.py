import os
import math
from typing import List, Dict, Any
from pypdf import PdfReader


CHUNK_SIZE = 120
CHUNK_OVERLAP = 30
MIN_SCORE = 0.35


def read_pdf(path: str) -> str:
    reader = PdfReader(path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"

    return text


def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_document(path: str) -> str:
    if path.endswith(".pdf"):
        return read_pdf(path)

    if path.endswith(".txt") or path.endswith(".md"):
        return read_txt(path)

    raise ValueError("Unsupported file type. Use PDF, TXT, or MD.")


def chunk_text(text: str) -> List[str]:
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def embed(text: str) -> List[float]:
    vector = [0.0] * 50

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


class RAGChatbot:
    def __init__(self):
        self.index: List[Dict[str, Any]] = []

    def add_document(self, path: str) -> None:
        text = load_document(path)
        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            self.index.append({
                "source": os.path.basename(path),
                "chunk_id": i,
                "text": chunk,
                "embedding": embed(chunk),
            })

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        query_embedding = embed(query)
        results = []

        for item in self.index:
            score = cosine_similarity(query_embedding, item["embedding"])

            if score >= MIN_SCORE:
                results.append({
                    "score": round(score, 3),
                    "source": item["source"],
                    "chunk_id": item["chunk_id"],
                    "text": item["text"],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def detect_conflicts(self, results: List[Dict[str, Any]]) -> bool:
        texts = [r["text"].lower() for r in results]

        conflict_pairs = [
            ("allowed", "not allowed"),
            ("true", "false"),
            ("yes", "no"),
            ("increase", "decrease"),
            ("required", "optional"),
        ]

        combined = " ".join(texts)

        for a, b in conflict_pairs:
            if a in combined and b in combined:
                return True

        return False

    def answer(self, query: str) -> Dict[str, Any]:
        results = self.retrieve(query)

        if not results:
            return {
                "answer": "I don't know. I could not find evidence in the documents.",
                "citations": [],
                "warning": "Missing evidence",
            }

        conflict = self.detect_conflicts(results)

        context = "\n\n".join(
            f"[{r['source']}#chunk{r['chunk_id']}] {r['text']}"
            for r in results
        )

        if conflict:
            answer = (
                "I found possibly conflicting evidence in the documents. "
                "Please review the cited chunks before trusting the answer.\n\n"
                f"Relevant evidence:\n{context}"
            )
            warning = "Conflicting sources detected"
        else:
            answer = (
                "Based only on the retrieved document evidence:\n\n"
                f"{results[0]['text']}\n\n"
                "I am not using outside knowledge."
            )
            warning = None

        citations = [
            f"{r['source']}#chunk{r['chunk_id']}"
            for r in results
        ]

        return {
            "answer": answer,
            "citations": citations,
            "warning": warning,
        }


if __name__ == "__main__":
    bot = RAGChatbot()

    # Add your files here
    bot.add_document("example.pdf")
    # bot.add_document("notes.txt")
    # bot.add_document("README.md")

    print("PDF/DOC RAG Chatbot")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in ["exit", "quit"]:
            break

        result = bot.answer(question)

        print("\nAnswer:")
        print(result["answer"])

        print("\nCitations:")
        print(result["citations"])

        if result["warning"]:
            print("\nWarning:", result["warning"])

        print()