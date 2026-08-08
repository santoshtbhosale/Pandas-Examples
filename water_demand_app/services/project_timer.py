"""Project timer calculations — elapsed, remaining, delay, status."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from models.project_workflow import (
    OUTCOME_EARLY,
    OUTCOME_LATE,
    OUTCOME_ON_TIME,
    STATUS_COMPLETED,
    STATUS_DELAYED,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
    STATUS_PAUSED,
    ProjectWorkflow,
)


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _fmt_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def active_elapsed_seconds(wf: ProjectWorkflow, now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    start = _parse_iso(wf.project_opened_at) or _parse_iso(wf.assigned_at)
    if not start:
        return 0
    end = _parse_iso(wf.completed_at) or now
    total = int((end - start).total_seconds())
    total -= int(wf.total_paused_seconds or 0)
    if wf.status == STATUS_PAUSED and wf.paused_at:
        paused = _parse_iso(wf.paused_at)
        if paused:
            total -= int((now - paused).total_seconds())
    return max(0, total)


def remaining_seconds(wf: ProjectWorkflow, now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    expected = _parse_iso(wf.expected_completion_at)
    if not expected or wf.status == STATUS_COMPLETED:
        return 0
    if now >= expected:
        return 0
    return int((expected - now).total_seconds())


def delay_seconds(wf: ProjectWorkflow, now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    if wf.status == STATUS_COMPLETED:
        return int(wf.delay_seconds or 0)
    expected = _parse_iso(wf.expected_completion_at)
    if not expected or now <= expected:
        return 0
    return int((now - expected).total_seconds())


def effective_status(wf: ProjectWorkflow, now: Optional[datetime] = None) -> str:
    if wf.status in (STATUS_COMPLETED, STATUS_PAUSED, STATUS_NOT_STARTED):
        if wf.status == STATUS_NOT_STARTED and delay_seconds(wf, now) > 0:
            return STATUS_DELAYED
        return wf.status
    if wf.status == STATUS_IN_PROGRESS and delay_seconds(wf, now) > 0:
        return STATUS_DELAYED
    return wf.status


def completion_outcome(wf: ProjectWorkflow) -> str:
    if wf.completion_outcome:
        return wf.completion_outcome
    expected = _parse_iso(wf.expected_completion_at)
    completed = _parse_iso(wf.completed_at)
    if not expected or not completed:
        return ""
    if completed < expected:
        return OUTCOME_EARLY
    if completed == expected:
        return OUTCOME_ON_TIME
    return OUTCOME_LATE


def timer_snapshot(wf: ProjectWorkflow, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now()
    elapsed = active_elapsed_seconds(wf, now)
    remaining = remaining_seconds(wf, now)
    delay = delay_seconds(wf, now)
    status = effective_status(wf, now)
    return {
        "elapsed_seconds": elapsed,
        "elapsed_display": _fmt_duration(elapsed),
        "remaining_seconds": remaining,
        "remaining_display": _fmt_duration(remaining),
        "delay_seconds": delay,
        "delay_display": _fmt_duration(delay),
        "status": status,
        "completion_outcome": completion_outcome(wf),
        "expected_completion_at": wf.expected_completion_at,
        "assigned_at": wf.assigned_at,
        "project_opened_at": wf.project_opened_at,
        "completed_at": wf.completed_at,
        "progress_pct": wf.progress_pct,
    }


def compute_completion(
    wf: ProjectWorkflow,
    now: Optional[datetime] = None,
) -> ProjectWorkflow:
    now = now or datetime.now()
    wf.completed_at = now.isoformat()
    wf.total_time_taken_seconds = active_elapsed_seconds(wf, now)
    wf.delay_seconds = max(0, wf.total_time_taken_seconds - int((wf.assigned_duration_minutes or 0) * 60))
    expected = _parse_iso(wf.expected_completion_at)
    if expected:
        if now < expected:
            wf.completion_outcome = OUTCOME_EARLY
        elif int((now - expected).total_seconds()) <= 60:
            wf.completion_outcome = OUTCOME_ON_TIME
        else:
            wf.completion_outcome = OUTCOME_LATE
            wf.delay_seconds = int((now - expected).total_seconds())
    wf.status = STATUS_COMPLETED
    wf.progress_pct = 100
    return wf
