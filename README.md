# 词元研究所

**多智能体协同驱动的计算机学科助学服务平台**

面向首都经济贸易大学计算机专业学生，以培养方案和课程资料为知识基础，为 **C 语言、Python、数据结构** 三门课程提供个性化规划、可信辅导、代码实践与学习画像更新。项目当前目标是在三周内完成可演示、可扩展、可验证的初步版本。

> 核心不变：计算机专业课程学习。财经管理元素只进入课程学习后的综合练习，以真实问题背景帮助学生应用编程、算法与数据库能力，不替代课程知识本身。

## 总体架构

![词元研究所总体架构](docs/assets/architecture-v0.3.png)

详细说明见 [系统架构](docs/architecture.md)。

## 初步版本范围

- 三门课程同步建设，每门首期整理约 **40 个核心知识点**；
- 每个知识点至少具有学习目标、前置关系、基础内容和测评映射；
- 每门课程均提供问答、分级练习、代码题或 Debug 任务，并跑通一条完整学习流程；
- 跑通“初始测评 → 个性化计划 → 学习辅导 → 练习/Debug → 确定性代码验证 → 画像更新 → 下一任务推荐”；
- 使用数据库保存课程结构、学习记录与学生画像，使用 RAG 提供有来源的课程问答；
- 通用推理能力优先接入科大讯飞星火 MaaS/Agent 平台，**不进行模型微调**；
- “驼灵”API仅用于经授权、脱敏的经管综合练习背景与业务解释，不访问或暴露底层敏感数据；
- 暂不追求生产级高并发、全培养方案覆盖、大规模题库和复杂虚拟仿真实训。

## 三个协同智能体

| 智能体 | 主要职责 | 不负责什么 |
|---|---|---|
| 学情规划智能体 | 分析测评与学习记录，形成阶段目标、学习顺序和下一步推荐 | 不独立判定代码正确性 |
| 课程辅导智能体 | 基于课程知识库讲解、追问、提示、Debug 引导和拓展练习 | 不绕过知识来源直接编造结论 |
| 质量监督智能体 | 检查任务路由、引用、输出格式、安全边界与反馈一致性 | 不用语言模型主观判断替代测试结果 |

三个智能体是同一系统内职责清晰的逻辑模块，不是为了数量而拆分的三个独立产品。代码正确性由编译、单元测试、测试用例和资源限制等确定性机制验证，模型负责解释结果和组织反馈。

## 技术路线

```text
Vue 3 / Vite 前端
        ↓
FastAPI 模块化单体后端
        ├─ 智能体编排与学情规划
        ├─ 课程/RAG 与引用
        ├─ 练习、Debug 与代码验证
        ├─ 学习画像与推荐
        └─ 模型适配层（讯飞 MaaS/Agent；驼灵受限场景）
        ↓
PostgreSQL + pgvector / Redis / 受控代码运行环境
```

采用模块化单体是三周初步版本的主动选择：一个后端进程完成部署，各业务模块通过清晰接口隔离；未来确有性能或团队规模需求时再拆分服务。决策记录见 [ADR-0001](docs/adr/0001-modular-monolith-mvp.md)。

## 仓库结构

```text
apps/
  api/                     FastAPI 后端
    app/modules/
      orchestration/       三智能体编排与流程控制
      rag/                 知识入库、检索、引用
      learner_profile/     学生画像、掌握度和学习计划
      practice/            练习、Debug、代码验证
      model_adapters/      讯飞与驼灵模型适配
  web/                     Vue/Vite 学生端
contracts/                 OpenAPI、JSON Schema 等公共契约
course_packs/
  _template/               课程包统一模板
  c/                       C 语言课程包
  python/                  Python 课程包
  data_structures/         数据结构课程包
infra/                     本地与演示环境
scripts/                   校验、导入和辅助脚本
docs/                      架构、范围、标准与决策记录
.gitee/                    Issue 与 PR 模板
```

## 快速启动初步版本

Windows + Docker Desktop 环境下：

```powershell
.\scripts\setup_demo.ps1 -PullSandboxImages
.\scripts\run_demo.ps1 -EnableCodeExecution
```

