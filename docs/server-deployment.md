# 服务器部署说明

## 当前部署目标

- 主机：`39.105.104.230`
- 独立目录：`/home/ciyuan/chenjunren/etf_agent/ciyuan-lab`
- 公网入口：`http://39.105.104.230:3004`
- Compose 文件：`infra/compose.production.yaml`

截图给出的父目录已有其他项目，因此本项目只能使用独立子目录，禁止覆盖、移动或清理父目录现有文件。

## 架构

公网只开放 Nginx 的 3004 端口。Nginx 提供 Vue 静态资源并将 `/api`、`/docs`、
`/openapi.json` 转发给 FastAPI。PostgreSQL、Redis 和 FastAPI 只存在于 Compose 内部网络。
代码题由 FastAPI 通过宿主机 Docker Socket 启动一次性、无网络、受限资源的沙箱容器。Python 使用固定版本的 Alpine 镜像；C 使用由 `infra/c-sandbox.Dockerfile` 构建的精简 C17 编译镜像。

## 启动

在服务器的项目目录执行：

```bash
mkdir -p .runtime/sandbox
chmod 700 .runtime/sandbox
sudo env DOCKER_BUILDKIT=0 docker build -f infra/api.Dockerfile -t ciyuan-lab-api:latest .
sudo env DOCKER_BUILDKIT=0 docker build -f infra/web.Dockerfile -t ciyuan-lab-web:latest .
sudo env DOCKER_BUILDKIT=0 docker build -f infra/c-sandbox.Dockerfile -t ciyuan-lab-c-sandbox:latest .
sudo docker pull docker.1panel.live/library/python:3.11.15-alpine3.24
sudo docker compose --env-file .env.production -f infra/compose.production.yaml up -d --no-build
```

`.env.production` 权限必须为 `600`，数据库密码在服务器随机生成；讯飞密钥可为空，空值时使用
明确标识的安全降级版本。任何真实密钥均不得上传至 Git。

## 验证

```bash
curl -fsS http://127.0.0.1:3004/api/v1/health
sudo docker compose --env-file .env.production -f infra/compose.production.yaml ps
```

本地或CI可把冒烟地址指向公网API：

```powershell
.\.venv\Scripts\python.exe scripts\demo_smoke.py `
  --base-url http://39.105.104.230:3004/api/v1 --with-code-execution
```

## 更新与回滚

每次更新前将当前目录归档到同级时间戳备份，且不包含数据库卷。上传新版本后按“启动”章节重新构建镜像并执行
`docker compose up -d --no-build`。如新版本验收失败，停止当前 Compose、恢复上一份代码归档，
再使用同一 `.env.production` 和持久化卷重新构建。不得使用 `docker compose down -v`，否则会删除学习数据。
