# 课程包统一标准

## 1. 目标与适用范围

C、Python、数据结构三门课程由不同成员建设，但平台只维护一套读取、检索、测评、代码验证和画像更新逻辑。所有课程必须使用本标准和 `course_packs/_template/`，差异只能通过课程数据与受控执行配置表达，不得复制页面、API、智能体或验证器。

本标准冻结三周 MVP 的课程数据契约。它定义课程内容怎样存储和关联，不实现 RAG 入库、代码执行、自动评分、来源法律审查或课程事实审核。

## 2. 唯一目录结构

```text
course_packs/<course_id>/
  manifest.yaml
  concepts/<ID>.yaml|json
  exercises/<ID>.yaml|json
  projects/<ID>.yaml|json
  sources/<ID>.yaml|json
  sources/<可选正文>.md|txt
  handoff.yaml                 # 交接阶段添加；published 时必需
```

课程 ID 固定为 `c`、`python`、`data_structures`。四个内容目录不可改名。`_template/` 中的 `*.example.yaml` 仅作示例，不是正式内容；复制后必须改成与真实 `id` 完全一致的文件名。

## 3. 全局字段、ID 与状态规则

- `schema_version` 当前固定为字符串 `"0.1.0"`；公共字段变化必须先修改模板、校验器、测试和本文档；
- 正式记录使用 UTF-8 YAML 或 JSON，每个文件根节点只能是一条映射记录；
- 记录 `version` 为正整数，内容发生实质变化时递增；
- 文件名必须等于 `<id>.yaml`、`<id>.yml` 或 `<id>.json`；
- ID 只能使用大写字母、数字和连字符，并在全仓唯一；
- 知识点、练习、项目使用 `C-*`、`PY-*`、`DS-*`；来源使用 `SRC-C-*`、`SRC-PY-*`、`SRC-DS-*`；
- 内容状态只允许 `draft`、`reviewed`；`reviewed` 内容不能引用 `draft` 内容；
- 未列出的顶层字段会被拒绝。确有课程专用补充信息时只能放入可选 `extensions` 映射，并先确认没有影响公共消费者；
- 所有引用必须指向同一课程包内真实存在且类型正确的 ID；三门课程不得通过私下约定新增字段。

## 4. manifest.yaml

三个课程包使用完全相同的 manifest 结构：

```yaml
schema_version: "0.1.0"
course:
  id: python
  title: Python程序设计
  status: scaffold
  target_core_concepts: 40
  implemented_core_concepts: 0
content:
  concepts_dir: concepts
  exercises_dir: exercises
  projects_dir: projects
  sources_dir: sources
features:
  rag_qa: planned
  adaptive_practice: planned
  debug_tasks: planned
  comprehensive_project: planned
review:
  content_owner: unassigned
  last_reviewed_at: null
```

课程状态只允许：

| 状态 | 含义 |
|---|---|
| `scaffold` | 空骨架，不得包含正式记录 |
| `draft` | 负责人正在按冻结格式建设内容 |
| `review` | 内容进入人工审核，必须填写负责人和 ISO 8601 审核时间 |
| `published` | 已满足本节发布门禁，可供后续模块正式消费 |

`target_core_concepts` 只能为 30—50，首期统一目标为 40；`implemented_core_concepts` 必须等于 `concepts/` 中的记录文件数。功能状态只允许 `planned`、`in_progress`、`ready`、`disabled`。

课程标为 `published` 时，校验器额外要求：

- 知识点数量达到 `target_core_concepts`；
- 所有正式记录均为 `reviewed`；
- 代码题或 Debug 题至少覆盖 8 个不同知识点；
- 至少有一个综合项目；
- 存在通过审核的 `handoff.yaml`。

发布门禁不等于 RAG 已入库或全部外部服务可用；这些状态由对应集成 Issue 单独验收。

## 5. 知识点 Schema

知识点完整示例见 `_template/concepts/PY-FUNC-01.example.yaml`。必填字段：

```yaml
id: PY-FUNC-01
title: 函数定义与调用
course: python
schema_version: "0.1.0"
version: 1
difficulty: beginner
estimated_minutes: 30
prerequisites: []
learning_objectives:
  - 能定义带参数和返回值的函数
concepts: [参数, 返回值, 作用域]
lesson:
  summary: 使用函数封装可复用逻辑。
assessment_ids: [PY-FUNC-01-Q1]
source_refs: [SRC-PY-OUTLINE-01]
status: draft
```

