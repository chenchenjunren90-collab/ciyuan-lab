# 练习文件

每道练习使用一个 UTF-8 YAML 或 JSON 文件，文件名必须等于练习 `id`。公共字段见同目录示例；`type` 仅允许 `objective`、`short_answer`、`code`、`debug`。

- 客观题使用 `evaluation.mode: exact`，正确答案只能引用已有选项；
- 简答题使用 `evaluation.mode: rubric`，分项之和必须等于 `max_score`；
- 代码题和 Debug 题使用 `evaluation.mode: tests`，必须同时提供公开与隐藏测试；
- C 课程只能使用 `c`/`C17` 和单个 `.c` 入口，Python 课程只能使用 `python`/`3.11` 和单个 `.py` 入口，数据结构课程可选择上述任一固定环境；入口不得包含目录、`..` 或控制字符；
- 时间限制为 100—10000 ms、内存限制为 16—512 MB、输出限制为 1—1024 KB；
- 代码执行声明必须关闭网络并使用隔离文件系统；Schema 只描述要求，真正执行由代码验证模块完成；
- `concept_ids` 和 `source_refs` 必须引用本课程包中已经存在的记录。

复制 `*.example.yaml` 时须改为真实 ID 文件名，保留全部必填字段并替换示例内容与占位引用。
