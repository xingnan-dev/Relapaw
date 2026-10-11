# 比赛要求矩阵

依据：用户提供的比赛要求截图。若官方完整规则或截止要求更新，必须按 `docs/PROJECT_EXECUTION_GUIDE.md` 的变更控制流程更新本矩阵。

## 当前已知要求

| 编号 | 比赛要求 | Relapaw 对应方案 | 当前证据 | 状态 |
|---|---|---|---|---|
| 1 | 参赛作品必须使用 AI Coding 工具完成开发，不限具体平台 | 使用 OpenAI Codex 覆盖需求、架构、实现、测试、Review、修复、验收和文档 | 工具清单、各 Phase 开发记录 | 已满足，需在最终材料中展示 |
| 2 | 提交时注明 AI 工具名称及具体用途 | 独立工具清单与简明声明，区分 Codex 与运行时 Provider | `01_AI_TOOLS_AND_PURPOSES.md` | 框架完成 |
| 3 | AI 自动编程工具使用流程须作为重点内容单独阐述，清晰展示交互和完整开发过程，不可只嵌在说明书中 | 独立工作流、真实交互案例、commit/证据地图；最终再制作演示章节与视频 | `02`、`03`、`06` | 文档框架完成；演示资产待制作 |
| 4 | 考虑 AI 原生软件开发方法论，AI 嵌入整个软件开发生命周期 | 定义七项原则，映射发现、设计、开发、验证、Review、体验、交付和未来运营 | `04_AI_NATIVE_METHODOLOGY.md` | 框架完成，后续阶段持续执行 |
| 5 | 引用他人程序需明确标注来源 | 建立直接依赖、官方文档、引用规则和后续素材登记要求 | `05_THIRD_PARTY_ATTRIBUTIONS.md` | 初始清单完成；RC 前做最终许可证清单 |

## 产品自身要求的比赛证据

| 主题 | 已完成证据 | 后续缺口 |
|---|---|---|
| 真实用户问题 | Observation 与 Interpretation 分离、Timeline 与 Follow-up | 比赛叙事与用户画像整理 |
| AI 差异化 | Evidence/Uncertainty/Confirmation、失败审计、Safety short-circuit | Evaluation 指标与对照案例 |
| 工程完整性 | 前后端、迁移、测试、build、Git 历史 | PostgreSQL、部署、监控和恢复演练 |
| 安全负责 | 不诊断、不治疗、非 NORMAL 不调用、密钥边界 | 版本化 Safety/Evaluation 数据集 |
| 人机协作 | 真实 REJECTED Claim 与 Prompt 迭代 | 更多语言/边界样本和统计 |
| 展示质量 | 核心路径可运行 | Design System、完整 UI 精修、Demo 视频 |

轻量 Design System 已于 2026-10-11 完成自动回归和浏览器可用性验收；完整 UI/UX 与品牌精修仍按总指引安排在 Phase 3 和 Evaluation 之后。

Phase 3 已建立 Requirements、Architecture、Scope、Acceptance 和固定实施切片；Slice 1 后端功能、migration、自动测试与人工验收已经完成，尚待 Git 门禁。Slice 2–4 不得在比赛材料中描述为已完成。

## 最终提交前门禁

- [ ] 获得并核对官方完整规则、提交格式、截止时间、文件大小和版权要求；
- [ ] AI 工具名称与具体用途在主提交材料中独立出现；
- [ ] AI Coding 工作流作为独立重点章节，不只链接开发手册；
- [ ] 至少展示一条“人类目标 → AI 实现 → 失败 → 修复 → 验收”的真实链路；
- [ ] 展示 Git commit、测试、Review、人工决定和运行界面的一致版本；
- [ ] 第三方代码、素材、字体、图标和数据来源完整；
- [ ] 不把未完成的 Phase 3–6、部署或 Evaluation 描述为已实现；
- [ ] 演示环境不含 API key、个人路径、私人窗口或真实敏感数据；
- [ ] Release Candidate 门禁全部通过并创建比赛版本标签。

## 当前结论

比赛要求已经进入固定项目顺序和日常开发流程，而不是留到最后补写。当前阶段完成的是“可持续收集证据的框架”，并不等于比赛提交材料已经完成。下一阶段只有在本阶段通过审查后，才按总指引进入轻量 Design System。

人工验收：用户于 2026-10-11 确认本阶段框架通过。该确认不代表最终比赛材料、演示资产或 Release Candidate 已完成。