规则：

- `difficulty` 只允许 `beginner`、`intermediate`、`advanced`；
- `estimated_minutes` 为正整数；
- `prerequisites` 可为空，但不得自引用、悬空或形成环；
- `learning_objectives`、`concepts`、`assessment_ids`、`source_refs` 均不得为空；
- `assessment_ids` 必须指向真实练习，`source_refs` 必须指向已登记来源；
- `lesson.summary` 必填；可选 `key_points`、`examples`、`common_mistakes` 字符串列表；
- 学习目标使用可观察、可测量的动词；机器只能检查结构，目标质量仍由负责人审核。

## 6. 练习 Schema 与确定性判定

所有练习公共字段如下，完整客观题和代码题见 `_template/exercises/`：

```yaml
id: PY-FUNC-01-Q1
title: 识别函数返回值
course: python
schema_version: "0.1.0"
version: 1
type: objective
difficulty: beginner
estimated_minutes: 5
concept_ids: [PY-FUNC-01]
prompt: 请选择正确答案。
source_refs: [SRC-PY-OUTLINE-01]
evaluation: {}
status: draft
```

`type` 仅允许四种：

| 类型 | `evaluation.mode` | 必要判定信息 |
|---|---|---|
| `objective` | `exact` | 至少两个 `options`；`accepted_answers` 只能引用选项 ID |
| `short_answer` | `rubric` | `max_score` 与非空 `rubric`；各项分值之和必须相等 |
| `code` | `tests` | 运行环境、资源限制、至少一个公开测试和一个隐藏测试 |
| `debug` | `tests` | 与代码题相同，另需非空 `starter_code` |

代码题和 Debug 题的 `runtime` 固定包含：

```yaml
runtime:
  language: python       # 仅 c 或 python
  version: "3.11"
  entrypoint: main.py
  time_limit_ms: 2000
  memory_limit_mb: 128
  output_limit_kb: 64
  network_access: false
  filesystem_access: isolated
```

为保证三门课程能由同一验证器稳定复现，运行时字段采用统一硬约束：

- `language: c` 时 `version` 必须为 `C17`，入口必须是当前目录内的单个 `.c` 文件；
- `language: python` 时 `version` 必须为 `3.11`，入口必须是当前目录内的单个 `.py` 文件；
- C 语言课程只能声明 `c`，Python 课程只能声明 `python`，数据结构课程可按题目实现选择 `c` 或 `python`；
- `entrypoint` 只能是普通文件名，不允许绝对路径、子目录或 `..`；
- `time_limit_ms` 范围为 100—10000，`memory_limit_mb` 范围为 16—512，`output_limit_kb` 范围为 1—1024；
- `network_access` 必须为 `false`，`filesystem_access` 必须为 `isolated`。

每个测试包含 `id`、`visibility`、`input`、`expected_output`，`visibility` 仅允许 `public`、`hidden`。隐藏测试只能供后端验证器使用，不得通过 API、前端、RAG 文本或模型提示泄露。课程包只声明确定性判定事实；真正的隔离执行、限时限资源和诊断脱敏由 `PRACTICE-*` Issue 实现。模型可以解释测试结果，但不能改变是否通过。

### 6.1 中文初学者讲练适配字段

面向中文初学者的练习可在 `extensions` 中声明统一的教学脚手架。该映射不保存答案，也不能替代 `evaluation.tests` 的确定性判定：

```yaml
extensions:
  learning_stage: after_class       # diagnostic / in_class / after_class / challenge
  audience: chinese_beginner
  scaffolding:
    - 先识别输入包含几个值
    - 再完成类型转换
    - 最后核对输出格式
  input_format: 一行两个空格分隔的整数。
  output_format: 输出两个整数的和。
  constraints: [不得拼接字符串]
  public_examples:
    - input: "3 5\n"
      expected_output: "8\n"
      explanation: 3 与 5 均转换为整数后相加。
  reflection_prompt: input().split() 后为什么仍需 int()？
  source_adaptation:
    source_id: SRC-PY-EXERCISM-TRACK
    source_scope: concept basics / practice input-output
    method: 保留能力目标与边界测试思路，使用中文重写题面、提示、样例和测试。
```

