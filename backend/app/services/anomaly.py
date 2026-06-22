"""Deterministic execution anomaly detection (P0.4).

No LLM: flags are derived statistically from a workflow's recent execution
history. (LLM-written explanations are deferred to P1.)
"""

import statistics

from app.models import Execution


def _duration_seconds(execution: Execution) -> float | None:
    if execution.completed_at is None:
        return None
    return (execution.completed_at - execution.started_at).total_seconds()


def detect_anomalies(execution: Execution, history: list[Execution]) -> list[str]:
    """Return human-readable anomaly flags for one execution.

    `history` is the workflow's recent executions (most-recent first), and may
    include `execution` itself.
    """
    flags: list[str] = []

    others = [e for e in history if e.id != execution.id]
    durations = [d for e in others if (d := _duration_seconds(e)) is not None]
    duration = _duration_seconds(execution)
    if duration is not None and len(durations) >= 3:
        mean = statistics.mean(durations)
        stdev = statistics.pstdev(durations)
        # Use the spread when there is one; otherwise flag a large jump over a
        # stable baseline (stdev == 0 would otherwise never trigger).
        threshold = mean + 2 * stdev if stdev > 0 else mean * 2
        if mean > 0 and duration > threshold:
            flags.append(f"Slow run: {duration:.1f}s vs ~{mean:.1f}s average")

    if execution.status == "failed":
        recent = others[:3]
        if len(recent) == 3 and all(e.status == "failed" for e in recent):
            flags.append("Repeated failures: the last 3 runs also failed")

    if execution.error:
        node = execution.error.get("node_id")
        if node:
            flags.append(f"Failed at node '{node}'")

    return flags
