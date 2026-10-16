# Relapaw Product and Engineering Roadmap

具体执行顺序与不可跳过的阶段门禁以 [项目完整执行指引](PROJECT_EXECUTION_GUIDE.md) 为准；路线调整必须先走该指引中的变更控制流程。

更新日期：2026-10-15

## 长期目标

Relapaw 是基于长期行为记录、个体基线、关系建模、证据追溯和安全边界的宠物行为理解与人宠关系 Copilot。核心原则始终是 **Observation ≠ Interpretation**，Medical Safety 始终先于行为解释。

技术路线保持为：

```text
React + TypeScript + FastAPI + Pydantic + SQLAlchemy
  -> PostgreSQL
  -> LLM Adapter
  -> RAG / vector retrieval
  -> Evaluation
```

## 阶段顺序与出口条件

| Phase | 目标 | 主要出口条件 |
|---|---|---|
| 0/0.1 | 工程、数据边界、入口与低保真 UX | Review、回归通过、开发留痕、Git 基线 |
| 1 | 无 AI 的结构化记录闭环 | 记录→观察→复评→长期记忆可人工完成；最小 EvidenceReference |
| 2 | 文本 Understanding | 经 Adapter 输出 Claim/Evidence/Uncertainty；用户逐条确认/拒绝并保留不可变审计，不自动写 Baseline 或长期记忆投影 |
| 3 | 长期记忆与量化 Baseline | 可重算时间窗口、样本量、范围和趋势；不足样本有明确状态 |
| 4 | 安全 RAG | 知识来源与版本可追溯；安全评估优先且可阻断解释 |
| 5 | 多模态 | 媒体只作为可追溯输入来源；识别结果仍需确认和评估 |
| 6 | Relationship Copilot | 人↔宠物和 Pet↔Pet 长期关系；多参与者与修订历史完整 |

每阶段进入下一阶段前必须通过证据门禁、安全门禁和记忆门禁，并完成自动测试、AI Code Review、修复、回归、人工验收与对应 Git commit。

比赛 AI Coding 要求同时作为每个阶段的持续门禁：记录 AI 工具及用途，保留可独立展示的完整交互与开发链路，把 AI 原生方法贯穿需求到交付，并即时登记第三方代码与素材来源。证据框架已经建立，但最终比赛材料、视频和来源总表仍需在比赛版本冻结前完成。

## 四项长期加强方向

1. **多宠关系**：Phase 6 重点实现 Pet↔Pet；近期只保留显式架构边界。
2. **Evidence**：Phase 1 开始建立来源、时间和对象引用；Phase 2/4 再加入模型与知识版本。
3. **量化 Baseline**：Phase 1 先保证原始记录可计算，Phase 3 建立可重算派生快照。
4. **AI Coding 留痕**：从现在起每个 Phase 保存真实需求、决策、Prompt、修改、Review、测试、验收和 Git 关联。

## 近期执行顺序

```text
Phase 0–3（已关闭）
  -> 比赛 AI Coding 证据框架（已验收）
  -> 轻量 Design System（已验收）
  -> Evaluation 与 Safety（已关闭；当前模型组合 NOT_QUALIFIED）
  -> 完整 UI/UX 与品牌精修（已完成人工验收，待授权提交）
  -> 生产部署与可观测性（下一阶段）
  -> 比赛演示数据与材料
  -> Release Candidate 总验收
  -> 比赛提交与版本冻结
  -> 赛后 Phase 4–6
```

完整 UI/UX 与品牌精修必须建立在现有信息架构、安全边界和人工决定语义之上。当前进入产品结构收口：页面职责与入口审计 → 删除重复跳转和虚假交互 → 核心业务链路与深层状态 → 响应式/无障碍/视觉回归 → AI Review 与完整回归 → 人工验收和比赛证据同步。之后才进入生产部署、比赛演示材料和 Release Candidate；不提前进行 RAG、Agent、多模态、自动医疗判断或 Pet↔Pet 数据模型。