- `after_class` 练习必须由至少一个知识点的 `assessment_ids` 引用，形成“知识卡—练习”的可追踪关系；
- `scaffolding` 按从启发到具体的顺序提供，不直接给出完整答案；
- `public_examples` 用于帮助初学者理解输入输出，不能包含隐藏测试；
- `reflection_prompt` 用于提交后复盘错因，不影响自动评分；
- `source_adaptation` 必须指向同课程已登记来源，并说明借鉴范围和重写方法；不得复制许可不明、非商业限制或未授权题面。

## 7. 来源 Schema 与 RAG 边界

完整示例见 `_template/sources/SRC-PY-OUTLINE-01.example.yaml`。必填字段：

```yaml
id: SRC-PY-OUTLINE-01
title: Python课程函数教学提要
course: python
schema_version: "0.1.0"
version: 1
source_type: synthetic
citation:
  locator: 课程组自编函数章节提要
rights:
  basis: synthetic
  note: 课程组自行编写，可用于教学与检索演示。
data_classification: synthetic
rag:
  eligible: false
  content:
    mode: inline
    text: 函数用于封装可复用逻辑。
status: draft
```

规则：

- `source_type` 只允许 `course_outline`、`textbook`、`official_documentation`、`open_resource`、`authorized_case`、`synthetic`；
- `citation.locator` 必填，URL 如存在必须使用 HTTP(S)；
- `rights.basis` 只允许 `open_license`、`authorized`、`synthetic`，并通过 `rights.note` 记录可核对的使用依据；
- `data_classification` 只允许 `public`、`authorized_desensitized`、`synthetic`；合成来源必须标记 `synthetic`，授权脱敏资料必须具有 `authorized` 使用依据；
- `rag.content.mode` 只允许 `inline`、`file`、`reference_only`；
- `inline` 提供非空 `text`；`file` 只能指向当前课程 `sources/` 内已存在的 `.md` 或 `.txt`；`reference_only` 必须设置 `rag.eligible: false`；
- 只有 `reviewed` 来源可以设置 `rag.eligible: true`；草稿来源即使带有正文也不得进入 RAG；
- 来源记录不得保存真实个人信息、密钥、未授权资料或未经脱敏业务数据。

ARCH-02 不定义 `chunk_id`、分块、向量、embedding 或索引字段。`RAG-01` 只读取已经登记并获准使用的来源，根据此 Schema 生成索引元数据；来源不存在、不可用或检索分数不足时必须降级，不得编造答案。

校验器可以检查授权声明是否填写及字段是否自洽，不能判断声明真实性、版权法律结论或教材内容是否准确，这些仍需负责人提供证据并由成员1验收。

## 8. 综合项目与财经场景

完整示例见 `_template/projects/PY-PROJ-DATA-01.example.yaml`。项目至少关联两个知识点，并包含：

- 公共头字段、`difficulty`、`estimated_minutes`；
- `summary`、非空 `requirements`、`deliverables`；
- `concept_ids`、`source_refs`；
- 至少一个指向代码题或 Debug 题的 `verification_exercise_ids`；
- 非空 `computer_science_objectives`；
- `evaluation.mode: rubric`、`max_score` 和分项 Rubric；
- 场景范围、提供方、数据分类和业务背景目标。

普通计算机项目必须使用：

```yaml
scenario_scope: none
scenario_provider: none
business_context_objectives: []
```

当 `scenario_scope: none` 时，`business_context_objectives` 必须为空，避免把财经包装混入课程基础知识与普通练习。

财经管理背景只能出现在课后综合项目中：

```yaml
scenario_scope: post_course_finance_practice
scenario_provider: tuoling       # 或 fixed_synthetic
data_classification: authorized_desensitized
computer_science_objectives:
  - 使用Python完成数据清洗与异常处理
business_context_objectives:
  - 理解字段含义并解释结果限制
```

评价核心始终是程序设计、算法、数据处理和调试能力。驼灵只提供经授权的背景、字段解释或业务约束，不获得学生身份信息，不替学生完成代码；调用不可用时，项目必须能使用固定合成背景降级。C 指针、内存等不适配财经的基础内容不得强行包装。

当 `scenario_provider: tuoling` 时，还必须提供：

```yaml
fallback:
  mode: fixed_synthetic
  source_refs: [SRC-PY-SYNTHETIC-01]
  note: 驼灵不可用时使用固定合成背景继续完成编程任务。
```

