"""In-process fake of the Judge0 batch API, driven by directives inside the submitted source code.

A source line like  #FAKE status=3,3,4 time=0.05 memory=900 stdout=echo  sets, per test index in the batch:
  status    Judge0 status ids (the last one repeats)       stdout  echo | expected | literal text
  time/memory  reported usage                              compile  compile_output text
  hold      comma list of indexes that stay "processing" until release() is called
"""
import base64
import json
import uuid

import httpx


def b64(s):
    return base64.b64encode(s.encode()).decode() if s is not None else None


def unb64(s):
    return base64.b64decode(s).decode() if s else ""


class FakeJudge:
    def __init__(self):
        self.subs = {}
        self.create_mode = None   # None | int status | "disconnect" | "badjson" | "notoken" | "short"
        self.get_mode = None
        self.creates = 0
        self.gets = 0
        self.get_fields = []
        self.created_items = []

    def release(self):
        for s in self.subs.values():
            s["held"] = False

    def _fail(self, mode):
        if mode == "disconnect":
            raise httpx.ConnectError("boom")
        if mode == "badjson":
            return httpx.Response(200, content=b"<html>not json")
        if isinstance(mode, int):
            return httpx.Response(mode, json={"error": "fake"})
        return None

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            self.creates += 1
            if self.create_mode not in (None, "notoken", "short"):
                return self._fail(self.create_mode)
            items = json.loads(request.content)["submissions"]
            self.created_items.extend(items)
            out = []
            for idx, it in enumerate(items):
                d = self._directives(unb64(it["source_code"]))
                statuses = [int(x) for x in d.get("status", "3").split(",")]
                stdin, expected = unb64(it.get("stdin")), unb64(it.get("expected_output"))
                so = d.get("stdout", "")
                stdout = stdin if so == "echo" else expected if so == "expected" else so
                tok = str(uuid.uuid4())
                self.subs[tok] = {
                    "status_id": statuses[min(idx, len(statuses) - 1)], "time": d.get("time", "0.010"),
                    "memory": int(d.get("memory", "1000")), "stdout": stdout, "stderr": d.get("stderr", ""),
                    "compile_output": d.get("compile", ""), "message": "",
                    "held": str(idx) in d.get("hold", "").split(","),
                }
                out.append({"token": tok})
            if self.create_mode == "notoken":
                out[-1] = {"error": "language_id is invalid"}
            if self.create_mode == "short":
                out = out[:-1]
            return httpx.Response(201, json=out)
        self.gets += 1
        self.get_fields.append(request.url.params.get("fields", ""))
        if self.get_mode is not None:
            return self._fail(self.get_mode)
        fields = request.url.params["fields"].split(",")
        res = []
        for tok in request.url.params["tokens"].split(","):
            s = self.subs.get(tok)
            if s is None:
                res.append(None)
                continue
            full = {"token": tok, "status_id": 2 if s["held"] else s["status_id"], "time": s["time"],
                    "memory": s["memory"], "stdout": b64(s["stdout"]), "stderr": b64(s["stderr"]),
                    "compile_output": b64(s["compile_output"]), "message": b64(s["message"])}
            res.append({k: v for k, v in full.items() if k in fields})
        return httpx.Response(200, json={"submissions": res})

    @staticmethod
    def _directives(source):
        for line in source.splitlines():
            if line.startswith("#FAKE"):
                return dict(kv.split("=", 1) for kv in line[5:].split())
        return {}
