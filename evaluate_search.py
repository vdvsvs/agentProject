import sys

from knowledge_agent import NOTES_ROOT, chunk_documents, read_markdown_directory, search_documents


CASES = [
    {
        "question": "Agent 项目 评测",
        "keywords": ["Agent", "项目", "评测"],
        "expected_path": "AI Agent 开发学习",
    },
    {
        "question": "火星殖民计划",
        "keywords": ["火星殖民计划"],
        "expected_path": None,
    },
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    chunks = chunk_documents(read_markdown_directory(NOTES_ROOT))
    passed = 0

    for case in CASES:
        results = search_documents(chunks, case["keywords"])
        paths = [str(result["path"]) for result in results]
        if case["expected_path"] is None:
            ok = not results
        else:
            ok = any(case["expected_path"] in path for path in paths)

        status = "PASS" if ok else "FAIL"
        print(f"{status} | {case['question']} | results={len(results)}")
        passed += ok

    print(f"Passed: {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()
