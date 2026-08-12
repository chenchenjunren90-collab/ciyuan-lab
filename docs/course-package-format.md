# 课程包入库格式规范（对齐仓库标准版）

> **权威基准声明**：本规范的权威定义是仓库内 `docs/course-package-standard.md` 与 `course_packs/_template/`（manifest.yaml + concepts/README.md）。本文件是它的落地执行说明，任何不一致一律以仓库官方文档与校验脚本为准。本文件不新增目录结构，只细化"每个目录里装什么、按什么格式写、AI/RAG 岗位如何入库"。

## 这份规范解决什么问题

平台的知识问答（RAG）、课程地图、分级练习、Debug 引导都从统一格式的课程包取数。课程包由各课程负责人建设，由 AI / RAG 岗位统一入库。规范把"交什么、按什么格式交"定下来，课程负责人按此交付，入库端才能不返工、直接消费。

先读三条总原则，其余章节都是它的展开：

1. **课程包是数据，不是代码。** 一个课程包只描述"这门课有什么内容"，不包含平台逻辑；入库、验证、展示都由平台按统一格式读取。三门课程（C、Python、数据结构）由不同成员并行建设，但平台只维护一套读取、检索、测评和画像更新逻辑，所以目录与 Schema 必须完全一致。
2. **内容可追溯。** 每个知识点、每道题都要能说清来源（经授权教材 / 讲义 / 自编 / 开源），并带版本号；`source_refs` 必须指向 `sources/` 里已登记的资料。
3. **确定性优先。** 客观题带标准答案，代码题带可运行的测试用例，代码对错由沙箱编译/运行判定，不由模型猜测；模型生成的解释不得改变测试通过情况。

## 目录结构（以仓库为准）

```
course_packs/<course>/
  manifest.yaml               课程元数据、版本、状态与内容统计
  concepts/                  每个知识点一个 YAML 文件，含学习卡
  exercises/                 客观题、代码题、Debug 任务与评价规则
  projects/                  课后综合练习及其非敏感样例数据
  sources/                   经授权资料清单与片段元数据
```

课程标识统一为 `c`、`python`、`data_structures`（与目录名、`course` 字段一致）。新增公共字段时先更新 `_template/` 和校验脚本，再迁移三个课程包，禁止各课程自行加目录。

## manifest.yaml（课程清单）

以 `course_packs/_template/manifest.yaml` 为模板，课程负责人复制并填充：

```yaml
schema_version: "0.1.0"
course:
  id: data_structures            # c | python | data_structures
  title: 数据结构
  status: scaffold               # scaffold → in_progress → reviewed → released
  target_core_concepts: 40       # 首期目标，三门课程统一为 40
  implemented_core_concepts: 0   # 已实现数量，随提交更新
content:
  concepts_dir: concepts
  exercises_dir: exercises
  projects_dir: projects
  sources_dir: sources
features:
  rag_qa: planned                # RAG 问答
  adaptive_practice: planned     # 自适应练习
  debug_tasks: planned           # Debug 任务
  comprehensive_project: planned # 综合项目
review:
  content_owner: <课程负责人Gitee用户名>   # 未分配前保持 unassigned
  last_reviewed_at: null
```

## 知识点（concepts/）

每个知识点一个 YAML 文件，文件名与 `id` 一致（如 `PY-FUNC-01.yaml`）。最小字段如下（来自仓库 `_template/concepts/README.md`）：

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

硬性要求：

- **ID 全局唯一**，格式 `课程前缀-主题-序号`：`C-PTR-01`、`PY-FUNC-01`、`DS-TREE-01`。发布后不复用、不随标题变化。
- `prerequisites` 引用已存在的知识点 ID，且不得形成环。
- `learning_objectives` 使用可观察、可测量的动词（能定义、能实现、能比较…）。
- 每个知识点至少关联一个测评（`assessment_ids` 指向 `exercises/` 中的题）。
- `source_refs` 必须指向 `sources/` 中已登记的资料。
- 未经人工审核使用 `draft`，不得进入默认学习路径。

## 练习与评价（exercises/）

五种类型，判定方式如下（仓库标准第 4 节）：

| 类型 | 适用场景 | 主要判定方式 |
|---|---|---|
| 客观题 | 概念识别与基础理解 | 标准答案 / 规则 |
| 简答题 | 解释思路与比较 | 评分要点 + 模型辅助，标明非绝对判定 |
| 代码题 | 编程与算法实现 | 编译 / 运行 + 公开及隐藏测试 |
| Debug | 错误定位与修复 | 目标测试 + 错误类型标签 |
| 综合练习 | 多知识点应用 | 确定性结果 + 分项 Rubric + 人工/模型反馈 |

