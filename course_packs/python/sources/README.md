# Python 课程来源清单说明

来源统一登记在 `sources/sources.yaml`，每个来源至少包含：

- `source_id`：全局唯一，概念文件通过 `source_refs` 引用；
- `title` / `type` / `url` / `license`：来源标识与许可；
- `data_classification`：数据分级（D0 公开 / D1 项目授权 / D2 受限 / D3 禁止）；
- `authorization_status`：`authorized` 或 `pending`。

## 当前已登记来源

| source_id | 类型 | 分级 | 状态 |
|---|---|---|---|
| SRC-PY-OFFICIAL-TUTORIAL | 官方教程 | D0 | authorized |
| SRC-PY-OFFICIAL-REF | 官方库参考 | D0 | authorized |
| SRC-PY-SYNTHETIC | 合成数据 | D0 | authorized |

## 提交前必须完成

1. **补充课程指定教材（D1）**：将实际使用的授权教材登记为新的 `source_id`（如
   `SRC-PY-TEXTBOOK-XX`），并把 `authorization_status` 置为 `authorized` 后，再在相关概念的
   `source_refs` 中引用。**未获授权前不要把教材内容或页码写入来源清单。**

2. **逐条核验 `source_refs`**：当前校验脚本只能检查字段是否存在，不会确认 `source_refs`
   指向的来源文件确实登记。请人工核对每个概念文件的 `source_refs` 都能在 `sources/sources.yaml`
   中找到对应条目。

3. **财经数据脱敏**：综合练习使用的 `sales_sample.csv` 为项目合成数据（无真实主体）。
   如需接入真实或授权数据，必须完成脱敏并确认授权后再替换，且不得提交任何真实主体信息。
