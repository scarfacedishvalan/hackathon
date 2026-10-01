import json
import requests

BASE_URL = "http://66.42.81.158:8000"


def call(method: str, path: str, body: dict | None = None, timeout: float = 60.0):
    """Make a single API call and pretty-print + return the parsed JSON response."""
    url = BASE_URL.rstrip("/") + path
    resp = requests.request(method, url, json=body, timeout=timeout)
    print(f"{method} {url} -> {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        print(resp.text)
        return resp.text
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return data


def get(path: str, **kwargs):
    return call("GET", path, **kwargs)


def post(path: str, body: dict | None = None, **kwargs):
    return call("POST", path, body, **kwargs)


def put(path: str, body: dict | None = None, **kwargs):
    return call("PUT", path, body, **kwargs)


def patch(path: str, body: dict | None = None, **kwargs):
    return call("PATCH", path, body, **kwargs)


def delete(path: str, **kwargs):
    return call("DELETE", path, **kwargs)


print(post("/views/parse", {"text": "Rising rates will strongly benefit financials and slightly hurt defensives."}))