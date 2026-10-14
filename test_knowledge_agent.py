from pathlib import Path

from knowledge_agent import (
    NOTES_ROOT,
    chunk_documents,
    build_answer_context,
    build_grounded_response,
    build_model_payload,
    redact_sensitive_data,
    get_model_api_key,
    load_model_config,
    read_markdown_directory,
    search_documents,
)


def main() -> None:
    documents = read_markdown_directory(Path(NOTES_ROOT))
    assert documents, "Expected Markdown documents"

    chunks = chunk_documents(documents)
    assert chunks, "Expected document chunks"
    assert {"path", "chunk_id", "start", "end", "content"} <= chunks[0].keys()

    matches = search_documents(chunks, ["Agent"])
    assert matches, "Expected at least one Agent match"
    assert str(matches[0]["path"]) in build_answer_context("Agent", matches)
    assert "已确认" in build_grounded_response("Agent", matches[:1])
    assert "无法确认" in build_grounded_response("未知", [])
    payload = build_model_payload("Agent", matches[:1])
    assert payload["question"] == "Agent"
    assert str(matches[0]["path"]) in payload["evidence"]
    assert "instructions" in payload
    config = load_model_config()
    assert config["model"]
    assert config["base_url"]
    assert config["credential_name"]
    redacted = redact_sensitive_data("phone 13800138000 id 110101199001011234")
    assert "13800138000" not in redacted
    assert "110101199001011234" not in redacted
    try:
        get_model_api_key("missing-test-credential")
    except RuntimeError as error:
        assert "missing-test-credential" in str(error)
    else:
        raise AssertionError("Missing API key should raise RuntimeError")

    no_matches = search_documents(chunks, ["不存在的测试词"])
    assert no_matches == [], "Expected no matches for unknown keyword"

    print("All fixed tests passed")


if __name__ == "__main__":
    main()
