---
name: "词元研究所 · luckystar-2 原版适配"
description: "原版视觉与动效保持不变，课程和页面导航通过隔离兼容层接入"
colors:
  dusk-background: "#042341"
  dusk-accent: "#ba5bb8"
  peach-background: "#1a1a1d"
  peach-accent: "#e6397c"
  violet-background: "#8a3bec"
  violet-accent: "#b2fc06"
  dawn-background: "#ffffcd"
  dawn-accent: "#ff8d10"
typography:
  body:
    fontFamily: "Ciyuan Sans, Noto Sans SC, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  caption:
    fontSize: "0.8125rem"
  section:
    fontSize: "1.375rem"
  page:
    fontSize: "1.625rem"
  intro:
    fontSize: "2rem"
---

# Design System: luckystar-2 原版适配

## Overview

2026-10-07 用户明确指定完整保留幸运星原版，在原版基础上做适配；有无法兼容的取舍时由用户决定。基准为 GitHub `luckystar-2` 的 `f731194355d3047c101c1b237c5431e6f6f6aa2e`。不得再把它当作待重新设计的页面。

之前本地美化的文件已备份至 `output/luckystar-before-restore-20261007-8d50f481/`，旧 `workspace.css` 已撤下，不再参与页面。

## Colors

四套原版配色、名称、色样和明暗映射保持原样：暮紫沉蓝、桃焰玄夜、星绿堇夜、凝光橙晓。精确值由原版 `themes.css` 和 `uiPreferences.ts` 定义。不因审美偏好另换主色或底色。

## Typography

保留原版 `typography.css`、自托管字体及字重；局部字号和层级不重新统一缩放。新增测评页使用同一套字体和主题 token。

## Layout

欢迎页、学习总览、知识路线、六功能导航、设置抽屉和课堂保留原布局与响应式规则。C/数据结构的新课堂使用现有组件；兼容层只解决内部 `workspace` 类名与外壳规则冲突，不改变原版工作台布局。

用户已明确要求的例外：首页摸底题目改为入口，进入独立 `?tab=assessment&course=…` 页面逐题作答；主要功能使用网址和浏览器历史，支持后退/前进。同课程往返保留答案和题号。

## Elevation & Depth

原版阴影、光团、光晕、鼠标高光和扫描效果保持原样。不得以“干净”“克制”或“性能”为由自行关闭。

## Shapes

配色选择器的斜置色块、展开文字与预览，原版面板、按钮和欢迎页形状均保留。新增测评控件仅使用原版控件语言，不覆盖旧组件。

## Components

- 原版动态：欢迎页光团漂移、扫描/扫光、品牌呼吸、步骤入场；粒子背景、卡片高光、滚动入场、数字变化、按钮水波；页面、黑板和反馈的状态更新动画。
- 原版“减少动态”及系统 reduced-motion 仍然有效，由用户设置决定，不全局禁用。
- `styles.css`、`themes.css`、`typography.css` 为原版文件；新增的 `luckystar-adapter.css` 只处理测评独立页和必要课程兼容。
- 黑板的旧选择器冲突通过兼容层使用原色 token 修复，不重新设计黑板。
- 原版文件哈希由 `luckystarPreservation.test.ts` 固定；变更这些文件前需先确认用户是否接受差异。
- 原分支 3 个演示脚本和 74 个设计/评审资源完整保留。

## Do's and Don'ts

- 保留本地最新数据库、API、课程包和 C/数据结构功能，不用旧分支覆盖后端。
- 新功能优先放在独立组件和兼容层，避免覆盖原版 CSS。
- 保留真实服务错误；没有数据不伪装成完整学习结果。
- 必须取舍原版效果、内容或交互时先向用户解释，让用户决定。
- 不以文件“存在”替代动画和交互验收；实际检查入口、样式和 reduced-motion 状态。
