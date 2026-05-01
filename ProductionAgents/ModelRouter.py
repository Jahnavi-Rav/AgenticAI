import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


CHEAP_MODEL_COST = 0.001
QUALITY_MODEL_COST = 0.01

MAX_CACHE_AGE_SECONDS = 300


@dataclass
class ModelResponse:
    model_name: str
    answer: str
    cost: float
    latency_seconds: float
    confidence: float


@dataclass
class CacheEntry:
    answer: str
    model_name: str
    created_at: float


class ResponseCache:
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}

    def make_key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.strip().lower().encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> Optional[CacheEntry]:
        key = self.make_key(prompt)
        entry = self.cache.get(key)

        if not entry:
            return None

        age = time.time() - entry.created_at

        if age > MAX_CACHE_AGE_SECONDS:
            del self.cache[key]
            return None

        return entry

    def set(self, prompt: str, answer: str, model_name: str) -> None:
        key = self.make_key(prompt)

        self.cache[key] = CacheEntry(
            answer=answer,
            model_name=model_name,
            created_at=time.time(),
        )


class CheapModel:
    def call(self, prompt: str) -> ModelResponse:
        start = time.time()

        time.sleep(0.1)

        prompt_lower = prompt.lower()

        # Silent failure examples:
        if "explain transformer attention" in prompt_lower:
            answer = "It is about AI."
            confidence = 0.9  # falsely confident

        elif "json" in prompt_lower:
            answer = "Sure, here is the data."  # not actual JSON
            confidence = 0.8

        elif "2 + 2" in prompt_lower:
            answer = "4"
            confidence = 0.95

        else:
            answer = "I don't know."
            confidence = 0.4

        return ModelResponse(
            model_name="cheap-model",
            answer=answer,
            cost=CHEAP_MODEL_COST,
            latency_seconds=time.time() - start,
            confidence=confidence,
        )


class QualityModel:
    def call(self, prompt: str) -> ModelResponse:
        start = time.time()

        time.sleep(0.4)

        prompt_lower = prompt.lower()

        if "explain transformer attention" in prompt_lower:
            answer = (
                "Transformer attention lets each token compare itself with other tokens "
                "using query, key, and value vectors, then weight the most relevant context."
            )

        elif "json" in prompt_lower:
            answer = '{"status": "ok", "answer": "valid structured output"}'

        elif "2 + 2" in prompt_lower:
            answer = "4"

        else:
            answer = "A higher-quality model handled this request with more complete reasoning."

        return ModelResponse(
            model_name="quality-model",
            answer=answer,
            cost=QUALITY_MODEL_COST,
            latency_seconds=time.time() - start,
            confidence=0.95,
        )


class OutputVerifier:
    def is_silent_failure(self, prompt: str, response: ModelResponse) -> bool:
        answer = response.answer.strip()
        prompt_lower = prompt.lower()

        if not answer:
            return True

        if len(answer.split()) < 5 and "2 + 2" not in prompt_lower:
            return True

        vague_answers = [
            "i don't know",
            "it is about ai",
            "sure",
            "okay",
            "done",
        ]

        if answer.lower() in vague_answers:
            return True

        if "json" in prompt_lower:
            if not (answer.startswith("{") and answer.endswith("}")):
                return True

        if "explain" in prompt_lower and len(answer.split()) < 12:
            return True

        # Cheap model claiming high confidence does not guarantee correctness.
        if response.model_name == "cheap-model" and response.confidence > 0.85:
            if len(answer.split()) < 8 and "2 + 2" not in prompt_lower:
                return True

        return False


class ModelRouter:
    def __init__(self):
        self.cache = ResponseCache()
        self.cheap_model = CheapModel()
        self.quality_model = QualityModel()
        self.verifier = OutputVerifier()

        self.total_cost = 0.0
        self.total_latency = 0.0

    def classify_task(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        complex_keywords = [
            "explain",
            "analyze",
            "compare",
            "write code",
            "json",
            "debug",
            "architecture",
        ]

        if any(keyword in prompt_lower for keyword in complex_keywords):
            return "complex"

        return "simple"

    def ask(self, prompt: str) -> str:
        cached = self.cache.get(prompt)

        if cached:
            return f"[cache:{cached.model_name}] {cached.answer}"

        task_type = self.classify_task(prompt)

        if task_type == "simple":
            response = self.cheap_model.call(prompt)
        else:
            # Try cheap model first for cost saving, then verify.
            response = self.cheap_model.call(prompt)

            if self.verifier.is_silent_failure(prompt, response):
                print("Cheap model failed verification. Routing to quality model.")
                response = self.quality_model.call(prompt)

        # Verify even simple cheap-model answers.
        if self.verifier.is_silent_failure(prompt, response):
            print("Response failed verification. Escalating to quality model.")
            response = self.quality_model.call(prompt)

        self.total_cost += response.cost
        self.total_latency += response.latency_seconds

        self.cache.set(prompt, response.answer, response.model_name)

        return f"[{response.model_name}] {response.answer}"

    def batch_ask(self, prompts: List[str]) -> List[str]:
        """
        Simple batching.
        In real systems, this could send many prompts in one API request
        if the provider supports batching.
        """
        results = []

        for prompt in prompts:
            results.append(self.ask(prompt))

        return results

    def print_stats(self) -> None:
        print("\nRouter stats:")
        print("Total cost:", round(self.total_cost, 4))
        print("Total latency:", round(self.total_latency, 3), "seconds")


if __name__ == "__main__":
    router = ModelRouter()

    prompts = [
        "What is 2 + 2?",
        "Explain transformer attention",
        "Return JSON with status ok",
        "Explain transformer attention",  # cache hit
        "Hello",
    ]

    results = router.batch_ask(prompts)

    for prompt, result in zip(prompts, results):
        print("\nPrompt:", prompt)
        print("Answer:", result)

    router.print_stats()