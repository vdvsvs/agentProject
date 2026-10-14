# 企业知识库问答

只读、本地运行的知识库问答工作台。默认使用 `sample_docs/` 中的虚构企业制度；打开网页即可搜索文档、查看原文与来源。配置模型后，可显式授权将问题及工具读取的片段发送给模型服务商并生成回答。模型回答仍需人工核对引用。

项目目标与进度见 [项目背景与现状](PROJECT_CONTEXT.md)；改动见 [变更记录](CHANGELOG.md)，代码分工见 [代码功能索引](CODE_MAP.md)。

## 本地启动

需要 Python 3.11+。在本目录运行：

```powershell
python -m pip install -r requirements.txt
python web_server.py
```

浏览器打开 `http://127.0.0.1:8000`。服务只监听本机；关闭终端服务即停止。检索、原文预览和无答案提示无需模型密钥。服务启动时加载指定目录下的 Markdown；文档更新后重启服务即可刷新。可用 `python web_server.py --docs "路径" --port 8001` 选择另一组文档和端口。向其他人演示时优先使用虚构样例；本服务没有用户身份认证，不应直接暴露到公网。

## 模型回答

Windows 本机运行 `python configure_credential.py`，将 API Key 存入当前用户的 Credential Manager；`model_config.json` 只保存模型、服务地址和凭据名称。配置完成后刷新网页，选择“模型回答”并勾选远端发送许可。没有密钥时仍可使用本地检索。模型服务调用有 30 秒超时；实际用量与费用以服务商为准。

```text
问题 -> 模型调用 search -> 本地检索片段
     -> 模型调用 read   -> 本地核实来源
     -> 模型回答 / 依据不足 / 达到轮次上限
```

授权只作用于当前请求。仅有搜索命中的元数据和读取到的片段会交给模型；模型引用仍可能不充分，应点击来源核对原文。网页展示的来源仅包含本次模型实际读取成功的片段。文档文本视为不可信数据，提示词不构成绝对的安全隔离；使用私人资料前先确认服务商的数据政策。

## Docker

在有 Docker 的机器上：

```powershell
docker build -t knowledge-workspace .
docker run --rm -p 127.0.0.1:8000:8000 knowledge-workspace
```

容器默认只含虚构样例。若要指定自己的文档，运行时将目录以只读方式挂载到 `/docs`，并在命令末尾使用 `python web_server.py --host 0.0.0.0 --docs /docs`；确保挂载路径只含准备给本地界面和所选模型查看的资料。容器中的模型凭据通过 `KNOWLEDGE_AGENT_API_KEY` 环境变量提供，切勿把密钥写进镜像、命令历史或提交到 Git；不提供密钥时可离线使用。

## 命令行与验证

原有命令行演示仍可使用：

```powershell
python demo_agent.py --question "忘记密码怎么重置"
python demo_agent.py --question "忘记密码怎么重置" --agent --allow-remote
python test_demo_agent.py
python test_knowledge_agent.py
python test_web_server.py
python eval_demo.py
```

## 评测与边界

`eval_demo.py` 包含 12 道有答案题、3 道无答案题，指标是 Top-3 来源命中数 / 12 和无答案误匹配数 / 3。样例文档与问题集同时设计，该结果不代表回答准确率、真实业务召回率或生产安全性。离线测试使用模拟模型，**不证明真实 API 在当前环境可用**；`test_knowledge_agent.py` 依赖本机早期 Vault 目录，换机器时不属于可复现验收。

2026-10-14 本机样例评测：Top-3 来源命中 12/12，无答案误匹配 0/3。当前检索使用中文双字片段和关键词匹配，遇到同义词可能漏检。向量检索、混合检索、MCP 与 LangGraph 均未实现；引入新组件前先用真实问题记录失败案例。

`knowledge_agent.py` 末尾保留早期本机 Vault 练习入口，不用于网页产品和他人复现演示。