`fixed_synthetic` 项目的数据分类必须为 `synthetic`，并至少引用一条 `source_type`、`rights.basis` 和 `data_classification` 均为 `synthetic` 的来源。驼灵降级来源同样必须在 `sources/` 登记，且三项合成声明一致并通过引用校验。

## 9. handoff.yaml

`handoff.yaml` 由课程内容通过审核后的独立 `HANDOFF-*` Issue 添加，格式见 `_template/handoff.example.yaml`。`package_revision` 必须使用 `develop@<7—40 位小写 Git 提交哈希>` 格式，填写交接前已经合入 `develop` 的课程内容提交号，不能填写占位文字或尚未产生的当前提交 SHA。

交接文件必须包含：

- 3—5 个代表性知识点、一道客观题、一道代码或 Debug 题、一个综合项目；
- 已登记来源；
- 至少 5 个黄金问题及预期来源；
- 至少 1 个依据不足问题和 1 个错误引用样例；
- 至少一个预期通过和一个预期失败的代码样例及完整确定性结果：`accepted`、`passed_tests`、`total_tests`、`diagnostics`；失败样例的 `diagnostics` 不得为空；
- 演示路径和已知限制。

数据结构课程还必须提供至少一条 `algorithm_expectations`，把算法练习与边界输入、预期复杂度、推导理由和依据来源绑定：

```yaml
algorithm_expectations:
  - id: AE-01
    exercise_id: DS-LIST-01-C1
    boundary_cases: [空输入, 单元素, 重复元素]
    expected_complexity: 时间 O(n)，额外空间 O(1)
    rationale: 每个元素只处理一次，且未创建与输入规模同阶的额外结构。
    source_refs: [SRC-DS-TEXTBOOK-01]
```

所有引用必须存在且类型正确；代码样例的 `language` 与 `total_tests` 必须分别匹配所引用练习的运行语言和测试数量；`reviewed` 交接文件只能引用 `reviewed` 内容，且黄金问题的预期来源必须已审核并标记为 `rag.eligible: true`。交接合入只代表课程事实和预期已准备好，不代表向量库已经写入；RAG 入库命令、实际提交号、成功/失败数量和黄金问题回归结果由 `RAG-01`/`RAG-ACCEPT-*` 另行记录。

## 10. 自动校验与人工验收边界

统一命令：

```powershell
python scripts/validate_course_pack.py
.\scripts\check.ps1
```

校验器自动检查：

- manifest、知识点、练习、来源、项目和交接文件的必填字段、枚举与未知字段；
- 文件名、ID 命名空间、版本、状态和全仓 ID 唯一性；
- manifest 知识点计数、固定目录和发布门禁；
- 前置关系存在且无环；
- 知识点、练习、来源、项目和交接文件的跨引用存在、类型正确；
- 已审核内容不依赖草稿；
- 客观题答案、Rubric 分值、代码运行安全声明、公开/隐藏测试结构；
- 来源授权/数据分类声明、RAG 正文路径和财经项目字段边界。

校验器明确不做：

- 不判断课程内容、算法答案、来源事实或法律授权是否真实正确；
- 不运行学生代码，不证明沙箱、隐藏测试和资源限制已实现；
- 不调用讯飞或驼灵，不执行 RAG 分块、向量化、入库或检索；
- 不自动证明 `package_revision` 已合入 `develop`；校验器会拒绝格式错误和已知占位值，真实祖先关系仍由 PR 验收人核对；
- 不自动证明 40 个知识点的教学覆盖合理；
- 不替代课程负责人自检、来源证据和成员1最终验收。

## 11. 课程负责人提交步骤

1. 等 ARCH-02 合入 `develop` 后更新本地分支；
2. 只修改自己的 `course_packs/<course_id>/**`；
3. 将 manifest 从 `scaffold` 改为 `draft`，填写 `content_owner`；
4. 每次提交的知识点必须同时带上其引用的来源和练习，不能留下悬空 ID；
5. 更新 `implemented_core_concepts`，运行统一校验和全量检查；
6. PR 记录来源证据、校验结果、已知限制和未覆盖风险，由成员1最终验收合并。

聊天附件、口头字段、未合并分支和只通过结构校验但没有来源/答案证据的内容，均不算正式交付。
