from dataclasses import dataclass
from typing import List


@dataclass
class AgentDesign:
    agents: List[str]
    tools: List[str]
    memory: bool
    reason: str
    warnings: List[str]


class MetaAgentBuilder:
    MAX_AGENTS = 4
    MAX_TOOLS = 5

    def build_agent_system(self, requirement: str) -> AgentDesign:
        req = requirement.lower()

        agents = ["ManagerAgent"]
        tools = []
        memory = False
        warnings = []

        if "code" in req:
            agents.extend(["CoderAgent", "TesterAgent"])
            tools.extend(["file_writer", "test_runner"])

        if "research" in req:
            agents.append("ResearchAgent")
            tools.extend(["search_tool", "summarizer"])

        if "memory" in req or "long-term" in req:
            memory = True
            tools.append("vector_memory")

        if "everything" in req or "all features" in req:
            warnings.append("Overcomplication risk: requirement is too broad.")

        if len(agents) > self.MAX_AGENTS:
            warnings.append("Too many agents. Simplifying architecture.")
            agents = agents[:self.MAX_AGENTS]

        if len(tools) > self.MAX_TOOLS:
            warnings.append("Too many tools. Simplifying toolset.")
            tools = tools[:self.MAX_TOOLS]

        return AgentDesign(
            agents=agents,
            tools=tools,
            memory=memory,
            reason="Designed the smallest useful agent architecture.",
            warnings=warnings,
        )


if __name__ == "__main__":
    builder = MetaAgentBuilder()

    requirements = [
        "Build a coding agent with tests",
        "Build a research agent with memory",
        "Build everything with all features",
    ]

    for requirement in requirements:
        design = builder.build_agent_system(requirement)

        print("\nRequirement:", requirement)
        print("Agents:", design.agents)
        print("Tools:", design.tools)
        print("Memory:", design.memory)
        print("Reason:", design.reason)

        if design.warnings:
            print("Warnings:")
            for warning in design.warnings:
                print("-", warning)