import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

"""Temporary PM Calendar seeder.

This script seeds PM Calendar data through the backend endpoint that uses
`new_doc`/`save_doc` internally.

Reason: the remote DB may already contain records. Calling the generic entity
create endpoint can hit naming collisions (unique IDs) and fail. The feature
seed endpoint is designed for this dataset and handles existing records.
"""

BASE_URL = os.environ.get("EAM_BASE_URL", "http://localhost:8000")

USERNAME = os.environ.get("EAM_USERNAME", "admin")
PASSWORD = os.environ.get("EAM_PASSWORD", "admin123")

SEED_ENDPOINT = f"{BASE_URL}/api/features/pm-calendar/seed"


def _http_json(method: str, url: str, token: str | None, payload: dict[str, Any] | None = None) -> Any:
    body: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url=url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {raw}") from None


def _login() -> str:
    url = f"{BASE_URL}/api/auth/login"
    data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
        obj = json.loads(raw)
        token = obj.get("access_token")
        if not token:
            raise RuntimeError(f"Login failed: {obj}")
        return token


def _seed_all(token: str) -> None:
    res = _http_json("POST", SEED_ENDPOINT, token)
    if not isinstance(res, dict) or res.get("status") != "success":
        raise RuntimeError(f"Seed failed: {res}")
    print(res.get("message") or "Seed complete")


def main() -> int:
    print("This temporary seeding script has already been run successfully.")
    print("Delete backend/scripts/tmp_seed_pm_calendar_excel.py when you are done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
