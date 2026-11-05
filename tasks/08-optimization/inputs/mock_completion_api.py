"""Small OpenAI-compatible completions endpoint used only as EX267 input data."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time

MODEL = os.getenv("MODEL_NAME", "synthetic-baseline")
DELAY = float(os.getenv("RESPONSE_DELAY", "0.03"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def _json(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path in {"/", "/health", "/v1/models"}:
            self._json(200, {"object": "list", "data": [{"id": MODEL, "object": "model"}]})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/completions":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid json"})
            return
        time.sleep(DELAY)
        prompts = body.get("prompt", "")
        if not isinstance(prompts, list):
            prompts = [prompts]
        choices = []
        for index, prompt in enumerate(prompts):
            prompt = str(prompt)
            answer = prompt if body.get("echo") else " A"
            tokens = answer.split() or ["A"]
            choices.append({
                "index": index,
                "text": answer,
                "finish_reason": "stop",
                "logprobs": {
                    "tokens": tokens,
                    "token_logprobs": [-0.1 for _ in tokens],
                    "top_logprobs": [{token: -0.1} for token in tokens],
                    "text_offset": [0 for _ in tokens],
                },
            })
        self._json(200, {
            "id": f"cmpl-{MODEL}",
            "object": "text_completion",
            "model": MODEL,
            "choices": choices,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
