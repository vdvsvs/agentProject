"""Offline checks for tool permissions and model loop behavior."""

from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

from demo_agent import KnowledgeTools, MAX_STEPS, SAMPLE_DIR, run_agent


def response(*calls, text=""):
    return SimpleNamespace(output=list(calls), output_text=text)


def call(name, args, number):
    return SimpleNamespace(
        type="function_call", name=name, arguments=args, call_id=str(number)
    )


class FakeClient:
    def __init__(self, responses):
        self.queue = list(responses)
        self.history = []
        self.responses = self

    def create(self, **kwargs):
        self.history.append(kwargs)
        return self.queue.pop(0)


def main():
    tools = KnowledgeTools(SAMPLE_DIR)
    matches = tools.search("忘记密码怎么重置")
    assert matches and matches[0]["path"] == "accounts.md"
    assert tools.read("accounts.md", 1)["content"]
    assert "error" in tools.read("../model_config.json", 1)
    assert "error" in tools.read("accounts.md", 999)
    assert tools.search("") == []

    client = FakeClient(
        [
            response(call("search", '{"query":"忘记密码"}', 1)),
            response(call("read", '{"path":"accounts.md","chunk_id":1}', 2)),
            response(text="使用公司邮箱重置。[accounts.md | chunk 1]"),
        ]
    )
    result = run_agent("怎么重置密码", tools, client, "test-model")
    assert "已读取来源：" in result and "accounts.md | chunk 1" in result
    assert all(request["store"] is False for request in client.history)
    assert any(
        item.get("type") == "function_call_output"
        for item in client.history[-1]["input"]
        if isinstance(item, dict)
    )
    no_read = FakeClient([response(text="编造的回答")])
    assert "依据不足" in run_agent("未知问题", tools, no_read, "test-model")
    invalid = FakeClient(
        [response(call("read", '{"path":"../secret","chunk_id":1}', 1)), response()]
    )
    assert "依据不足" in run_agent("越界", tools, invalid, "test-model")
    looping = FakeClient(
        [response(call("search", '{"query":"密码"}', i)) for i in range(MAX_STEPS + 1)]
    )
    assert "轮次上限" in run_agent("密码", tools, looping, "test-model")
    assert len(looping.history) == MAX_STEPS + 1
    last_step = FakeClient(
        [
            response(call("read", '{"path":"accounts.md","chunk_id":1}', i))
            for i in range(MAX_STEPS)
        ]
        + [response(text="最终回答")]
    )
    assert "最终回答" in run_agent("密码", tools, last_step, "test-model")
    with TemporaryDirectory() as directory:
        Path(directory, "note.md").write_text("public content", encoding="utf-8")
        assert KnowledgeTools(Path(directory)).search("public content")
    print("All demo tests passed")


if __name__ == "__main__":
    main()
