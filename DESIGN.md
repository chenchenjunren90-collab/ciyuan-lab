---
name: "词元研究所"
description: "以学习索引组织任务、来源与确定性验证的计算机学习主机"
colors:
  dark-ink: "#eff2f3"
  dark-muted: "#98a1aa"
  dark-line: "#2c333b"
  dark-surface: "#0b0d10"
  dark-surface-raised: "#11151a"
  dark-surface-muted: "#171c22"
  light-ink: "#172126"
  light-muted: "#606d73"
  light-line: "#cbd4d8"
  light-surface: "#eef2f3"
  light-surface-raised: "#f8faf9"
  light-surface-muted: "#e5ebed"
  ion: "#34beca"
  ion-dark: "#1aa5b0"
  ion-bright: "#5be4ea"
  ion-soft: "#12383c"
  ion-pale: "#0f2528"
  ion-ink: "#66eaf0"
  ion-contrast: "#061214"
  ion-light: "#007f8a"
  ion-light-dark: "#00636c"
  ion-light-bright: "#0aa6b4"
  ion-light-soft: "#dceff1"
  ion-light-pale: "#edf8f8"
  ion-light-ink: "#005b63"
  pulse: "#e24b5f"
  pulse-dark: "#ba2c43"
  pulse-bright: "#ff7283"
  pulse-soft: "#3a1920"
  pulse-pale: "#251318"
  pulse-ink: "#ff8290"
  pulse-contrast: "#180307"
  pulse-light: "#c32842"
  pulse-light-dark: "#9c1930"
  pulse-light-bright: "#df4058"
  pulse-light-soft: "#f6e1e5"
  pulse-light-pale: "#fbf0f2"
  pulse-light-ink: "#8d1429"
  solar: "#e9a83c"
  solar-dark: "#bf7a12"
  solar-bright: "#ffc966"
  solar-soft: "#3b2b12"
  solar-pale: "#271d10"
  solar-ink: "#ffd37f"
  solar-contrast: "#1a1002"
  solar-light: "#9a5b00"
  solar-light-dark: "#794500"
  solar-light-bright: "#c27a0d"
  solar-light-soft: "#f5e8cf"
  solar-light-pale: "#fbf5e9"
  solar-light-ink: "#704100"
  success: "#54c991"
  warning: "#efb44d"
  danger: "#f06b72"
  code: "#080b0e"
typography:
  display:
    fontFamily: "Bahnschrift, Segoe UI Variable, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "clamp(24px, 2.6vw, 36px)"
    fontWeight: 400
    lineHeight: 1.16
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Bahnschrift, Segoe UI Variable, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "25px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Aptos, Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Aptos, Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "9px"
    fontWeight: 750
    lineHeight: 1.4
  data:
    fontFamily: "Cascadia Mono, Cascadia Code, Consolas, monospace"
    fontSize: "8px"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "0.1em"
rounded:
  compact: "6px"
  control: "8px"
  panel: "12px"
spacing:
  micro: "5px"
  xs: "8px"
  sm: "12px"
  md: "18px"
  lg: "24px"
  xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.ion}"
    textColor: "{colors.ion-contrast}"
    typography: "{typography.label}"
    rounded: "{rounded.panel}"
    padding: "11px 18px"
  button-secondary:
    backgroundColor: "{colors.dark-surface-muted}"
    textColor: "{colors.dark-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 13px"
  accent-switch:
    backgroundColor: "transparent"
    textColor: "{colors.dark-muted}"
    typography: "{typography.data}"
    rounded: "{rounded.compact}"
    padding: "7px 9px"
    height: "34px"
  tab:
    backgroundColor: "transparent"
    textColor: "{colors.dark-muted}"
    typography: "{typography.label}"
    rounded: "0"
    padding: "15px 0 13px"
  panel:
    backgroundColor: "{colors.dark-surface-raised}"
    textColor: "{colors.dark-ink}"
    rounded: "{rounded.panel}"
    padding: "28px"
    width: "100%"
---

# Design System: 词元研究所

## Overview

**Creative North Star: "学习索引 / 可核验学习主机"**

词元研究所是一台面向计算机专业学习的主机：左侧课程轨像可触达的学习索引，顶部任务栏报告当前课程、服务与外观状态，主工作区把诊断、知识路线、课堂、辅导、练习、项目和验证结果放在同一套操作语法里。它不采用纸面卡册或固定单色框线，而是克制的哑光 mainframe / instrument panel。

界面保持原产品的信息密度，学生可以同时看到任务、进度、来源、智能体状态和验证证据。层级主要由中性表面、精确的 1px 分隔、紧凑字号与少量信号色形成；不靠发光边框、装饰仪表或大面积渐变制造“科技感”。

**Key Characteristics:**

- 课程轨、taskbar、功能 tab 与内容面板组成持续可扫描的学习主机。
- 深色与浅色都使用中性哑光表面，结构以精确 1px 线条为主。
- Ion 青、Pulse 红、Solar 金是三套全局信号色，一次只激活一套。
- success、warning、danger 是独立语义，不随信号色切换。
- 高信息密度服务于学习索引、来源和确定性验证，不制造假数据。

