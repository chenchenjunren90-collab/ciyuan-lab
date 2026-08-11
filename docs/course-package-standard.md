# 课程包统一标准

## 1. 目标

C、Python、数据结构三门课程由不同成员并行建设，但平台只能维护一套读取、检索、测评和画像更新逻辑。所有课程必须基于 `course_packs/_template/`，差异通过数据和受控执行配置表达，不复制业务代码。

## 2. 推荐结构

```text
course_packs/<course>/
  manifest.yaml              课程元数据、版本、状态与内容统计
  concepts/                  每个知识点一个YAML/JSON文件，含学习卡
  exercises/                 客观题、代码题、Debug任务与评价规则
  projects/                  课后综合练习及其非敏感样例数据
  sources/                   经授权资料清单与片段元数据
```

三门课程的目录与文件Schema必须完全一致。新增公共字段时先更新 `_template/` 和校验脚本，再迁移三个课程包。

## 3. 知识点最小字段

```yaml
id: PY-FUNC-01
title: 函数定义与调用
course: python
schema_version: 0.1.0
version: 1
difficulty: beginner
estimated_minutes: 30
prerequisites: [PY-BASE-03]
learning_objectives:
  - 能定义带参数和返回值的函数
concepts: [参数, 返回值, 作用域]
lesson:
  summary: 使用函数封装可复用逻辑，并通过参数接收输入、返回值输出结果。
assessment_ids: [PY-FUNC-01-Q1, PY-FUNC-01-C1]
source_refs: [SRC-PY-TEXTBOOK-04]
status: reviewed
```

要求：

- `id` 发布后不复用、不随标题变化；
- 前置关系不得形成环；
- 学习目标使用可观察、可测量的动词；
- 每个知识点至少关联一个测评；
- `source_refs` 必须指向已登记资料；
- 未经人工审核使用 `draft`，不得进入默认学习路径。

## 4. 练习类型与判定

| 类型 | 适用场景 | 主要判定方式 |
|---|---|---|
| 客观题 | 概念识别与基础理解 | 标准答案/规则 |
| 简答题 | 解释思路与比较 | 评分要点 + 模型辅助，标明非绝对判定 |
| 代码题 | 编程与算法实现 | 编译/运行 + 公开及隐藏测试 |
| Debug | 错误定位与修复 | 目标测试 + 错误类型标签 |
| 综合练习 | 多知识点应用 | 确定性结果 + 分项Rubric + 人工/模型反馈 |

代码题至少定义语言版本、入口、输入输出、时间/内存限制、公开示例、隐藏测试分类和禁止能力。模型生成的解释不得改变测试通过情况。

## 5. 首期内容深度

每门课程首期约40个核心知识点，分两层建设：

- **全量基础层**：每个知识点具有完整元数据、学习卡、来源和至少一个测评映射；
- **重点实践层**：优先选择8—12个高频或高难知识点，提供代码、Debug、递进提示和高质量反馈；
- **综合应用层**：每门至少一个覆盖多个知识点的课后综合练习。

这种分层保证三门课程都有完整结构，同时将有限时间投入最能展示学习闭环的内容。

## 6. 财经管理场景规则

财经场景只能出现在 `projects/` 或明确标记的课后综合练习中：

```yaml
scenario_scope: post_course_finance_practice
scenario_provider: tuoling
data_classification: authorized_desensitized
computer_science_objectives:
  - 使用Python完成数据清洗与异常值处理
business_context_objective:
  - 理解字段含义并解释结果限制
```

- 评价核心仍是程序设计、算法、数据处理和调试能力；
- 驼灵提供背景、字段解释或业务约束，不替学生完成代码；
- 不适合财经化的知识点不强行加入财经包装；
- 示例数据必须为合成、公开或经授权脱敏数据；
- 无授权或来源不确定时使用仓库固定的合成案例。

## 7. 内容审核

课程负责人自检后，由另一课程负责人审核结构与表达；涉及算法正确性由数据结构负责人复核；涉及财经含义、授权与驼灵调用由AI/RAG与数据负责人复核。所有修改保留版本和评审记录。
