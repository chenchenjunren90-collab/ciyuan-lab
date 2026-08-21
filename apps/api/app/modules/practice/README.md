# 确定性代码验证模块

本模块只通过隔离运行器执行学生代码。`DockerSandboxRunner` 不会调用宿主机的
Python、C 编译器，也不会在 FastAPI 进程中执行提交内容。Docker 不可用或镜像
未准备好时，验证器返回“隔离运行环境未就绪”，禁止自动降级为宿主机执行。

首次使用前由开发环境管理员预拉取固定镜像：

```powershell
docker pull python:3.11.15-alpine3.24
docker pull gcc:13.4.0-bookworm
```

拉取镜像后执行真实容器回归测试（不能只依据 Mock 单元测试验收）：

```powershell
python -m pytest apps/api/tests/test_practice_docker_integration.py -rs
```

两项测试都必须显示为通过；如果显示为跳过，应先启动 Docker 并确认上述固定镜像
已经存在，再重新执行。

当前 PRACTICE-01 已实现：

- C17 与 Python 3.11 的统一测试编排；
- 正确、编译失败、运行错误、答案错误、超时和输出超限的稳定结果；
- 网络关闭、只读根文件系统、非 root 用户、能力移除、PID/内存限制；
- Python 临时目录禁止执行文件，C 临时编译目录仅为运行编译结果而允许执行；
- 隐藏测试输入、期望输出和运行错误细节不进入诊断。

当前环境未安装 Docker 时，只能运行 Mock 单元测试，不能声称完成了真实容器
验收。恶意无限输出的流式截断、容器残留监控和对抗性资源超限测试属于
`PRACTICE-02`，在完成前不得将本模块描述为生产级在线判题沙箱。
