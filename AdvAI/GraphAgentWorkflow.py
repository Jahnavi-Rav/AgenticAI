from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set


START = "START"
END = "END"


@dataclass
class AgentState:
    goal: str
    plan: List[str] = field(default_factory=list)
    result: Optional[str] = None
    valid: bool = False
    errors: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)


@dataclass
class NodeResult:
    next_node: str
    state: AgentState


NodeFunction = Callable[[AgentState], NodeResult]


class GraphValidationError(Exception):
    pass


class GraphWorkflow:
    def __init__(self):
        self.nodes: Dict[str, NodeFunction] = {}
        self.edges: Dict[str, Set[str]] = {}

    def add_node(self, name: str, fn: NodeFunction) -> None:
        self.nodes[name] = fn

        if name not in self.edges:
            self.edges[name] = set()

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self.nodes:
            raise GraphValidationError(f"Unknown from_node: {from_node}")

        if to_node not in self.nodes:
            raise GraphValidationError(f"Unknown to_node: {to_node}")

        self.edges[from_node].add(to_node)

    def validate_graph(self) -> None:
        if START not in self.nodes:
            raise GraphValidationError("Missing START node.")

        if END not in self.nodes:
            raise GraphValidationError("Missing END node.")

        self.detect_dead_nodes()
        self.detect_terminal_problems()

    def reachable_nodes(self) -> Set[str]:
        visited = set()

        def dfs(node: str):
            if node in visited:
                return

            visited.add(node)

            for neighbor in self.edges.get(node, set()):
                dfs(neighbor)

        dfs(START)
        return visited

    def detect_dead_nodes(self) -> None:
        reachable = self.reachable_nodes()
        all_nodes = set(self.nodes.keys())

        dead_nodes = all_nodes - reachable

        if dead_nodes:
            raise GraphValidationError(
                f"Dead nodes detected: {sorted(dead_nodes)}"
            )

    def detect_terminal_problems(self) -> None:
        for node in self.nodes:
            if node == END:
                continue

            if not self.edges.get(node):
                raise GraphValidationError(
                    f"Node '{node}' has no outgoing edge and cannot reach END."
                )

    def run(self, initial_state: AgentState, max_steps: int = 10) -> AgentState:
        self.validate_graph()

        current_node = START
        state = initial_state

        for step in range(1, max_steps + 1):
            state.history.append(f"Step {step}: entered {current_node}")

            if current_node == END:
                state.history.append("Workflow completed.")
                return state

            node_fn = self.nodes[current_node]
            result = node_fn(state)

            next_node = result.next_node
            state = result.state

            allowed_next_nodes = self.edges.get(current_node, set())

            if next_node not in allowed_next_nodes:
                state.errors.append(
                    f"Invalid transition: {current_node} -> {next_node}"
                )
                state.history.append("Workflow stopped due to invalid transition.")
                return state

            current_node = next_node

        state.errors.append("Workflow stopped: max steps reached.")
        return state


# -------------------------
# Node functions
# -------------------------

def start_node(state: AgentState) -> NodeResult:
    if not state.goal.strip():
        state.errors.append("Goal is empty.")
        return NodeResult(next_node="error", state=state)

    return NodeResult(next_node="plan", state=state)


def plan_node(state: AgentState) -> NodeResult:
    goal_lower = state.goal.lower()

    if "bad transition" in goal_lower:
        # Intentional invalid transition edge case.
        return NodeResult(next_node="nonexistent_node", state=state)

    if "code" in goal_lower or "python" in goal_lower:
        state.plan = [
            "Understand requirements",
            "Write Python code",
            "Validate code",
        ]

    elif "research" in goal_lower:
        state.plan = [
            "Collect sources",
            "Summarize findings",
            "Compare evidence",
        ]

    else:
        state.plan = [
            "Understand goal",
            "Execute task",
            "Review result",
        ]

    return NodeResult(next_node="execute", state=state)


def execute_node(state: AgentState) -> NodeResult:
    if not state.plan:
        state.errors.append("No plan available.")
        return NodeResult(next_node="error", state=state)

    state.result = "Executed plan: " + " → ".join(state.plan)

    return NodeResult(next_node="validate", state=state)


def validate_node(state: AgentState) -> NodeResult:
    if not state.result:
        state.errors.append("No result to validate.")
        return NodeResult(next_node="error", state=state)

    if "unsafe" in state.goal.lower():
        state.errors.append("Unsafe goal detected during validation.")
        return NodeResult(next_node="error", state=state)

    state.valid = True

    return NodeResult(next_node=END, state=state)


def error_node(state: AgentState) -> NodeResult:
    state.history.append("Error handler reached.")
    return NodeResult(next_node=END, state=state)


def end_node(state: AgentState) -> NodeResult:
    return NodeResult(next_node=END, state=state)


# -------------------------
# Build workflows
# -------------------------

def build_valid_workflow() -> GraphWorkflow:
    workflow = GraphWorkflow()

    workflow.add_node(START, start_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("error", error_node)
    workflow.add_node(END, end_node)

    workflow.add_edge(START, "plan")
    workflow.add_edge(START, "error")
    workflow.add_edge("plan", "execute")
    workflow.add_edge("execute", "validate")
    workflow.add_edge("execute", "error")
    workflow.add_edge("validate", END)
    workflow.add_edge("validate", "error")
    workflow.add_edge("error", END)

    return workflow


def build_workflow_with_dead_node() -> GraphWorkflow:
    workflow = build_valid_workflow()

    def unused_node(state: AgentState) -> NodeResult:
        state.history.append("This should never run.")
        return NodeResult(next_node=END, state=state)

    workflow.add_node("dead_node", unused_node)

    # No edge points to dead_node.
    # This should fail validation.

    return workflow


# -------------------------
# Demo
# -------------------------

if __name__ == "__main__":
    print("\n=== Valid workflow ===")
    workflow = build_valid_workflow()

    state = AgentState(goal="Build Python code for a calculator")
    final_state = workflow.run(state)

    print("Goal:", final_state.goal)
    print("Valid:", final_state.valid)
    print("Result:", final_state.result)
    print("Errors:", final_state.errors)
    print("History:")
    for item in final_state.history:
        print("-", item)

    print("\n=== Invalid transition demo ===")
    workflow = build_valid_workflow()

    state = AgentState(goal="bad transition example")
    final_state = workflow.run(state)

    print("Valid:", final_state.valid)
    print("Errors:", final_state.errors)
    print("History:")
    for item in final_state.history:
        print("-", item)

    print("\n=== Dead node demo ===")
    try:
        broken_workflow = build_workflow_with_dead_node()
        broken_workflow.run(AgentState(goal="Research AI agents"))
    except GraphValidationError as e:
        print("Graph validation failed:", e)