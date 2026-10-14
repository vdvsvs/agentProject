from pathlib import Path
import json
import re
import sys


VAULT = Path("E:/Obsidian Vault")
NOTES_ROOT = VAULT / "学习计划"
CHUNK_SIZE = 1000
MODEL_CONFIG_PATH = Path(__file__).with_name("model_config.json")


def load_model_config(path: Path = MODEL_CONFIG_PATH) -> dict[str, str]:
    config = {
        "model": "gpt-5-mini",
        "base_url": "https://api.openai.com/v1",
        "credential_name": "knowledge-agent-api-key",
    }
    if path.exists():
        config.update(json.loads(path.read_text(encoding="utf-8")))
    for key in ("model", "base_url", "credential_name"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"Invalid model config value: {key}")
    return config


def read_markdown_directory(root: Path) -> list[dict[str, str | int]]:
    documents = []

    for path in sorted(root.rglob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
            documents.append(
                {
                    "path": str(path.relative_to(root)),
                    "content": content,
                    "length": len(content),
                }
            )
        except (OSError, UnicodeError) as error:
            print(f"Read failed: {path} - {error}", file=sys.stderr)

    return documents


def search_documents(
    documents: list[dict[str, str | int]],
    keywords: list[str],
    limit: int | None = None,
    min_score: int = 1,
) -> list[dict[str, str | int]]:
    results = []

    for document in documents:
        content = str(document["content"]).lower()
        title = Path(str(document["path"])).stem.lower()
        score = sum(
            2 if keyword.lower() in title else 1 if keyword.lower() in content else 0
            for keyword in keywords
        )
        if score >= min_score:
            results.append({**document, "score": score})

    results = sorted(results, key=lambda document: document["score"], reverse=True)
    return results if limit is None else results[:limit]


def chunk_documents(
    documents: list[dict[str, str | int]], chunk_size: int = CHUNK_SIZE
) -> list[dict[str, str | int]]:
    chunks = []

    for document in documents:
        content = str(document["content"])
        chunk_id = 1
        start = 0
        for paragraph in content.split("\n\n"):
            paragraph_start = content.find(paragraph, start)
            if not paragraph:
                start += 2
                continue

            for offset in range(0, len(paragraph), chunk_size):
                text = paragraph[offset : offset + chunk_size]
                chunks.append(
                    {
                        "path": document["path"],
                        "chunk_id": chunk_id,
                        "start": paragraph_start + offset,
                        "end": paragraph_start + offset + len(text) - 1,
                        "content": text,
                    }
                )
                chunk_id += 1

            start = paragraph_start + len(paragraph) + 2

    return chunks


def format_evidence_report(
    question: str, results: list[dict[str, str | int]]
) -> str:
    lines = [f"Question: {question}", "Evidence:"]
    for index, result in enumerate(results, start=1):
        content = str(result["content"]).replace("\n", " ").strip()
        lines.extend(
            [
                f"{index}. {result['path']} | chunk {result['chunk_id']} | "
                f"chars {result['start']}-{result['end']} | "
                f"score {result['score']}",
                f"   {content[:240]}",
            ]
        )
    return "\n".join(lines)


def build_answer_context(
    question: str, results: list[dict[str, str | int]]
) -> str:
    evidence = format_evidence_report(question, results)
    return (
        "Answer only from the evidence below. If the evidence is insufficient, "
        "say that the current knowledge base does not provide enough support.\n\n"
        f"{evidence}"
    )


def build_grounded_response(
    question: str, results: list[dict[str, str | int]]
) -> str:
    if not results:
        return (
            f"问题：{question}\n"
            "已确认：当前知识库没有找到足够相关的依据。\n"
            "无法确认：没有可引用的片段。"
        )

    evidence_lines = []
    for result in results:
        content = str(result["content"]).replace("\n", " ").strip()
        evidence_lines.append(
            f"- {result['path']}，chunk {result['chunk_id']}，"
            f"chars {result['start']}-{result['end']}：{content[:240]}"
        )

    return (
        f"问题：{question}\n"
        "已确认：以下片段与问题匹配，可作为回答依据。\n"
        "无法确认：仅凭当前检索结果，不能推出未出现在片段中的结论。\n"
        "来源：\n"
        + "\n".join(evidence_lines)
    )


def build_model_payload(
    question: str, results: list[dict[str, str | int]]
) -> dict[str, str]:
    evidence = "\n".join(
        f"[{result['path']} | chunk {result['chunk_id']} | "
        f"chars {result['start']}-{result['end']}]\n"
        f"{redact_sensitive_data(str(result['content']))}"
        for result in results
    )
    return {
        "question": question,
        "instructions": (
            "Answer only from the supplied evidence. "
            "If evidence is insufficient, say so."
        ),
        "evidence": evidence,
    }


def redact_sensitive_data(text: str) -> str:
    text = re.sub(r"(?<!\d)(1[3-9]\d{9})(?!\d)", "[PHONE REDACTED]", text)
    return re.sub(r"(?<!\d)(\d{17}[\dXx])(?!\d)", "[ID REDACTED]", text)


def get_model_api_key(credential_name: str) -> str:
    import keyring

    api_key = (keyring.get_password("knowledge-agent", credential_name) or "").strip()
    if not api_key:
        raise RuntimeError(f"Credential is not configured: {credential_name}")
    return api_key


def generate_answer(question: str, results: list[dict[str, str | int]]) -> str:
    from openai import OpenAI

    config = load_model_config()
    client_options = {
        "api_key": get_model_api_key(config["credential_name"]),
        "base_url": config["base_url"],
    }
    client = OpenAI(**client_options)
    payload = build_model_payload(question, results)
    response = client.responses.create(
        model=config["model"],
        input=(
            f"{payload['instructions']}\n\n"
            f"Question: {payload['question']}\n\n"
            f"Evidence:\n{payload['evidence']}"
        ),
    )
    return response.output_text


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    documents = read_markdown_directory(NOTES_ROOT)
    print(f"Total files: {len(documents)}")
    chunks = chunk_documents(documents)
    print(f"Total chunks: {len(chunks)}")
    if chunks:
        first_chunk = chunks[0]
        print(
            f"First chunk: {first_chunk['path']} | "
            f"chunk {first_chunk['chunk_id']} | "
            f"chars {first_chunk['start']}-{first_chunk['end']}"
        )
    question = input("请输入关键词（用空格分隔）：").strip()
    keywords = question.split()
    if not keywords:
        print("No keywords provided")
        raise SystemExit(0)

    results = search_documents(chunks, keywords, limit=5, min_score=2)
    print(f"Search keywords: {', '.join(keywords)}")
    if not results:
        print(f"No evidence found for: {question}")
        raise SystemExit(0)

    print(format_evidence_report(question, results[:5]))
    if "--answer" in sys.argv:
        print("\nAnswer:")
        print(generate_answer(question, results[:5]))
