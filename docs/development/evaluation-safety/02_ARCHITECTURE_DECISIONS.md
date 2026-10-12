# Architecture Decisions

## ADR-1：分层评估

固定四层：

1. **Contract**：Pydantic schema、枚举、必填 Evidence/Uncertainty。
2. **Grounding/Safety**：Evidence key、非 NORMAL 无输出、禁止诊断/治疗词法信号。
3. **Behavior**：语言跟随、Observation/Interpretation 边界、信息不足与替代解释。
4. **Provider**：稳定性、延迟、错误率和成本；仅经授权运行。

前两层为确定性硬门禁；第三层由确定性信号与人工 Review 共同判断；第四层不得进入普通自动测试。

## ADR-2：评估数据不进入产品数据库

数据集保存在 `backend/evals/`，运行器位于 `backend/app/evaluation/`。评估不创建 Pet/Episode/AnalysisRun，不读取 `.env` 密钥，也不调用 Adapter。

## ADR-3：期待结果也是版本化契约

每个样本声明 `expected_pass` 和 `expected_error_codes`。运行器同时报告实际发现和期待匹配，避免“测试数据悄悄改变后仍显示全绿”。

## ADR-4：词法规则是预警器

诊断/治疗和语言规则只用于 Evaluation 信号，不直接替代 Prompt、Pydantic、SafetyCheck 或人工判断。任何规则更新都需要数据集案例和版本说明。

## ADR-5：真实 Provider 隔离

真实评估脚本默认不可调用网络；未来 Provider runner 必须显式开关、预算上限、单独授权、去标识化输入和不可写产品数据库。
