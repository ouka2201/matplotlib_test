from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def _prepare_numeric_target(value: Any):
    if value in (None, ""):
        return None

    target = value.strip() if isinstance(value, str) else value
    if target == "":
        return ""
    return target


def normalize_decimal_string(value: Any):
    """
    Return a string representation of the numeric input without unnecessary trailing zeros.
    Non-numeric inputs are returned unchanged so callers can decide how to handle them.
    """
    target = _prepare_numeric_target(value)
    if target in (None, ""):
        return target

    try:
        decimal_value = Decimal(str(target))
    except (InvalidOperation, ValueError):
        return value

    if not decimal_value.is_finite():
        return value

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        normalized = normalized.to_integral()

    return format(normalized, "f")


def format_decimal_with_scale(value: Any, scale: int = 3):
    """
    Format numeric input as a string with a fixed number of decimal places (default: 3).
    Non-numeric inputs are returned unchanged.
    """
    target = _prepare_numeric_target(value)
    if target in (None, ""):
        return target

    if scale < 0:
        raise ValueError("scale must be non-negative")

    try:
        decimal_value = Decimal(str(target))
    except (InvalidOperation, ValueError):
        return value

    if not decimal_value.is_finite():
        return value

    quantize_pattern = "1." + "0" * scale if scale > 0 else "1"
    quantized = decimal_value.quantize(
        Decimal(quantize_pattern), rounding=ROUND_HALF_UP
    )

    return f"{quantized:.{scale}f}" if scale > 0 else str(quantized)
