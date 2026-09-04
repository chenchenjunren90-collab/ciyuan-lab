# DATA-01 最小数据模型

DATA-01 只负责保存和查询事实，不决定掌握度如何变化，也不生成学习推荐。评分、
幂等画像更新和推荐依据属于 DATA-02。

## 表与边界

- `course_versions`：记录三门课程的版本、状态和 manifest 摘要；
- `learner_profiles`：使用平台内部随机 `student_id`，关联学生当前课程版本；
- `mastery_states`：保存已经由确定性规则计算出的掌握度快照、证据数和修订号；
- `learning_events`：按 `event_id` 追加学习事件，保存契约版本、事件类型、课程版本、
  证据摘要和 JSON 载荷。
- `mastery_update_audits`：由 DATA-02 增加，以 `event_id` 为主键，保存一次证据投影的
  更新前后分数、证据数、修订号、权重、策略版本、原因码和服务端时间。

仓库不保存姓名、明文学号、手机号等身份信息。演示种子只使用固定随机 ID 和合成事件。

## 本地迁移与种子数据

先通过 `infra/compose.yaml` 启动 PostgreSQL，然后配置未跟踪的 `.env`：

```powershell
python -m alembic upgrade head
python scripts/seed_demo_data.py
```

回退全部 DATA-01 表：

```powershell
python -m alembic downgrade base
```

真实 PostgreSQL 验收必须使用独立测试数据库：

```powershell
$env:CIYUAN_TEST_DATABASE_URL = "postgresql+psycopg://.../ciyuan_test"
python -m pytest apps/api/tests/test_learning_persistence.py -rs
```

测试会执行 `base → head → base → head`，证明从零迁移、读写、重复事件幂等和回退均可复现。

画像更新与推荐数据规则见
[`mastery-evidence-policy.md`](mastery-evidence-policy.md)。
