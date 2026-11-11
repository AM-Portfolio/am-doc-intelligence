"""Broker extractor registry — dispatch without sprawling if/elif in app_api."""
from __future__ import annotations

from typing import Any, Callable

ExtractorFn = Callable[[str, str | None], list[dict[str, Any]]]


def _load_legacy(module_path: str) -> ExtractorFn:
    def _run(file_path: str, password: str | None = None) -> list[dict[str, Any]]:
        import importlib

        mod = importlib.import_module(module_path)
        return mod.extract_holdings(file_path, password)

    return _run


EXTRACTORS: dict[str, ExtractorFn] = {
    "groww": _load_legacy("brokers.groww.extractor"),
    "zerodha": _load_legacy("brokers.zerodha.extractor"),
    "angleone": _load_legacy("brokers.angleone.extractor"),
    "dhan": _load_legacy("brokers.dhan.extractor"),
    "mstock": _load_legacy("brokers.mstock.extractor"),
    "cdsl": _load_legacy("brokers.cdsl.extractor"),
    "nps": _load_legacy("brokers.nps.extractor"),
}

SUPPORTED_BROKERS = sorted(EXTRACTORS.keys())


def extract_broker_holdings(broker: str, file_path: str, password: str | None = None) -> list[dict[str, Any]]:
    key = (broker or "").strip().lower()
    fn = EXTRACTORS.get(key)
    if not fn:
        raise ValueError(f"Unsupported broker: {broker}")
    return fn(file_path, password)
