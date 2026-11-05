import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen


LLM_URL = os.environ.get("LLM_URL", "http://mock-llm:8080")
TOOL_URL = os.environ.get("TOOL_URL", "http://todo-tool:8080")
TOOL_TOKEN = os.environ["TOOL_TOKEN"]
BLOCKED_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"reveal\s+(the\s+)?secret", re.I),
]
DOCUMENTS = {path.name: path.read_text(encoding="utf-8") for path in Path("/docs").glob("*.md")}


def post_json(url, payload, headers=None):
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def call_llm(message):
    response = post_json(
        f"{LLM_URL}/v1/chat/completions",
        {"model": "mock-llm", "messages": [{"role": "user", "content": message}]},
    )
    return response["choices"][0]["message"]["content"]


def retrieve(query):
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    ranked = []
    for name, text in DOCUMENTS.items():
        score = len(terms & set(re.findall(r"[a-z0-9]+", text.lower())))
        ranked.append((score, name, text.strip()))
    return max(ranked) if ranked else (0, "", "")


def call_tool(name, arguments):
    return post_json(
        TOOL_URL,
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
        {"Authorization": f"Bearer {TOOL_TOKEN}"},
    )["result"]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_message(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}").get("message", "")

    def do_GET(self):
        if self.path == "/healthz":
            return self.send_json(200, {"status": "ok", "documents": sorted(DOCUMENTS)})
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        message = self.read_message()
        if self.path == "/chat":
            return self.send_json(200, {"answer": call_llm(message)})

        if self.path == "/rag":
            score, source, context = retrieve(message)
            prompt = f"CONTEXT [{source}]: {context}\nQUESTION: {message}"
            return self.send_json(
                200,
                {"answer": call_llm(prompt), "sources": [source], "retrieval_score": score},
            )

        if self.path == "/agent":
            match = re.match(r"add todo\s+(.+)", message, re.I)
            if match:
                result = call_tool("add_todo", {"title": match.group(1).strip()})
            elif re.match(r"list todos?", message, re.I):
                result = call_tool("list_todos", {})
            else:
                return self.send_json(400, {"error": "no permitted tool matched"})
            return self.send_json(200, {"tool_result": result})

        if self.path == "/guarded":
            matched = next((pattern.pattern for pattern in BLOCKED_PATTERNS if pattern.search(message)), None)
            if matched:
                return self.send_json(400, {"blocked": True, "reason": "prompt policy", "pattern": matched})
            return self.send_json(200, {"blocked": False, "answer": call_llm(message)})

        self.send_json(404, {"error": "not found"})

    def log_message(self, format, *args):
        print(f"genai-app {self.address_string()} {format % args}", flush=True)


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
