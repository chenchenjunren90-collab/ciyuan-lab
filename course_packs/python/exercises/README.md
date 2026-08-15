# Python 课程练习目录说明

> 说明：`exercises/` 的正式 Schema 尚待 `ARCH-02` 冻结。当前采用如下**临时约定**，
> 冻结后以 `course_packs/_template/` 为准迁移，不得三门课程各创一套格式。

## 目录结构

```text
exercises/
  objective/          客观题（每知识点至少一道）
  code/               代码题（含公开/隐藏测试）
  debug/              Debug 任务（含错误标签）
  fixtures/           测试夹具（如文件读取所需的样例文件）
```

## 客观题（objective/*.yaml）

```yaml
type: multiple_choice
id: PY-BASE-02-Q1
concept_id: PY-BASE-02
difficulty: beginner
question: 下列哪个是 Python 中合法的变量名？
options: [2name, student_name, class, name-1]
answer: B
explanation: 变量名不能以数字开头、不能含连字符、不能是关键字。
```

- `answer` 为选项字母（A/B/C/D），对应 `options` 的下标。
- 判定方式：标准答案/规则（确定性），不依赖模型。

## 代码题（code/*.yaml）

```yaml
type: code
language: python
id: PY-FUNC-01-C1
concept_id: PY-FUNC-01
title: 阶乘计算
function_name: factorial
signature: 'factorial(n: int) -> int'
statement: 实现函数 factorial(n)：返回 n 的阶乘（n!）。约定 0! = 1。
public_tests:
  - input: [0]
    expected: 1
hidden_tests:
  - input: [10]
    expected: 3628800
limits: {time_ms: 1000, memory_mb: 64}
hints: [...]          # 递进提示，避免直接给答案
feedback: [...]       # 反馈要点，供辅导智能体组织反馈
reference_solution: | # 参考实现，仅供课程负责人/评审使用
  def factorial(n): ...
```

- `public_tests` 展示给学生；`hidden_tests` 仅用于判定，运行器不得向学生泄露。
- `input` 为位置参数列表，`expected` 为期望返回值；判定方式为 `function_name(*input) == expected`。
- 代码正确性由编译/运行 + 测试决定（`PRACTICE-01` 的验证器），模型不得改变测试结果。

## Debug 任务（debug/*.yaml）

```yaml
type: debug
id: PY-EXC-01-D1
concept_id: PY-EXC-01
buggy_code: |
  def safe_divide(a, b):
      return a / b
description: 说明缺陷与修复目标
expected_behavior: 描述修复后的可观察行为
public_tests: [...]   # 目标测试
error_tag: missing_exception_handling
reference_solution: |
  def safe_divide(a, b): ...
```

- `error_tag` 为错误类型标签，用于诊断分类与反馈（如 `missing_exception_handling`、`resource_not_closed`）。
