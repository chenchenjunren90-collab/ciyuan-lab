# 产品版本记录

当前产品版本为 **v0.10.4**。前端、后端包、健康接口与 OpenAPI 的 `info.version` 共同标识这次产品构建；接口路径 `/api/v1`、课程包和事件 Schema 各自独立演进。

## 历史版本对照

2026-11-25 按可核验的功能与发布里程碑补编产品标签。日期对应提交或合入日期；补编标签不代表当日另行上线。历史包元数据中的 `0.1.0` 长期未随产品更新，不能单靠包号定位构建。中间开发提交归入相应里程碑，历史文件中的原称保留。11 月的旧标签 `frontend-v0.2.0` 继续指向原提交，其产品编号为 `v0.8.0`。8 月验收报告中的 MVP v0.2 对应发布候选。

| 产品版本 | 日期 | Git 提交 | 里程碑 |
| --- | --- | --- | --- |
| [v0.1.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.1.0) | 2026-08-12 | `62d4783` | 首个经过审核的主线发布 |
| [v0.2.0-alpha.1](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.2.0-alpha.1) | 2026-08-24 | `6129158` | 加入可复现的 MVP 演示流程 |
| [v0.2.0-rc.1](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.2.0-rc.1) | 2026-08-25 | `02df728` | 原称 MVP v0.2 发布候选 |
| [v0.3.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.3.0) | 2026-08-26 | `994591b` | 原称 MVP v0.3 完整演示版 |
| [v0.4.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.4.0) | 2026-08-30 | `f871af9` | Python 个性化沉浸课堂与知识路线 |
| [v0.4.1](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.4.1) | 2026-09-04 | `08d4b43` | 自适应课堂完善 |
| [v0.4.2](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.4.2) | 2026-09-13 | `78269f5` | 当期课堂版本同步到主线 |
| [v0.5.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.5.0) | 2026-09-27 | `da51bd6` | C 与数据结构课堂适配 |
| [v0.5.1](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.5.1) | 2026-09-30 | `2f01644` | 合入学习计划持久化及前端适配 |
| [v0.6.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.6.0) | 2026-10-22 | `875bdd9` | 线上前端与导航同步到主线 |
| [v0.7.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.7.0) | 2026-11-19 | `dc50502` | 实验步骤追问与项目分项验证 |
| [v0.8.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.8.0) | 2026-11-25 | `2e087b4` | 双主题与二分查找路径图，旧标签 frontend-v0.2.0 |
| [v0.9.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.9.0) | 2026-11-25 | 见版本标签 | 新字体、灰轨分段控件、统一版本展示与一致性校验 |
| [v0.10.0](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.10.0) | 2026-11-25 | 见版本标签 | 自托管宋体、粗宋标题与可单步查看的二分查找分支 |
| [v0.10.1](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.10.1) | 2026-11-26 | 见版本标签 | 练习反馈、课堂目录和学习推荐使用学生可读的名称 |
| [v0.10.2](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.10.2) | 2026-11-28 | 见版本标签 | 总览突出学习成果，改善说明文字对比度、导航间距和阶段进度显示 |
| [v0.10.3](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.10.3) | 2026-11-28 | 见版本标签 | 深色界面改用炭黑背景和中性灰面板 |
| [v0.10.4](https://github.com/chenchenjunren90-collab/ciyuan-lab/tree/v0.10.4) | 2026-11-28 | 见版本标签 | 欢迎页、侧栏和浏览器标签使用折页标志，缩小浅色与暗色切换控件 |

10 月 8 日的服务器恢复有独立验收记录。该记录给出上游视觉来源和镜像标识，未给出完整部署树对应的本仓库提交，因此归档于 10 月的同步里程碑。详见[服务器发布记录](audits/server-web-release-20261008.md)。

后续功能迭代增加次版本，修复增加补丁版本，候选构建使用 `-rc.N`。同一标签只对应一个提交。
