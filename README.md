# 企业知识库 Agent | 可复现演示

这是求职展示用的只读知识库项目。默认使用 `sample_docs/` 中的虚构企业制度，不读取 Wang 的私人笔记。模型可自行调用 `search` 和 `read` 两个工具；没有模型凭据时仍可演示证据检索并运行全部离线测试。

## 启动

需要 Python 3.11+。在本目录运行：

```powershell
python -m pip install -r requirements.txt
python demo_agent.py --question "忘记密码怎么重置"
python eval_demo.py
python test_demo_agent.py
python test_knowledge_agent.py
```

可通过 `--docs "路径"` 明确选择其他 Markdown 文档目录，工具只会读取该目录下的 `.md` 文件。`--question` 省略时会交互式提问。离线模式输出排名、文件名、片段编号和预览；它展示证据，不声称已生成答案。

## 模型驱动工具调用

首次配置时运行 `python configure_credential.py`，密钥存入当前 Windows 用户的 Credential Manager；模型地址和名称保存在 `model_config.json`。不要提交密钥或私人文档。

```powershell
python demo_agent.py --question "忘记密码怎么重置" --agent --allow-remote
```

`--agent` 必须同时指定 `--allow-remote`，因为工具返回的文档片段会发送给配置的模型服务商。对私人资料使用 `--docs` 前先确认服务商的数据政策；样例数据无需使用私有 Vault。若没有配置凭据，请使用上面的离线模式。

```text
问题 -> 模型选择 search -> 本地检索片段
     -> 模型选择 read   -> 本地核实来源
     -> 带来源回答 / 依据不足 / 达到轮次上限
```

`read` 只能按检索所得的路径与片段编号读取已加载内容，不能接受任意文件路径。工具调用最多 5 轮，文档中的命令被视为数据。代码中的提示词不是可靠的安全隔离，仍需人工核对回答是否被引用片段支持。

## 评测与边界

运行 `eval_demo.py` 会输出固定的 12 道有答案题及 3 道无答案题的逐题结果。指标定义：Top-3 来源命中数 / 12；无答案误匹配数 / 3。这个小样例只验证检索基线，不代表模型回答准确率、真实业务召回率或生产安全性。`test_demo_agent.py` 使用模拟模型验证工具调用、非法路径、无来源和轮次上限，**不代表真实 API 已在本版本测试通过**。

2026-10-14 本机实测：Top-3 来源命中 12/12，无答案误匹配 0/3；新旧两组离线测试均通过。样例文档与问题集同时设计，数字不能推广到真实企业文档。

现阶段采用中文双字片段匹配，不使用向量库、LangGraph、MCP 或 Docker。文本表达差异很大时可能漏检；面试时应展示失败案例，再决定是否引入更复杂的检索方法。已有 `knowledge_agent.py` 是早期本地 Vault 练习入口，默认绑定本机目录，不用于项目复现演示。
