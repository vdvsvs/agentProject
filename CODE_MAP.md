# 代码功能索引

从使用入口开始找代码；下表记录当前实际职责，文件改名或职责变化时同步更新。

| 功能部分 | 文件 | 主要职责 |
| --- | --- | --- |
| 网页工作台 | `web/index.html`、`web/app.css`、`web/app.js` | 浏览文档、选择检索或模型回答、确认远端许可、查看来源与高亮原文。 |
| 本地接口与静态服务 | `web_server.py` | 加载指定目录、提供网页和只读 HTTP 接口、执行检索或受限模型工具循环。 |
| 网页接口集成测试 | `test_web_server.py` | 用本地 HTTP 服务和模拟模型检查请求校验、文档范围、远端许可与实际来源。 |
| 演示入口与工具调用 | `demo_agent.py` | 命令行参数、问题关键词、`search` / `read` 工具、模型工具循环、来源核对及远端发送许可。 |
| 文档处理与模型能力 | `knowledge_agent.py` | 读取 Markdown、切分和检索、构造证据内容、敏感内容遮盖、模型配置与凭据读取；文件末尾还保留早期本地 Vault 练习入口。 |
| 模型凭据配置 | `configure_credential.py`、`model_config.json` | 将 API Key 写入 Windows Credential Manager；JSON 仅保存模型地址、名称及凭据名称。 |
| 虚构演示数据 | `sample_docs/*.md` | 账号、请假、报销、支持四类示例制度；默认演示仅读取这个目录。 |
| 可复现评测 | `eval_demo.py` | 用样例数据核对 Top-3 来源命中及无答案误匹配；不评测模型回答质量。 |
| 演示离线测试 | `test_demo_agent.py` | 用模拟模型检查检索、工具参数、来源、路径限制和轮次上限；无需真实 API。 |
| 早期本地练习及测试 | `evaluate_search.py`、`test_knowledge_agent.py` | 使用 `knowledge_agent.py` 的本机 Vault 目录，依赖当地文件，不能当作独立环境可复现的演示测试。 |
| 项目说明与部署 | `README.md`、`requirements.txt`、`Dockerfile`、`.dockerignore` | 本地或 Docker 启动方式、使用边界、Python 依赖与容器构建范围。 |
| 背景、协作与历史 | `PROJECT_CONTEXT.md`、`AGENTS.md`、`CHANGELOG.md`、`CODE_MAP.md`、`.gitignore` | 项目目标与现状、Agent 工作约定、变更记录、功能索引和提交排除规则。 |

主流程：`web_server.py` 复用 `demo_agent.py` 的检索工具和模型循环，调用 `knowledge_agent.py` 读取、切分与检索文档；`web/` 调用本地接口，显示检索证据或模型输出，并打开来源原文。命令行入口 `demo_agent.py` 仍可独立使用。
