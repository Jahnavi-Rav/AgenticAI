import random
from typing import List


class GridWorld:
    def __init__(self, size: int = 5, slip_probability: float = 0.0):
        self.size = size
        self.slip_probability = slip_probability
        self.agent_pos = [0, 0]
        self.goal_pos = [size - 1, size - 1]

    def reset(self) -> None:
        self.agent_pos = [0, 0]

    def step(self, action: str) -> bool:
        if random.random() < self.slip_probability:
            action = random.choice(["up", "down", "left", "right"])

        if action == "up":
            self.agent_pos[0] = max(0, self.agent_pos[0] - 1)

        elif action == "down":
            self.agent_pos[0] = min(self.size - 1, self.agent_pos[0] + 1)

        elif action == "left":
            self.agent_pos[1] = max(0, self.agent_pos[1] - 1)

        elif action == "right":
            self.agent_pos[1] = min(self.size - 1, self.agent_pos[1] + 1)

        return self.agent_pos == self.goal_pos


class NavigationAgent:
    def choose_action(self, position: List[int], goal: List[int]) -> str:
        if position[0] < goal[0]:
            return "down"

        if position[1] < goal[1]:
            return "right"

        return "stay"


class SimulationTester:
    def run_episode(self, env: GridWorld, max_steps: int = 20) -> bool:
        agent = NavigationAgent()
        env.reset()

        for _ in range(max_steps):
            action = agent.choose_action(env.agent_pos, env.goal_pos)
            reached_goal = env.step(action)

            if reached_goal:
                return True

        return False

    def evaluate(self, env: GridWorld, episodes: int = 20) -> float:
        successes = 0

        for _ in range(episodes):
            if self.run_episode(env):
                successes += 1

        return successes / episodes

    def compare_sim_to_real(self) -> None:
        ideal_sim = GridWorld(slip_probability=0.0)
        noisy_real_like_sim = GridWorld(slip_probability=0.3)

        ideal_score = self.evaluate(ideal_sim)
        noisy_score = self.evaluate(noisy_real_like_sim)

        print("Ideal simulation success:", ideal_score)
        print("Noisy real-like success:", noisy_score)

        if ideal_score - noisy_score > 0.25:
            print("Warning: sim-to-real mismatch detected.")
        else:
            print("No major sim-to-real mismatch detected.")


if __name__ == "__main__":
    tester = SimulationTester()
    tester.compare_sim_to_real()