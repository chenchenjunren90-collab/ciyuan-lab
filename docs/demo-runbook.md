# 初步版本演示与验收手册

## 1. 演示前准备

Windows 11 环境需安装 Python 3.11、Node.js 20/22、Git 和 Docker Desktop。首次准备：

```powershell
.\scripts\setup_demo.ps1 -PullSandboxImages
```

该命令安装前后端依赖、启动 PostgreSQL/Redis、执行数据库迁移，并准备 Python/C 隔离运行镜像。镜像已存在时可省略 `-PullSandboxImages`。

真实模型凭据只写入未跟踪的 `.env`。不配置讯飞MaaS时，系统使用固定模型回复和经过审核的合成财经场景，核心学习闭环仍可演示。

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

1. 在左侧展示 C语言 42 个、Python 40 个、数据结构 40 个知识点；
2. 选择 Python，完成 8 项服务器判分的初始诊断（前端不持有答案）；
3. 展示由知识前置关系和掌握度生成的三阶段路径；
4. 打开 PY-LIST-01，展示“学习顺序—分步例题—立即检验”的固定教学骨架；
5. 在“AI辅导”询问数据清洗或异常处理，展示课程来源引用和组件执行审计；
6. 询问课程资料未覆盖的问题，展示“依据不足”降级；
7. 在“练习工坊”逐级获取提示，说明提示不会直接泄露答案；
8. 在个性化 Python 编程挑战中生成薄弱点新题，提交代码并展示隐藏测试、画像更新和下一道变式题；
9. 返回课程概览完成阶段重测，展示不同题集带来的画像变化；
10. 打开一个课后综合项目，输入学习目标并生成个性化合成财经项目；
11. 展示来源引用、计算机知识目标、约束、固定种子数据及其校验哈希；
12. 提交项目说明与测试证据，展示材料完整性检查，并确认系统没有虚构项目分数或修改掌握度；
13. 断开模型服务，展示经过审核的固定项目仍能支撑同一计算机课程任务。

## 4. 自动冒烟验收

服务启动后运行：

```powershell
.\.venv\Scripts\python.exe scripts\demo_smoke.py
```

脚本会验证健康检查、三门课程共 122 个知识点、结构化知识卡、服务器诊断、初始画像、个性化路径、
个性化 Python 新题、带引用问答及审计、分层提示、受控合成项目生成、安全降级和项目证据记录入口。

启用 Docker 代码执行后，可进一步验证 C、Python、数据结构各一道真实代码题：

```powershell
.\.venv\Scripts\python.exe scripts\demo_smoke.py --with-code-execution
```

全仓质量门禁：

```powershell
$env:CIYUAN_TEST_DATABASE_URL="postgresql+psycopg://ciyuan:replace-before-use@127.0.0.1:5432/ciyuan?connect_timeout=3"
.\scripts\check.ps1 -Python ".\.venv\Scripts\python.exe"
```

## 5. 外部模型配置

讯飞MaaS上的 DeepSeek-V4-Flash 负责通用讲解与受控项目编排，RAG负责课程事实，质量监督负责引用、结构和隐私门禁。外部模型只接收非身份化的学习要求与已审核模板，不接收学生身份、源代码或原始财经数据。

本地 `.env` 只需配置：

```dotenv
XFYUN_MAAS_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
XFYUN_MAAS_MODEL=xopdeepseekv4flash0731
XFYUN_MAAS_API_KEY=从服务管控页面获取的项目密钥
```

不得把密钥提交到Git。适配器使用 OpenAI 兼容的 `/chat/completions` 接口和 Bearer 鉴权，所有课程统一使用已配置的 MaaS 推理服务。

配置可先做不联网自检：

```powershell
.\.venv\Scripts\python.exe scripts\check_provider_readiness.py
```

只有确认授权和额度后才增加 `--live`，避免误耗配额。

## 6. 已知边界

- 这是竞赛初步版本，不含统一身份认证、教师后台和生产级监控；
- 学生标识为演示用匿名 ID，不录入姓名、学号和联系方式；
- 课程包为项目组 MVP 内容，正式发布前仍需教师依据培养方案复核；
- 代码执行默认关闭，只有明确启用且 Docker 镜像就绪时才运行不可信代码；
- 生产环境已用项目专用讯飞 MaaS 凭据完成真实问答、规划和项目生成回归；凭据只保存在
  服务器权限受限的环境文件。更换服务器或服务卡后仍须重新执行最小调用与降级测试。
