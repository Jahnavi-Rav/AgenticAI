class RuleBasedAgent:
    def __init__(self, max_steps=5):
        self.max_steps = max_steps
        self.unsafe_keywords = ["delete", "buy", "purchase", "send", "transfer", "password"]
        self.vague_goals = ["help me", "do something", "make it better", "fix it", "plan it"]

    def is_vague_goal(self, goal):
        return len(goal.strip()) < 10 or goal.lower() in self.vague_goals

    def is_unsafe_action(self, action):
        return any(word in action.lower() for word in self.unsafe_keywords)

    def plan(self, goal):
        if "email" in goal.lower():
            return ["draft email", "ask user before sending"]
        elif "file" in goal.lower():
            return ["read file", "summarize file"]
        elif "buy" in goal.lower():
            return ["search options", "ask user before purchase"]
        else:
            return ["ask user for clarification"]

    def run(self, goal):
        if self.is_vague_goal(goal):
            return "Goal is too vague. Please give a clearer goal."

        steps = self.plan(goal)

        for step_number, action in enumerate(steps, start=1):
            if step_number > self.max_steps:
                return "Stopped: agent reached max step limit."

            if self.is_unsafe_action(action):
                return f"Stopped: unsafe action detected → {action}"

            print(f"Step {step_number}: {action}")

        return "Agent finished safely."


agent = RuleBasedAgent()

print(agent.run("Summarize this file"))
print(agent.run("Buy a laptop"))
print(agent.run("fix it"))