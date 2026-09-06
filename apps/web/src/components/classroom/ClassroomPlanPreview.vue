<script setup lang="ts">
import type { ClassroomLesson } from "../../services/api";
defineProps<{ plan: ClassroomLesson }>();
</script>

<template>
  <article class="plan-result classroom-plan-preview" aria-label="本次课堂安排">
    <header><div><b>助教小程 · 本次课堂安排</b><h3>{{ plan.title }}</h3><span>{{ plan.subtitle }}</span></div></header>
    <p>{{ plan.planning_reason }}</p>
    <ul><li v-for="goal in plan.beats[0]?.board_points ?? []" :key="goal">{{ goal }}</li></ul>
    <p><b>学习顺序：</b>{{ plan.beats.map(beat => beat.title).join(" → ") }}</p>
    <small>{{ plan.beats.length }} 个环节 · {{ plan.duration_minutes }} 分钟 · 依据已有测评、前置关系与课程讲义编排</small>
  </article>
</template>

<style scoped>
.classroom-plan-preview { padding:18px; color:var(--ink); border:1px solid var(--line); border-radius:10px; background:var(--surface-raised); }
h3 { margin:8px 0; } p,li { line-height:1.8; } small,header span { color:var(--muted); }
</style>
