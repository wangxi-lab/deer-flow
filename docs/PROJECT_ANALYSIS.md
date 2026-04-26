# DeerFlow 2.x 项目分析

## 1. 项目定位

DeerFlow 2.x 是一个基于 LangGraph 的通用智能体运行框架，目标不是单一的“聊天机器人”，而是一个可以编排模型、工具、子代理、技能、记忆和隔离执行环境的 super agent harness。

从代码和文档来看，这个仓库的核心价值主要在三层：

- 智能体运行时：围绕 `lead_agent` 组织模型调用、工具调用、子任务委派和中间件链。
- 基础设施层：提供 sandbox、线程级文件隔离、上传文件处理、MCP 集成、持久化记忆等能力。
- 产品层：通过 Gateway API、Next.js 前端和 Nginx 反向代理，形成一个可直接运行的 Web 应用。

`README.md` 也明确说明，`2.0` 是一次完全重写，与 `1.x` 不共享代码；如果要找旧版 Deep Research / 旧版 RAG 架构，需要看 `main-1.x` 分支，而不是当前主线。

## 2. 顶层目录结构

仓库主要由这几个部分组成：

- `backend/`
  - Python 后端，包含 LangGraph 运行时、FastAPI Gateway、配置系统、工具系统、sandbox、skills、memory 等核心逻辑。
- `frontend/`
  - Next.js 16 + React 19 的前端 Web 界面。
- `scripts/`
  - 本地开发、Docker、部署、检查、配置相关脚本，是 `make dev` / `make install` / `make doctor` 这些命令的实际执行入口。
- `skills/`
  - 系统可加载的技能目录，包含 `public` 和 `custom`。
- `docs/`
  - 项目文档和部分设计说明。
- `docker/`
  - Docker 开发与部署相关资源。
- `config.example.yaml`
  - 完整配置模板，是理解项目能力边界的最好入口之一。

## 3. 运行架构

本地开发和 Docker 开发都围绕 4 个进程展开：

- `Frontend`：Next.js，默认 `3000`
- `Gateway API`：FastAPI，默认 `8001`
- `LangGraph Server`：默认 `2024`
- `Nginx`：统一反向代理，默认 `2026`

请求路由大致是：

- `/api/langgraph/*` -> LangGraph Server
- `/api/*` -> Gateway API
- `/` -> Frontend

所以用户最终访问的通常是 `http://localhost:2026`，而不是直接访问 `3000` 或 `8001`。

项目根目录 `Makefile` 把这些流程统一包装掉了：

- `make setup`：交互式初始化
- `make doctor`：检查环境和配置
- `make install`：安装前后端依赖
- `make dev`：本地热更新开发模式
- `make docker-start`：Docker 开发模式
- `make up`：偏生产化的 Docker 部署

## 4. 后端架构

### 4.1 包结构

后端采用 workspace 形式：

- `backend/pyproject.toml`
  - 顶层应用包，主要负责 FastAPI、IM bridge、LangGraph SDK 等集成。
- `backend/packages/harness/pyproject.toml`
  - 真正的核心框架包 `deerflow-harness`，绝大多数运行时能力都在这里。

也就是说，`backend/app/...` 更像“应用层”，`backend/packages/harness/deerflow/...` 更像“框架层”。

### 4.2 Agent 运行时

当前主智能体入口是：

- `backend/langgraph.json`
- `backend/packages/harness/deerflow/agents/__init__.py`
- `backend/packages/harness/deerflow/agents/lead_agent/`

核心工厂函数是 `make_lead_agent(...)`。从代码和文档可以看出，`lead_agent` 负责：

- 读取模型配置
- 组装工具集
- 注入系统提示词
- 挂接中间件链
- 在需要时触发子代理

### 4.3 中间件链

DeerFlow 的一个关键设计点是中间件化。典型职责包括：

- 线程目录初始化
- 上传文件上下文注入
- sandbox 获取与回收
- 长上下文摘要
- Todo / plan 模式
- 自动生成标题
- 记忆抽取
- 图片查看
- 澄清请求中断

这意味着系统很多能力不是散落在工具函数里，而是通过 runtime middleware 统一插入到 agent 生命周期中。

### 4.4 工具系统

工具来源主要有四类：

- sandbox 工具
  - `bash`、`ls`、`read_file`、`write_file`、`str_replace`
