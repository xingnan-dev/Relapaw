# Evidence Architecture

状态：方向冻结，尚未实现持久化模型。

## 目的

Evidence 体系让重要判断可追溯，而不是让引用看起来更权威。证据只能支持或限制一个 Claim，不能把模型推测变成 Observation。

## 建议契约

```text
EvidenceReference
- source_type: OBSERVATION | BASELINE_SNAPSHOT | EPISODE | KNOWLEDGE
- source_id
- observed_at
- recorded_at
- field_path / excerpt
- knowledge_source_id? / knowledge_version?

AnalysisRun
- id
- model_provider / model_name / model_version
- prompt_contract_version
- created_at

Claim
- analysis_run_id
- claim_type
- statement
- evidence_references[]
- uncertainties[]
- confirmation_status
- confirmed_at?
```

## 写入规则

- Raw Owner Input、Observation、OwnerInterpretation、Model Claim、User Confirmation 是不同对象。
- 模型运行记录引用 Observation；不能反向改写 Observation。
- 用户确认的是某个结果及其版本，不代表确认永久真理；后续复评追加新记录。
- 知识证据必须保留来源版本；历史个体记录不能覆盖当前 Veterinary Escalation。
- EvidenceReference 优先保存对象引用和字段路径；摘录只是展示辅助。

## 分阶段落地

- Phase 1：Observation/Episode/Baseline 的最小对象引用和审计时间。
- Phase 2：AnalysisRun、Claim、Uncertainty、UserConfirmation。
- Phase 3：BaselineSnapshot 与计算版本。
- Phase 4：KnowledgeSource、知识版本、检索运行和引用评估。
- Phase 5：媒体原件、人工确认的提取结果与模型运行引用。

所有表结构需在对应 Phase 设计评审后通过 Alembic 新 revision 引入，本文件不授权提前建表。
