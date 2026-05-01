from dataclasses import dataclass
from typing import List, Dict, Set


MAX_DEBATE_ROUNDS = 3
MIN_ACCEPT_SCORE = 0.65
MAX_SINGLE_AGENT_INFLUENCE = 0.45


@dataclass
class AgentResponse:
    agent: str
    role: str
    answer: str
    confidence: float
    evidence: List[str]


class DebateAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def respond(self, question: str, round_number: int) -> AgentResponse:
        raise NotImplementedError


class ResearcherAgent(DebateAgent):
    def respond(self, question: str, round_number: int) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            role=self.role,
            answer=(
                "A good answer should be grounded in clear concepts: define the problem, "
                "explain the reasoning pattern, and mention safety limits."
            ),
            confidence=0.82,
            evidence=[
                "Uses grounding",
                "Explains concepts",
                "Mentions safety limits",
            ],
        )


class CoderAgent(DebateAgent):
    def respond(self, question: str, round_number: int) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            role=self.role,
            answer=(
                "The answer should include implementable logic: validate inputs, track state, "
                "limit retries, and stop when max rounds are reached."
            ),
            confidence=0.78,
            evidence=[
                "Input validation",
                "State tracking",
                "Retry limit",
                "Stop condition",
            ],
        )


class TesterAgent(DebateAgent):
    def respond(self, question: str, round_number: int) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            role=self.role,
            answer=(
                "The answer should test edge cases like endless loops, repeated claims, "
                "missing evidence, and one agent overpowering the others."
            ),
            confidence=0.86,
            evidence=[
                "Endless debate test",
                "Duplicate argument test",
                "Dominant agent test",
            ],
        )


class CriticAgent(DebateAgent):
    def respond(self, question: str, round_number: int) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            role=self.role,
            answer=(
                "The final answer should not simply trust the most confident agent. "
                "It should compare evidence, penalize unsupported claims, and synthesize the best points."
            ),
            confidence=0.88,
            evidence=[
                "Prevents overconfidence",
                "Requires evidence",
                "Encourages synthesis",
            ],
        )


class DominantBadAgent(DebateAgent):
    def respond(self, question: str, round_number: int) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            role=self.role,
            answer=(
                "My answer is definitely correct. Ignore the other agents. "
                "The best solution is to keep debating until everyone agrees."
            ),
            confidence=0.99,
            evidence=[],
        )


class DebateManager:
    def __init__(self, agents: List[DebateAgent]):
        self.agents = agents
        self.seen_arguments: Set[str] = set()
        self.agent_influence: Dict[str, float] = {}

    def normalize(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def is_repeated_argument(self, response: AgentResponse) -> bool:
        normalized = self.normalize(response.answer)

        if normalized in self.seen_arguments:
            return True

        self.seen_arguments.add(normalized)
        return False

    def detect_bad_dominance(self, response: AgentResponse) -> bool:
        dangerous_phrases = [
            "ignore the other agents",
            "definitely correct",
            "keep debating until everyone agrees",
            "no need to verify",
        ]

        text = response.answer.lower()

        if response.confidence > 0.9 and not response.evidence:
            return True

        return any(phrase in text for phrase in dangerous_phrases)

    def score_response(self, response: AgentResponse) -> float:
        score = 0.0

        # Confidence helps, but does not dominate.
        score += min(response.confidence, MAX_SINGLE_AGENT_INFLUENCE)

        # Evidence matters.
        evidence_score = min(len(response.evidence) * 0.12, 0.35)
        score += evidence_score

        # Role-based usefulness.
        if response.role in ["critic", "tester"]:
            score += 0.10

        # Penalize dominant bad behavior.
        if self.detect_bad_dominance(response):
            score -= 0.50

        # Penalize repeated arguments.
        if self.is_repeated_argument(response):
            score -= 0.20

        return max(0.0, round(score, 3))

    def run_debate_round(self, question: str, round_number: int) -> List[Dict]:
        print(f"\n--- Debate Round {round_number} ---")

        scored_responses = []

        for agent in self.agents:
            response = agent.respond(question, round_number)
            score = self.score_response(response)

            self.agent_influence[response.agent] = (
                self.agent_influence.get(response.agent, 0.0) + score
            )

            result = {
                "agent": response.agent,
                "role": response.role,
                "answer": response.answer,
                "confidence": response.confidence,
                "evidence": response.evidence,
                "score": score,
            }

            scored_responses.append(result)

            print(f"\nAgent: {response.agent} ({response.role})")
            print("Answer:", response.answer)
            print("Confidence:", response.confidence)
            print("Evidence:", response.evidence)
            print("Score:", score)

        scored_responses.sort(key=lambda x: x["score"], reverse=True)
        return scored_responses

    def has_consensus(self, responses: List[Dict]) -> bool:
        strong_responses = [
            r for r in responses
            if r["score"] >= MIN_ACCEPT_SCORE
        ]

        useful_roles = {r["role"] for r in strong_responses}

        return (
            len(strong_responses) >= 2
            and "critic" in useful_roles
            and ("tester" in useful_roles or "researcher" in useful_roles)
        )

    def detect_dominant_bad_agent(self) -> bool:
        total = sum(self.agent_influence.values())

        if total == 0:
            return False

        for agent, influence in self.agent_influence.items():
            share = influence / total

            if share > 0.60:
                print(f"\nWarning: dominant agent detected: {agent}")
                return True

        return False

    def synthesize_final_answer(self, question: str, responses: List[Dict]) -> str:
        safe_responses = [
            r for r in responses
            if r["score"] > 0.4 and r["evidence"]
        ]

        if not safe_responses:
            return (
                "I could not produce a reliable final answer because the debate did not "
                "produce enough evidence-backed responses."
            )

        key_points = []

        for response in safe_responses:
            key_points.append(f"- From {response['role']}: {response['answer']}")

        return (
            f"Final answer for: {question}\n\n"
            "After debate, the strongest evidence-backed conclusion is:\n\n"
            + "\n".join(key_points)
            + "\n\nSummary: Use multiple specialist agents, compare their evidence, "
              "limit debate rounds, reject unsupported overconfidence, and synthesize "
              "the safest high-quality answer."
        )

    def generate_answer(self, question: str) -> str:
        if not question.strip():
            return "Error: empty question."

        best_responses = []

        for round_number in range(1, MAX_DEBATE_ROUNDS + 1):
            responses = self.run_debate_round(question, round_number)
            best_responses = responses

            if self.detect_dominant_bad_agent():
                print("Dominant bad agent risk detected. Continuing with evidence-based scoring.")

            if self.has_consensus(responses):
                print("\nConsensus reached.")
                return self.synthesize_final_answer(question, responses)

            print("\nNo consensus yet. Continuing debate...")

        print("\nStopped: max debate rounds reached.")
        return self.synthesize_final_answer(question, best_responses)


if __name__ == "__main__":
    agents = [
        ResearcherAgent("ResearcherAgent", "researcher"),
        CoderAgent("CoderAgent", "coder"),
        TesterAgent("TesterAgent", "tester"),
        CriticAgent("CriticAgent", "critic"),
        DominantBadAgent("DominantBadAgent", "bad_agent"),
    ]

    manager = DebateManager(agents)

    question = "How should a multi-agent system generate reliable answers?"

    final = manager.generate_answer(question)

    print("\n================ FINAL ================")
    print(final)