# 统一课程包模板

本目录是 C、Python、数据结构三门课程唯一的数据格式来源。正式规则以 `docs/course-package-standard.md` 和 `scripts/validate_course_pack.py` 为准。

使用方法：

1. 课程负责人等待 ARCH-02 合入 `develop`；
2. 在自己的课程目录中复制需要的 `*.example.yaml`；
3. 将内容记录改名为真实 `<ID>.yaml`；交接示例必须单独改名为课程根目录下唯一的 `handoff.yaml`，不得保留 `handoff.example.yaml`、`.yml` 或 `.json` 别名；
4. 同一个 PR 中补齐知识点引用的练习和来源；
5. 更新 manifest 的状态、负责人和知识点数量；
6. 运行 `python scripts/validate_course_pack.py` 和 `.\scripts\check.ps1`。

示例文件只展示统一形状，不构成完整课程，也不代表内容、答案、来源授权、提交号真实性或 RAG 入库已经通过审核。
