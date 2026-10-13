# Human Review Record

## 固定复核问题

- Claim 是否聚焦记录的 Episode 行为，而非主人决定或假设？
- 是否严格区分 Observation 与 Owner Interpretation？
- 是否引入输入未记录的原因、刺激、意图、情绪或内部状态？
- 时间顺序、主体和动作是否与 Evidence 一致？
- 置信度是否符合“待确认解释”的谨慎程度？
- 输出语言是否跟随 Raw Input？

## 三轮决定

| Prompt | 自动门禁 | 人工决定 | 主要原因 |
| --- | --- | --- | --- |
| v3 | passed | rejected | Interpretation 当作支持事实；未记录原因和内部状态；报告编码问题 |
| v4 | mixed | rejected | 中文返回英文；主人假设成为 Claim；未记录原因 |
| v5 | passed | rejected | 中文时间顺序偏移和复述；英文继续引入未记录原因 |

最终决定：`NOT_QUALIFIED`。

人工决定不会改写原始 Episode，也不会被自动测试覆盖或自动升级为 `QUALIFIED`。任何资格变更必须有新的版本化样本、真实授权运行和新的人工记录。
