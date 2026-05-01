import html
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


DASHBOARD_FILE = "agent_dashboard.html"


# ----------------------------
# Privacy-safe redaction
# ----------------------------

class PrivacyRedactor:
    SECRET_PATTERNS = [
        r"sk-[A-Za-z0-9]{10,}",
        r"hf_[A-Za-z0-9]{10,}",
        r"api[_-]?key\s*[:=]\s*\S+",
        r"password\s*[:=]\s*\S+",
        r"token\s*[:=]\s*\S+",
        r"secret\s*[:=]\s*\S+",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    def redact(self, text: str) -> str:
        safe = text

        for pattern in self.SECRET_PATTERNS:
            safe = re.sub(
                pattern,
                "[REDACTED]",
                safe,
                flags=re.IGNORECASE,
            )

        return safe


# ----------------------------
# Data models
# ----------------------------

@dataclass
class LogRecord:
    timestamp: float
    level: str
    message: str
    trace_id: str
    span_id: Optional[str] = None


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None

        return round((self.end_time - self.start_time) * 1000, 2)


@dataclass
class Metric:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


# ----------------------------
# Observability store
# ----------------------------

class ObservabilityStore:
    def __init__(self):
        self.logs: List[LogRecord] = []
        self.spans: List[Span] = []
        self.metrics: List[Metric] = []
        self.redactor = PrivacyRedactor()

    def log(
        self,
        level: str,
        message: str,
        trace_id: str,
        span_id: Optional[str] = None,
    ) -> None:
        safe_message = self.redactor.redact(message)

        self.logs.append(
            LogRecord(
                timestamp=time.time(),
                level=level,
                message=safe_message,
                trace_id=trace_id,
                span_id=span_id,
            )
        )

    def start_span(
        self,
        trace_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        span = Span(
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            name=name,
            start_time=time.time(),
            metadata=metadata or {},
        )

        self.spans.append(span)
        return span

    def end_span(self, span: Span, status: str = "ok") -> None:
        span.end_time = time.time()
        span.status = status

    def metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        self.metrics.append(
            Metric(
                name=name,
                value=value,
                labels=labels or {},
            )
        )

    def find_logs_for_span(self, span: Span) -> List[LogRecord]:
        return [
            log for log in self.logs
            if log.trace_id == span.trace_id and log.span_id == span.span_id
        ]

    def detect_missing_logs(self) -> List[str]:
        warnings = []

        for span in self.spans:
            related_logs = self.find_logs_for_span(span)

            if not related_logs:
                warnings.append(
                    f"Missing logs for span '{span.name}' ({span.span_id})"
                )

        return warnings


# ----------------------------
# Example agent with tracing
# ----------------------------

class TracedAgent:
    def __init__(self, store: ObservabilityStore):
        self.store = store

    def run(self, user_input: str) -> str:
        trace_id = str(uuid.uuid4())

        self.store.log(
            level="INFO",
            message=f"Agent request started. User input: {user_input}",
            trace_id=trace_id,
        )

        self.store.metric("agent_requests_total", 1)

        root_span = self.store.start_span(
            trace_id=trace_id,
            name="agent_run",
            metadata={"user_input_length": len(user_input)},
        )

        try:
            validated = self.validate_input(trace_id, user_input)
            retrieved = self.retrieve_context(trace_id, validated)
            answer = self.call_llm(trace_id, validated, retrieved)

            self.store.end_span(root_span, status="ok")
            self.store.metric("agent_success_total", 1)

            self.store.log(
                level="INFO",
                message="Agent request completed successfully.",
                trace_id=trace_id,
                span_id=root_span.span_id,
            )

            return answer

        except Exception as e:
            self.store.end_span(root_span, status="error")
            self.store.metric("agent_errors_total", 1)

            self.store.log(
                level="ERROR",
                message=f"Agent failed: {e}",
                trace_id=trace_id,
                span_id=root_span.span_id,
            )

            return "Agent failed safely."

    def validate_input(self, trace_id: str, user_input: str) -> str:
        span = self.store.start_span(trace_id, "validate_input")

        self.store.log(
            level="INFO",
            message="Validating user input.",
            trace_id=trace_id,
            span_id=span.span_id,
        )

        if not user_input.strip():
            self.store.end_span(span, status="error")
            raise ValueError("Empty input")

        self.store.end_span(span, status="ok")
        return user_input.strip()

    def retrieve_context(self, trace_id: str, query: str) -> str:
        span = self.store.start_span(trace_id, "retrieve_context")

        # Intentionally no log here.
        # This simulates the edge case: missing logs.

        time.sleep(0.05)

        self.store.metric(
            "retrieval_latency_ms",
            50,
            labels={"step": "retrieve_context"},
        )

        self.store.end_span(span, status="ok")
        return "Relevant context about agents, tools, and memory."

    def call_llm(self, trace_id: str, query: str, context: str) -> str:
        span = self.store.start_span(trace_id, "call_llm")

        self.store.log(
            level="INFO",
            message=(
                "Calling LLM with user email jenny@example.com "
                "and api_key=sk-thisShouldBeRedacted123456"
            ),
            trace_id=trace_id,
            span_id=span.span_id,
        )

        time.sleep(0.08)

        self.store.metric(
            "llm_latency_ms",
            80,
            labels={"model": "mock-llm"},
        )

        self.store.end_span(span, status="ok")

        return f"Answer based on context: {context}"


# ----------------------------
# HTML dashboard
# ----------------------------

class DashboardRenderer:
    def __init__(self, store: ObservabilityStore):
        self.store = store

    def render(self, output_file: str = DASHBOARD_FILE) -> None:
        missing_log_warnings = self.store.detect_missing_logs()

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Agent Observability Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 30px;
            background: #f7f7f7;
        }}
        h1, h2 {{
            color: #222;
        }}
        .card {{
            background: white;
            padding: 16px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        th, td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }}
        th {{
            background: #eee;
        }}
        .ok {{
            color: green;
            font-weight: bold;
        }}
        .error {{
            color: red;
            font-weight: bold;
        }}
        .warning {{
            color: #b36b00;
            font-weight: bold;
        }}
        code {{
            background: #eee;
            padding: 2px 4px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <h1>Agent Observability Dashboard</h1>

    <div class="card">
        <h2>Summary</h2>
        <p>Total logs: <strong>{len(self.store.logs)}</strong></p>
        <p>Total spans: <strong>{len(self.store.spans)}</strong></p>
        <p>Total metrics: <strong>{len(self.store.metrics)}</strong></p>
        <p>Missing-log warnings: <strong>{len(missing_log_warnings)}</strong></p>
    </div>

    <div class="card">
        <h2>Warnings</h2>
        {self.render_warnings(missing_log_warnings)}
    </div>

    <div class="card">
        <h2>Traces and Spans</h2>
        {self.render_spans()}
    </div>

    <div class="card">
        <h2>Logs</h2>
        {self.render_logs()}
    </div>

    <div class="card">
        <h2>Metrics</h2>
        {self.render_metrics()}
    </div>
</body>
</html>
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Dashboard written to: {output_file}")

    def render_warnings(self, warnings: List[str]) -> str:
        if not warnings:
            return "<p class='ok'>No warnings.</p>"

        items = "".join(
            f"<li class='warning'>{html.escape(w)}</li>"
            for w in warnings
        )

        return f"<ul>{items}</ul>"

    def render_spans(self) -> str:
        rows = ""

        for span in self.store.spans:
            status_class = "ok" if span.status == "ok" else "error"

            rows += f"""
<tr>
    <td>{html.escape(span.trace_id)}</td>
    <td>{html.escape(span.span_id)}</td>
    <td>{html.escape(span.name)}</td>
    <td class="{status_class}">{html.escape(span.status)}</td>
    <td>{span.duration_ms}</td>
    <td><code>{html.escape(str(span.metadata))}</code></td>
</tr>
"""

        return f"""
<table>
    <tr>
        <th>Trace ID</th>
        <th>Span ID</th>
        <th>Name</th>
        <th>Status</th>
        <th>Duration ms</th>
        <th>Metadata</th>
    </tr>
    {rows}
</table>
"""

    def render_logs(self) -> str:
        rows = ""

        for log in self.store.logs:
            rows += f"""
<tr>
    <td>{round(log.timestamp, 3)}</td>
    <td>{html.escape(log.level)}</td>
    <td>{html.escape(log.trace_id)}</td>
    <td>{html.escape(str(log.span_id))}</td>
    <td>{html.escape(log.message)}</td>
</tr>
"""

        return f"""
<table>
    <tr>
        <th>Timestamp</th>
        <th>Level</th>
        <th>Trace ID</th>
        <th>Span ID</th>
        <th>Message</th>
    </tr>
    {rows}
</table>
"""

    def render_metrics(self) -> str:
        rows = ""

        for metric in self.store.metrics:
            rows += f"""
<tr>
    <td>{html.escape(metric.name)}</td>
    <td>{metric.value}</td>
    <td><code>{html.escape(str(metric.labels))}</code></td>
</tr>
"""

        return f"""
<table>
    <tr>
        <th>Name</th>
        <th>Value</th>
        <th>Labels</th>
    </tr>
    {rows}
</table>
"""


if __name__ == "__main__":
    store = ObservabilityStore()
    agent = TracedAgent(store)

    print("Running traced agent...")

    response = agent.run(
        "Explain observability. My email is jenny@example.com and password=hello123"
    )

    print("\nAgent response:")
    print(response)

    dashboard = DashboardRenderer(store)
    dashboard.render()

    print("\nOpen this file in your browser:")
    print(DASHBOARD_FILE)