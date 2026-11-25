<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import CourseQuestionPanel from "./CourseQuestionPanel.vue";
import { frameQuestion, buildTrace, parseTraceInput, traceConcepts, traceKinds, type TeachingTrace, type TraceKind } from "./algorithmTrace";

const props = defineProps<{ studentId: string; initialKind: TraceKind; courseId: "c" | "data_structures" }>();
const reference = ref<{ label: string; question: string; pointId: string }>();
const kind = ref<TraceKind>(props.initialKind);
const input = ref("1 2 2 5 8"), target = ref("2"), index = ref(0), error = ref("");
const trace = ref<TeachingTrace | null>(null), playing = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;
const available = computed(() => Object.entries(traceKinds).filter(([key]) => props.courseId === "c"
  ? ["pointer", "array", "memory"].includes(key) : !["pointer", "array", "memory"].includes(key)));
const frame = computed(() => trace.value?.frames[index.value]);
function pause() { if (timer) clearInterval(timer); timer = undefined; playing.value = false; }
function rebuild() {
  pause(); index.value = 0; error.value = ""; trace.value = null;
  try {
    if (kind.value === "binary" && !/^-?\d+$/.test(target.value)) throw new Error("查找目标应为整数。");
    trace.value = buildTrace(kind.value, ["bfs", "memory"].includes(kind.value) ? [] : parseTraceInput(input.value), kind.value === "binary" ? Number(target.value) : 2);
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "无法构建演示。"; }
}
function askFrame() {
  if (!trace.value) return;
  pause();
  reference.value = {
    label: trace.value.title + " · 第 " + (index.value + 1) + " 步",
    pointId: traceConcepts[kind.value],
    question: frameQuestion(trace.value, index.value, kind.value === "binary" ? Number(target.value) : undefined,
      ["bfs", "memory"].includes(kind.value) ? undefined : parseTraceInput(input.value)),
  };
}
function move(offset: number) { pause(); index.value = Math.max(0, Math.min((trace.value?.frames.length ?? 1) - 1, index.value + offset)); }
function play() {
  if (playing.value) { pause(); return; }
  if (!trace.value) return;
  if (index.value === trace.value.frames.length - 1) index.value = 0;
  playing.value = true;
  timer = setInterval(() => {
    if (index.value >= (trace.value?.frames.length ?? 1) - 1) pause();
    else index.value++;
  }, 1400);
}
watch(() => props.initialKind, value => { kind.value = value; }, { immediate: true });
watch(kind, rebuild, { immediate: true });
watch([input, target], () => { pause(); trace.value = null; });
onBeforeUnmount(pause);
</script>

<template>
  <div class="lab-studio">
    <section class="algorithm-lab" aria-label="算法与内存演示">
      <header class="lab-heading">
        <div><small>交互实验</small><h3>{{ traceKinds[kind] }}</h3></div>
        <label>切换实验<select v-model="kind"><option v-for="[id, name] in available" :key="id" :value="id">{{ name }}</option></select></label>
      </header>
      <template v-if="trace && frame">
        <div class="trace-screen">
          <div class="trace-heading"><b>运行状态</b><span>第 {{ index + 1 }} / {{ trace.frames.length }} 步</span></div>
          <div class="cells" :aria-label="trace.title">
            <div v-for="(cell, i) in frame.cells" :key="i" class="cell" :class="{ active: frame.active.includes(i) }">
              <small>{{ kind === 'pointer' ? ['a', 'b'][i] : `[ ${i} ]` }}</small>
              <strong>{{ cell }}</strong>
              <span v-if="frame.active.includes(i)">当前</span>
            </div>
            <span v-if="!frame.cells.length">空结构</span>
          </div>
          <dl v-if="Object.keys(frame.variables).length" class="variables">
            <div v-for="(value, name) in frame.variables" :key="name"><dt>{{ name }}</dt><dd>{{ value }}</dd></div>
          </dl>
          <p class="step-note" aria-live="polite">{{ frame.note }}</p>
          <p v-if="frame.output" class="trace-output"><b>当前输出</b> <code>{{ frame.output }}</code></p>
          <progress :value="index + 1" :max="trace.frames.length" aria-label="演示步骤进度"></progress>
        </div>
        <nav class="trace-controls" aria-label="演示播放控制">
          <button :disabled="index === 0" @click="move(-1)">上一步</button>
          <button :aria-pressed="playing" @click="play">{{ playing ? '暂停' : '自动播放' }}</button>
          <button :disabled="index === trace.frames.length - 1" @click="move(1)">下一步</button>
          <button class="ask-frame" @click="askFrame">问这一步 ↗</button>
        </nav>
        <p class="invariant"><b>不变量</b>{{ trace.invariant }}</p>
      </template>
      <details v-if="!['memory','bfs'].includes(kind)" class="lab-detail">
        <summary>实验输入<span>{{ input || '空序列' }}{{ kind === 'binary' ? ' · 目标 ' + target : '' }}</span></summary>
        <form class="inputs" @submit.prevent="rebuild">
          <label>输入序列<input v-model="input" maxlength="100" placeholder="留空演示空序列" /></label>
          <label v-if="kind === 'binary'">查找目标<input v-model="target" inputmode="numeric" maxlength="4" /></label>
          <button type="submit">生成步骤</button>
        </form>
      </details>
      <button v-else class="restart" @click="rebuild">重置演示</button>
      <p v-if="error" class="lab-message" role="alert">{{ error }}</p>
      <p v-else-if="!trace" class="lab-message" role="status">输入已修改，展开实验输入并点击「生成步骤」查看结果。</p>
      <details v-if="trace" class="lab-detail"><summary>代码与复杂度</summary><pre><code>{{ trace.code }}</code></pre><p>{{ trace.complexity }}</p></details>
      <small class="lab-footnote">教学演示 · 程序正确性以练习区的编译和测试结果为准</small>
    </section>
    <CourseQuestionPanel :student-id="studentId" :course-id="courseId" :reference="reference" />
  </div>
