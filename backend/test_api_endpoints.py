"""Lightweight API smoke tests for the FastAPI backend.

Runs against either:
- an in-process FastAPI app (default), or
- a running server (pass --base-url http://localhost:8000)

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


def _check_root(get_json: Callable[[str], Any]) -> None:
    data = get_json("/")
    _assert(isinstance(data, dict), f"GET / should return JSON object, got: {type(data)}")
    _assert(data.get("status") == "running", f"GET / status mismatch: {_pretty(data)}")


def _check_health(get_json: Callable[[str], Any]) -> None:
    data = get_json("/health")
    _assert(isinstance(data, dict), f"GET /health should return JSON object, got: {type(data)}")
    _assert(data.get("status") == "healthy", f"GET /health status mismatch: {_pretty(data)}")


def _check_generate_recipe(
    post_json: Callable[[str, dict[str, Any]], Any],
) -> str:
    payload = {
        "stocks": ["SPY"],
        # Keep it blank to avoid hitting any optional LLM/OpenAI dependency.
        "strategy_instruction": "",
    }

    data = post_json("/api/generate-recipe", payload)
    _assert(isinstance(data, dict), f"POST /api/generate-recipe should return JSON object, got: {type(data)}")

    for key in ("recipe", "equity_curve", "summary_stats"):
        _assert(key in data, f"Missing key '{key}' in response: {_pretty(data)}")

    _assert(isinstance(data["recipe"], dict), f"recipe should be object: {type(data['recipe'])}")
    _assert(isinstance(data["equity_curve"], list), f"equity_curve should be list: {type(data['equity_curve'])}")
    _assert(isinstance(data["summary_stats"], dict), f"summary_stats should be object: {type(data['summary_stats'])}")

    plot_url = data.get("plot_url")
    _assert(isinstance(plot_url, str) and plot_url.startswith("/plots/"), f"plot_url missing/invalid: {_pretty(data)}")

    return plot_url


def _check_plot_fetch(get_text: Callable[[str], tuple[int, str, dict[str, str]]], plot_url: str) -> None:
    status_code, text, headers = get_text(plot_url)
    _assert(status_code == 200, f"GET {plot_url} expected 200, got {status_code}")

    content_type = headers.get("content-type", "")
    _assert(
        "text/html" in content_type or plot_url.endswith(".html"),
        f"Expected HTML content for {plot_url}, got content-type={content_type!r}",
    )

    _assert("<html" in text.lower(), f"Plot HTML response didn't look like HTML")


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

    from app.main import PLOTS_DIR, app

    client = TestClient(app)

    def get_json(path: str) -> Any:
        resp = client.get(path)
        _assert(resp.status_code == 200, f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def post_json(path: str, payload: dict[str, Any]) -> Any:
        resp = client.post(path, json=payload)
        _assert(resp.status_code == 200, f"POST {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def get_text(path: str) -> tuple[int, str, dict[str, str]]:
        resp = client.get(path)
        return resp.status_code, resp.text, {k.lower(): v for k, v in resp.headers.items()}

    _check_root(get_json)
    _check_health(get_json)
    plot_url = _check_generate_recipe(post_json)
    _check_plot_fetch(get_text, plot_url)

    plot_path = PLOTS_DIR / Path(plot_url).name
    _assert(plot_path.exists(), f"Expected plot file to exist on disk: {plot_path}")

    print("OK: in-process API tests passed")
    print(f"- Plot saved: {plot_path}")
    return 0


def _run_live(base_url: str) -> int:
    base_url = base_url.rstrip("/")

    def get_json(path: str) -> Any:
        resp = requests.get(base_url + path, timeout=60)
        _assert(resp.status_code == 200, f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def post_json(path: str, payload: dict[str, Any]) -> Any:
        resp = requests.post(base_url + path, json=payload, timeout=300)
        _assert(resp.status_code == 200, f"POST {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def get_text(path: str) -> tuple[int, str, dict[str, str]]:
        resp = requests.get(base_url + path, timeout=60)
        return resp.status_code, resp.text, {k.lower(): v for k, v in resp.headers.items()}

    _check_root(get_json)
    _check_health(get_json)
    plot_url = _check_generate_recipe(post_json)
    _check_plot_fetch(get_text, plot_url)

    print("OK: live-server API tests passed")
    print(f"- Plot URL: {base_url}{plot_url}")
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
