# 来源文件

每条来源使用一个 UTF-8 YAML 或 JSON 文件，文件名必须等于来源 `id`。来源 ID 必须使用课程命名空间，例如 `SRC-C-*`、`SRC-PY-*`、`SRC-DS-*`。

`rights.basis` 只允许开放许可、明确授权或合成内容；`rights.note` 必须留下可核对说明。`rag.content.mode` 有三种：

- `inline`：正文直接放在 `text`；
- `file`：`path` 只能指向本课程 `sources/` 内已存在的 `.md` 或 `.txt`；
- `reference_only`：仅作引用，必须设置 `rag.eligible: false`。

只有人工审核后的 `reviewed` 来源可以设置 `rag.eligible: true`。草稿来源可以保留正文，但不得进入 RAG。

本格式不定义分块、向量和索引字段，这些由 `RAG-01` 统一生成。
