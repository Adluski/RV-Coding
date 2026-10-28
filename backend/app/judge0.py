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
# Judged submissions never fetch stdout/stderr: a correct program's stdout on a hidden test IS the hidden answer.
SUBMISSION_FIELDS = "token,status_id,time,memory,message,compile_output"
RUN_FIELDS = SUBMISSION_FIELDS + ",stdout,stderr"


def _client() -> httpx.Client:
    """Separate function so tests can swap in an httpx.MockTransport."""
    return httpx.Client(timeout=15)


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
        raise Judge0Error("The judge is rate limiting requests. Please wait a bit and try again.", True)
    if resp.status_code >= 400:
        raise Judge0Error(f"The judge rejected the request (HTTP {resp.status_code}).")


def create_batch(source: str, language: str, cases, time_limit_sec: float, memory_mb: int) -> list[str]:
    """cases: list of (stdin, expected_output or None). Creates one Judge0 submission per case without
    waiting and returns the tokens in the same order."""
    items = []
    for stdin, expected in cases:
        item = {
            "language_id": config.LANGUAGES[language],
            "source_code": _b64(source),
            "stdin": _b64(stdin),
            "cpu_time_limit": time_limit_sec,
            "memory_limit": memory_mb * 1024,
        }
        if expected is not None:
            item["expected_output"] = _b64(expected)
        if language == "cpp":
            item["compiler_options"] = "-std=c++17"
        items.append(item)
    tokens: list[str] = []
    try:
        with _client() as c:
            for i in range(0, len(items), BATCH):
                r = c.post(
                    f"{config.JUDGE0_URL}/submissions/batch",
                    params={"base64_encoded": "true"},
                    json={"submissions": items[i:i + BATCH]},
                    headers=_headers(),
                )
                _check(r)
                data = r.json()
                if not isinstance(data, list) or len(data) != len(items[i:i + BATCH]):
                    raise Judge0Error("The judge returned an unexpected response.")
                for entry in data:
                    if not isinstance(entry, dict) or not entry.get("token"):
                        raise Judge0Error("The judge could not accept the submission.")
                    tokens.append(entry["token"])
    except httpx.HTTPError:
        raise Judge0Error("Could not reach the judge service.")
    except ValueError:  # invalid JSON
        raise Judge0Error("The judge returned an unexpected response.")
    return tokens


def get_batch(tokens: list[str], fields: str = SUBMISSION_FIELDS) -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        with _client() as c:
            for i in range(0, len(tokens), BATCH):
                r = c.get(
                    f"{config.JUDGE0_URL}/submissions/batch",
                    params={"tokens": ",".join(tokens[i:i + BATCH]), "base64_encoded": "true", "fields": fields},
                    headers=_headers(),
                )
                _check(r)
                data = r.json()
                subs = data.get("submissions") if isinstance(data, dict) else None
                if not isinstance(subs, list):
                    raise Judge0Error("The judge returned an unexpected response.")
                for s in subs:
                    if isinstance(s, dict) and s.get("token"):
                        for k in ("message", "compile_output", "stdout", "stderr"):
                            if k in s:
                                s[k] = _unb64(s.get(k))
                        out[s["token"]] = s
    except httpx.HTTPError:
        raise Judge0Error("Could not reach the judge service.")
    except ValueError:
        raise Judge0Error("The judge returned an unexpected response.")
    return out
