# Batch 1 AI Code Review 与修复

日期：2026-10-17

## Review 发现 1：能力状态作用域错误

首次实现只在 Timeline 顶层读取 capabilities，却在独立 EpisodePanel 中直接引用，导致 TypeScript build 失败及详情页运行时异常。

修复：把 `aiAnalysisEnabled` 作为显式 Panel prop 传递，重新运行相关前端测试和 build。

## Review 发现 2：关闭创建仍不是只读

首次实现隐藏了“开始文本分析”，但历史 Claim 仍可确认、拒绝或建立长期记忆候选，不符合当前演示的只读边界。

修复：把 `readOnly` 传到 AnalysisRun/Claim，隐藏这些写操作并增加清晰说明；新增回归测试确认无 POST 动作入口。

## Review 发现 3：既有测试没有显式开启新能力

默认关闭是产品安全要求，但既有 Understanding 与 Memory 测试仍假设分析可用，完整回归最初出现 5 项 Memory 测试失败。

修复：只有需要验证旧 AI 行为的测试显式覆盖 `get_ai_enabled=True`，保留产品默认关闭；再次执行后端 119 项完整回归并全部通过。

## 结论

未发现未关闭的自动化阻断问题。人工浏览器验收和 commit 授权仍未完成。
## Batch 2 Review（2026-10-17）

- seed CLI 增加三重门禁：demo 环境、AI 关闭、固定 `.demo` SQLite 路径；
- 已存在的数据集不只读取 manifest，还执行数据库完整性 verify，避免损坏数据被误判为幂等成功；
- manifest 仅在数据库事务提交后原子替换；事务异常不留下部分数据；
- 录制 AnalysisRun 明确标记 `recorded-demo`，seed 路径没有 Provider 调用；
- 基线使用现有 `recompute_snapshot` 生成，未手写聚合结果。

## Batch 3 Review（2026-10-17）

- 静态挂载严格排在 API 与 health 路由之后；
- demo 模式不允许静态目录缺失或降级启动；
- 静态目录必须为绝对路径且精确匹配仓库 `frontend/dist`，避免误暴露其他目录；
- 未增加全局 SPA fallback，未知 API 保持 404；
- development 未配置静态目录时的既有行为保持不变。

## Batch 4 Review（2026-10-17）

- 修复 Windows 无权读取 `Win32_Process.CommandLine` 时合法进程被误判的问题；
- 身份校验改为 PID、可执行文件绝对路径、精确启动时间、PID 记录常量和 demo health/capability 合约组合；
- stop 对身份或健康合约不一致的进程 fail-closed；
- reset 不使用通配符或递归删除，只逐个删除固定文件名；
- 端口探测发生在 build/migration 前，未知占用者不会被停止。

## Batch 5 Final Review（2026-10-17）

- 自动主演示与 Safety 路径均使用合成数据，未调用 Provider；
- AI disabled 的 403 路径确认不创建失败 AnalysisRun；
- 日志、密钥与 Git 跟踪产物检查通过；
- 没有发现需要阻断人工视觉验收的代码问题。

人工视觉验收期间发现的两项 720px 响应式问题均已修复并复验。最终 Review 未发现剩余阻断项。
