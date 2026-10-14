"""Local read-only knowledge base web server."""

import argparse
import json
import os
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from keyring.errors import KeyringError

from demo_agent import KnowledgeTools, SAMPLE_DIR, run_agent
from knowledge_agent import (
    build_grounded_response,
    get_model_api_key,
    load_model_config,
    read_markdown_directory,
)

WEB_DIR = Path(__file__).with_name("web")


def model_credentials():
    config = load_model_config()
    key = os.environ.get("KNOWLEDGE_AGENT_API_KEY") or get_model_api_key(
        config["credential_name"]
    )
    return config, key


def create_handler(root: Path, client_factory=None):
    tools = KnowledgeTools(root)
    documents = {
        str(document["path"]): str(document["content"])
        for document in read_markdown_directory(root)
    }
    counts = Counter(str(chunk["path"]) for chunk in tools.chunks)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB_DIR), **kwargs)

        def log_message(self, format, *args):
            # URLs and questions may contain private document names or user input.
            pass

        def send_json(self, value, status=200):
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def fail(self, status, message):
            self.send_json({"error": message}, status)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/api/status":
                try:
                    model_credentials()
                    ready = True
                except (RuntimeError, ValueError, OSError, ImportError, KeyringError):
                    ready = False
                self.send_json({
                    "name": root.name,
                    "documents": len(documents),
                    "chunks": len(tools.chunks),
                    "model_ready": ready,
                })
            elif url.path == "/api/documents":
                self.send_json([
                    {"path": path, "chunks": counts[path]}
                    for path in documents
                ])
            elif url.path == "/api/document":
                paths = parse_qs(url.query).get("path", [])
                if len(paths) != 1 or paths[0] not in documents:
                    self.fail(404, "Document not found")
                else:
                    self.send_json({"path": paths[0], "content": documents[paths[0]]})
            elif url.path.startswith("/api/"):
                self.fail(404, "Endpoint not found")
            else:
                super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path != "/api/ask":
                self.fail(404, "Endpoint not found")
                return
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                self.fail(403, "Cross-origin requests are not allowed")
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                self.fail(415, "Expected application/json")
                return
            try:
                size = int(self.headers.get("Content-Length", ""))
                if not 0 < size <= 65536:
                    raise ValueError
                request = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeDecodeError):
                self.fail(400, "Invalid JSON request")
                return
            if (
                not isinstance(request, dict)
                or not isinstance(request.get("question"), str)
                or not request["question"].strip()
                or request.get("mode") not in ("search", "answer")
                or type(request.get("allow_remote")) is not bool
            ):
                self.fail(400, "Expected question, mode, and allow_remote")
                return
            question = request["question"].strip()
            if len(question) > 4000:
                self.fail(400, "Question is too long")
                return
            if request["mode"] == "search":
                sources = [
                    tools.read(str(item["path"]), int(item["chunk_id"]))
                    for item in tools.search(question)
                ]
                self.send_json({
                    "answer": build_grounded_response(question, sources),
                    "sources": sources,
                    "mode": "search",
                })
                return
            if not request["allow_remote"]:
                self.fail(403, "Remote model use requires explicit permission")
                return
            try:
                config, key = model_credentials()
            except (RuntimeError, ValueError, OSError, ImportError, KeyringError):
                self.fail(503, "Model credential or configuration unavailable")
                return
            try:
                if client_factory is None:
                    from openai import OpenAI

                    client = OpenAI(
                        api_key=key,
                        base_url=config["base_url"],
                        timeout=30,
                        max_retries=0,
                    )
                else:
                    client = client_factory(config, key)
                read_sources = {}
                searchable = set()

                class TrackingTools:
                    def search(self, query):
                        results = tools.search(query)
                        searchable.update(
                            (item["path"], item["chunk_id"]) for item in results
                        )
                        return results

                    def read(self, path, chunk_id):
                        if (path, chunk_id) not in searchable:
                            return {"error": "Search for this excerpt before reading it"}
                        source = tools.read(path, chunk_id)
                        if "error" not in source:
                            read_sources[(path, chunk_id)] = source
                        return source

                answer = run_agent(question, TrackingTools(), client, config["model"])
            except Exception:
                # Provider errors can contain credentials or private document text.
                self.fail(502, "Model request failed")
                return
            self.send_json({
                "answer": f"模型生成，请核对下方来源：\n{answer}",
                "sources": list(read_sources.values()),
                "mode": "answer",
            })

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Local knowledge base web interface")
    parser.add_argument("--docs", type=Path, default=SAMPLE_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    handler = create_handler(args.docs.resolve())
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Listening on http://{args.host}:{server.server_port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