文件组织建议（以 `_template` 与校验脚本为准）：`exercises/` 下按题型或按知识点分文件，每个文件头部声明 `schema_version`；题 ID 沿用 `知识点ID-类型-序号`（如 `PY-FUNC-01-Q1` 为客观题、`PY-FUNC-01-C1` 为代码题）。

代码题至少定义：语言版本、入口、输入输出、时间/内存限制、公开示例、隐藏测试分类和禁止能力。Debug 题必须带"错误类型标签"，供 Debug 引导复用。

## 综合练习（projects/）

课后综合练习与综合项目放在 `projects/`。**财经管理场景只能出现在 `projects/` 或明确标记的课后综合练习中**，且必须声明以下字段（仓库标准第 6 节）：

```yaml
scenario_scope: post_course_finance_practice
scenario_provider: tuoling
data_classification: authorized_desensitized
computer_science_objectives:
  - 使用Python完成数据清洗与异常值处理
business_context_objective:
  - 理解字段含义并解释结果限制
```

规则：

- 评价核心仍是程序设计、算法、数据处理和调试能力；驼灵提供背景、字段解释或业务约束，**不替学生完成代码**。
- 不适合财经化的知识点不强行加入财经包装。
- 示例数据必须为合成、公开或经授权脱敏数据；无授权或来源不确定时使用仓库固定的合成案例。
- 本场景对应 AI/RAG 岗位的 `TUOLING-01` 适配工作：仅按 `post_course_finance_practice` 标签在课后调用，不进主课程主线。

## 资料来源（sources/）

登记经授权资料清单与片段元数据。每条资料有稳定 ID（如 `SRC-PY-TEXTBOOK-04`），含来源类型（教材/讲义/自编/开源）、标题、作者、章节、授权状态、是否脱敏。`concepts/` 的 `source_refs` 全部指向这里，**未登记的资料不得引用**。

## 首期内容深度（40 个知识点，分三层）

每门课程首期约 40 个核心知识点，分两层/三层建设：

- **全量基础层**：每个知识点具有完整元数据、学习卡、来源和至少一个测评映射。
- **重点实践层**：优先选择 8—12 个高频或高难知识点，提供代码、Debug、递进提示和高质量反馈。
- **综合应用层**：每门至少一个覆盖多个知识点的课后综合练习（财经场景在此层）。

这种分层保证三门课程都有完整结构，同时把有限时间投入最能展示学习闭环的内容。

## 验收标准（入库前核对）

1. **结构完整**：目录结构与 `manifest.yaml` 的四个 content 目录声明一致；与 `_template/` 的 Schema 完全一致；新增字段先改 `_template/` 和校验脚本。
2. **数据质量**：知识点 ≥ 40；ID 全局唯一且符合 `C-*` / `PY-*` / `DS-*` 约定；`prerequisites`、`assessment_ids`、`source_refs` 引用全部真实存在；无环。
3. **内容合规**：无未授权、未脱敏、含个人敏感信息的数据；财经场景仅在 `projects/` 且带 `scenario_scope: post_course_finance_practice` 标识；AI/RAG 与数据相关提交执行本验收条款。
4. **确定性**：代码题可编译/运行，公开与隐藏测试齐备；模型解释不影响判分。
5. **检查脚本**：通过仓库统一校验脚本。

## 交付流程

课程内容走标准 Gitee 协作流程，入库动作由 AI / RAG 岗位执行：

1. 从最新 `develop` 创建分支，命名 `content/<issue号>-<课程>`（如 `content/I8ABC3-python`）。
2. 按本规范填充课程包文件（复制 `_template/` 起步），运行仓库统一校验脚本。
3. 提交并推送，创建 PR 到 `develop`，关联对应 Issue。
4. 交叉审核：课程负责人自检后，由另一课程负责人审核结构与表达；涉及算法正确性由数据结构负责人复核；**涉及财经含义、授权与驼灵调用由 AI/RAG 与数据负责人（成员3）复核**。
5. 审核通过合入 `develop` 后，AI / RAG 岗位执行入库：分块 → 向量化 → 写入向量知识库（pgvector），完成 `RAG-01` 入库步骤，并用黄金问答集记录引用率/错误率测试结果。
