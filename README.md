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

## 协作原则

1. 所有工作先有 Gitee Issue，再建短期分支和 Pull Request；
2. 涉及多人模块时先冻结 `contracts/` 中的接口和数据结构；
3. 每个 PR 只有一名明确的人类负责人，AI生成代码同样需要测试和人工评审；
4. 禁止直接向 `main`、`develop` 推送，功能分支从 `develop` 创建；
5. 课程内容必须符合 [课程包标准](docs/course-package-standard.md)，数据和模型调用必须符合 [数据与安全边界](docs/data-and-security.md)。

完整流程见 [协作与开发流程](docs/workflow.md)，成员分工和全部待办见 [六人岗位分工与 Issue 清单](docs/responsibilities.md)，当前版本边界见 [MVP 范围与验收边界](docs/mvp-scope.md)。

## 本地启动

需要 Python 3.11+、Node.js 20.19+/22.12+ 与 Docker。首次运行使用 PowerShell：

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
docker compose --env-file .env -f infra/compose.yaml up -d
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

- [系统架构](docs/architecture.md)
- [协作与开发流程](docs/workflow.md)
- [六人岗位分工与 Issue 清单](docs/responsibilities.md)
- [MVP 范围与验收边界](docs/mvp-scope.md)
- [课程包统一标准](docs/course-package-standard.md)
- [数据、模型与安全边界](docs/data-and-security.md)
- [贡献指南](CONTRIBUTING.md)
- [AI 编码代理约束](AGENTS.md)

## 当前状态

仓库处于三周初步版本建设期。提交演示前，以“完整流程可运行、来源可追溯、代码结果可验证、三门课程结构一致”为优先级，不以功能数量或模型调用次数作为完成标准。
