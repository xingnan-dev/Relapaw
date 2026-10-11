# Fix and Regression

日期：2026-10-11

| 发现 | 修复 | 回归 |
|---|---|---|
| Safety 标题与正文重复 | 正文只保留解释，标题独立表达状态 | Understanding 定向测试通过 |
| 静态提示被默认声明为 live region | StatusNotice 默认无 role，动态状态显式使用 `status`/`alert` | 新增静态 guidance 非 live region 测试 |
| 控件触控高度仅 42px | token 统一为 44px | CSS 与 build 验证 |
| 缺少统一键盘焦点 | button/form/tabindex 增加 `:focus-visible` | CSS 与人工验收待复核 |

最终自动回归：backend 76 passed、frontend 49 passed、production build、pip check、Alembic current/check 与 diff check 全部通过。