## Colors

三套信号色通过同一组 `accent` 变量驱动导航、当前状态、按钮、进度与课堂交互；深浅主题分别使用前置 token 中列出的精确派生值。

### Primary

- **Ion 青：** 默认信号色，冷静、清晰，适合长期学习操作；在深色与浅色主题中分别使用 `ion*` 与 `ion-light*` 系列。
- **Pulse 红：** 高识别信号方案；使用 `pulse*` 与 `pulse-light*` 系列，不再是固定框线或唯一品牌色。
- **Solar 金：** 温暖、醒目的任务方案；使用 `solar*` 与 `solar-light*` 系列。

### Neutral

- **Dark surfaces：** `dark-surface` 是主底，`dark-surface-raised` 是主要面板，`dark-surface-muted` 是输入、行项和嵌套区域；`dark-line` 负责 1px 结构线。
- **Light surfaces：** `light-surface`、`light-surface-raised`、`light-surface-muted` 保持同一层级关系，`light-line` 保持清晰但不过度强调。
- **Ink / muted：** 主文字与辅助文字跟随当前主题；数据、来源、短状态与课程 ID 使用更紧凑的层级。
- **Code：** 代码编辑区维持独立的近黑背景，插入光标和细网格跟随当前信号色。

### Semantic

- **Success：** 仅表示服务在线、验证通过或已完成。
- **Warning：** 仅表示连接中、依据不足或需要先完成前置步骤。
- **Danger：** 仅表示服务离线、加载失败、课堂错误或操作失败。

### Named Rules

**The One Active Signal Rule.** Ion、Pulse、Solar 可全局切换，但同一时刻只能有一套信号色生效；不要在一个页面混用三套强调色。

**The Semantic Independence Rule.** success、warning、danger 保持事实语义，不得被当前信号色重染。

**The Neutral Surface Rule.** 信号色标记动作和状态，中性表面承载内容；不要用大面积强调色代替结构。

## Typography

**Display Font:** Bahnschrift，回退到 Segoe UI Variable、PingFang SC、Microsoft YaHei 与无衬线字体

**Body Font:** 当前正文以 Aptos 为首选；Windows 的系统回退为 Segoe UI，中文回退为 PingFang SC、Microsoft YaHei
**Data Font:** Cascadia Mono、Cascadia Code，回退到 Consolas 与 monospace

**Character:** 标题窄而稳，正文紧凑但可读，数据字体只承担课程 ID、状态、百分比、来源短标记和代码，不把整张界面伪装成终端。

### Hierarchy

- **Display (`display`)：** taskbar 标题及最高级工作区标题，使用流体字号与轻字重。
- **Title (`title`)：** 面板和任务标题，使用紧字距建立扫描锚点。
- **Body (`body`)：** 解释、任务摘要和证据说明，常用 1.7 行高。
- **Label (`label`)：** 按钮、筛选、状态和紧凑说明。
- **Data (`data`)：** 课程代码、LEARNING CORE、服务状态、编号和来源标记。

### Named Rules

**The Human First Rule.** 先用自然中文说明学习任务，再用数据字体补充 ID、状态或证据；数据字体不承载长段正文。

## Layout

桌面主壳采用 `116px minmax(0, 1fr)` 两列：116px sticky course rail 固定课程索引与服务状态，workspace 使用 `clamp(22px, 3vw, 46px)` 水平内边距。taskbar 最小高度为 106px，依次容纳学习任务标题、服务状态、全局信号色切换和用户/设置入口。其下是保留原信息密度的功能 tab；Python 课程最多显示六项：学习总览、沉浸课堂、个性路径、课程辅导、练习工坊、项目实战。

主区不是“卡片海”：面板以整宽内容区、嵌套列表和 1px 分隔组织信息。`classroom-focus` 会移除 rail 和 taskbar，把课堂限制在最大 1560px 的专注工作区。

在 820px 及以下，auto/mobile 布局把 course rail 转成顶部课程索引，workspace 收到 16px 边距，taskbar 降为 88px，tab 以三列网格重排；在 520px 及以下进一步隐藏品牌文字与课程名称，指标切为单列。`auto` 在 Vue 中以 768px 判断 mobile/desktop；`mobile` 强制使用最大 760px 的移动框架；`desktop` 即使在窄视口也保留 86px rail 与桌面信息架构。

**The Density Preservation Rule.** 响应式只重排和压缩 chrome，不删除课程、证据、验证或主要行动。

**The Device Choice Rule.** auto、mobile、desktop 是用户可控显示模式；设备模式必须在任意视口保持权威。

## Elevation & Depth

系统默认平面。主要 workspace、panel、指标、课堂表面和列表使用中性色差与 1px 边界建立深度，静态状态不加阴影。阴影只用于需要脱离当前平面的对象或直接操作反馈：主行动、发言中的课堂角色和右侧设置抽屉。

### Shadow Vocabulary

