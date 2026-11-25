<script setup lang="ts">
import { computed, ref } from "vue";
import type { ActivityDetail, ActivitySummary } from "../services/api";
import type { ProjectCheck } from "../services/projectChecks";

const props = defineProps<{
  project: ActivityDetail; activities: ActivitySummary[]; checks: Record<string, ProjectCheck>;
  resumeChecks: boolean;
}>();
const emit = defineEmits<{ practice: [id: string] }>();
const steps = ["项目任务", "分项验证", "提交与复盘"] as const;
const step = ref(props.resumeChecks ? 1 : 0);
const tasks = computed(() => (props.project.verification_exercise_ids ?? []).map(id => ({
  id, title: props.activities.find(item => item.id === id)?.title ?? id, check: props.checks[id],
})));
const verifiedCount = computed(() => tasks.value.filter(task => task.check).length);
</script>

<template>
  <div class="project-studio">
    <nav class="segment-rail" aria-label="项目学习阶段">
      <button v-for="(label,i) in steps" :key="label" :aria-current="step === i ? 'step' : undefined" @click="step = i">
        <span class="stage-index" aria-hidden="true">{{ i + 1 }}</span><span>{{ label }}</span>
      </button>
    </nav>
    <section v-if="step === 0" aria-label="项目任务">
      <slot name="brief" /><button class="secondary" @click="step = 1">进入分项验证 →</button>
    </section>
    <section v-else-if="step === 1" aria-label="分项验证">
      <header class="check-heading"><h3>编程能力验证</h3><small v-if="tasks.length">{{ verifiedCount }} / {{ tasks.length }} 项有验证记录</small></header>
      <ol v-if="tasks.length" class="check-list">
        <li v-for="task in tasks" :key="task.id">
          <div><h4>{{ task.title }}</h4><small>{{ task.id }}</small>
            <span v-if="task.check">上次提交通过 {{ task.check.passed }} / {{ task.check.total }} 项测试 · {{ new Date(task.check.at).toLocaleString() }}</span>
            <span v-else>尚无验证记录</span></div>
          <button class="secondary" @click="emit('practice', task.id)">打开练习 →</button>
        </li>
      </ol>
      <p v-else>本项目按交付要求提交实现说明和自测记录。</p>
      <button class="secondary" @click="step = 2">整理项目证据 →</button>
    </section>
    <section v-else aria-label="提交与复盘">
      <details v-if="tasks.some(t => t.check)" open><summary>分项验证记录</summary>
        <p v-for="task in tasks.filter(t => t.check)" :key="task.id">{{ task.title }} · 上次提交 {{ task.check?.passed }} / {{ task.check?.total }} 项通过</p>
      </details>
      <slot name="submit" />
    </section>
  </div>
</template>

<style scoped>
.project-studio { display:grid; gap:clamp(18px,2.4vw,30px); margin-top:20px; }
.project-studio > nav { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:4px; padding:5px; border:1px solid var(--line); background:var(--surface-muted); border-radius:12px; }
.project-studio nav button { display:flex; align-items:center; justify-content:center; gap:9px; min-width:0; min-height:46px; padding:6px; font:inherit; font-size:14px; color:var(--muted); background:transparent; border:1px solid transparent; border-radius:8px; cursor:pointer; }
.project-studio nav button[aria-current=step] { color:var(--ink); background:var(--surface-raised); border-color:var(--line); font-weight:700; }
.stage-index { display:grid; place-items:center; flex:none; width:24px; height:24px; border:1px solid currentColor; border-radius:50%; font:600 13px/1 Consolas,monospace; }
[aria-current=step] .stage-index { border-color:var(--accent); color:var(--accent-contrast); background:var(--accent); }
.project-studio section { min-width:0; }
.check-heading,.check-list li { display:flex; justify-content:space-between; align-items:center; gap:12px; }
.check-heading { flex-wrap:wrap; }
h3,h4 { margin:0; } h3 { font-size:20px; } h4 { font-size:17px; overflow-wrap:anywhere; }
.check-heading small,.check-list small,.check-list span { color:var(--muted); }
.check-list { padding:0; margin:14px 0 18px; list-style:none; border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.check-list li { padding:16px clamp(12px,2vw,22px); background:var(--surface-raised); }
.check-list li + li { border-top:1px solid var(--line); }
.check-list small { display:inline-block; font:12px/1.6 Consolas,monospace; margin-top:5px; }
.check-list span { display:inline-block; font-size:13px; border-inline-start:1px solid var(--line); margin-inline-start:10px; padding-inline-start:10px; }
.secondary { flex-shrink:0; min-height:44px; padding:8px 14px; border:1px solid var(--line); border-radius:8px; font:inherit; font-size:14px; color:var(--ink); background:var(--surface-raised); cursor:pointer; }
.secondary:hover,nav button:hover { border-color:var(--accent); }
.project-studio section > .secondary { color:var(--accent-contrast); border-color:var(--accent); background:var(--accent); font-weight:650; }
details { padding:14px; border:1px solid var(--line); border-radius:8px; } summary { cursor:pointer; }
:is(button,summary):focus-visible { outline:2px solid var(--accent-ink); outline-offset:2px; }
@media(max-width:640px) {
  .project-studio nav button { flex-direction:column; gap:4px; font-size:13px; }
  .check-list li { flex-wrap:wrap; }.check-list li .secondary { margin-inline-start:auto; }
}
</style>
