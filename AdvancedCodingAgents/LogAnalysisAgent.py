import re
from dataclasses import dataclass
from typing import List, Dict


ERROR_THRESHOLD = 3
CRITICAL_THRESHOLD = 1
LATENCY_THRESHOLD_MS = 1000


@dataclass
class LogEvent:
    timestamp: str
    level: str
    service: str
    message: str


@dataclass
class IncidentReport:
    is_incident: bool
    severity: str
    summary: str
    evidence: List[str]
    warnings: List[str]


SAMPLE_LOGS = """
2026-05-01T10:00:01 INFO api-service Request completed latency=120ms
2026-05-01T10:00:02 INFO worker-service Job completed successfully
2026-05-01T10:00:03 WARNING api-service Slow request latency=850ms
2026-05-01T10:00:04 ERROR api-service Failed request: database timeout
2026-05-01T10:00:05 INFO api-service Request completed latency=130ms
2026-05-01T10:00:06 WARNING deploy-service Deprecated config value used
2026-05-01T10:00:07 ERROR api-service Failed request: database timeout
2026-05-01T10:00:08 ERROR api-service Failed request: database timeout
2026-05-01T10:00:09 INFO worker-service Job completed successfully
"""


def parse_logs(raw_logs: str) -> List[LogEvent]:
    events = []

    pattern = re.compile(
        r"(?P<timestamp>\S+)\s+"
        r"(?P<level>INFO|WARNING|ERROR|CRITICAL)\s+"
        r"(?P<service>\S+)\s+"
        r"(?P<message>.+)"
    )

    for line in raw_logs.strip().splitlines():
        match = pattern.match(line.strip())

        if not match:
            continue

        events.append(
            LogEvent(
                timestamp=match.group("timestamp"),
                level=match.group("level"),
                service=match.group("service"),
                message=match.group("message"),
            )
        )

    return events


def extract_latency(message: str) -> int | None:
    match = re.search(r"latency=(\d+)ms", message)

    if not match:
        return None

    return int(match.group(1))


class LogAnalysisAgent:
    def analyze(self, events: List[LogEvent]) -> IncidentReport:
        error_events = [e for e in events if e.level == "ERROR"]
        critical_events = [e for e in events if e.level == "CRITICAL"]
        warning_events = [e for e in events if e.level == "WARNING"]

        high_latency_events = []

        for event in events:
            latency = extract_latency(event.message)

            if latency is not None and latency > LATENCY_THRESHOLD_MS:
                high_latency_events.append(event)

        evidence = []
        warnings = []

        service_error_counts: Dict[str, int] = {}

        for event in error_events:
            service_error_counts[event.service] = service_error_counts.get(event.service, 0) + 1

        # Critical errors are strong evidence.
        if len(critical_events) >= CRITICAL_THRESHOLD:
            for event in critical_events:
                evidence.append(
                    f"{event.timestamp} {event.service}: {event.message}"
                )

            return IncidentReport(
                is_incident=True,
                severity="critical",
                summary="Critical incident detected from CRITICAL log events.",
                evidence=evidence,
                warnings=warnings,
            )

        # Multiple repeated errors from same service are stronger evidence than one error.
        repeated_error_services = {
            service: count
            for service, count in service_error_counts.items()
            if count >= ERROR_THRESHOLD
        }

        if repeated_error_services:
            for service, count in repeated_error_services.items():
                evidence.append(
                    f"{service} has {count} ERROR events."
                )

            matching_errors = [
                e for e in error_events
                if e.service in repeated_error_services
            ]

            for event in matching_errors:
                evidence.append(
                    f"{event.timestamp} {event.service}: {event.message}"
                )

            return IncidentReport(
                is_incident=True,
                severity="high",
                summary="Incident likely: repeated errors detected in one or more services.",
                evidence=evidence,
                warnings=warnings,
            )

        # High latency alone is not automatically an incident.
        if high_latency_events:
            for event in high_latency_events:
                evidence.append(
                    f"{event.timestamp} {event.service}: {event.message}"
                )

            warnings.append(
                "High latency observed, but not enough evidence to declare an incident."
            )

            return IncidentReport(
                is_incident=False,
                severity="warning",
                summary="Performance warning detected, but incident not confirmed.",
                evidence=evidence,
                warnings=warnings,
            )

        # Warnings alone should not become incidents.
        if warning_events and not error_events:
            warnings.append(
                "Only WARNING logs found. Avoiding false incident diagnosis."
            )

            return IncidentReport(
                is_incident=False,
                severity="low",
                summary="Warnings detected, but no incident confirmed.",
                evidence=[
                    f"{e.timestamp} {e.service}: {e.message}"
                    for e in warning_events
                ],
                warnings=warnings,
            )

        # Isolated errors are suspicious but not enough.
        if error_events:
            warnings.append(
                "Isolated ERROR events found. Not enough evidence for incident diagnosis."
            )

            return IncidentReport(
                is_incident=False,
                severity="medium",
                summary="Potential issue detected, but incident not confirmed.",
                evidence=[
                    f"{e.timestamp} {e.service}: {e.message}"
                    for e in error_events
                ],
                warnings=warnings,
            )

        return IncidentReport(
            is_incident=False,
            severity="none",
            summary="No incident detected.",
            evidence=[],
            warnings=[],
        )


def print_report(report: IncidentReport) -> None:
    print("\nIncident Report")
    print("=" * 40)
    print("Incident:", report.is_incident)
    print("Severity:", report.severity)
    print("Summary:", report.summary)

    print("\nEvidence:")
    if report.evidence:
        for item in report.evidence:
            print("-", item)
    else:
        print("No evidence.")

    print("\nWarnings:")
    if report.warnings:
        for warning in report.warnings:
            print("-", warning)
    else:
        print("No warnings.")


if __name__ == "__main__":
    events = parse_logs(SAMPLE_LOGS)

    agent = LogAnalysisAgent()
    report = agent.analyze(events)

    print_report(report)