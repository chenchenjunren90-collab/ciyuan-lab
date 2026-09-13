# 协作前端适配记录

日期：2026-09-05

## 来源与集成范围

读取了用户提供的 GitHub 仓库，并对比 `github/main` 与 `github/luckystar`。本次前端设计来自 [a52ef8ad45d40317c5ab1620c0cabf83c3b8e07a](https://github.com/chenchenjunren90-collab/ciyuan-lab/commit/a52ef8ad45d40317c5ab1620c0cabf83c3b8e07a)，提交标题为 `feat(web): redesign learning workspace themes`。

协作分支把 10 个文件放在仓库根目录；直接合并不能使这些 Vue 文件进入现有 Vite 应用。本次将它们放回实际应用目录，再适配当前后端接口：

| 协作文件 | 实际落点 |
| --- | --- |
| App.vue、styles.css、uiPreferences.ts、uiPreferences.test.ts | apps/web/src/ |
| WelcomeExperience.vue、SettingsPanel.vue | apps/web/src/components/ |
| PythonFirstLesson.vue | apps/web/src/components/classroom/ |
| DESIGN.md、PRODUCT.md、design.json | apps/web/ |

保留离子青、脉冲红、太阳金三套配色、日夜模式、欢迎页和个性化设置。补充修改 `ClassroomCodeTask.vue`，新增 `services/workspaceState.ts` 及其回归测试。没有更改公共 API 契约、数据库结构或依赖，没有覆盖此前后端与 MaaS/RAG 工作，也没有恢复已删除的训练资料。

## 接口与行为适配

- 课程目录、知识点、活动与学习画像分别处理失败。画像服务不可用时，公开课程仍能浏览；显示恢复入口，重试成功后恢复在线状态。
- 区分尚未评测、只有自述的空档案与具有客观证据的画像。只使用有证据且分值有效的条目计算掌握度，无法载入时显示空值，不显示虚构成绩。
- 课程和账号切换使用请求版本标记，防止先发后到的课程响应覆盖当前工作区。初次加载保留用户选定的页签。
- 适配初始诊断、阶段重测、下一活动、RAG 引用与个性化课堂流程。修复生成练习时刷新账号数据导致新题被清空的问题。
- RAG 或模型降级不再显示“已通过质量检查”。课程计划进入课堂后仍保留依据有限的状态，引用数量取自响应。
- 验证服务不可用时，不展示为学生测试失败，不增加自适应练习失败次数，也不提示“代码已运行”。正常代码结果仍以服务端确定性验证为准。
- 设置面板支持 Escape、焦点恢复和正反向键盘焦点约束。补齐移动端点击区域、输入字号与代码任务主题适配。

## 验证结果

以下检查均在本地完成：

| 检查 | 结果 |
| --- | --- |
| apps/web 下 `npm run check` | 类型检查通过；4 个测试文件、24 项测试通过；生产构建通过 |
| 后端契约、学习流程、RAG、课堂及业务证据边界回归 | 46 项通过 |
| `scripts/validate_course_pack.py` | 3 门课程包通过 |
| `scripts/validate_repository.py` | 契约、Compose 骨架及必要文件通过 |
| `git diff --check` | 通过 |
| 浏览器基础流程 | 13 项断言通过，覆盖页签、空画像、配色、设置键盘操作、移动端、课程切换、诊断和降级辅导 |
| 浏览器故障恢复 | 5 项断言通过，覆盖画像故障、全服务故障与恢复 |
| 浏览器课堂流程 | 3 项断言通过，覆盖降级计划、课堂加载和进入课堂后的状态保持 |

浏览器验收使用真实应用与当前 FastAPI 路由、课程文件，配合内存学习存储及 Mock 模型；模拟 503 验证恢复流程。没有调用付费模型、读取生产凭据或向生产数据库写入。真实 MaaS、生产数据库和 Docker 代码沙箱的线上联调不包含在本次前端验收结果中。

后端测试有一条现有 Starlette/httpx 弃用提示，不影响测试结果。浏览器故障测试中预期的 HTTP 404/503 不属于页面运行异常。样式机械检查仍提示硬编码颜色、字号等存量设计约束项；本次只修复适配相关问题，没有宣称全量样式审计无问题。

已检查桌面明暗主题、390px 手机总览与设置面板、课程辅导及加载完成后的课堂截图。验收截图保存在工作区上一级 `output/playwright/`，名称为 `frontend-desktop-dark.png`、`frontend-desktop-light.png`、`frontend-mobile-overview.png`、`frontend-mobile-settings.png`、`frontend-tutor.png`、`frontend-classroom.png`。

本次为本地工作区适配，未提交、推送或部署。
