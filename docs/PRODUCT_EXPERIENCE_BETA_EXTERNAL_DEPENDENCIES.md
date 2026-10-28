# Relapaw 产品体验 Beta 外部依赖

| 外部项 | 当前状态 | 完成所需人工动作 |
|---|---|---|
| Resend 邮箱投递 | 本地真实闭环 VERIFIED | staging/production 域名、正式发件地址和部署配置仍需单独审批 |
| 真实 AI 供应商 | VERIFIED / QUALIFIED / DISABLED | 阿里云百炼 Qwen 北京地域固定候选 `qwen3.7-plus-2026-05-26` 的 v7 与 guidance v4 已通过并登记为可撤销运行时资格记录；另已用合成数据完成两条真实产品 API smoke。AI 保持关闭；密钥仅存本机 `backend/.env`，仓库和数据库均不含密钥或原始供应商输出。 |
| 模型资格评估 | QUALIFIED / REGISTERED / SMOKE VERIFIED | 0027 记录绑定固定端点政策、契约、知识版本及脱敏证据摘要；缺失、撤销或漂移均阻断。2026-10-26 临时启用后 facts v7 与 guidance v4 各一次成功，总请求 2、零重试，隔离库与进程已清理。后续长期启用或再次真实调用仍需新授权。 |
| 医疗安全内容 | UNABLE TO VERIFY | 执业兽医审核危险信号清单、行动措辞、版本和批准引用；未批准前 staging/production 保持失败关闭 |
| 条款与隐私 | UNABLE TO VERIFY | 法律审阅正式非草稿版本；未批准前 staging/production 保持失败关闭 |
| 提交、推送、部署 | 未授权 | 需要用户另行明确授权；当前工作区仅保留未提交实现 |

真实 AI 密钥只能存放于 `E:\Relapaw-ProductExperienceBeta\backend\.env`，不得进入聊天、日志、截图、源码、测试或文档。自动测试只使用依赖覆盖和假客户端，不发起真实付费请求。真实资格命令默认 dry-run，只有单次显式授权后才允许按冻结预算发起请求。
