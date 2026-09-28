"""Lightweight API smoke tests for the FastAPI backend.

Runs against either:
- an in-process FastAPI app (default), or
- a running server (pass --base-url http://localhost:8000)

Only hits GET endpoints that don't require an OPENAI_API_KEY / LLM call,
so this can run without any external dependency.

Usage (from repo root):
  python backend/test_api_endpoints.py
  python backend/test_api_endpoints.py --base-url http://localhost:8000

Exit code:
  0 on success, 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

import requests


BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))


def _fail(msg: str) -> None:
    raise AssertionError(msg)


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        _fail(msg)


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return repr(obj)


def _check_views_current(get_json: Callable[[str], Any]) -> None:
    data = get_json("/views/current")
    _assert(isinstance(data, dict), f"GET /views/current should return JSON object, got: {type(data)}")
    for key in ("bottom_up", "top_down"):
        _assert(key in data, f"Missing key '{key}' in response: {_pretty(data)}")
        _assert(isinstance(data[key], list), f"'{key}' should be a list: {_pretty(data)}")


def _check_model_parameters(get_json: Callable[[str], Any]) -> None:
    data = get_json("/views/model_parameters")
    _assert(isinstance(data, dict), f"GET /views/model_parameters should return JSON object, got: {type(data)}")


def _check_constraints(get_json: Callable[[str], Any]) -> None:
    data = get_json("/views/constraints")
    _assert(isinstance(data, dict), f"GET /views/constraints should return JSON object, got: {type(data)}")


def _check_universe(get_json: Callable[[str], Any]) -> None:
    data = get_json("/views/universe")
    _assert(isinstance(data, dict), f"GET /views/universe should return JSON object, got: {type(data)}")
    _assert("assets" in data, f"Missing key 'assets' in response: {_pretty(data)}")
    _assert(isinstance(data["assets"], list), f"'assets' should be a list: {_pretty(data)}")


def _check_portfolios(get_json: Callable[[str], Any]) -> None:
    data = get_json("/portfolios")
    _assert(isinstance(data, list), f"GET /portfolios should return a JSON array, got: {type(data)}")


def _check_backtest_theses(get_json: Callable[[str], Any]) -> None:
    data = get_json("/backtest/theses")
    _assert(isinstance(data, list), f"GET /backtest/theses should return a JSON array, got: {type(data)}")


def _check_admin_console(get_json: Callable[[str], Any]) -> None:
    data = get_json("/admin/console")
    _assert(isinstance(data, dict), f"GET /admin/console should return JSON object, got: {type(data)}")


def _run_all_checks(get_json: Callable[[str], Any]) -> None:
    _check_views_current(get_json)
    _check_model_parameters(get_json)
    _check_constraints(get_json)
    _check_universe(get_json)
    _check_portfolios(get_json)
    _check_backtest_theses(get_json)
    _check_admin_console(get_json)


def _run_inprocess() -> int:
    try:
        from fastapi.testclient import TestClient  # type: ignore
    except Exception as exc:
        print(
            "FastAPI TestClient not available (likely missing 'httpx'). "
            "Re-run with --base-url http://localhost:8000\n"
            f"Import error: {exc}",
            file=sys.stderr,
        )
        return 1

    from app.main import app

    client = TestClient(app)

    def get_json(path: str) -> Any:
        resp = client.get(path)
        _assert(resp.status_code == 200, f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    _run_all_checks(get_json)

    print("OK: in-process API tests passed")
    return 0


def _run_live(base_url: str) -> int:
    base_url = base_url.rstrip("/")

    def get_json(path: str) -> Any:
        resp = requests.get(base_url + path, timeout=60)
        _assert(resp.status_code == 200, f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    _run_all_checks(get_json)

    print("OK: live-server API tests passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test backend API endpoints")
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="If provided, test against a running server (e.g. http://localhost:8000). Otherwise uses in-process TestClient.",
    )

    args = parser.parse_args(argv)

    try:
        if args.base_url:
            return _run_live(args.base_url)
        return _run_inprocess()
    except AssertionError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
