<script setup lang="ts">
import { computed, ref, watch } from "vue";

const values = [3, 7, 12, 18, 26, 34, 49];
const positions = [
  [385, 34], [214, 89], [385, 132], [52, 166], [385, 211], [214, 253], [385, 300],
] as const;
const edges = [[3, 1], [3, 5], [1, 0], [1, 2], [5, 4], [5, 6]] as const;
const target = ref(26);
const step = ref(0);
const comparisons = computed(() => {
  const path: { left: number; right: number; mid: number; branch: number }[] = [];
  let left = 0;
  let right = values.length - 1;
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const value = values[mid]!;
    const branch = value < target.value ? 0 : value > target.value ? 1 : 2;
    path.push({ left, right, mid, branch });
    if (branch === 2) break;
    if (branch === 0) left = mid + 1;
    else right = mid - 1;
  }
  return path;
});
const current = computed(() => comparisons.value[step.value]!);
const visited = computed(() => comparisons.value.slice(0, step.value + 1).map(frame => frame.mid));
const branches = [
  ["if a[mid] < target:", "left = mid + 1"],
  ["elif a[mid] > target:", "right = mid - 1"],
  ["else:", "return mid"],
];
watch(target, () => { step.value = 0; }, { flush: "sync" });
function edgePath(start: number, end: number) {
  const [x, y] = positions[start]!, [nx, ny] = positions[end]!;
  const bend = (x + nx) / 2;
  return 'M' + x + ' ' + y + ' H' + (bend - 22) + ' L' + (bend + 22) + ' ' + ny + ' H' + nx;
}
</script>

<template>
  <figure class="search-trace">
    <figcaption><strong>二分查找</strong><label>目标值
      <select v-model.number="target" aria-label="二分查找目标值"><option v-for="n in values" :key="n" :value="n">{{ n }}</option></select>
    </label></figcaption>
    <div class="trace-registers"><span>当前区间 <code>[{{ current.left }}, {{ current.right }}]</code></span>
      <span>中点 <code>a[{{ current.mid }}] = {{ values[current.mid] }}</code></span></div>
    <ol class="trace-branches" aria-label="比较分支">
      <li v-for="(row, i) in branches" :key="row[0]" :aria-current="current.branch === i ? 'step' : undefined">
        <span class="branch-pointer" aria-hidden="true">{{ current.branch === i ? '›' : '' }}</span>
        <code>{{ row[0] }} <span>{{ row[1] }}</span></code>
      </li>
    </ol>
    <div class="trace-stepper">
      <span aria-live="polite">第 {{ step + 1 }} / {{ comparisons.length }} 次比较 · {{ ['向右查找', '向左查找', '找到目标'][current.branch] }}</span>
      <div><button type="button" :disabled="step === 0" @click="step--">上一步</button>
        <button type="button" :disabled="step + 1 === comparisons.length" @click="step++">下一步</button></div>
    </div>
    <details><summary>比较路径<span>{{ visited.map(i => values[i]).join(" → ") }}</span></summary>
    <svg viewBox="0 0 470 343" role="img" :aria-label="'查找 ' + target + ' 的比较路径：' + visited.map(i => values[i]).join('、')">
      <g v-for="[start, end] in edges" :key="end" :class="{ traversed: visited.includes(end) }">
        <path class="rail" :d="edgePath(start, end)" />
        <path v-if="visited.includes(end)" class="signal" :d="edgePath(start, end)" />
      </g>
      <g v-for="(value, i) in values" :key="value" :transform="'translate(' + positions[i]!.join(' ') + ')'" :class="{ traversed: visited.includes(i) }">
        <circle r="6"/><text y="-13" text-anchor="middle">a[{{ i }}] = {{ value }}</text>
      </g>
    </svg>
    </details>
  </figure>
</template>

<style scoped>
.search-trace { position:relative; margin:0; min-width:0; padding:16px clamp(12px,2vw,28px); border-block:1px solid var(--line); color:var(--ink); }
.search-trace::before,.search-trace::after { position:absolute; content:""; width:13px; height:13px; border-color:var(--trace-signal); border-style:solid; pointer-events:none; }
.search-trace::before { top:-1px; left:0; border-width:1px 0 0 1px; }
.search-trace::after { bottom:-1px; right:0; border-width:0 1px 1px 0; }
figcaption,.trace-registers,.trace-stepper { display:flex; align-items:center; flex-wrap:wrap; gap:8px 16px; }
figcaption,.trace-stepper { justify-content:space-between; }
figcaption strong { font-size:clamp(20px,2vw,28px); }
label,.trace-registers,.trace-stepper,summary { color:var(--muted); font-size:14px; }
select,.trace-stepper button { min-height:44px; padding:4px 12px; border-radius:24px; border:1px solid var(--line); background:var(--surface-raised); color:var(--ink); font:inherit; }
select { margin-left:6px; }
.trace-registers { padding:16px 0 10px; }
.trace-registers code { color:var(--ink); white-space:nowrap; }
.trace-branches { margin:0; list-style:none; padding:10px 0; border-block:1px dotted var(--line); }
.trace-branches li { display:flex; gap:6px; padding:4px 0; color:var(--muted); }
.trace-branches code { font-size:clamp(12px,1.2vw,15px); white-space:normal; overflow-wrap:anywhere; }
.trace-branches code span { display:inline-block; }
.trace-branches [aria-current=step] { color:var(--ink); font-weight:700; }
.branch-pointer { color:var(--trace-signal); width:12px; flex:none; }
.trace-stepper { padding:12px 0; }
.trace-stepper button:disabled { opacity:.5; cursor:default; }
details { border-top:1px solid var(--line); }
summary { padding:10px 0; cursor:pointer; }
summary span { color:var(--ink); margin-left:12px; }
svg { display:block; width:100%; height:auto; }
.rail,.signal { fill:none; stroke-linecap:round; stroke-linejoin:round; }
.rail { stroke:var(--muted); stroke-width:1.6; } .traversed .rail { stroke:var(--ink); stroke-width:3; }
.signal { stroke:var(--trace-signal); stroke-width:2; }
circle { fill:var(--surface); stroke:var(--muted); stroke-width:2; } .traversed circle { fill:var(--surface-raised); stroke:var(--trace-signal); stroke-width:3; }
text { fill:var(--muted); font-size:14px; } .traversed text { fill:var(--ink); font-weight:700; }
</style>
