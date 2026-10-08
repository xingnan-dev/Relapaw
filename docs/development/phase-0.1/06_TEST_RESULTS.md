# Test Results

验证日期：2026-10-07

## Backend

```text
collected 12 items
tests\test_episodes.py ....
tests\test_pets.py ...
tests\test_resources.py .....
12 passed, 1 warning in 0.34s
```

warning 为 FastAPI TestClient/Starlette 上游弃用提示，按约束未为消除 warning 修改业务代码。

## Alembic

```text
Running upgrade  -> 20261007_0001, Initial Relapaw Phase 0.1 schema.
20261007_0001 (head)
No new upgrade operations detected.
```

验证使用独立 SQLite 数据库，未改写现有开发数据。

## Frontend

```text
Test Files  1 passed (1)
Tests       15 passed (15)
Duration    1.89s
```

## Build

```text
26 modules transformed
CSS 5.87 kB (gzip 2.05 kB)
JS 236.64 kB (gzip 74.51 kB)
built in 143ms
```
