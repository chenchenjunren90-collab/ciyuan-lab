# 知识点文件

每个知识点使用一个 UTF-8 YAML 或 JSON 文件，文件名必须等于知识点 `id`。完整字段见 `PY-FUNC-01.example.yaml`。

课程与 ID 前缀固定为：C语言使用 `c`/`C-`，Python 使用 `python`/`PY-`，数据结构使用 `data_structures`/`DS-`。

- `prerequisites` 可以为空，其余列表不得为空；
- 前置知识点必须存在于同一课程包，且不能形成循环依赖；
- `assessment_ids` 必须指向 `exercises/` 中真实练习；
- `source_refs` 必须指向 `sources/` 中真实来源；
- 未完成人工审核的内容保持 `draft`；
- 复制 `*.example.yaml` 时须改为真实 ID 文件名，保留全部必填字段并替换示例内容与占位引用。
