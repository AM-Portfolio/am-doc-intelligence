#!/usr/bin/env python3
"""Seed GMAIL_BROKER_PATTERNS_JSON onto apps/data/{env}/services/am-email-extractor.

Uses VAULT_ADDR / VAULT_TOKEN from env or ~/.asrax (same as amctl google-oauth bridge).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ASRAX = Path.home() / ".asrax"
PATTERNS = {
    "groww": {
        "from": "groww.in",
        "subject": "Holding Statement",
        "file_pattern": [".pdf"],
    },
    "zerodha": {
        "from": "zerodha.net",
        "subject": "Holding Statement",
        "file_pattern": [".pdf"],
    },
    "angleone": {
        "from": "angelone.in",
        "subject": "Holdings",
        "file_pattern": [".xlsx"],
    },
    "dhan": {
        "from": "statements@dhan.co",
        "subject": "Demat Holding Summary",
        "file_pattern": [".pdf", ".xlsx", ".xls"],
    },
    "mstock": {
        "from": "mstock.com",
        "subject": "TRANSACTION STATEMENT",
        "file_pattern": [".pdf"],
    },
}


def _load_vault() -> tuple[str, str]:
    addr = (os.environ.get("VAULT_ADDR") or "").rstrip("/")
    token = os.environ.get("VAULT_TOKEN") or ""
    for name in ("credentials.vault.env", "credentials.env"):
        path = ASRAX / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("VAULT_ADDR=") and not addr:
                addr = line.split("=", 1)[1].strip().strip('"').rstrip("/")
            if line.startswith("VAULT_TOKEN=") and not token:
                token = line.split("=", 1)[1].strip().strip('"')
    if not addr or not token:
        raise SystemExit("VAULT_ADDR/VAULT_TOKEN missing (env or ~/.asrax)")
    return addr, token


def _kv_read(addr: str, token: str, secret_path: str) -> dict:
    # secret_path like "dev/services/am-email-extractor" under mount apps/data
    url = f"{addr}/v1/apps/data/data/{secret_path}"
    req = urllib.request.Request(
        url,
        headers={"X-Vault-Token": token, "User-Agent": "am-email-extractor-seed/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
        return (body.get("data") or {}).get("data") or {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise


def _kv_write(addr: str, token: str, secret_path: str, data: dict) -> None:
    url = f"{addr}/v1/apps/data/data/{secret_path}"
    payload = json.dumps({"data": data}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "X-Vault-Token": token,
            "Content-Type": "application/json",
            "User-Agent": "am-email-extractor-seed/1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", default="dev,preprod,prod")
    args = ap.parse_args()
    addr, token = _load_vault()
    blob = json.dumps(PATTERNS, separators=(",", ":"))
    for env in [e.strip() for e in args.envs.split(",") if e.strip()]:
        path = f"{env}/services/am-email-extractor"
        current = _kv_read(addr, token, path)
        current["GMAIL_BROKER_PATTERNS_JSON"] = blob
        _kv_write(addr, token, path, current)
        dhan = PATTERNS["dhan"]
        print(f"OK {path} dhan from={dhan['from']} subject={dhan['subject']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
