from __future__ import annotations

import re
from typing import Callable, Optional, Tuple


class ValidationError(Exception):
    def __init__(self, message: str, field: str = "") -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def validate_required(value: str, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError(f"{field_name} is required.", field_name)
    return cleaned


def validate_positive_int(value: str, field_name: str, allow_zero: bool = False) -> int:
    cleaned = (value or "").strip()
    if not cleaned:
        if allow_zero:
            return 0
        raise ValidationError(f"{field_name} must be a positive number.", field_name)
    try:
        num = int(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a whole number.", field_name) from exc
    if num < 0 or (not allow_zero and num == 0):
        raise ValidationError(f"{field_name} must be a positive number.", field_name)
    return num


def validate_positive_float(value: str, field_name: str, allow_zero: bool = True) -> float:
    cleaned = (value or "").strip()
    if not cleaned:
        return 0.0 if allow_zero else (_ for _ in ()).throw(
            ValidationError(f"{field_name} must be a number.", field_name)
        )
    try:
        num = float(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid number.", field_name) from exc
    if num < 0 or (not allow_zero and num == 0):
        raise ValidationError(f"{field_name} must be a positive number.", field_name)
    return num


def validate_date(value: str, field_name: str = "Date") -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError(f"{field_name} is required.", field_name)
    if not re.match(r"^\d{2}-\d{2}-\d{4}$", cleaned):
        raise ValidationError(f"{field_name} must be in DD-MM-YYYY format.", field_name)
    return cleaned


def safe_execute(action: Callable, on_error: Callable[[str], None]) -> bool:
    try:
        action()
        return True
    except ValidationError as exc:
        on_error(exc.message)
        return False
    except Exception as exc:
        on_error(str(exc))
        return False
