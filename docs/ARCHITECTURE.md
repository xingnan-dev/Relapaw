# Relapaw Architecture — Phase 0.1

## 系统边界

```text
React UX shell -> REST /api/v1 -> FastAPI routes -> services/domain -> SQLAlchemy -> SQLite
                                                    |
                                                    +-> Alembic schema history
```

开发期使用 SQLite，数据库 URL 由 `RELAPAW_DATABASE_URL` 配置。ORM 映射与 Alembic 迁移避免依赖 SQLite 专有能力，为未来 PostgreSQL 保留边界。应用运行时不自动建表。

## 目录与职责

```text
frontend/src/
├─ components/     # Splash / Onboarding / PetSetup 等流程组件
├─ pages/          # Today / Understand / Timeline / Us
├─ state/          # 当前宠物与 onboarding 本地状态
├─ api.ts          # REST client boundary
├─ types.ts        # 前端数据契约
└─ App.tsx         # 入口状态机与四页 App Shell

backend/
├─ alembic/        # 可审计数据库迁移
└─ app/
   ├─ main.py      # 应用装配与统一错误处理
   ├─ core/        # 配置
   ├─ db/          # engine、session、declarative base
   ├─ models/      # 持久化实体
   ├─ schemas/     # Pydantic 请求/响应契约
   ├─ api/         # 版本化 HTTP 路由与依赖
   ├─ services/    # Timeline 等应用用例
   └─ domain/      # 框架无关枚举与未来领域策略
```

## Phase 0.1 工程约定

- API 错误统一为 `error.code / message / details`，避免客户端解析不稳定的字符串。
- 外部 datetime 必须带时区并在进入系统时归一到 UTC。SQLite 读取可能丢失 timezone 标记，响应层会恢复 UTC 语义；切换 PostgreSQL 后仍需集成测试确认驱动行为。
- 受控状态与来源使用字符串枚举，数据库保持可迁移的 String 存储。
- Timeline 使用 `happened_at DESC, id DESC` 稳定排序并返回页码、总数和 `has_more`。
- Observation 与 OwnerInterpretation 使用独立表、schema、端点和前端展示区，禁止合并。
- VeterinaryEscalation 仅提供人工录入结构，不包含自动医学判断。
- 当前宠物由 React Context 管理，并以本地 ID 恢复；恢复失败时回到可解释的空状态。多宠物选择器尚未实现。

## 数据库迁移

初始 revision 为 `20261007_0001`，覆盖 Phase 0/0.1 的九张业务表。标准流程：

```powershell
cd E:\Relapaw\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

任何模型变更必须配套新 revision；不得重新启用 `Base.metadata.create_all()` 作为运行时迁移方案。

## 未来 Agent / RAG 位置

未来 Understanding Agent 应作为独立应用服务接入 `services/`，输入输出使用 `schemas/understand.py` 的版本化契约。编排、追问、观察计划与复评不得写进路由或 ORM model。

未来 RAG 使用独立 knowledge/infrastructure 适配层，承载检索接口、文档版本、引用与来源元数据。兽医知识不能混入宠物长期记忆；Medical Safety 必须在行为解释之前运行并可短路后续步骤。

以上组件在 Phase 0.1 均未实现，也没有用假逻辑模拟。

## Evidence 与记忆写入边界

未来分析采用 `Claim -> EvidenceReference[] -> Uncertainty[] -> UserConfirmation` 的可追溯结构。`EvidenceReference` 至少保留来源类型、来源 ID、观察时间、记录时间和字段路径；知识证据另带知识来源及版本，模型版本属于独立分析运行记录。

```text
RawInput
  ├─ Observation                    # 人工记录或经确认的事实
  ├─ OwnerInterpretation            # 主人的理解
  └─ AnalysisRun
       ├─ Claim                     # 模型推测，不是真实事实
       ├─ EvidenceReference[]
       ├─ Uncertainty[]
       └─ UserConfirmation          # 确认后才能进入指定长期记忆层
```

Phase 1 开始建立最小证据引用；Phase 2 接入文本模型时必须通过 LLM Adapter；Phase 4 的知识检索还需记录知识来源和版本。模型输出不得直接更新 Observation 或 Baseline。

## 量化 Baseline 演进边界

Phase 1 的原始记录必须保留时间、来源、单位和上下文，为 Phase 3 可重算基线提供输入。Phase 3 使用“原始样本 + 派生快照”，快照可包含时间窗口、样本数、均值/中位数、正常范围、趋势、计算时间与算法版本。派生快照不得覆盖原始 Observation。

## 多宠关系边界

Phase 6 引入 Pet↔Pet 时应支持两个以上参与者，并将 RelationshipObservation、主人解释和模型推测分层保存。现有单个 `pet_id` Episode 不应被强行扩展成隐式多宠关系；正式设计前需决定参与者关联表与事件所有权。

## 已知演进风险

- 当前仍是本地单用户模型，OwnerProfile 尚无账户所有权。
- 多宠物场景目前默认选择已有列表中的第一只，需要显式选择器和切换审计。
- SQLite 对时区与并发约束较弱，迁移 PostgreSQL 前必须加入数据库集成测试。
- Timeline 目前以 Episode 为主，LifeEvent、计划、升级记录尚未形成统一事件投影。
- 本地存储只适合开发期入口状态，账户同步后需定义服务端真源与冲突规则。
