# Fix and Regression

修复日期：2026-10-07

## 修复

1. 新增 `ApiError`，保留 HTTP status 和稳定错误 code；current pet 只有在 404 时清理。
2. Timeline 首次读取增加过期响应保护；加载更多增加 loading、错误反馈和重复点击保护。
3. Pet Setup 使用本地草稿恢复中断输入，创建成功后清除草稿。
4. 增加临时恢复失败保留 pet ID、Pet Setup 草稿恢复测试。
5. 根据人工截图 Review，将 App Shell 改为 Header/Main/Nav 三行视口网格；Main 独立滚动，底栏占据布局空间并支持移动端安全区，不再覆盖 Understand 表单。
6. 根据建档截图 Review，将出生日期与大约年龄改为显式填写方式选择；页面一次只显示一个年龄字段，避免互斥字段同时填写和不完整日期造成困惑。

## 回归结果

```text
Backend:  12 passed, 1 warning in 0.34s
Frontend: 1 test file passed, 15 tests passed in 1.89s
Build:    26 modules transformed, built in 143ms
Alembic:  20261007_0001 (head), no new upgrade operations detected
```

## 人工决定

- 不为上游 TestClient warning 升级或改写依赖。
- 不在本轮加入请求重试库、路由库或大型状态管理库。
- 不借 Review 提前实现 Evidence 数据表、AI、Baseline 计算或多宠关系。
