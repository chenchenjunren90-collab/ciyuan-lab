# 普通成员开发与提交指南

本文是除成员1·陈骏人之外的普通成员必须遵守的统一操作规则。成员只需完成一条主流程：

> 查看自己的 Issue → 更新 `develop` → 创建独立分支 → 按范围开发 → 本地检查 → 推送分支 → 创建 PR → 等待成员1验收合并。

如本文与聊天记录、个人笔记或口头约定冲突，以本文、对应 Issue 和已经合入 `develop` 的契约为准。

## 1. 开始任务前

1. 确认 Gitee Issue 的负责人是自己，Gitee“协作者”字段保持为空；
2. 完整阅读 Issue 的目标、前置依赖、允许修改范围、交付物、验收标准和“明确不做”；
3. 每人同时只进行一个主要编码 Issue；
4. 前置任务未合并时，可以整理资料、页面流、来源和本地草稿，但不得自行冻结公共字段或批量录入未定格式；
5. 对接口、Schema 或任务边界有疑问时，在 Issue 评论中提出，不以私聊口头约定替代仓库记录。

## 2. 从最新 `develop` 创建分支

在仓库根目录执行：

```powershell
git switch develop
git pull --ff-only origin develop
git switch -c <Issue 中指定的分支名>
```

分支命名使用：

- `feat/<issue>-<topic>`：功能；
- `fix/<issue>-<topic>`：缺陷；
- `content/<issue>-<course>`：课程内容；
- `test/<issue>-<topic>`：测试；
- `docs/<issue>-<topic>`：文档；
- `chore/<issue>-<topic>`：工程维护。

全体成员禁止直接向 `main` 或 `develop` 推送；成员1自己的变更也必须通过独立分支和 PR 合入。

## 3. 开发边界

- 只修改 Issue“允许修改”列出的目录和文件，不顺手修改其他成员模块；
- 一个 Issue 只对应一名实现负责人、一个分支和一个 PR；
- 需要跨目录修改、扩大范围或增加公共字段时，先提出小 Issue，由成员1决定是否拆分；
- 公共 HTTP 字段以 `contracts/openapi.yaml` 为准，内部端口以各模块 `ports.py` 为准；
- 三门课程只通过 `course_id` 和课程包数据区分，不复制页面、API、智能体或验证器；
- 正式交接只使用已经合入 `develop` 的 Schema、Mock、夹具、示例和测试，不上传无法追踪的代码压缩包；
- AI 生成内容由提交者本人核对，不能把模型判断替代编译、测试、Schema 校验或来源审核；
- 禁止提交密钥、账号、真实学生信息、未授权资料、未脱敏业务数据、本机绝对路径和本地 `.env`。

## 4. 主责目录

| 成员 | 主责工作 | 默认主责目录 |
|---|---|---|
| 张梦洋 | 前端与学生端体验 | `apps/web/**` |
| 阴怡彤 | 模型适配、RAG与智能体 | `apps/api/app/modules/model_adapters/**`、`rag/**`、`orchestration/**` |
| 王维庸 | C语言内容与代码验证 | `course_packs/c/**`、`apps/api/app/modules/practice/**` |
| 王梓豪 | Python课程 | `course_packs/python/**` |
| 曾毅扬 | 数据结构与算法课程 | `course_packs/data_structures/**` |
| 陈骏人 | 架构、公共契约、工程底座和集成 | `contracts/**`、共享模板、核心配置和集成目录 |

具体任务仍以 Issue 中的“允许修改”范围为准；主责目录不等于可以绕过 Issue 随意修改。

## 5. 提交前检查

先核对改动：

```powershell
git status
git diff
```

再从仓库根目录执行：

```powershell
.\scripts\check.ps1
```

未激活虚拟环境时可以执行：

```powershell
.\scripts\check.ps1 -Python .\.venv\Scripts\python.exe
```

提交前必须确认：

- 功能、课程内容或文档符合 Issue 目标；
- 正常、失败和边界情况有测试或可复现证据；
- 没有修改无关文件和未授权目录；
- 没有密钥、个人信息和未授权数据；
- 没有绕过公共契约；
- 已从 `docs/templates/pr-six-part-description.md` 复制并填写本 PR 独立说明，保存为 `docs/presentation/<issue-id>-<topic>.md`；
- 全量检查通过。确实无法执行某项检查时，PR 必须说明原因、已执行命令和未覆盖风险。

## 6. 提交与推送

只暂存本任务文件，并使用清晰的提交信息：

```powershell
git add <本任务文件>
git commit -m "<类型>(<模块>): <完成内容>"
git push -u origin <当前分支名>
```

示例：

```text
feat(ai): 实现讯飞模型适配器
content(python): 增加文件处理知识点
test(practice): 补充 C 语言编译错误用例
```

不要使用“修改”“最终版”“更新一下”“test”等无法说明意图的提交信息。

## 7. 创建 Pull Request

PR 必须从任务分支发往 `develop`，并满足：

1. 一个 Issue 对应一个 PR，标题包含 Issue 标识并关联该 Issue；
2. 写清完成内容、修改目录、运行方式、测试结果、未完成项和风险；
3. 前端改动附截图，接口改动附请求/响应示例，课程内容附来源与校验证据；
4. 填写本 PR 独立六部分作品说明文档路径；不得让多人同时修改总汇总文档；
5. 指派成员1·陈骏人（Gitee：`@jrchen2026`）为最终验收与合并负责人；
6. 普通成员不得点击自己 PR 的“审查通过”“测试通过”或“合并”。

收到修改意见后，在原分支继续修改并推送，原 PR 会自动更新；除非成员1要求，不要新建重复 PR。

## 8. 验收与合并规则

- 所有普通成员 PR 统一由成员1检查、验收并合并；
- 成员1重点检查任务范围、接口一致性、安全边界、测试证据和可复现性；
- 普通成员只负责处理修改意见，不自行确认通过或合并；
- 成员1自己的 PR，在逐项检查差异、全量检查通过、记录验收证据和回退方式后，可以自行审核并合并；
- 默认采用 Squash 合并，并删除已合并的任务分支；
- PR 合入 `develop` 后才算进入项目，聊天附件和未合并分支不算正式交付。

## 9. 合并后与问题处理

PR 合并后更新本地代码：

```powershell
git switch develop
git pull --ff-only origin develop
```

确认 Issue 已完成后再领取下一项任务。遇到问题时：

- 需求不清楚：在对应 Issue 评论；
- 接口缺字段：提出契约需求，不自行增加；
- 需要修改他人目录：先申请新的边界清晰 Issue；
- 分支与 `develop` 冲突：停止合并并联系成员1；
- 不确定是否可提交：先提供 `git status`、改动范围和检查结果。

## 10. 五条最重要的规则

> 一人一个任务；一项一个分支；一项一个 PR；只改允许范围；统一由陈骏人验收合并。
