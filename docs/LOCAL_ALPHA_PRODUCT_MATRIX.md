# Relapaw 本地产品 Alpha 功能矩阵

更新日期：2026-10-22
目标分支：`local-product-alpha`
起点：`ec991aefc8c980a667f51039e9a55e64a34678fc`

本文件是本地长期使用 Alpha 的执行矩阵。证据状态只有：`VERIFIED`、`INFERRED`、`UNABLE TO VERIFY`。已有 API 或静态展示不等于前后端闭环。

## 不可破坏门禁

| 门禁 | 当前证据 | 状态 |
|---|---|---|
| Observation 与 Owner Interpretation 独立 | 独立表、Schema、API 与真实浏览器详情展示 | VERIFIED |
| Medical Safety 优先 | SafetyCheck、非 NORMAL 阻断测试与浏览器 NORMAL 持久化 | VERIFIED |
| AI 默认关闭且非核心依赖 | capabilities、demo 配置与非 AI 空库旅程 | VERIFIED |
| 原始输入不被标准化覆盖 | Episode.raw_owner_input 与 Observation 比较字段并存 | VERIFIED |
| 派生结果来源、版本、stale | Baseline、Claim 和知识引用分别保留适用的来源、版本与 stale；关系事件不是派生结论 | VERIFIED |
| 跨宠物数据隔离 | owner/pet scope 与 Episode、计划、关系、媒体等跨账户负向请求均返回 404 且不修改数据 | VERIFIED |

## 价值与依赖顺序

| 优先级 | 用户能力 | 当前状态 | 下一出口条件 |
|---:|---|---|---|
| 1 | 多宠选择、切换、状态隔离 | VERIFIED | 选择持久化；页面重挂载；提交期冻结；草稿与 API 负向隔离测试通过 |
| 2 | 宠物资料查看、编辑、归档、安全删除 | VERIFIED | 资料编辑、可逆归档、归档管理与恢复闭环；归档资源禁止日常访问 |
| 3 | 完整记录表单、受控类别、标准单位 | VERIFIED | 原始输入、Observation、Interpretation、安全确认和受控比较字段独立保存 |
| 4 | 按宠物隔离的本地草稿恢复 | VERIFIED | 按用户+宠物自动保存、恢复、丢弃、故障提示及提交竞态冻结 |
| 5 | Timeline 搜索、标签、日期、日历、详情 | VERIFIED | 独立镜头全文搜索、受控标签、快捷/自定义日期与详情导航闭环 |
| 6 | 观察计划完整生命周期 | VERIFIED | 多观察项创建/编辑、完成、取消、Episode 关联与反馈闭环 |
| 7 | Today 工作台 | VERIFIED | 到期/逾期复评、观察任务、仅引用记录的近七天变化与快捷记录统一导航 |
| 8 | 人工长期记忆 | VERIFIED | 用户原话创建/编辑、分类与状态筛选、搜索、纳入/撤回、追加式修订和决定历史；Claim 来源只读 |
| 9 | 人工与量化 Baseline | VERIFIED | 人工创建/编辑保留未知结构；量化窗口、趋势对比图、冻结来源、算法版本与 stale 完整呈现 |
| 10 | Life Event 与证据变化摘要 | VERIFIED | 创建/编辑、精确半开时间窗关联、完整计数与截断说明；摘要只引用 Episode 并明确非因果 |
| 11 | 非 AI 引导观察 | VERIFIED | 固定规则依据已加载事实的字段缺口和日期覆盖提示后续观察，不调用模型、不解释状态 |
| 12 | Owner↔Pet / Pet↔Pet 关系 | VERIFIED | Owner↔Pet 与 Pet↔Pet 多参与者、受控客观事件、主人理解分层、完整修订快照、来源与关系时间线；归档和租户隔离已覆盖 |
| 13 | 版本化安全知识与引用 | VERIFIED | 本地示例集含物种、逐条与集合审核状态、版本及来源；仅引用已记录事实；非 NORMAL 阻断；无 AI/诊断/治疗/药物路径 |
| 14 | 本地媒体记录 | VERIFIED | Episode 关联、类型/内容签名/流式大小边界、SHA-256、人工事实、缺失/损坏/删除与迁移闭环 |
| 15 | 产品整合与本地运维 | VERIFIED | 全新 E2E 数据库中的两个隔离空账户分别完成桌面/移动核心记录旅程；键盘激活、Tab 顺序、焦点、accessibility tree、移动布局、备份恢复与手册均通过 |

## 每项共同验收

每个能力必须同时具备 loading、empty、error、success、重试和持久化状态；具备前后端真实操作路径；包含跨宠物隔离、时间线血缘、派生 stale 与 Observation/Interpretation 分层检查；最后经过定向测试、全量回归和独立代码审查。

## 验证证据分级

- `VERIFIED`：后端、前端组件、类型检查与生产构建均通过；每次 Chromium 运行创建全新数据库，桌面和移动使用各自空账户，从登录、条款、首次建档、手工记录到 Timeline 详情真实运行，并验证键盘激活、自然 Tab 顺序、焦点样式、关键 Safety 状态、accessibility-tree 名称、无横向溢出及移动关键控件边界/不重叠。浏览器证据限定于这条核心记录旅程；其余功能由 API 与组件集成测试证明。
- `INFERRED`：响应式和键盘结论覆盖已选定的 1440×1000 与 Pixel 7 视口；其他尺寸依据同一 CSS 断点与语义结构推断，没有逐像素穷举。
- `UNABLE TO VERIFY`：真实屏幕阅读器语音质量、操作系统高对比度组合以及长期多进程并发压力未在当前环境验证；这些不属于本地单用户 Alpha 的 P0/P1 阻断项。

## Git 保护记录

- `post-competition` 保持在起点 commit，禁止移动或修改。
- 仓库审计发现三个既有 annotated tag；即使目标描述写“两个”，仍全部按不可修改资产保护。
- 未经明确授权不提交、不推送、不合并、不部署、不切换分支。
