from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import uuid
import random


MAX_DELEGATION_DEPTH = 4
MAX_RETRIES = 2


@dataclass
class Message:
    sender: str
    receiver: str
    role: str
    content: str
    task_id: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace: List[str] = field(default_factory=list)
    retries: int = 0


class MessageBus:
    def __init__(self, simulate_loss: bool = True):
        self.queues: Dict[str, List[Message]] = {}
        self.delivered_messages: Set[str] = set()
        self.simulate_loss = simulate_loss

    def register_agent(self, agent_name: str) -> None:
        if agent_name not in self.queues:
            self.queues[agent_name] = []

    def send(self, message: Message) -> bool:
        if message.receiver not in self.queues:
            print(f"Message failed: unknown receiver '{message.receiver}'")
            return False

        if message.message_id in self.delivered_messages:
            print(f"Duplicate message ignored: {message.message_id}")
            return False

        # Simulate message loss
        if self.simulate_loss and random.random() < 0.15:
            print(f"Message lost: {message.sender} -> {message.receiver}")
            return False

        self.queues[message.receiver].append(message)
        self.delivered_messages.add(message.message_id)

        print(f"Message sent: {message.sender} -> {message.receiver}")
        return True

    def receive(self, agent_name: str) -> Optional[Message]:
        queue = self.queues.get(agent_name, [])

        if not queue:
            return None

        return queue.pop(0)


class Agent:
    def __init__(self, name: str, role: str, bus: MessageBus):
        self.name = name
        self.role = role
        self.bus = bus
        self.bus.register_agent(name)

    def send_with_retry(self, message: Message) -> None:
        for attempt in range(MAX_RETRIES + 1):
            success = self.bus.send(message)

            if success:
                return

            message.retries += 1
            print(f"Retrying message {message.message_id}, attempt {attempt + 1}")

        print(f"Message permanently failed: {message.message_id}")

    def detect_circular_delegation(self, message: Message) -> bool:
        return self.name in message.trace

    def handle_message(self, message: Message) -> None:
        raise NotImplementedError


class ManagerAgent(Agent):
    def handle_message(self, message: Message) -> None:
        print(f"\n{self.name} received:", message.content)

        if self.detect_circular_delegation(message):
            print("Stopped: circular delegation detected.")
            return

        if len(message.trace) >= MAX_DELEGATION_DEPTH:
            print("Stopped: max delegation depth reached.")
            return

        if "research" in message.content.lower():
            receiver = "ResearchAgent"
        elif "code" in message.content.lower():
            receiver = "CodeAgent"
        else:
            print("Manager final result:", message.content)
            return

        new_message = Message(
            sender=self.name,
            receiver=receiver,
            role="task",
            content=message.content,
            task_id=message.task_id,
            trace=message.trace + [self.name],
        )

        self.send_with_retry(new_message)


class ResearchAgent(Agent):
    def handle_message(self, message: Message) -> None:
        print(f"\n{self.name} received:", message.content)

        if self.detect_circular_delegation(message):
            print("Stopped: circular delegation detected.")
            return

        result = "Research complete: agents use communication protocols and handoffs."

        handoff = Message(
            sender=self.name,
            receiver="CodeAgent",
            role="handoff",
            content=f"{result} Now write code.",
            task_id=message.task_id,
            trace=message.trace + [self.name],
        )

        self.send_with_retry(handoff)


class CodeAgent(Agent):
    def handle_message(self, message: Message) -> None:
        print(f"\n{self.name} received:", message.content)

        if self.detect_circular_delegation(message):
            print("Stopped: circular delegation detected.")
            return

        result = "Code complete: created a message bus implementation."

        reply = Message(
            sender=self.name,
            receiver="ManagerAgent",
            role="result",
            content=result,
            task_id=message.task_id,
            trace=message.trace + [self.name],
        )

        self.send_with_retry(reply)


def run_system() -> None:
    bus = MessageBus(simulate_loss=True)

    manager = ManagerAgent("ManagerAgent", "manager", bus)
    researcher = ResearchAgent("ResearchAgent", "researcher", bus)
    coder = CodeAgent("CodeAgent", "coder", bus)

    agents = {
        "ManagerAgent": manager,
        "ResearchAgent": researcher,
        "CodeAgent": coder,
    }

    initial_message = Message(
        sender="User",
        receiver="ManagerAgent",
        role="task",
        content="Research agent communication and write code",
        task_id="task_001",
    )

    bus.send(initial_message)

    for _ in range(10):
        progress_made = False

        for agent_name, agent in agents.items():
            message = bus.receive(agent_name)

            if message:
                progress_made = True
                agent.handle_message(message)

        if not progress_made:
            break


if __name__ == "__main__":
    run_system()