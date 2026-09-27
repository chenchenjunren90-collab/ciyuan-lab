<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { buildTrace, parseTraceInput, traceKinds, type TeachingTrace, type TraceKind } from "./algorithmTrace";

const props = defineProps<{ initialKind: TraceKind; courseId: "c" | "data_structures" }>();
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
  <section class="algorithm-lab" aria-label="算法与内存演示">
    <header><div><h3>先预测，再走一步</h3></div><label>演示主题<select v-model="kind"><option v-for="[id, name] in available" :key="id" :value="id">{{ name }}</option></select></label></header>
    <p class="notice">这是教学模型。你的程序仍需在练习区通过编译或隐藏测试验证。</p>
    <form class="inputs" @submit.prevent="rebuild">
      <label v-if="!['memory', 'bfs'].includes(kind)">输入序列<input v-model="input" maxlength="100" placeholder="留空演示空序列" /></label>
      <label v-if="kind === 'binary'">查找目标<input v-model="target" inputmode="numeric" maxlength="4" /></label>
      <button type="submit">生成步骤 / 重置</button>
    </form>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-else-if="!trace" role="status">输入已修改，点击“生成步骤”查看新结果。</p>
    <template v-if="trace && frame">
      <p class="invariant"><b>始终成立的规则</b>{{ trace.invariant }}</p>
      <div class="cells" :aria-label="trace.title"><div v-for="(cell, i) in frame.cells" :key="i" class="cell" :class="{ active: frame.active.includes(i) }"><small>{{ kind === 'pointer' ? ['a', 'b'][i] : `位置 ${i}` }}</small><strong>{{ cell }}</strong><span v-if="frame.active.includes(i)">当前操作</span></div><span v-if="!frame.cells.length">空结构</span></div>
      <dl><template v-for="(value, name) in frame.variables" :key="name"><dt>{{ name }}</dt><dd>{{ value }}</dd></template></dl>
      <p class="step-note" aria-live="polite">{{ frame.note }}</p>
      <p v-if="frame.output"><b>当前输出：</b><code>{{ frame.output }}</code></p>
      <nav aria-label="演示播放控制"><button :disabled="index === 0" @click="move(-1)">上一步</button><button :aria-pressed="playing" @click="play">{{ playing ? '暂停' : '自动播放' }}</button><button :disabled="index === trace.frames.length - 1" @click="move(1)">下一步</button><span>{{ index + 1 }} / {{ trace.frames.length }}</span></nav>
      <details><summary>查看对应代码 / 伪代码与复杂度</summary><pre><code>{{ trace.code }}</code></pre><p>{{ trace.complexity }}</p></details>
    </template>
  </section>
</template>

<style scoped>
.algorithm-lab { padding:24px; border:1px solid var(--line); background:var(--surface-raised); border-radius:12px; color:var(--ink); }
header,.inputs,nav { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }header{justify-content:space-between;}h3{margin:6px 0;}small,.notice{color:var(--muted);}label{display:grid;gap:6px;font-size:13px;}input,select,button{min-height:44px;padding:8px 12px;border:1px solid var(--line);border-radius:6px;background:var(--surface-raised);color:var(--ink);}button{cursor:pointer;}button:disabled{opacity:.45;cursor:default;}.invariant{display:grid;gap:8px;padding:16px;background:var(--accent-pale);line-height:1.7;}.cells{display:flex;gap:8px;flex-wrap:wrap;min-height:95px;align-items:center;margin:24px 0;}.cell{min-width:68px;padding:12px;border:1px solid var(--line);border-radius:6px;display:grid;gap:7px;text-align:center;}.cell.active{outline:2px solid var(--accent);background:var(--accent-pale);}.cell span{font-size:11px;color:var(--accent-ink);}strong{font-family:Consolas,monospace;}dl{display:flex;gap:10px;flex-wrap:wrap;}dt{font-weight:700;}dd{margin:0 14px 0 0;font-family:Consolas,monospace;}.step-note{min-height:48px;line-height:1.8;}nav{margin:18px 0;}summary{cursor:pointer;padding:12px 0;}pre{overflow:auto;padding:16px;background:var(--code);color:var(--code-ink);border-radius:8px;font:13px/1.7 Consolas,monospace;}button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px;}@media(max-width:600px){input,select{font-size:16px;max-width:100%;}.algorithm-lab{padding:14px;}.inputs label{width:100%;}.cell{min-width:54px;}}
</style>
