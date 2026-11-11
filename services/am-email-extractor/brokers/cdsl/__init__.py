"""CDSL Consolidated Account Statement (CAS) extractor."""

from brokers.cdsl.extractor import extract_document, extract_holdings

__all__ = ["extract_document", "extract_holdings"]
