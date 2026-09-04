# 综合项目文件

每个项目使用一个 UTF-8 YAML 或 JSON 文件，文件名必须等于项目 `id`，至少关联两个知识点、一个代码或 Debug 练习，并使用确定性验证结果与可复现 Rubric 验收。

普通计算机项目使用 `scenario_scope: none`、`scenario_provider: none` 和空的 `business_context_objectives`。财经管理背景只能使用 `scenario_scope: post_course_finance_practice`，数据必须是公开、合成或经授权脱敏数据；使用 `scenario_provider: tuoling` 时必须在同一项目记录中提供 `fixed_synthetic` 降级来源。固定合成场景及驼灵降级来源必须引用来源类型、授权依据、数据分类三项均标记为 `synthetic` 的来源记录。

评价核心始终是程序设计、算法、数据处理和调试能力，不能用业务包装替代计算机学习目标。
