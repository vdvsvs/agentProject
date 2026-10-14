"""Exercise web endpoints over a real local HTTP connection."""

import json
import os
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.parse import quote
from unittest.mock import patch

from web_server import create_handler


def response(*calls, text=""):
    return SimpleNamespace(output=list(calls), output_text=text)


def call(name, args, number):
    return SimpleNamespace(
        type="function_call", name=name, arguments=json.dumps(args), call_id=str(number)
    )


class FakeClient:
    def __init__(self):
        self.responses = self
        self.queue = [
            response(call("search", {"query": "password reset"}, 1)),
            response(
                call("read", {"path": "../outside.md", "chunk_id": 1}, 2),
                call("read", {"path": "handbook.md", "chunk_id": 1}, 3),
            ),
            response(text="Use the reset form."),
        ]

    def create(self, **kwargs):
        return self.queue.pop(0)


def main():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "handbook.md").write_text(
            "Use the password reset form.", encoding="utf-8"
        )
        clients = [FakeClient()]

        def make_client(config, key):
            return clients.pop(0)

        with patch.dict(os.environ, {"KNOWLEDGE_AGENT_API_KEY": "test-key"}):
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(root, client_factory=make_client),
            )
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)

            def request(method, path, body=None, headers=None):
                connection.request(
                    method,
                    path,
                    body=json.dumps(body) if body is not None else None,
                    headers={"Content-Type": "application/json", **(headers or {})},
                )
                result = connection.getresponse()
                return result.status, json.loads(result.read())

            try:
                status, data = request("GET", "/api/status")
                assert status == 200 and data["documents"] == 1
                assert data["chunks"] == 1 and data["model_ready"]
                status, data = request("GET", "/api/documents")
                assert status == 200 and data == [{"path": "handbook.md", "chunks": 1}]
                status, data = request(
                    "GET", f"/api/document?path={quote('handbook.md')}"
                )
                assert status == 200 and data["content"] == "Use the password reset form."
                assert request("GET", "/api/document?path=../outside.md")[0] == 404
                query = {
                    "question": "password reset",
                    "mode": "search",
                    "allow_remote": False,
                }
                status, data = request("POST", "/api/ask", query)
                assert status == 200 and data["sources"][0]["path"] == "handbook.md"
                assert data["mode"] == "search"
                query["mode"] = "answer"
                assert request("POST", "/api/ask", query)[0] == 403
                query["allow_remote"] = True
                assert request(
                    "POST", "/api/ask", query, {"Origin": "https://other.example"}
                )[0] == 403
                assert request(
                    "POST", "/api/ask", query, {"Content-Type": "text/plain"}
                )[0] == 415
                status, data = request("POST", "/api/ask", query)
                assert status == 200 and data["sources"][0]["path"] == "handbook.md"
                assert len(data["sources"]) == 1 and data["mode"] == "answer"
                unauthorized = FakeClient()
                unauthorized.queue = [
                    response(call("read", {"path": "handbook.md", "chunk_id": 1}, 1)),
                    response(text="Unverified answer"),
                ]
                clients.append(unauthorized)
                status, data = request("POST", "/api/ask", query)
                assert status == 200 and data["sources"] == []
                assert "依据不足" in data["answer"]
                assert request("POST", "/api/ask", {"question": ""})[0] == 400
                print("Web API integration tests passed")
            finally:
                connection.close()
                server.shutdown()
                server.server_close()
                worker.join()


if __name__ == "__main__":
    main()
