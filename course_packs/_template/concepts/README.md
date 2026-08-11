# 知识点文件模板

复制下面的结构到新的 `.yaml` 文件后，替换所有示例值。不要把本说明文件改名后直接当作知识点提交。

```yaml
id: PY-FUNC-01
title: 函数定义与调用
course: python
schema_version: 0.1.0
version: 1
difficulty: beginner
estimated_minutes: 30
prerequisites: []
learning_objectives:
  - 能定义带参数和返回值的函数
concepts:
  - 参数
  - 返回值
lesson:
  summary: 使用函数封装可复用逻辑，并通过参数接收输入、返回值输出结果。
assessment_ids:
  - PY-FUNC-01-Q1
source_refs:
  - SRC-PY-TEXTBOOK-04
status: draft
```

课程与知识点 ID 前缀固定为：C语言使用 `c`/`C-`，Python使用 `python`/`PY-`，数据结构使用 `data_structures`/`DS-`。`prerequisites` 可以为空；其余列表不得为空。前置知识点必须已存在于同一课程包中，且不能形成循环依赖。
