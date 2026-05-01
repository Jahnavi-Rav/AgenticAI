import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


MAX_RETRIES = 3
BASE_DELAY = 0.5
MAX_DELAY = 5.0
FAILURE_THRESHOLD = 3
CIRCUIT_RESET_TIMEOUT = 5.0


class CircuitState(Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # block calls
    HALF_OPEN = "half_open" # test if service recovered


@dataclass
class ServiceResult:
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_timeout: float):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[float] = None

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                return False

            time_since_failure = time.time() - self.last_failure_time

            if time_since_failure >= self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                return True

            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class MockPrimaryService:
    """
    Simulates an unreliable primary service.
    """

    def call(self, prompt: str) -> ServiceResult:
        if random.random() < 0.75:
            return ServiceResult(
                success=False,
                error="Primary service temporary failure."
            )

        return ServiceResult(
            success=True,
            data=f"Primary response for: {prompt}"
        )


class MockFallbackService:
    """
    Simulates a more reliable but simpler fallback service.
    """

    def call(self, prompt: str) -> ServiceResult:
        if random.random() < 0.15:
            return ServiceResult(
                success=False,
                error="Fallback service also failed."
            )

        return ServiceResult(
            success=True,
            data=f"Fallback response for: {prompt}"
        )


class ReliabilityLayer:
    def __init__(self):
        self.primary = MockPrimaryService()
        self.fallback = MockFallbackService()

        self.primary_circuit = CircuitBreaker(
            failure_threshold=FAILURE_THRESHOLD,
            reset_timeout=CIRCUIT_RESET_TIMEOUT,
        )

        self.fallback_circuit = CircuitBreaker(
            failure_threshold=FAILURE_THRESHOLD,
            reset_timeout=CIRCUIT_RESET_TIMEOUT,
        )

    def backoff_delay(self, attempt: int) -> float:
        exponential = BASE_DELAY * (2 ** (attempt - 1))
        capped = min(exponential, MAX_DELAY)

        # Jitter prevents many agents from retrying at the exact same time.
        jitter = random.uniform(0, 0.3)

        return capped + jitter

    def call_with_retries(
        self,
        service_name: str,
        service_call: Callable[[str], ServiceResult],
        circuit: CircuitBreaker,
        prompt: str,
    ) -> ServiceResult:
        if not circuit.allow_request():
            return ServiceResult(
                success=False,
                error=f"{service_name} circuit is OPEN. Skipping call."
            )

        for attempt in range(1, MAX_RETRIES + 1):
            print(f"{service_name} attempt {attempt}")

            result = service_call(prompt)

            if result.success:
                circuit.record_success()
                return result

            print(f"{service_name} failed:", result.error)

            circuit.record_failure()

            if circuit.state == CircuitState.OPEN:
                return ServiceResult(
                    success=False,
                    error=f"{service_name} circuit opened after repeated failures."
                )

            delay = self.backoff_delay(attempt)
            print(f"Waiting {round(delay, 2)} seconds before retry...")
            time.sleep(delay)

        return ServiceResult(
            success=False,
            error=f"{service_name} failed after retries."
        )

    def ask(self, prompt: str) -> ServiceResult:
        print("\nTrying primary service...")

        primary_result = self.call_with_retries(
            service_name="Primary",
            service_call=self.primary.call,
            circuit=self.primary_circuit,
            prompt=prompt,
        )

        if primary_result.success:
            return primary_result

        print("Primary unavailable:", primary_result.error)

        print("\nTrying fallback service...")

        fallback_result = self.call_with_retries(
            service_name="Fallback",
            service_call=self.fallback.call,
            circuit=self.fallback_circuit,
            prompt=prompt,
        )

        if fallback_result.success:
            return fallback_result

        print("Fallback unavailable:", fallback_result.error)

        return ServiceResult(
            success=False,
            error="All services failed safely. No cascading failure triggered."
        )


if __name__ == "__main__":
    reliability = ReliabilityLayer()

    prompts = [
        "Explain retries",
        "Explain fallbacks",
        "Explain circuit breakers",
        "Explain cascading failures",
        "Explain retry storms",
    ]

    for prompt in prompts:
        print("\n==============================")
        print("Prompt:", prompt)

        result = reliability.ask(prompt)

        print("\nFinal result:")
        print("Success:", result.success)
        print("Data:", result.data)
        print("Error:", result.error)

        print("\nCircuit states:")
        print("Primary:", reliability.primary_circuit.state.value)
        print("Fallback:", reliability.fallback_circuit.state.value)