import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


ERROR_RATE_THRESHOLD = 0.25
LATENCY_THRESHOLD_MS = 1200
QUALITY_THRESHOLD = 0.75
REGRESSION_DROP_THRESHOLD = 0.15

ALERT_COOLDOWN_SECONDS = 10
ROLLING_WINDOW_SIZE = 5


@dataclass
class AgentRun:
    run_id: int
    success: bool
    latency_ms: int
    quality_score: float
    cost: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class Alert:
    name: str
    severity: str
    message: str
    timestamp: float = field(default_factory=time.time)


class MetricsStore:
    def __init__(self):
        self.runs: List[AgentRun] = []

    def add_run(self, run: AgentRun) -> None:
        self.runs.append(run)

    def recent_runs(self, limit: int = ROLLING_WINDOW_SIZE) -> List[AgentRun]:
        return self.runs[-limit:]

    def error_rate(self) -> float:
        recent = self.recent_runs()

        if not recent:
            return 0.0

        failures = sum(1 for run in recent if not run.success)
        return failures / len(recent)

    def average_latency(self) -> float:
        recent = self.recent_runs()

        if not recent:
            return 0.0

        return sum(run.latency_ms for run in recent) / len(recent)

    def average_quality(self) -> float:
        recent = self.recent_runs()

        if not recent:
            return 1.0

        return sum(run.quality_score for run in recent) / len(recent)

    def average_cost(self) -> float:
        recent = self.recent_runs()

        if not recent:
            return 0.0

        return sum(run.cost for run in recent) / len(recent)


class AlertManager:
    """
    Prevents alert fatigue by suppressing repeated alerts
    within a cooldown window.
    """

    def __init__(self):
        self.last_alert_times: Dict[str, float] = {}
        self.alert_history: List[Alert] = []

    def should_send_alert(self, alert_name: str) -> bool:
        now = time.time()
        last_sent = self.last_alert_times.get(alert_name)

        if last_sent is None:
            return True

        return now - last_sent >= ALERT_COOLDOWN_SECONDS

    def send_alert(self, name: str, severity: str, message: str) -> None:
        if not self.should_send_alert(name):
            print(f"Suppressed duplicate alert: {name}")
            return

        alert = Alert(
            name=name,
            severity=severity,
            message=message,
        )

        self.alert_history.append(alert)
        self.last_alert_times[name] = alert.timestamp

        print("\nALERT")
        print("Name:", alert.name)
        print("Severity:", alert.severity)
        print("Message:", alert.message)


class EvalRegressionChecker:
    """
    Detects hidden degradation by comparing current quality
    to a baseline quality score.
    """

    def __init__(self, baseline_quality: float):
        self.baseline_quality = baseline_quality

    def check(self, current_quality: float) -> Optional[str]:
        drop = self.baseline_quality - current_quality

        if drop >= REGRESSION_DROP_THRESHOLD:
            return (
                f"Eval regression detected. Baseline quality={self.baseline_quality:.2f}, "
                f"current quality={current_quality:.2f}, drop={drop:.2f}"
            )

        return None


class Dashboard:
    def render(self, metrics: MetricsStore, alerts: AlertManager) -> None:
        print("\n================ DASHBOARD ================")
        print("Total runs:", len(metrics.runs))
        print("Recent error rate:", round(metrics.error_rate(), 3))
        print("Recent avg latency:", round(metrics.average_latency(), 2), "ms")
        print("Recent avg quality:", round(metrics.average_quality(), 3))
        print("Recent avg cost:", round(metrics.average_cost(), 4))
        print("Total alerts:", len(alerts.alert_history))

        if alerts.alert_history:
            latest = alerts.alert_history[-1]
            print("Latest alert:", latest.name, "-", latest.severity)

        print("===========================================\n")


class MockProductionAgent:
    """
    Simulates an agent in production.

    Later runs silently degrade in quality while still returning success.
    This demonstrates hidden degradation.
    """

    def run(self, run_id: int) -> AgentRun:
        latency = random.randint(300, 1500)
        cost = round(random.uniform(0.002, 0.02), 4)

        # Most runs technically succeed.
        success = random.random() > 0.15

        # Hidden degradation starts after run 7.
        if run_id < 7:
            quality = random.uniform(0.82, 0.95)
        else:
            quality = random.uniform(0.55, 0.72)

        return AgentRun(
            run_id=run_id,
            success=success,
            latency_ms=latency,
            quality_score=round(quality, 3),
            cost=cost,
        )


class MonitoringLoop:
    def __init__(self):
        self.metrics = MetricsStore()
        self.alerts = AlertManager()
        self.dashboard = Dashboard()
        self.agent = MockProductionAgent()
        self.eval_checker = EvalRegressionChecker(baseline_quality=0.88)

    def check_alerts(self) -> None:
        error_rate = self.metrics.error_rate()
        avg_latency = self.metrics.average_latency()
        avg_quality = self.metrics.average_quality()

        if error_rate >= ERROR_RATE_THRESHOLD:
            self.alerts.send_alert(
                name="high_error_rate",
                severity="high",
                message=f"Error rate is {error_rate:.2f}, above threshold {ERROR_RATE_THRESHOLD}.",
            )

        if avg_latency >= LATENCY_THRESHOLD_MS:
            self.alerts.send_alert(
                name="high_latency",
                severity="medium",
                message=f"Average latency is {avg_latency:.0f}ms, above threshold {LATENCY_THRESHOLD_MS}ms.",
            )

        if avg_quality < QUALITY_THRESHOLD:
            self.alerts.send_alert(
                name="low_quality",
                severity="high",
                message=f"Average quality is {avg_quality:.2f}, below threshold {QUALITY_THRESHOLD}.",
            )

        regression_message = self.eval_checker.check(avg_quality)

        if regression_message:
            self.alerts.send_alert(
                name="eval_regression",
                severity="critical",
                message=regression_message,
            )

    def run_once(self, run_id: int) -> None:
        run = self.agent.run(run_id)
        self.metrics.add_run(run)

        print(f"Run {run.run_id}: success={run.success}, latency={run.latency_ms}ms, quality={run.quality_score}, cost=${run.cost}")

        self.check_alerts()
        self.dashboard.render(self.metrics, self.alerts)

    def run_loop(self, total_runs: int = 12) -> None:
        for run_id in range(1, total_runs + 1):
            self.run_once(run_id)

            # Short sleep for demo.
            # Real systems run this on a schedule or streaming pipeline.
            time.sleep(1)


if __name__ == "__main__":
    monitor = MonitoringLoop()
    monitor.run_loop()