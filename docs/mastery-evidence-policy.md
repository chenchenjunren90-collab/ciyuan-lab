# DATA-02 证据驱动画像更新规范

## 1. 边界

DATA-02 只把已经持久化、可核验的学习事件投影为掌握度，并向 `AGENT-01`
提供可解释的推荐候选数据。大模型不得直接写掌握度、修改代码测试事实或编造知识点 ID。

## 2. 事件与幂等

- 一个 `event_id` 只允许产生一条 `mastery_update_audits` 记录；重复处理返回原结果，
  不增加分数、证据数或版本号。
- 事件、画像行、掌握度与审计记录在一个数据库事务内处理。
- 同一学生同一课程的并发更新通过画像行锁串行化，避免两个首次事件同时创建掌握度时丢失更新。
- 缺少知识点、结果字段错误、测试计数矛盾或非证据事件均不更新画像。

该行为借鉴 xAPI 对相同 Statement ID 不得再次改变状态的要求，并使用 PostgreSQL
事务、唯一主键和行锁落实，而不是只在应用内做一次脆弱的“是否处理过”判断。

## 3. 当前策略 `evidence-ewma-v1`

当前没有足够的真实、授权且代表性良好的学生答题序列来拟合知识追踪模型，因此采用透明、
固定且可替换的指数加权更新：

`new_score = old_score + evidence_weight × (evidence_value - old_score)`

- 新知识点的中性先验为 `0.5`；分数限制在 `[0, 1]` 并保留四位小数。
- 基线测评：`is_correct` 为客观证据，权重 `0.45`。
- 普通练习：`accepted` 为客观证据，权重 `0.25`。
- 代码验证：`passed_tests / total_tests` 为客观证据，权重 `0.35`；如同时提供
  `accepted`，必须与是否全部通过一致。
- 每次有效事件只增加一次 `evidence_count` 和一次 `revision`。

这些权重是 MVP 的显式产品规则，不声称是统计校准后的认知参数。后续积累匿名化序列后，
可离线评估 pyBKT 等模型，再以新 `policy_version` 灰度替换；历史审计仍保留原策略版本。

## 4. 审计字段

每次有效更新记录事件 ID、知识点、更新前后分数、更新前后证据数、修订号、证据值、
证据权重、策略版本、原因码和服务端时间。原始证据仍保存在 `learning_events`，审计表不复制
诊断全文或个人信息。

## 5. 推荐数据边界

`LearnerProfileService.build_recommendation_data` 仅对调用方提供的课程知识点白名单排序：

1. 已有证据且分数低于 `0.6`：`needs_reinforcement`；
2. 无证据：`insufficient_evidence`；
3. 分数在 `[0.6, 0.8)`：`continue_practice`；
4. 分数不低于 `0.8`：`ready_to_progress`。

服务返回分数、证据数、置信度、优先级和原因码，不自行生成练习 ID。
`AGENT-01` 必须再结合课程前置关系和真实活动目录选择下一任务。

## 6. 参考实现与规范

- [ADL xAPI Specification](https://github.com/adlnet/xAPI-Spec)：Statement ID、
  不可重复改变状态与事件结果表达。
- [CAHLR pyBKT](https://github.com/CAHLR/pyBKT)：基于学生解题序列和技能字段
  拟合知识追踪参数。
- [PostgreSQL INSERT](https://www.postgresql.org/docs/current/sql-insert.html)：
  `INSERT ... ON CONFLICT`、事务与行锁语义。

本实现吸收事件不可变、序列证据和版本化策略思想；未直接引入 pyBKT 运行依赖，因为当前
数据量不足以可靠拟合 prior、learn、guess、slip 等参数。
