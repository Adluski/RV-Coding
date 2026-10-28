"""Thin client for hosted Judge0 CE. Code execution happens there, not here."""
import base64

import httpx

from . import config


class Judge0Error(Exception):
    def __init__(self, message: str, throttled: bool = False):
        super().__init__(message)
        self.message = message
        self.throttled = throttled


BATCH = 20  # Judge0 CE default max_submission_batch_size


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _unb64(s: str | None) -> str:
    if not s:
        return ""
    try:
        return base64.b64decode(s).decode(errors="replace")
    except ValueError:
        return ""


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if config.JUDGE0_AUTH_TOKEN:
        h[config.JUDGE0_AUTH_HEADER] = config.JUDGE0_AUTH_TOKEN
    return h


def _check(resp: httpx.Response):
    if resp.status_code == 429:
        raise Judge0Error("The judge is rate limiting requests. Please wait a bit and submit again.", True)
    if resp.status_code >= 400:
        raise Judge0Error(f"The judge rejected the request (HTTP {resp.status_code}).")


def create_batch(source: str, language: str, tests, time_limit_sec: float, memory_mb: int) -> list[str]:
    """Create one Judge0 submission per test (no waiting). Returns tokens in test order."""
    items = []
    for t in tests:
        item = {
            "language_id": config.LANGUAGES[language],
            "source_code": _b64(source),
            "stdin": _b64(t.input),
            "expected_output": _b64(t.expected_output),
            "cpu_time_limit": time_limit_sec,
            "memory_limit": memory_mb * 1024,
        }
        if language == "cpp":
            item["compiler_options"] = "-std=c++17"
        items.append(item)
    tokens: list[str] = []
    try:
        with httpx.Client(timeout=15) as c:
            for i in range(0, len(items), BATCH):
                r = c.post(
                    f"{config.JUDGE0_URL}/submissions/batch",
                    params={"base64_encoded": "true"},
                    json={"submissions": items[i:i + BATCH]},
                    headers=_headers(),
                )
                _check(r)
                for entry in r.json():
                    if not isinstance(entry, dict) or "token" not in entry:
                        raise Judge0Error("The judge could not accept the submission.")
                    tokens.append(entry["token"])
    except httpx.HTTPError:
        raise Judge0Error("Could not reach the judge service.")
    return tokens


def get_batch(tokens: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        with httpx.Client(timeout=15) as c:
            for i in range(0, len(tokens), BATCH):
                r = c.get(
                    f"{config.JUDGE0_URL}/submissions/batch",
                    params={
                        "tokens": ",".join(tokens[i:i + BATCH]),
                        "base64_encoded": "true",
                        "fields": "token,status_id,time,memory,message,compile_output",
                    },
                    headers=_headers(),
                )
                _check(r)
                for s in r.json().get("submissions", []):
                    if isinstance(s, dict) and s.get("token"):
                        s["message"] = _unb64(s.get("message"))
                        s["compile_output"] = _unb64(s.get("compile_output"))
                        out[s["token"]] = s
    except httpx.HTTPError:
        raise Judge0Error("Could not reach the judge service.")
    return out
