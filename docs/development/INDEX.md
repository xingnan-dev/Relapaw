# AI Coding Development Record

本目录是比赛材料与工程审计记录，不是宣传性总结。记录必须能够区分 AI 输出、人工决策、实际代码修改、原始测试结果和 Git 历史。

## 每个 Phase 的标准材料

```text
01_REQUIREMENTS.md
02_ARCHITECTURE_DECISIONS.md
03_SCOPE_ACCEPTANCE.md
04_PROMPTS.md
05_IMPLEMENTATION_LOG.md
06_TEST_RESULTS.md
07_AI_CODE_REVIEW.md
08_FIX_AND_REGRESSION.md
09_ACCEPTANCE.md
```

## 记录规则

- 只记录真实发生的过程；历史资料不足时明确标记“重建”，不得伪造逐步记录。
- Prompt 保存用户目标、约束和关键迭代，可做隐私脱敏，但不能改变原意。
- 记录 AI 工具名称、用途、人工采纳/拒绝的理由、修改文件和测试原始摘要。
- 每轮验收关联 Git commit；提交只能在人工明确授权后进行。
- 禁止保存密钥、令牌、个人数据、临时附件绝对路径和无关环境信息。
- AI Review 与实现记录分开，Review 发现、修复和回归形成闭环。

## 当前记录

- [Phase 0（历史重建）](phase-0/README.md)
- [Phase 0.1（当前可验证记录）](phase-0.1/README.md)
- [Phase 1（无 AI 的结构化记录闭环）](phase-1/README.md)
