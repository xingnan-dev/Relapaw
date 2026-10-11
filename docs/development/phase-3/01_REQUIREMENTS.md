# Requirements

## 1. 长期记忆候选

1. 只有用户已明确 CONFIRMED、所属 AnalysisRun 为 COMPLETED 的 Claim 才能成为候选。
2. Claim 确认不等于进入长期记忆；用户必须另行执行 INCLUDE。
3. REJECTED、PROPOSED、FAILED、BLOCKED_BY_SAFETY 或跨宠物 Claim 不得进入候选。
4. Episode 编辑导致 AnalysisRun stale 时，候选与已纳入项必须显式 stale，不得静默保持“当前事实”。
5. 候选保存 Claim、Evidence、Uncertainty、模型和契约版本快照，不依赖可变展示文本。

## 2. 纳入、撤回与审计

1. INCLUDE/WITHDRAW 是追加式人工决定，既有事件不可覆盖或删除。
2. 撤回不修改 UserConfirmation、Claim、Episode、Observation 或 OwnerInterpretation。
3. 撤回后允许再次 INCLUDE，但历史决定和时间必须完整保留。
4. 列表必须区分 ELIGIBLE、ACTIVE、WITHDRAWN、STALE，不只依赖颜色。
5. 所有写入必须校验宠物归属、候选资格和合法状态转换。

## 3. 量化 Baseline

1. 提供 7 天、30 天、90 天和全部历史窗口；窗口以 Episode `happened_at` 和显式 `as_of` 计算。
2. v1 只使用结构化 Episode/Observation 数值：持续时间、发生次数、强度，以及具有明确 behavior_type/unit 的 measured_value。
3. 不从 Raw Input、Owner Interpretation、模型 Claim 或自然语言中猜测数值。
4. 每项指标展示样本量、最小值、最大值和中位数；不足最低样本量时显示 INSUFFICIENT_DATA，不生成趋势。
5. Episode 类型频率只报告计数和观察天数，不包装成健康、情绪或风险评分。
6. 趋势比较只有在当前窗口与对照窗口各自满足样本门槛时才生成；算法阈值必须版本化。

## 4. 重算、stale 与血缘

1. BaselineSnapshot 是可重算派生物，不覆盖人工 `PetBaseline`。
2. 每个快照保存算法版本、窗口、as_of、source fingerprint、样本量、计算状态和创建时间。
3. Evidence lineage 精确到 Episode/Observation/字段；即使源记录删除也保留最小不可变快照并将旧结果标记 stale。
4. 新增、编辑或删除相关 Episode 后，旧快照在读取时可判定 stale；重算创建新快照，不覆盖旧快照。
5. 同一 pet/window/as_of/algorithm/source fingerprint 的重算必须幂等。

## 5. UI 与安全

1. 独立展示“人工档案 Baseline”“长期记忆”“量化 Baseline”，不得混成一个事实卡片。
2. 每个派生结论可下钻查看来源、窗口、样本量、算法版本和 stale 原因。
3. SafetyCheck、VeterinaryEscalation 继续独立，不因 Baseline 或 Memory 自动变化。
4. 不输出诊断、治疗、用药、健康评分或确定性情绪标签。
5. 失败时保留页面、历史快照和人工决定；不得保存部分聚合。

## 6. 非目标

- 不接 RAG、Agent、多模态、联网搜索或长期模型记忆。
- 不调用模型生成量化指标或趋势。
- 不修改旧 migration；数据库变化使用新 revision。
- 不进行最终 UI/品牌精修或生产部署。

