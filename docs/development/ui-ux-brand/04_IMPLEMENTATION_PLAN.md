# Implementation Plan

## 固定顺序

```text
现状截图与组件盘点
→ 品牌方向与文案原则
→ Token / primitive / app shell
→ Today / Timeline / Episode
→ Understand / Memory / Baseline
→ Onboarding / Setup / Us
→ 全局状态与响应式收口
→ 截图、键盘与无障碍验收
→ AI Code Review / 修复 / 完整回归
→ 人工验收
→ commit / push 独立门禁
```

## 视觉验收矩阵

| 维度 | 固定覆盖 |
| --- | --- |
| 视口 | 360px 手机、约 720px、宽桌面 |
| 浏览器 | Chrome、Edge |
| 输入 | 鼠标、键盘、触控尺寸 |
| 动效 | 默认、reduced-motion |
| 数据 | 空、正常、长文本、长列表、错误、stale、insufficient-data |
| Safety | NORMAL、NEED_MORE_INFO、ESCALATE_TO_VET |
| AI | 未运行、运行中、失败、完成、确认、拒绝、模型未获资格 |
| Memory | eligible、active、withdrawn、stale、无快照、有来源下钻 |

## 首轮实施门禁

在用户确认本规划包前，只允许继续审计和准备视觉方向，不修改产品界面。确认后从 Slice 1 开始，每个 Slice 单独测试、Review 和人工验收。

