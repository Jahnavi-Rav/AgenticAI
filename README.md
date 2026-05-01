# AgenticAI

A hands-on learning repository for understanding and building **Agentic AI systems** from fundamentals to production-style architectures.

This repo contains small, focused Python projects that explain how agents work: planning, tools, memory, RAG, multi-agent systems, safety, evaluation, deployment, monitoring, and more.

---

## What is Agentic AI?

Agentic AI refers to AI systems that can do more than respond once. An agent can:

- Understand a goal
- Plan steps
- Use tools
- Maintain state or memory
- Take actions
- Observe feedback
- Recover from failures
- Improve over time

A simple agent loop looks like:

```text
Goal → Perception → Reasoning → Action → Feedback → Repeat
```

---

## Repository Structure

```text
AgenticAI/
├── Foundations/
├── BuildingBasicAgents/
├── ReadingPlanningExecution/
├── RetrievalPlanningData/
├── MultiAgentArch/
├── AdvancedAgents/
├── requirements.txt
└── README.md
```

---

## Topics Covered

### Foundations

Core concepts behind AI agents:

- AI, ML, Deep Learning, and LLM basics
- Tokens, embeddings, transformers, prompts
- Attention mechanism
- LLM APIs and local models
- Python basics for Agentic AI
- CLI assistants
- Prompt engineering
- Structured outputs
- State management

### Building Basic Agents

Agent fundamentals:

- Anatomy of an agent
- Minimal agent loops
- Tool calling
- Human-in-the-loop approval
- Self-reflection and self-correction
- Reliability patterns
- Safety policy layers

### Reading, Planning, and Execution

Planning and execution systems:

- Task decomposition
- Planner agents
- Sequential and parallel execution
- Retry-based task executors
- Long-horizon task runners
- Graph-based workflows
- Hierarchical agents

### Retrieval, Planning, and Data

Knowledge and retrieval systems:

- Embeddings and vector search
- RAG pipelines
- PDF/document search
- Advanced RAG
- Knowledge graphs
- SQL agents
- Spreadsheet and analytics agents
- Persistence and databases

### Multi-Agent Architectures

Multi-agent collaboration patterns:

- Supervisor-worker systems
- Message buses
- Agent communication
- Debate-based agents
- Software engineering agent teams
- Research agents
- Browser/UI agents
- DevOps agents

### Advanced Agents

Advanced agent design topics:

- Synthetic data generation
- Simulation environments
- Autonomous tool creation
- Meta-agents
- Self-improving agents
- Production monitoring
- Deployment with Docker
- Scaling with queues and workers

---

## Key Agent Concepts Implemented

This repo demonstrates:

```text
Agents vs chatbots
Planning
Tool use
Memory
State tracking
RAG
Vector search
Knowledge graphs
SQL agents
Multi-agent systems
Human approval
Safety policies
Prompt injection defense
Tool security
Retries and fallbacks
Observability
Evaluation
Deployment
Monitoring
```

---

## Edge Cases Covered

Each module includes real-world failure cases, such as:

```text
Infinite loops
Repeated actions
Vague goals
Unsafe tool calls
Wrong arguments
Invalid JSON
Schema drift
Corrupted state
Stale state
False memories
Privacy leaks
Irrelevant recall
Tool hallucination
Reasoning loops
Overplanning
Underplanning
Impossible goals
Race conditions
Duplicate jobs
Prompt injection
Command injection
Leaked API keys
Queue overload
Partial failure
Hidden degradation
Goal drift
Context loss
Dead graph nodes
Invalid transitions
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/Jahnavi-Rav/AgenticAI.git
cd AgenticAI
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` does not exist yet, generate it from your current environment:

```bash
python3 -m pip freeze > requirements.txt
```

---

## Local LLM Setup with Ollama

Some examples use a local LLM through Ollama.

### Install Ollama

```bash
brew install ollama
```

### Pull a model

```bash
ollama pull llama3.2:1b
```

or:

```bash
ollama pull llama3
```

### Start Ollama

```bash
ollama serve
```

Then run Python examples that call:

```text
http://localhost:11434/api/generate
```

---

## Example Commands

Run a basic agent:

```bash
python3 Foundations/RuleBasedAgent.py
```

Run a CLI assistant:

```bash
python3 Foundations/cli_assistant.py
```

Run a tool-calling agent:

```bash
python3 BuildingBasicAgents/tool_calling_agent.py
```

Run a RAG pipeline:

```bash
python3 RetrievalPlanningData/rag_pipeline.py
```

Run a multi-agent manager:

```bash
python3 MultiAgentArch/SW.py
```

Run advanced modules:

```bash
python3 AdvancedAgents/synthetic_data_generator.py
python3 AdvancedAgents/simulation_environment.py
python3 AdvancedAgents/autonomous_tool_creation.py
python3 AdvancedAgents/meta_agent_builder.py
```

---

## Example: Agent Loop

A minimal agent loop generally follows this structure:

```python
while not done:
    observation = perceive()
    action = reason(observation)
    result = act(action)
    update_state(result)
```

This repo expands that idea into:

- tool-using agents
- planner agents
- multi-agent systems
- graph-based workflows
- production-style backend services

---

## Safety Principles

This repo emphasizes safe agent behavior:

```text
Agents propose actions.
Policy layers approve or reject actions.
Executors only run approved actions.
High-risk actions require human approval.
Tool calls must be validated.
Secrets must never be logged or exposed.
```

Examples include:

- prompt injection detection
- command injection blocking
- API key redaction
- approval-based actions
- tool allowlists
- unsafe action prevention

---

## Production Patterns

Several modules introduce production-style design:

```text
FastAPI backend services
Async queues
Worker pools
Retries
Fallbacks
Circuit breakers
Health checks
Docker deployment
Monitoring loops
Observability dashboards
Evaluation benchmarks
```

These are simplified learning examples, but they map to real production systems.

---

## Recommended Learning Path

A suggested order:

```text
1. Foundations
2. Python for Agentic AI
3. Prompt Engineering
4. Tool Calling
5. Agent State
6. Memory Systems
7. Planning and Execution
8. RAG and Vector Search
9. Multi-Agent Architectures
10. Safety and Security
11. Evaluation
12. Deployment and Monitoring
13. Advanced Agents
```

---

## Notes

This repository is for learning and experimentation.

Some examples intentionally include flawed behavior first, such as:

- broken code
- unsafe tool calls
- weak tests
- bad manager decisions
- fake model failures

Those failures are included so the agent can detect, reject, repair, or safely stop.

---

## Git Workflow

Typical workflow:

```bash
git status
git add .
git commit -m "Update agent module"
git push origin main
```

Make sure you run Git commands from the main repo root:

```text
/Users/jenny/Desktop/LearningPhase/AgenticAI
```

---

## Author

Created by **Jahnavi Rav** as part of a hands-on Agentic AI learning journey.

GitHub: [Jahnavi-Rav](https://github.com/Jahnavi-Rav)

---

## License

This project is for educational use.