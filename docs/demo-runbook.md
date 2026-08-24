# 初步版本演示与验收手册

## 1. 演示前准备

Windows 11 环境需安装 Python 3.11、Node.js 20/22、Git 和 Docker Desktop。首次准备：

```powershell
.\scripts\setup_demo.ps1 -PullSandboxImages
```

该命令安装前后端依赖、启动 PostgreSQL/Redis、执行数据库迁移，并准备 Python/C 隔离运行镜像。镜像已存在时可省略 `-PullSandboxImages`。

真实模型凭据只写入未跟踪的 `.env`。不配置讯飞或驼灵时，系统分别使用固定模型回复和合成经营场景，核心学习闭环仍可演示。

## 2. 启动与停止

```powershell
.\scripts\run_demo.ps1 -EnableCodeExecution
```

- 学生端：`http://localhost:3000`
- API 文档：`http://127.0.0.1:8000/docs`
- 运行日志：`.runtime/`

停止：

```powershell
.\scripts\stop_demo.ps1
```

如需同时停止 PostgreSQL 和 Redis，增加 `-StopDataServices`。脚本只停止自己记录的前后端进程，不按名称批量结束其他程序。

## 3. 建议演示主线

1. 在左侧展示 C语言、Python、数据结构各 40 个知识点；
2. 选择 Python，完成 8 项快速能力基线；
3. 展示由知识前置关系和掌握度生成的三阶段路径；
4. 在“AI辅导”询问数据清洗或异常处理，展示课程来源引用；
5. 询问课程资料未覆盖的问题，展示“依据不足”降级；
6. 在“练习工坊”完成客观题或代码题，展示确定性验证、画像更新和下一任务；
7. 打开“脱敏经营数据质量分析”，说明驼灵只补充课后项目背景；
8. 关闭驼灵或断开模型服务，展示固定合成场景仍能支撑同一 Python 任务。

## 4. 自动冒烟验收

服务启动后运行：

```powershell
.\.venv\Scripts\python.exe scripts\demo_smoke.py
```

脚本会验证健康检查、三门课程、初始画像、个性化路径、带引用问答和驼灵安全降级。全仓质量门禁：

```powershell
$env:CIYUAN_TEST_DATABASE_URL="postgresql+psycopg://ciyuan:replace-before-use@127.0.0.1:5432/ciyuan?connect_timeout=3"
.\scripts\check.ps1 -Python ".\.venv\Scripts\python.exe"
```

## 5. 外部模型配置

讯飞星火负责通用讲解表达，RAG负责课程事实，质量监督负责引用与结构门禁。驼灵只接受 `post_course_finance_practice` 项目元数据，不接收学生身份、源代码或未授权原始数据。

接入驼灵前，需依据学校提供的最终 API 文档确认 `.env` 中：

```dotenv
TUOLING_ENABLED=true
TUOLING_BASE_URL=https://实际授权地址
TUOLING_CONTEXT_PATH=/实际场景接口路径
TUOLING_API_KEY=本地密钥
```

当前适配层约定响应包含 `context`，可选包含 `constraints` 与 `source_refs`。若校方接口字段不同，只修改 `model_adapters/tuoling.py` 的请求/响应映射，课程与前端接口无需改变。

## 6. 已知边界

- 这是竞赛初步版本，不含统一身份认证、教师后台和生产级监控；
- 学生标识为演示用匿名 ID，不录入姓名、学号和联系方式；
- 课程包为项目组 MVP 内容，正式发布前仍需教师依据培养方案复核；
- 代码执行默认关闭，只有明确启用且 Docker 镜像就绪时才运行不可信代码；
- 驼灵 API 的实际 URL、鉴权和返回字段必须以学校最终授权文档为准。
