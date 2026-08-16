# Admissions Assistant 微信小程序

可运行的毕业项目复现版：微信小程序前端 + FastAPI REST API + SQLite/SQLAlchemy/Alembic + DeepSeek + BM25/BGE/Graph RAG + Agent 工具路由 + 多轮历史持久化。

> `knowledge/` 中的 Markdown 文件全部是演示数据，不代表任何学校的真实政策。替换资料后，重启后端即可重新加载并切分文档。

## Windows 快速启动

准备：安装 Python 3.11 或 3.12，并在安装界面勾选“Add Python to PATH”。

1. 启动后端（二选一）：
   - 在 Windows 文件资源管理器中双击 `start-backend.bat`；
   - 在 VS Code 顶部选择“终端 → 新建终端”，输入 `.\start-backend.bat` 后按回车。

   注意：在 VS Code 左侧文件列表中双击只会打开脚本进行编辑，不会运行脚本。首次运行会自动创建环境、安装依赖、迁移数据库并导入演示知识，可能需要几分钟。
2. 浏览器打开 `http://127.0.0.1:8001/docs`，可先在网页里测试 API。
3. 打开微信开发者工具，选择“导入项目”，目录选本项目下的 `miniprogram`。
4. 本地调试需在开发者工具中关闭“校验合法域名”。真机测试时，把 `miniprogram/app.js` 中地址改为电脑局域网 IP，并确保手机和电脑同一网络。

## 启用 DeepSeek

首次启动后会生成 `.env`。用记事本打开并填写：

```env
DEEPSEEK_API_KEY=你的密钥
```

保存后重启后端。未填写密钥时系统仍可运行，会直接展示本地检索结果，便于离线演示。

## 项目结构

```text
backend/       FastAPI、数据库、检索与模型调用
alembic/       数据库迁移
knowledge/     按 admissions / faculty / policy 分类的演示 Markdown 知识库
data/          SQLite 运行时数据库（sample_knowledge.json 仅保留为旧版示例）
miniprogram/   微信小程序
```

当前版本会在启动时读取 `knowledge/`，按 Markdown 标题和段落切分为 chunks，并保留 `source`、`title`、`category` 元数据。检索同时使用 BM25、BGE 中文 embedding 与轻量知识图，再通过 RRF 融合排序。

检索结果会过滤低相关 chunks，同一文档最多提供两个章节作为回答上下文；API 的 `sources` 会按 Markdown 文件去重，因此微信小程序只显示一次精简后的文档标题。

为适配微信小程序的普通文本组件，模型被要求返回纯文本，后端也会清理常见 Markdown 标记。一次回答最多引用两份相关文档。

## Hybrid Retrieval

当前检索采用 BM25 与 `BAAI/bge-small-zh-v1.5` 中文语义 embedding，并通过 Reciprocal Rank Fusion（RRF）融合排名。模型由 FastEmbed 使用 ONNX 在本地 CPU 推理，首次启动会下载约 90 MB 的模型文件到 `data/model_cache/`，之后可离线复用。若依赖或模型下载失败，系统会自动回退到字符 n-gram 向量，避免影响基础问答。

文档向量会按模型名和 chunk 内容生成指纹并缓存到 `data/embedding_cache.json`。知识文档没有变化时，重启直接读取缓存；替换或修改 Markdown 后会自动重建。Windows 用户可双击 `evaluate-retrieval.bat` 运行六个固定问题的检索回归测试。

BM25 会过滤常见中文问句停用词并提高文档标题权重；当前 RRF 权重为 BM25 0.50、BGE 0.35、Graph 0.15，用于兼顾专有词精确命中、自然语言语义召回与实体关系召回。

## Query Router

检索前会通过软路由判断问题更偏向 `admissions`、`faculty` 或 `policy`，命中类别获得小幅排序加权，但不会硬过滤其他类别。这样可以为后续拆分 Admissions DB、Faculty DB、Policy KB 工具做好接口准备，同时保留跨类别问题的召回能力。

路由结果现已连接到三个独立知识工具：`admissions_kb`、`faculty_kb`、`policy_kb`。单一意图只调用对应工具；包含多个明确意图的问题可调用多个工具；无法分类时使用全部工具作为安全回退。工具内部继续使用 BM25 + BGE + RRF。

## Entities and retrieval logs

实体层会识别申请材料、申请状态、录取结果、奖学金、学费、国际学生、新生及专业方向，并把自然表达扩展为标准检索词。每次聊天的原问题、增强问题、路由、工具、实体和来源会写入 `retrieval_logs`，可通过本地开发接口 `/api/retrieval/logs` 检查，为后续 Graph RAG 的节点与边构建提供数据。

## Lightweight Graph RAG

启动时会在内存中构建 `文档—类别` 和 `文档—实体` 图关系。查询实体先沿图召回关联文档，再以 BM25 0.50、BGE 0.35、Graph 0.15 的权重进行 RRF 融合。`/api/graph?query=...` 可查看实体与关联文档；这是一套轻量、可解释的 Graph RAG 基线，不依赖外部图数据库。

本地启动后访问 `/debug/retrieval` 可打开 Retrieval Trace 页面，交互查看路由、工具、实体、三路分数、RRF 排名、图关联文档和最近检索日志。Trace 接口只执行检索，不调用 DeepSeek，也不会产生模型 API 费用。

## Release checklist

- `evaluate-retrieval.bat`：验证六个固定问题的检索、路由、工具、实体和 Graph RAG。
- `smoke-tests.bat`：在后端运行时验证健康状态、会话列表、404 行为和 Trace，不调用 DeepSeek。
- 开发环境可使用 `/debug/retrieval`、`/api/retrieval/trace`、`/api/retrieval/logs`、`/api/graph`。部署时设置 `APP_ENV=production` 和 `ENABLE_DEBUG_ENDPOINTS=false`。
- 部署时把 `MINIPROGRAM_ORIGIN` 改为明确的允许来源；多个来源使用英文逗号分隔。
- DeepSeek 网络、鉴权或响应异常时自动使用检索内容生成本地回退回答，返回模式为 `local_fallback`。

## 常用地址

- API 文档：`http://127.0.0.1:8001/docs`
- 健康检查：`http://127.0.0.1:8001/api/health`
- 检索可视化：`http://127.0.0.1:8001/debug/retrieval`
- 检索日志：`http://127.0.0.1:8001/api/retrieval/logs`
