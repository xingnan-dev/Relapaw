# Phase 1 Codex Coding Prompt

以下 Prompt 用于启动 Phase 1 编码。执行者必须先读取 Phase 0/0.1 基线和本目录前三份文档；文档中的复选框不是完成声明，只有测试与人工验收后才能勾选。

## 启动 Prompt

```text
你现在负责继续开发 Relapaw 项目。

正式且唯一的项目目录：
E:\Relapaw

当前进入：
Phase 1：无 AI 的结构化记录闭环

开始前必须完整读取：
- docs/PRODUCT_CORE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/UX_ARCHITECTURE.md
- docs/EVIDENCE_ARCHITECTURE.md
- docs/development/phase-0.1/README.md
- docs/development/phase-1/README.md
- docs/development/phase-1/01_REQUIREMENTS.md
- docs/development/phase-1/02_ARCHITECTURE_DECISIONS.md
- docs/development/phase-1/03_SCOPE_ACCEPTANCE.md

不可违反的产品边界：
1. Observation ≠ Interpretation。原始输入、客观观察、主人解释必须分层保存和展示。
2. Phase 1 禁止接入 LLM、RAG、Agent、多模态识别、自动情绪判断或医疗诊断。
3. Safety Check 只能是人工显式输入；高风险选择进入 Veterinary Escalation，不输出诊断。
4. Follow-up 必须是引用原 Episode 的新记录，不能覆盖原始内容。
5. AI 结果不存在于本阶段，也不能写入长期记忆或 Baseline。
6. 数据库变更必须新增 Alembic revision，不得修改 20261007_0001，也不得恢复运行时 create_all。
7. 不得 push；Git commit 只能在人工验收并明确授权后建立。

执行顺序：
A. 先审计现有模型、schema、route、service、测试和前端状态，不直接编码。
B. 输出实现切片、模型变化、API 契约和风险；与 Phase 1 文档不一致时先更新决策记录。
C. 按垂直切片实现：
   1) 数据模型、迁移与事务型组合创建
   2) Timeline 详情、筛选、编辑和删除
   3) 人工 Safety Check 与 Veterinary Escalation
   4) Follow-up 预约与完成
   5) Observation Plan 项目和 Episode 关联
   6) 最小 EvidenceReference
   7) 前端完整闭环与可访问性
D. 每个切片先写或更新测试，再实现，再运行相关测试。
E. 完成后运行完整后端测试、前端测试、前端 build 和迁移升级/降级验证。
F. 将真实过程写入本 Phase 的实现日志、测试结果、AI Code Review、修复回归和验收文件。

完成定义：
- docs/development/phase-1/03_SCOPE_ACCEPTANCE.md 中自动化可验证项有证据支撑；
- 人工验收项保持未完成，直到用户实际验收；
- 工作区仅包含本阶段相关修改；
- 不提交、不 push，等待用户验收授权。

现在先完成步骤 A，并给出具体实施计划与发现；不要在审计完成前大规模修改代码。
```
