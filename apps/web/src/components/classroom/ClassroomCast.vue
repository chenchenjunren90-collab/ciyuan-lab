<script setup lang="ts">
import type { ClassroomRole } from "../../services/api";
import ClassroomPortrait from "./ClassroomPortrait.vue";
defineProps<{ activeRole: ClassroomRole; selectedRole: ClassroomRole }>();
const emit = defineEmits<{ select: [role: ClassroomRole] }>();
const cast = [
  { role: "teacher", name: "林老师", description: "讲解与答疑" },
  { role: "peer_cautious", name: "小禾", description: "认真提问" },
  { role: "peer_debugger", name: "阿拓", description: "一起排错" },
  { role: "peer_summarizer", name: "宁宁", description: "整理笔记" },
] as const;
</script>

<template>
  <section class="classroom-cast" aria-label="课堂师生">
    <header><b>课堂师生</b><span>选择一位，继续交流</span></header>
    <div class="cast-members">
      <button v-for="person in cast" :key="person.role" type="button" :aria-label="`和${person.name}交流`" :aria-pressed="selectedRole === person.role" @click="emit('select', person.role)">
        <ClassroomPortrait :person="person.role" />
        <span class="cast-name">{{ person.name }}</span>
        <span class="cast-description">{{ person.description }}</span>
        <span class="cast-status">{{ activeRole === person.role ? '正在发言' : selectedRole === person.role ? '已选择' : '参与课堂' }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.classroom-cast { margin-top: 24px; color: var(--ink); }
header { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
header b { font-size: 14px; } header span { color: var(--muted); font-size: 12px; }
.cast-members { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
button { display: flex; flex-direction: column; align-items: center; gap: 5px; min-width: 0; padding: 12px 4px; border: 1px solid transparent; border-radius: 8px; background: transparent; color: inherit; font: inherit; cursor: pointer; }
button:hover { background: var(--surface-raised); border-color: var(--line); }
button[aria-pressed="true"] { border-color: var(--accent); background: var(--accent-pale); }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.cast-name { margin-top: 4px; font-size: 14px; font-weight: 700; }
.cast-description { color: var(--muted); font-size: 12px; }
.cast-status { min-height: 18px; color: var(--accent-ink); font-size: 11px; }
@media (max-width: 480px) { .cast-members { grid-template-columns: repeat(2,minmax(0,1fr)); } }
</style>
