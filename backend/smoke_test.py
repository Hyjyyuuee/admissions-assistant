import json
import sys
from urllib.error import HTTPError
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:8001"


def get_json(path: str):
    with urlopen(f"{BASE_URL}{path}", timeout=15) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def check(name: str, callback) -> bool:
    try:
        callback()
        print(f"[PASS] {name}")
        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    checks = []

    def health():
        status, body = get_json("/api/health")
        assert status == 200 and body["status"] == "ok"
        assert body["embedding"]["status"] == "ready"
        assert body["graph"]["status"] == "ready"

    def conversations():
        status, body = get_json("/api/conversations")
        assert status == 200 and isinstance(body, list)

    def invalid_conversation():
        try:
            get_json("/api/conversations/does-not-exist")
        except HTTPError as exc:
            assert exc.code == 404
            return
        raise AssertionError("expected 404")

    def trace():
        status, body = get_json("/api/retrieval/trace?query=%E6%96%B0%E7%94%9F%E5%A5%96%E5%AD%A6%E9%87%91")
        assert status == 200 and body["route"]["primary"] == "policy"
        assert body["results"]

    checks.append(check("health / embedding / graph", health))
    checks.append(check("conversation list", conversations))
    checks.append(check("invalid conversation returns 404", invalid_conversation))
    checks.append(check("retrieval trace", trace))
    print(f"\nResult: {sum(checks)}/{len(checks)} passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