</template>

<style scoped>
.lab-studio { display:grid; gap:16px; align-items:start; }
@media(min-width:1150px) { .lab-studio { grid-template-columns:minmax(0,1.9fr) minmax(244px,1fr); } }
.algorithm-lab { min-width:0; padding:clamp(15px,1.6vw,26px); border:1px solid var(--line); border-radius:16px; background:var(--surface-raised); }
.lab-heading,.trace-heading,.trace-controls,.variables,.inputs { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.lab-heading,.trace-heading { justify-content:space-between; }
.lab-heading { margin-bottom:18px; }
.lab-heading h3 { margin:2px 0 0; font-size:clamp(19px,2vw,25px); }
.lab-heading small,label,.lab-footnote { font-size:12px; color:var(--muted); }
label { display:grid; gap:4px; min-width:0; }
input,select,button { font:inherit; color:var(--ink); background:var(--surface-raised); border:1px solid var(--line); border-radius:8px; min-height:44px; padding:7px 12px; }
input,select { max-width:100%; }
button,summary { cursor:pointer; }
button:disabled { opacity:.45; cursor:default; }
button:not(:disabled):hover,summary:hover { color:var(--accent-ink); }
.trace-screen {
  --board:var(--surface-muted); --board-ink:var(--ink); --board-muted:var(--muted);
  position:relative; overflow:hidden; padding:clamp(16px,2vw,28px); border-radius:12px;
  color:var(--board-ink); background-color:var(--board);
  border:1px solid var(--line);
}
.trace-heading { color:var(--board-muted); font-size:12px; }
.trace-heading b { color:var(--board-ink); font-size:14px; }
.trace-heading span,.cell small,.variables { font-variant-numeric:tabular-nums; }
.cells { display:flex; flex-wrap:wrap; align-items:stretch; gap:6px; margin:23px 0 18px; }
.cell { display:grid; align-content:start; justify-items:center; gap:2px; flex:0 1 auto; min-width:46px; max-width:100%; padding:7px 8px; border:1px solid var(--line); border-radius:7px; color:var(--board-ink); background:var(--surface-raised); overflow-wrap:anywhere; }
.cell small,.cell span { color:var(--board-muted); font:11px/1.5 var(--font-body); }
.cell strong { font:650 20px/1.3 Consolas,monospace; }
.cell.active { color:var(--accent-contrast); background:var(--accent); border-color:var(--accent); }
.cell.active :is(small,span) { color:inherit; }
.variables { gap:5px 16px; margin:0; }
.variables div { display:flex; gap:6px; font:14px/1.5 Consolas,monospace; }
.variables dt { color:var(--board-muted); }
.variables dd { margin:0; font-weight:700; overflow-wrap:anywhere; }
.step-note { margin:14px 0 0; padding-top:12px; border-top:1px solid var(--line); font-size:15px; line-height:1.65; }
.trace-output { margin:8px 0 0; overflow-wrap:anywhere; }
.trace-screen progress { position:absolute; bottom:0; inset-inline:0; width:100%; height:4px; appearance:none; border:0; background:var(--line); }
progress::-webkit-progress-bar { background:var(--line); } progress::-webkit-progress-value { background:var(--accent); } progress::-moz-progress-bar { background:var(--accent); }
.trace-controls { margin:12px 0 18px; gap:6px; }
.trace-controls button { font-size:14px; }
.trace-controls .ask-frame { margin-inline-start:auto; background:var(--accent); color:var(--accent-contrast); border-color:var(--accent); font-weight:700; }
.trace-controls .ask-frame:hover { color:var(--accent-contrast); filter:brightness(.94); }
.invariant { margin:16px 0; padding:3px 0 3px 12px; border-inline-start:3px solid var(--accent); font-size:14px; line-height:1.65; }
.invariant b { display:block; color:var(--accent-ink); }
.lab-detail { border-top:1px solid var(--line); }
summary { padding:12px 0; font-weight:600; }
summary span { margin-inline-start:10px; color:var(--muted); font-weight:400; font-size:13px; overflow-wrap:anywhere; }
.inputs { align-items:end; margin:0 0 14px; } .inputs input { width:100%; font-size:16px; }
pre { max-width:100%; overflow:auto; padding:14px; color:var(--code-ink); background:var(--code); border-radius:8px; }
.lab-footnote { display:block; margin-top:9px; line-height:1.6; }
.lab-message { color:var(--accent-ink); }
.restart { margin-bottom:8px; }
:is(button,select,input,summary):focus-visible { outline:2px solid var(--accent-ink); outline-offset:2px; }
@media(max-width:600px) { .trace-controls { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); } .trace-controls button { padding-inline:4px; } .trace-controls .ask-frame { grid-column:1/-1; width:100%; } }
</style>