- 内建工具
  - 例如 `task`、`view_image`、`ask_clarification`
- community 工具
  - 如搜索、抓取等第三方能力
- MCP 工具
  - 通过 Model Context Protocol 接入外部服务器

工具系统的扩展性很强，这也是 DeerFlow 2.x 最适合继续演化的切入点之一。

### 4.5 Sandbox

Sandbox 设计是这个项目的另一条主线。

当前主要有两种 provider：

- `LocalSandboxProvider`
  - 本地文件系统映射，适合开发环境
- `AioSandboxProvider`
  - 容器隔离，适合更安全的执行环境

线程级目录通常会被映射为：

- `workspace`
- `uploads`
- `outputs`

这让每个会话都拥有相对独立的文件上下文，也支撑了“上传文件后问答”和“生成产物文件”这类能力。

### 4.6 Gateway API

Gateway 是前端真正依赖的应用层 API，当前大致覆盖：

- 模型列表
- MCP 配置
- Skills 管理
- Memory 读取和刷新
- 文件上传
- 线程清理
- Artifact 访问
- Agents 管理
- Runs / Suggestions / Channels 等

当前我们本地还新增了一组 RAG 相关路由，见后文第 8 节。

## 5. 前端架构

前端使用：

- Next.js 16
- React 19
- Tailwind CSS 4
- TanStack Query
- LangGraph SDK

整体风格是比较标准的现代应用架构：

- `src/app/`
  - 路由页面
- `src/components/`
  - UI 组件和 workspace 组件
- `src/core/`
  - 业务逻辑，包括 API、messages、models、settings、threads、skills 等

目前前端承担的职责主要是：

- 聊天工作区交互
- 线程管理
- 设置管理
- 上传文件展示
- 对后端能力做轻量配置和状态展示

前端不是单纯的“壳”，而是有自己的一套 settings / thread context / API adapter 体系。

## 6. 配置系统

项目使用根目录 `config.yaml` 作为主配置入口，`.env` 主要存放敏感信息。

配置系统的特点：

- 支持多模型并存
- 支持 thinking / vision / responses API 等模型特性
- 支持切换 sandbox provider
- 支持 skills、memory、MCP、agents API 等开关
- 当前已经支持一部分热加载，改配置后不一定总要完全重启代码

实际开发时，最重要的两个文件是：

- `config.example.yaml`
- `config.yaml`

如果要理解系统“理论上支持什么”，看 `config.example.yaml` 最直接。

## 7. 当前版本的“文件问答”与 RAG 现状

### 7.1 当前 2.x 已经支持什么

当前主线已经稳定支持“上传文件后基于文件问答”：

- 前端上传文件到线程
- Gateway 存储并管理上传物
- `UploadsMiddleware` 把文件信息注入上下文
- agent 在运行时调用 `read_file` / `grep` / `glob` 这类工具读取文件内容回答

所以从用户体验看，它已经具备一种“轻量知识问答”的能力，但本质更接近 file-grounded QA，而不是传统向量检索式 RAG。

### 7.2 1.x 与 2.x 的差异

代码历史表明：

- `1.x` 有完整的 RAG 模块、provider 配置、API 和前端设置页
- `2.x` 重写后没有把这套架构迁进来

也就是说，当前 2.x 的核心能力不是“原生标准 RAG”，而是“线程文件 + 工具读取”。

这也是为什么你会在一些 demo 文件里看到 `RAGFlow`、`Qdrant`、`Milvus` 等描述，但当前主线运行时代码里又找不到对应实现。

## 8. 当前本地分支新增的 RAGFlow 骨架

结合当前 2.x 架构，我们已经在本地工作区里落了一版新的 RAG 骨架，走的是“provider 插件化 + Gateway 暴露 + 前端线程级资源选择”的路线。

### 8.1 后端新增内容

新增的主要模块包括：

- `backend/packages/harness/deerflow/config/rag_config.py`
- `backend/packages/harness/deerflow/rag/`
- `backend/packages/harness/deerflow/rag/providers/ragflow.py`
- `backend/packages/harness/deerflow/tools/builtins/local_search_tool.py`
- `backend/app/gateway/routers/rag.py`

目前后端已经支持：

