"""Lightweight API smoke tests for the FastAPI backend.

Runs against either:
- an in-process FastAPI app (default), or
- a running server (pass --base-url http://localhost:8000)

By default only hits GET endpoints that don't require an OPENAI_API_KEY /
LLM call. Pass --with-llm to additionally exercise the LLM-backed endpoints
(/backtest/parse, /views/parse) with real OpenAI calls — requires
OPENAI_API_KEY to be set and will incur API cost.

Usage (from repo root):
  python backend/test_api_endpoints.py
  python backend/test_api_endpoints.py --base-url http://localhost:8000
  python backend/test_api_endpoints.py --base-url http://localhost:8000 --with-llm

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


# ---------------------------------------------------------------------------
# LLM-backed checks (opt-in via --with-llm; real OpenAI calls, real cost)
# ---------------------------------------------------------------------------

def _check_llm_backtest_parse(post_json: Callable[[str, dict[str, Any]], Any]) -> None:
    """POST /backtest/parse — real LLM call, no side effects."""
    payload = {"text": "Backtest SmaCross on AAPL daily from 2021-01-01 to 2022-01-01"}
    data = post_json("/backtest/parse", payload)
    _assert(isinstance(data, dict), f"POST /backtest/parse should return JSON object, got: {type(data)}")
    _assert("strategy_name" in data, f"Missing key 'strategy_name' in response: {_pretty(data)}")


def _check_llm_views_parse(
    get_json: Callable[[str], Any],
    post_json: Callable[[str, dict[str, Any]], Any],
    delete_call: Callable[[str], None],
) -> None:
    """POST /views/parse — real LLM call that appends to current.json; cleans up after itself."""
    before = get_json("/views/current")
    n_bottom_before = len(before.get("bottom_up", []))
    n_top_before = len(before.get("top_down", []))

    payload = {"text": "AAPL is expected to outperform the market by 5% with high confidence"}
    data = post_json("/views/parse", payload)
    _assert(isinstance(data, dict), f"POST /views/parse should return JSON object, got: {type(data)}")
    _assert("view" in data, f"Missing key 'view' in response: {_pretty(data)}")

    after = get_json("/views/current")
    n_bottom_after = len(after.get("bottom_up", []))
    n_top_after = len(after.get("top_down", []))

    # Clean up any newly appended rows (delete from the end so indices stay valid).
    for i in range(n_bottom_after - 1, n_bottom_before - 1, -1):
        delete_call(f"/views/bottom_up/{i}")
    for i in range(n_top_after - 1, n_top_before - 1, -1):
        delete_call(f"/views/top_down/{i}")


def _run_llm_checks(
    get_json: Callable[[str], Any],
    post_json: Callable[[str, dict[str, Any]], Any],
    delete_call: Callable[[str], None],
) -> None:
    _check_llm_backtest_parse(post_json)
    _check_llm_views_parse(get_json, post_json, delete_call)


def _run_inprocess(with_llm: bool) -> int:
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

    def post_json(path: str, payload: dict[str, Any]) -> Any:
        resp = client.post(path, json=payload)
        _assert(resp.status_code == 200, f"POST {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def delete_call(path: str) -> None:
        resp = client.delete(path)
        _assert(resp.status_code in (200, 204), f"DELETE {path} -> {resp.status_code}: {resp.text}")

    _run_all_checks(get_json)
    if with_llm:
        _run_llm_checks(get_json, post_json, delete_call)

    print("OK: in-process API tests passed" + (" (incl. LLM calls)" if with_llm else ""))
    return 0


def _run_live(base_url: str, with_llm: bool) -> int:
    base_url = base_url.rstrip("/")

    def get_json(path: str) -> Any:
        resp = requests.get(base_url + path, timeout=60)
        _assert(resp.status_code == 200, f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def post_json(path: str, payload: dict[str, Any]) -> Any:
        resp = requests.post(base_url + path, json=payload, timeout=300)
        _assert(resp.status_code == 200, f"POST {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def delete_call(path: str) -> None:
        resp = requests.delete(base_url + path, timeout=60)
        _assert(resp.status_code in (200, 204), f"DELETE {path} -> {resp.status_code}: {resp.text}")

    _run_all_checks(get_json)
    if with_llm:
        _run_llm_checks(get_json, post_json, delete_call)

    print("OK: live-server API tests passed" + (" (incl. LLM calls)" if with_llm else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test backend API endpoints")
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="If provided, test against a running server (e.g. http://localhost:8000). Otherwise uses in-process TestClient.",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Also exercise LLM-backed endpoints (/backtest/parse, /views/parse) with real OpenAI calls. Requires OPENAI_API_KEY.",
    )

    args = parser.parse_args(argv)

    try:
        if args.base_url:
            return _run_live(args.base_url, args.with_llm)
        return _run_inprocess(args.with_llm)
    except AssertionError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

