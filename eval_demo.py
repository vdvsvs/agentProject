"""Fixed, offline Top-3 source-hit baseline on fictional documents."""

import sys

from demo_agent import KnowledgeTools, SAMPLE_DIR

CASES = [
    ("密码连续输错会怎样", "accounts.md"),
    ("忘记密码如何重置", "accounts.md"),
    ("重置链接有效期多久", "accounts.md"),
    ("请假提前多久提交", "leave.md"),
    ("突发病假何时补交", "leave.md"),
    ("哪里看年假余额", "leave.md"),
    ("差旅报销需要哪些材料", "expenses.md"),
    ("报销何时打款", "expenses.md"),
    ("大额采购报销需要什么", "expenses.md"),
    ("普通工单多久响应", "support.md"),
    ("安全事件该联系谁", "support.md"),
    ("支持工作时间是什么", "support.md"),
    ("公司停车费是多少", None),
    ("食堂周末是否营业", None),
    ("允许携带宠物上班吗", None),
]


def main() -> None:
    tools = KnowledgeTools(SAMPLE_DIR)
    hits = 0
    false_matches = 0
    for question, expected in CASES:
        paths = [item["path"] for item in tools.search(question, limit=3)]
        hit = expected in paths if expected else not paths
        if expected:
            hits += hit
        else:
            false_matches += bool(paths)
        print(f"{'PASS' if hit else 'FAIL'} | {question} | {paths}")
    print(f"Top-3 source hits: {hits}/12; no-answer false matches: {false_matches}/3")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