- `GET /api/rag/config`
- `GET /api/rag/health`
- `GET /api/rag/resources`
- `POST /api/rag/retrieve`

并且 `local_search_tool` 已经可以把线程上下文里选中的 `rag_resource_ids` 作为默认检索范围。

### 8.2 前端新增内容

前端新增了一个最小可用的知识库选择入口，核心代码在：

- `frontend/src/core/rag/`
- `frontend/src/components/workspace/input-box.tsx`
- `frontend/src/core/settings/*`

当前交互设计是：

- 如果 `rag.enabled: true`，输入框工具栏显示“知识库”菜单
- 资源选择按线程保存
- 发送消息时把 `rag_resource_ids` 一起传给后端

### 8.3 当前限制

这版是“骨架可用”，还不是完整产品化 RAG：

- 还没有文档 chunking / embedding / rerank 这一套内建链路
- 目前优先对接外部 provider，首选 `RAGFlow`
- 如果 `cloud.ragflow.io` 账号拿不到 API key，整条链路就无法真正接通
- 前端还没有把检索来源做成回答中的 citation 卡片

换句话说，当前分支已经具备“接外部 RAG 服务”的基本框架，但还没有达到完全开箱即用的程度。

## 9. 项目优点

从代码组织和产品方向看，这个项目有几个明显优点：

- 架构分层比较清楚
  - Gateway、Harness、Frontend、Scripts 的边界明确。
- 工具扩展能力强
  - 很适合继续接 MCP、外部搜索、外部知识库。
- 线程级文件隔离做得扎实
  - 对 agent 产品非常关键。
- 中间件设计合理
  - 很多横切能力可插拔。
- 本地开发体验较完整
  - `make` 命令、Nginx 统一入口、Docker / local 双路径都比较完整。

## 10. 当前痛点和风险点

### 10.1 Windows 开发体验存在摩擦

虽然项目支持 Windows 本地开发，但脚本和依赖链明显更偏 Linux / macOS 习惯。我们本地已经遇到并修复过：

- Git Bash 下端口探测失效
- LangGraph 本地开发的 blocking 限制导致接口 500
- YAML front-matter 在技能文档中触发解析错误

说明这套开发链在 Windows 上不是完全无摩擦的。

### 10.2 配置能力强，但复杂度也高

`config.example.yaml` 很强大，但体量也很大。对新接手的人来说：

- 不容易快速判断哪些配置是必须的
- 不容易区分“当前主线可用”与“历史能力/预留能力”
- 某些功能打开后是否生效，还依赖具体运行时和端口进程状态

### 10.3 2.x 功能重写后仍有认知断层

仓库文档、demo 素材、历史分支能力之间有一定错位：

- 一部分内容在讲 1.x 的历史能力
- 运行时代码是 2.x 的新架构
- 用户很容易误以为“文档提到的 RAG 现在就一定能用”

这会带来认知成本。

### 10.4 RAG 仍处于早期接回阶段

如果项目后续要把知识库问答做成一条核心产品线，当前还有不少工作：

- provider 能力补齐
- 更稳定的资源选择与权限模型
- 前端引用展示
- 更完善的测试覆盖
- 云端托管场景下的 API key / dataset 管理体验

## 11. 适合的后续演进方向

如果从“当前仓库最值得继续投入的方向”来看，我会优先建议：

1. 把 RAG 做成正式能力
   - 先完成 `RAGFlow` 接入闭环，再考虑 `Qdrant`
2. 补强 Windows 和本地开发稳定性
   - 减少脚本环境差异带来的问题
3. 收敛配置和产品认知
   - 把“当前 2.x 真正支持什么”写得更明确
4. 增强前端可观测性
   - 例如来源引用、工具调用状态、线程资源范围展示

## 12. 总结

DeerFlow 2.x 已经不是一个单点功能项目，而是一套较完整的智能体应用底座。

它当前最成熟的部分是：

- agent runtime
- middleware / tools / sandbox
- 线程文件工作流
- 前后端联动的本地开发体验

它当前最值得继续建设的部分是：

- 标准化 RAG
- 更清晰的配置与产品边界
- 更稳定的跨平台开发体验

如果把它看成一个“可扩展的 agent operating layer”，这个项目是很有潜力的；如果把它看成一个“已经产品化完成的知识库问答系统”，那现在还差几步。