打开 `http://localhost:3000`。服务启动后可运行：

```powershell
.\.venv\Scripts\python.exe scripts\demo_smoke.py
```

完整演示顺序、模型配置、安全降级和停止方式见 [初步版本演示与验收手册](docs/demo-runbook.md)。代码执行默认关闭，只有显式传入 `-EnableCodeExecution` 且 Docker 隔离镜像就绪时才开启。

## 协作原则

> **普通成员开始开发前，必须先阅读：[普通成员开发与提交指南](docs/member-workflow.md)。**

1. 一人负责一个 Issue；一个 Issue 对应一个独立分支和一个 PR，Gitee“协作者”字段保持为空；
2. 所有任务分支从最新 `develop` 创建，全体成员禁止直接向 `main`、`develop` 推送；
3. 只修改 Issue 明确允许的目录；公共字段、跨目录修改和范围扩大必须先提出新 Issue；
4. 提交前执行 `.\scripts\check.ps1`，PR 写明改动、测试、风险和可复现证据；
5. 普通成员的 PR 统一由成员1·陈骏人审核、验收和合并，普通成员不得自审或自合并；
6. 成员1自己的 PR，在全量检查通过并记录证据后可以自行审核合并；
7. AI生成代码和课程内容仍由提交者负责，课程内容必须符合 [课程包标准](docs/course-package-standard.md)，数据和模型调用必须符合 [数据与安全边界](docs/data-and-security.md)。

完整流程见 [协作与开发流程](docs/workflow.md)，岗位边界见 [六人岗位分工与独立交付说明](docs/responsibilities.md)，可直接创建到 Gitee 的任务描述见 [单人 Issue 执行手册](docs/collaborator-issues.md)，当前版本边界见 [MVP 范围与验收边界](docs/mvp-scope.md)。

## 本地启动

需要 Python 3.11+、Node.js 20.19+/22.12+ 与 Docker。首次运行使用 PowerShell：

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
docker compose --env-file .env -f infra/compose.yaml up -d
python -m alembic upgrade head
python -m uvicorn app.main:app --app-dir apps/api --reload
```

另开一个终端启动前端：

```powershell
Set-Location apps/web
npm ci
npm run dev
```

默认前端地址为 `http://localhost:3000`，后端文档为 `http://localhost:8000/docs`。提交前在仓库根目录执行 `.\scripts\check.ps1`。真实模型调用前须替换本地 `.env` 中的占位值；`.env` 不得提交。

## 文档索引

- [普通成员开发与提交指南（必读）](docs/member-workflow.md)
- [系统架构](docs/architecture.md)
- [协作与开发流程](docs/workflow.md)
- [六人岗位分工与独立交付说明](docs/responsibilities.md)
- [单人 Issue 执行手册](docs/collaborator-issues.md)
- [MVP 范围与验收边界](docs/mvp-scope.md)
- [课程包统一标准](docs/course-package-standard.md)
- [数据、模型与安全边界](docs/data-and-security.md)
- [初步版本演示与验收手册](docs/demo-runbook.md)
- [DATA-01 最小数据模型与迁移](docs/data-model.md)
- [RAG 入库与混合检索](docs/rag-hybrid-search.md)
- [RAG 75 问检索评测](docs/rag-evaluation.md)
- [模型服务接入与验收](docs/provider-integration.md)
- [贡献指南](CONTRIBUTING.md)
- [AI 编码代理约束](AGENTS.md)

## 当前状态

仓库已形成 `MVP v0.2` 发布候选：三门课程共 120 个知识点已完成结构与内容补齐，
课程内容仍保持 `draft`，并附有 AI 辅助技术复核记录；RAG 只索引 14 个已审核、权利明确的项目原创来源片段，
并具备课程隔离、pgvector 可选后端和 75 问回归评测。学习端已跑通知识学习、学情路径、
有来源问答、三级提示、确定性练习与项目人工评审入口。真实讯飞/驼灵联调仍依赖授权凭据，
无凭据时使用明确标识的安全降级，不把 Mock 当作真实调用结果。
