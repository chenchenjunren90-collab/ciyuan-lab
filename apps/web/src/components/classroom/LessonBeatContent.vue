<script setup lang="ts">
import type { ClassroomBeat } from "../../services/api";
import SafeMarkdown from "../SafeMarkdown.vue";
defineProps<{ beat: ClassroomBeat }>();
</script>

<template>
  <article class="lesson-beat-content" :aria-label="`${beat.title}讲义`">
    <h4>{{ beat.board_title }}</h4>
    <SafeMarkdown :source="beat.board_explanation" />
    <ul v-if="beat.board_points.length"><li v-for="point in beat.board_points" :key="point">{{ point }}</li></ul>
    <section v-if="beat.board_code"><b>完整示例</b><pre><code>{{ beat.board_code }}</code></pre></section>
    <section v-if="beat.board_trace.length"><b>{{ beat.phase === 'summary' ? '复盘与下一步' : '按执行顺序理解' }}</b><ol><li v-for="step in beat.board_trace" :key="step">{{ step }}</li></ol></section>
  </article>
</template>

<style scoped>
.lesson-beat-content { min-width:0; margin:18px 0; padding:18px; border:1px solid var(--line); border-radius:10px; color:var(--ink); background:var(--surface-muted); font-size:14px; line-height:1.8; }
h4 { margin:0 0 12px; font-size:18px; } section { margin-top:16px; } li { margin:6px 0; }
pre { max-width:100%; overflow:auto; padding:16px; color:var(--code-ink); background:var(--code); border-radius:8px; }
code { font:14px/1.8 Consolas,monospace; } :deep(.safe-markdown) { color:var(--ink); }
</style>
