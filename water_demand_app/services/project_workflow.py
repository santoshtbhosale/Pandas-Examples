"""Project workflow status, timing, and dashboard aggregation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config.nbc_2026 import STAFF_NAMES, project_type_label

STATUS_NEW = "new"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_PENDING = "pending"
STATUS_DELAYED = "delayed"
STATUS_CANCELLED = "cancelled"

STATUS_LABELS = {
    STATUS_NEW: "New",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_COMPLETED: "Completed",
    STATUS_PENDING: "Pending",
    STATUS_DELAYED: "Delayed",
    STATUS_CANCELLED: "Cancelled",
}

STATUS_FILTER_OPTIONS = ["All Status"] + [STATUS_LABELS[s] for s in (
    STATUS_NEW,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_DELAYED,
    STATUS_CANCELLED,
)]

LABEL_TO_STATUS = {v: k for k, v in STATUS_LABELS.items()}


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")[:26])
    except ValueError:
        return None


def format_duration(seconds: Optional[int]) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours:02d}h {minutes:02d}m"
    return f"{minutes:02d}m"


def format_duration_or_dash(seconds: Optional[int]) -> str:
    if seconds is None:
        return "—"
    return format_duration(seconds)


def _now() -> datetime:
    return datetime.now()


def effective_status(row: Dict[str, Any], *, now: Optional[datetime] = None) -> str:
    now = now or _now()
    stored = (row.get("workflow_status") or STATUS_NEW).strip().lower()
    if stored == STATUS_CANCELLED:
        return STATUS_CANCELLED
    if stored == STATUS_COMPLETED or row.get("completed_at"):
        return STATUS_COMPLETED
    if stored == STATUS_PENDING or int(row.get("is_paused") or 0):
        return STATUS_PENDING

    opened = _parse_iso(row.get("project_opened_at"))
    expected = _parse_iso(row.get("expected_completion_at"))
    if expected and now > expected and opened and not row.get("completed_at"):
        return STATUS_DELAYED
    if stored == STATUS_DELAYED:
        return STATUS_DELAYED

    if opened or stored == STATUS_IN_PROGRESS:
        return STATUS_IN_PROGRESS
    return STATUS_NEW


def active_elapsed_seconds(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Optional[int]:
    now = now or _now()
    if int(row.get("is_paused") or 0):
        return max(0, int(row.get("total_time_taken_seconds") or 0))

    if row.get("completed_at"):
        if row.get("total_time_taken_seconds") is not None:
            return max(0, int(row["total_time_taken_seconds"]))
        opened = _parse_iso(row.get("project_opened_at"))
        completed = _parse_iso(row.get("completed_at"))
        if opened and completed:
            paused = int(row.get("total_paused_seconds") or 0)
            return max(0, int((completed - opened).total_seconds()) - paused)
        return None

    opened = _parse_iso(row.get("project_opened_at"))
    if not opened:
        return None
    paused = int(row.get("total_paused_seconds") or 0)
    return max(0, int((now - opened).total_seconds()) - paused)


def expected_seconds(row: Dict[str, Any]) -> Optional[int]:
    minutes = row.get("assigned_duration_minutes")
    if minutes is not None and str(minutes).strip() != "":
        return int(minutes) * 60
    expected = _parse_iso(row.get("expected_completion_at"))
    opened = _parse_iso(row.get("project_opened_at"))
    if expected and opened:
        return max(0, int((expected - opened).total_seconds()))
    return None


def performance_indicator(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Tuple[str, str]:
    now = now or _now()
    status = effective_status(row, now=now)
    elapsed = active_elapsed_seconds(row, now=now)
    expected = expected_seconds(row)

    if status == STATUS_COMPLETED:
        outcome = (row.get("completion_outcome") or "").strip().lower()
        delay = int(row.get("delay_seconds") or 0)
        if outcome == "early" or delay < 0:
            detail = f"{format_duration(abs(delay))} early" if delay else "Completed Early"
            return "✓ Completed Early", detail
        if outcome == "delayed" or delay > 0:
            return "⚠ Delayed", f"{format_duration(delay)} late"
        return "✓ On Time", "On Time"

    if status == STATUS_DELAYED:
        if expected is not None and elapsed is not None:
            overdue = max(0, elapsed - expected)
            return "⚠ Delayed", f"{format_duration(overdue)} overdue"
        return "⚠ Delayed", "Overdue"

    if status in (STATUS_IN_PROGRESS, STATUS_NEW, STATUS_PENDING):
        if expected is not None and elapsed is not None:
            remaining = expected - elapsed
            if remaining >= 0:
                return "● In Progress", f"{format_duration(remaining)} remaining"
            return "⚠ Delayed", f"{format_duration(abs(remaining))} overdue"
        return "● In Progress", STATUS_LABELS.get(status, "In Progress")

    if status == STATUS_CANCELLED:
        return "Cancelled", "Cancelled"
    return STATUS_LABELS.get(status, status.title()), ""


def enrich_dashboard_row(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    status = effective_status(row, now=now)
    elapsed = active_elapsed_seconds(row, now=now)
    expected = expected_seconds(row)
    perf_title, perf_detail = performance_indicator(row, now=now)
    project_type = (row.get("project_type") or "").strip()
    return {
        **row,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status.title()),
        "time_taken_seconds": elapsed,
        "time_taken_display": format_duration_or_dash(elapsed),
        "expected_seconds": expected,
        "expected_display": format_duration_or_dash(expected),
        "performance_title": perf_title,
        "performance_detail": perf_detail,
        "project_type_label": project_type_label(project_type) if project_type else "—",
        "created_display": _display_date(row.get("created_at") or row.get("date")),
        "updated_display": _display_date(row.get("updated_at")),
    }


def _display_date(value: Optional[str]) -> str:
    dt = _parse_iso(value)
    if dt:
        return dt.strftime("%d-%m-%Y %H:%M")[:16]
    return (value or "—")[:16]


def is_today(value: Optional[str], *, now: Optional[datetime] = None) -> bool:
    now = now or _now()
    dt = _parse_iso(value)
    if not dt:
        return False
    return dt.date() == now.date()


def compute_statistics(rows: List[Dict[str, Any]], *, now: Optional[datetime] = None) -> Dict[str, int]:
    now = now or _now()
    stats = {
        "total": 0,
        "in_progress": 0,
        "completed": 0,
        "pending": 0,
        "delayed": 0,
        "today": 0,
    }
    for raw in rows:
        row = enrich_dashboard_row(raw, now=now)
        stats["total"] += 1
        status = row["status"]
        if status == STATUS_IN_PROGRESS:
            stats["in_progress"] += 1
        elif status == STATUS_COMPLETED:
            stats["completed"] += 1
        elif status == STATUS_PENDING:
            stats["pending"] += 1
        elif status == STATUS_DELAYED:
            stats["delayed"] += 1
        if is_today(raw.get("created_at"), now=now) or is_today(raw.get("project_opened_at"), now=now):
            stats["today"] += 1
    return stats


def compute_engineer_performance(rows: List[Dict[str, Any]], *, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    now = now or _now()
    buckets: Dict[str, Dict[str, Any]] = {}
    for raw in rows:
        row = enrich_dashboard_row(raw, now=now)
        engineer = (row.get("engineer_name") or "Unassigned").strip() or "Unassigned"
        bucket = buckets.setdefault(
            engineer,
            {
                "engineer": engineer,
                "projects": 0,
                "completed": 0,
                "in_progress": 0,
                "delayed": 0,
                "completed_seconds": [],
            },
        )
        bucket["projects"] += 1
        status = row["status"]
        if status == STATUS_COMPLETED:
            bucket["completed"] += 1
            if row.get("time_taken_seconds") is not None:
                bucket["completed_seconds"].append(int(row["time_taken_seconds"]))
        elif status == STATUS_IN_PROGRESS:
            bucket["in_progress"] += 1
        elif status == STATUS_DELAYED:
            bucket["delayed"] += 1

    result = []
    for engineer in sorted(buckets, key=lambda k: (-buckets[k]["projects"], k.lower())):
        bucket = buckets[engineer]
        seconds = bucket["completed_seconds"]
        avg = int(sum(seconds) / len(seconds)) if seconds else None
        result.append(
            {
                "engineer": engineer,
                "projects": bucket["projects"],
                "completed": bucket["completed"],
                "in_progress": bucket["in_progress"],
                "delayed": bucket["delayed"],
                "avg_time_display": format_duration_or_dash(avg),
            }
        )
    return result


def list_engineer_options(rows: List[Dict[str, Any]]) -> List[str]:
    names = {name for name in STAFF_NAMES}
    for row in rows:
        engineer = (row.get("engineer_name") or "").strip()
        if engineer:
            names.add(engineer)
    return ["All Engineers"] + sorted(names, key=str.lower)


def filter_rows(
    rows: List[Dict[str, Any]],
    *,
    engineer: str = "All Engineers",
    status_label: str = "All Status",
    search: str = "",
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    now = now or _now()
    search_key = (search or "").strip().lower()
    status_key = LABEL_TO_STATUS.get(status_label)

    filtered: List[Dict[str, Any]] = []
    for raw in rows:
        row = enrich_dashboard_row(raw, now=now)
        if engineer and engineer != "All Engineers":
            eng = (row.get("engineer_name") or "").strip()
            if eng != engineer:
                continue
        if status_key and row["status"] != status_key:
            continue
        if search_key:
            haystack = " ".join(
                [
                    row.get("project_id", ""),
                    row.get("project_name", ""),
                    row.get("client_name", ""),
                    row.get("engineer_name", ""),
                    row.get("project_type_label", ""),
                    row.get("status_label", ""),
                    row.get("project_type", ""),
                ]
            ).lower()
            if search_key not in haystack:
                continue
        filtered.append(row)
    return filtered


def rows_for_stats(
    rows: List[Dict[str, Any]],
    *,
    engineer: str = "All Engineers",
    status_label: str = "All Status",
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    return filter_rows(rows, engineer=engineer, status_label=status_label, search="", now=now)


def completion_fields_on_finish(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    opened = _parse_iso(row.get("project_opened_at")) or now
    paused = int(row.get("total_paused_seconds") or 0)
    elapsed = max(0, int((now - opened).total_seconds()) - paused)
    expected = expected_seconds(row)
    delay = 0
    outcome = "on_time"
    if expected is not None:
        delay = elapsed - expected
        if delay < 0:
            outcome = "early"
        elif delay > 0:
            outcome = "delayed"
    return {
        "workflow_status": STATUS_COMPLETED,
        "completed_at": now.isoformat(),
        "total_time_taken_seconds": elapsed,
        "delay_seconds": max(0, delay) if delay > 0 else delay,
        "completion_outcome": outcome,
        "is_paused": 0,
    }


def open_fields_on_start(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    updates: Dict[str, Any] = {}
    if not row.get("project_opened_at"):
        updates["project_opened_at"] = now.isoformat()
    status = (row.get("workflow_status") or STATUS_NEW).strip().lower()
    if status in ("", STATUS_NEW, STATUS_PENDING):
        updates["workflow_status"] = STATUS_IN_PROGRESS
        updates["is_paused"] = 0
    return updates