- **Primary action:** `0 8px 20px #0003`，只给当前主行动提供轻微触达反馈。
- **Speaking classmate:** `0 14px 28px #0003`，只表示课堂人物正在发言。
- **Settings drawer:** `-24px 0 64px #0008`，只用于右侧抽屉与主工作区分层。
- **Focus halo:** 3px accent 混合外轮廓；高对比模式提升为 4px 实色 accent。

### Named Rules

**The Flat Instrument Rule.** 静态学习表面保持无阴影；先用层级表面和 1px 分隔，再考虑临时浮层阴影。

## Shapes

形状遵循 6/8/12 三档：6px 用于 taskbar 紧凑按钮和小型信号开关，8px 用于 rail、设置控件、状态块和常规输入，12px 用于主面板、hero 与课堂大表面。圆形只保留给在线点、头像和开关滑块；完全圆角只用于确实是进度轨或 switch 的控件。

**The Three Radius Rule.** 新组件只能从 6px、8px、12px 中选择；不要继续增加 10px、11px、16px 等近似圆角。

**The One Pixel Rule.** 常规结构边界使用精确 1px；高对比模式才提升交互控件边界宽度。

## Components

### Accent Switch

- taskbar 中横向排列 Ion、Pulse、Solar 三个按钮，按钮最小高 34px、圆角 6px，色样为 10px 方块。
- active 态使用当前 accent 边界、accent ink 文本与 accent pale 背景，并同步 `aria-pressed`。
- 窄屏把每项收为 28px 图形按钮，但三项始终可见且一次仅一项 active。

### Taskbar

- 桌面最小高 106px，底部为 1px 分隔；标题用 display 字体，课程名用数据字体与当前 accent ink。
- 服务点使用独立 success/warning/danger；设置入口是 6px 圆角的透明描边按钮。
- 820px 以下隐藏服务详情和非必要用户文字，不隐藏信号色切换与设置入口。

### Course Rail

- 桌面宽 116px、全高 sticky；品牌标记、三门课程、课程进度和 API 状态垂直排列。
- 选中课程用 accent 文本、accent 细边与 inset 2px 标记；不是整块彩色卡。
- mobile 将 rail 变成顶部三列课程索引；desktop 强制模式在窄屏保留 86px 紧凑 rail。

### Panels

- 主要 panel 使用 raised surface、1px line、12px 圆角、28px 内边距、无静态阴影。
- 嵌套列表和输入使用 muted surface，避免每层都变成独立浮卡。
- 标题、说明、证据、操作保持原产品的高信息密度和稳定顺序。

### Tabs

- tab 使用透明背景、底部 1px 导轨与 active 2px accent 下划线；常态无圆角、无阴影。
- 使用 `repeat(auto-fit, minmax(104px, 1fr))` 承载最多六项功能；移动端改为三列并保留全部功能入口。
- active 同步 `aria-current="page"`，hover 只提升文字对比。

### Settings

- 右侧抽屉宽 `min(520px, 100%)`，28px 内边距、左侧 1px line、无 backdrop blur。
- 明暗模式包含 light/dark/system；设备模式包含 auto/mobile/desktop；颜色模式为单列 Ion/Pulse/Solar 说明项。
- reduced motion、high contrast 使用语义 switch；焦点被限制在 dialog 内，Escape 关闭后恢复触发点。

### Classroom Surfaces

- 课堂 masthead、讲解、对话、材料、代码任务与规划区域复用 raised/muted 中性表面和 12px 大圆角。
- active 课程交互使用当前 accent；success/warning/danger、代码语法和验证结果保持独立语义。
- `classroom-focus` 隐藏外层 chrome；减少动态时动画与滚动过渡立即收敛。

### Service Offline

- 离线面板使用 danger 文本、danger 混合边界与低浓度 danger 背景，并提供明确重试按钮。
- 未载入的知识点、证据、掌握数、练习和项目显示“—”及原因，不把空数组或未连接状态伪装成 0。
- 离线是可靠性状态，不使用当前 accent 代替 danger。

## Do's and Don'ts

### Do:

- **Do** 用学习索引、来源和确定性验证结果主导视觉层级。
- **Do** 让 Ion、Pulse、Solar 中仅一套全局信号色控制导航、按钮、进度和课堂 active 状态。
- **Do** 用中性哑光表面与精确 1px 分隔保持 instrument panel 的可扫描性。
- **Do** 在 dark/light/system、auto/mobile/desktop、高对比和减少动态下保留完整任务语义。
- **Do** 把服务离线显示为 danger，并把未载入数值显示为“—”。

### Don't:

- **Don't** 恢复纸面卡册、固定单色框线或单一红色品牌规则。
- **Don't** 把 success、warning、danger 重映射为当前信号色。
- **Don't** 用多层阴影、霓虹光晕、玻璃模糊或装饰仪表制造虚假层级。
- **Don't** 在窄屏删除来源、验证、主要行动或六功能信息架构。
- **Don't** 把尚未加载的数据呈现为真实的 0。
