# HANDOFF-PY · Python 课程统一交接包

> 用途：本文件是给成员2（前端）与成员3（RAG）的验收材料。默认应写入 Gitee 的
> `HANDOFF-PY` Issue；在交接包 Schema 由 `ARCH-02` 冻结前，先以本文件形式交付，
> 冻结后迁移到 `course_packs/_template/` 统一格式。

## 1. 身份

| 项目 | 值 |
|---|---|
| course_id | `python` |
| 课程包版本 | schema_version `0.1.0` |
| 内容负责人 | 成员5 |
| 审核人 | 成员4（互审，算法部分成员6） |

## 2. 展示样例（代表性知识点）

| 知识点 ID | 标题 | 用途 |
|---|---|---|
| PY-FUNC-01 | 函数定义与调用 | 知识卡样例 |
| PY-LIST-03 | 列表推导式 | 知识卡样例 |
| PY-DICT-02 | 字典遍历与常用方法 | 知识卡样例 |
| PY-FILE-03 | CSV 文件处理 | 知识卡样例 |
| PY-DATA-01 | 数据清洗基础 | 知识卡样例 |

- **一道知识卡**：`concepts/PY-FUNC-01.yaml`
- **一道客观题**：`exercises/objective/PY-DICT-01-Q1.yaml`
- **一道代码题**：`exercises/code/PY-FUNC-01-C1.yaml`（阶乘计算）
- **一道 Debug 题**：`exercises/debug/PY-EXC-01-D1.yaml`（修复除法异常处理）
- **一个综合练习**：`projects/PY-FIN-01-P1.yaml`（脱敏经营数据清洗与统计）

## 3. 前端状态（预期样例）

| 状态 | 触发场景 | 预期展示 |
|---|---|---|
| 正常 | 浏览 `PY-FUNC-01` 知识卡 | 完整元数据、目标、前置关系、来源 `source_refs` 可展开 |
| 加载 | 请求课程目录时 | 显示加载态，不闪白屏 |
| 空数据 | 知识点暂无练习 | 显示"暂无练习"，不报错 |
| 验证失败 | 提交错误的 `factorial` 代码 | 展示编译/测试失败诊断（脱敏、限长），前端不自行判定对错 |
| 模型降级 | 外部模型不可用 | 问答显示基于检索/固定内容的降级结果并明确标注 |

## 4. RAG 验收

**黄金问题及预期来源**

| # | 黄金问题 | 预期知识点 | 预期来源 |
|---|---|---|---|
| 1 | Python 中如何定义函数？ | PY-FUNC-01 | SRC-PY-OFFICIAL-TUTORIAL |
| 2 | 列表和元组有什么区别？ | PY-TUPLE-01 | SRC-PY-OFFICIAL-TUTORIAL |
| 3 | 如何用 with 语句安全打开文件？ | PY-FILE-02 | SRC-PY-OFFICIAL-TUTORIAL |
| 4 | f-string 如何格式化字符串？ | PY-STR-03 | SRC-PY-OFFICIAL-REF |
| 5 | csv 模块如何读取带表头的表格？ | PY-FILE-03 | SRC-PY-OFFICIAL-REF |
| 6 | try/except 如何捕获除零异常？ | PY-EXC-01 | SRC-PY-OFFICIAL-TUTORIAL |

**依据不足（应拒答或降级）**

- "Python 中如何实现线程安全的锁机制？" → 超出当前课程包范围，应返回依据不足并引导查看课程资料。

**错误引用样例**

- 将 `PY-FILE-03`（CSV 处理）的内容片段错误标注为 `PY-FILE-01`（文件读写基础）→ 引用校验应拦截。

## 5. 代码事实

| 场景 | 代码 | 预期 VerificationResult |
|---|---|---|
| 正确 | `factorial` 参考实现（见 code 题） | `{accepted: true, passed_tests: N, total_tests: N, diagnostics: []}` |
| 错误 | `def factorial(n): return n * factorial(n-1)`（无基线条件，递归溢出） | `{accepted: false, ...}` 诊断含超时/递归错误 |
| 错误 | `def factorial(n): return 0` | `{accepted: false, ...}` 诊断含答案错误（隐藏测试不通过） |

## 6. 演示与限制

**演示路径**：Python 课程入口 → 选择知识点 `PY-FUNC-01` → 阅读知识卡 → 完成客观题与
代码题 → 确定性代码验证 → 画像更新 → 推荐下一任务 `PY-FUNC-02`。

**当前不支持**：
- RAG 入库与检索（`RAG-01` 未实现，本包只提供来源与黄金问题）；
- 代码验证器（`PRACTICE-01` 未实现，本包只提供测试与资源要求）；
- 驼灵 API 适配（综合练习默认使用合成数据，可离线完成）。
