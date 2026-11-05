import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


TOKEN = os.environ["TOOL_TOKEN"]
TODOS = []


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            return self.send_json(200, {"status": "ok"})
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self.send_json(403, {"error": "service identity rejected"})

        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "add_todo",
                        "description": "Add one todo item",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"title": {"type": "string"}},
                            "required": ["title"],
                        },
                    },
                    {
                        "name": "list_todos",
                        "description": "List todo items",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if name == "add_todo" and arguments.get("title"):
                TODOS.append(arguments["title"])
                result = {"content": [{"type": "text", "text": f"added: {TODOS[-1]}"}]}
            elif name == "list_todos":
                result = {"content": [{"type": "text", "text": json.dumps(TODOS)}]}
            else:
                return self.send_json(
                    400,
                    {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "invalid tool call"}},
                )
        else:
            return self.send_json(
                400,
                {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}},
            )

        self.send_json(200, {"jsonrpc": "2.0", "id": request_id, "result": result})

    def log_message(self, format, *args):
        print(f"tool-service {self.address_string()} {format % args}", flush=True)


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
