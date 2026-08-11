<script setup lang="ts">
import { onMounted, ref } from "vue";

import { fetchApiHealth } from "./services/api";

type ConnectionState = "connecting" | "online" | "offline";
const connectionState = ref<ConnectionState>("connecting");

const courses = [
  { id: "c", title: "C语言程序设计", description: "语法、指针、内存与调试基础" },
  { id: "python", title: "Python程序设计", description: "程序设计、数据处理与应用实践" },
  { id: "data_structures", title: "数据结构与算法", description: "结构、算法、复杂度与问题求解" }
] as const;

const capabilities = [
  "学习路径规划",
  "课程知识检索",
  "分级练习与 Debug",
  "代码验证",
  "学习画像更新",
  "下一任务推荐"
] as const;

onMounted(async () => {
  try {
    await fetchApiHealth();
    connectionState.value = "online";
  } catch {
    connectionState.value = "offline";
  }
});
</script>

<template>
  <main class="page-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">三周 MVP · 技术骨架</p>
        <h1>词元研究所</h1>
        <p class="subtitle">多智能体协同驱动的计算机学科助学服务平台</p>
      </div>
      <div class="connection" :data-state="connectionState">
        <span aria-hidden="true"></span>
        API {{ connectionState === "online" ? "已连接" : connectionState === "offline" ? "未连接" : "连接中" }}
      </div>
    </header>

    <section aria-labelledby="courses-heading">
      <div class="section-heading">
        <div>
          <p class="eyebrow">COURSE PACKS</p>
          <h2 id="courses-heading">三门课程同步建设</h2>
        </div>
        <p>每门课目标约 40 个核心知识点；当前只声明建设目标，不虚构已完成内容。</p>
      </div>
      <div class="course-grid">
        <article v-for="course in courses" :key="course.id" class="course-card">
          <span class="course-code">{{ course.id }}</span>
          <h3>{{ course.title }}</h3>
          <p>{{ course.description }}</p>
          <div class="progress-label"><span>课程包状态</span><strong>待建设</strong></div>
          <div class="progress-track"><span></span></div>
        </article>
      </div>
    </section>

    <section class="capability-panel" aria-labelledby="capabilities-heading">
      <div>
        <p class="eyebrow">SHARED CAPABILITIES</p>
        <h2 id="capabilities-heading">一套平台能力，服务三门课程</h2>
        <p>课程负责人维护内容；公共模块统一处理检索、编排、代码验证与学生画像。</p>
      </div>
      <ol>
        <li v-for="(capability, index) in capabilities" :key="capability">
          <span>{{ String(index + 1).padStart(2, "0") }}</span>{{ capability }}
        </li>
      </ol>
    </section>
  </main>
</template>
