# Architecture Decisions

1. 使用 Alembic 代替运行时 `create_all()`，SQLite 当前可运行，未来通过 URL 与迁移脚本切 PostgreSQL。
2. 受控状态使用稳定字符串枚举，避免数据库原生枚举带来的早期迁移负担。
3. API 错误统一为 `error.code/message/details`。
4. Timeline 采用 `page/page_size`，以时间和 ID 双字段稳定倒序。
5. 外部 datetime 拒绝 naive 值并归一 UTC；SQLite 限制写入架构文档。
6. Current Pet 使用轻量 React Context + localStorage，不引入大型状态库。
7. App Shell 当前不引入 React Router；入口状态和四个一级 Tab 足够简单，减少依赖。详情层级增加后重新评估。
8. VeterinaryEscalation 和 ObservationPlan 只有人工 CRUD，不实现自动执行或医学规则。
