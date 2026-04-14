"""Utility helpers for stock symbol formatting."""

from __future__ import annotations

import re

from app.core.exceptions import InputValidationError


# Supports symbols like RELIANCE, RELIANCE.NS, TCS.NS, SBIN.BO.
STOCK_SYMBOL_PATTERN = r"^[A-Z0-9][A-Z0-9._-]{0,14}(\.(NS|BO))?$"
_SYMBOL_REGEX = re.compile(STOCK_SYMBOL_PATTERN)


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or not _SYMBOL_REGEX.fullmatch(normalized):
        raise InputValidationError(
            "Invalid stock symbol format. Use NSE/BSE format like RELIANCE.NS or TCS.BO"
        )

    # Default plain Indian symbols to NSE for better UX (e.g., RELIANCE -> RELIANCE.NS).
    if not normalized.endswith(".NS") and not normalized.endswith(".BO"):
        normalized = f"{normalized}.NS"

    return normalized


def stock_code(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if ":" in normalized:
        normalized = normalized.split(":", 1)[1]
    return normalized.split(".")[0]
