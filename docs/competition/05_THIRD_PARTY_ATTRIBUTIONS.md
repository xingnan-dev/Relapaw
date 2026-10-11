# 第三方来源与引用规则

状态：初始清单；Release Candidate 前必须依据锁文件和部署镜像生成最终版本。

## 当前直接依赖和官方来源

| 项目 | 用途 | 官方来源 | 许可证/说明 |
|---|---|---|---|
| React / React DOM | Web UI | https://github.com/facebook/react | MIT |
| TypeScript | 类型系统与编译 | https://github.com/microsoft/TypeScript | Apache-2.0 |
| Vite / `@vitejs/plugin-react` | 前端开发与构建 | https://github.com/vitejs/vite | MIT |
| Vitest | 前端自动测试 | https://github.com/vitest-dev/vitest | MIT |
| Testing Library | UI 行为测试 | https://github.com/testing-library/react-testing-library | MIT |
| FastAPI | REST API | https://github.com/fastapi/fastapi | MIT |
| Uvicorn | ASGI 服务 | https://github.com/encode/uvicorn | BSD-3-Clause |
| Pydantic / pydantic-settings | 输入输出与配置校验 | https://github.com/pydantic/pydantic | MIT |
| SQLAlchemy | ORM 与事务 | https://github.com/sqlalchemy/sqlalchemy | MIT |
| Alembic | 数据库迁移 | https://github.com/sqlalchemy/alembic | MIT |
| OpenAI Python SDK | Responses/Chat Completions 客户端 | https://github.com/openai/openai-python | Apache-2.0 |
| pytest | 后端自动测试 | https://github.com/pytest-dev/pytest | MIT |

版本来源以 `backend/requirements*.txt`、`backend/pyproject.toml`、`frontend/package.json` 和 `frontend/package-lock.json` 为准，不以本表替代锁定文件。

## API 与官方文档来源

- OpenAI Responses API、Structured Outputs 与 Python SDK：
  - https://developers.openai.com/api/reference/overview
  - https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
  - https://github.com/openai/openai-python
- 阿里云百炼 OpenAI 兼容接口与结构化输出：
  - https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope
  - https://help.aliyun.com/zh/model-studio/qwen-structured-output

上述文档用于确认 API 契约和 Provider 能力。Relapaw 没有把官方示例整体复制为业务实现；Adapter 代码围绕本项目的 Understanding 契约、错误映射、Safety 与事务边界独立编写。

## AI 工具来源

- OpenAI Codex：用于软件开发生命周期，详见 `01_AI_TOOLS_AND_PURPOSES.md`。
- Qwen：作为可选运行时 Provider，模型与端点由服务端环境变量配置。

AI 生成的代码仍由本项目测试、Review 和人工验收负责；“由 AI 生成”不能替代来源、许可证或质量审查。

## 引用规则

1. 复制或改编第三方代码时，在代码邻近位置或本文件记录项目、原始 URL、许可证和改动说明。
2. 只参考官方 API 文档的调用方式时，记录文档 URL，不声称复制了第三方业务代码。
3. 不复制不明许可证的博客、问答或竞赛作品代码。
4. 图片、图标、字体、音频和演示素材也必须记录作者、URL、许可证及是否修改。
5. Release Candidate 前根据生产依赖生成完整 license inventory，并核对 NOTICE/署名义务。

## 当前声明

截至 2026-10-11，仓库内未识别到直接复制的第三方业务程序片段；当前主要使用上表开源框架与官方 API 文档。该声明只覆盖已审计的 Phase 0–2，后续新增依赖和素材必须同步更新。
