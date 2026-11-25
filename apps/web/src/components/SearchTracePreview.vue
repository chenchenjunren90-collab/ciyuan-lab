<script setup lang="ts">
import { computed, ref } from "vue";

const values = [3, 7, 12, 18, 26, 34, 49];
const positions = [
  [385, 34], [214, 89], [385, 132], [52, 166], [385, 211], [214, 253], [385, 300],
] as const;
const edges = [[3, 1], [3, 5], [1, 0], [1, 2], [5, 4], [5, 6]] as const;
const target = ref(26);
const visited = computed(() => {
  const path: number[] = [];
  let left = 0;
  let right = values.length - 1;
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    path.push(mid);
    if (values[mid] === target.value) break;
    if (values[mid]! < target.value) left = mid + 1;
    else right = mid - 1;
  }
  return path;
});
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
    <svg viewBox="0 0 470 343" role="img" :aria-label="'查找 ' + target + ' 的比较路径：' + visited.map(i => values[i]).join('、')">
      <g v-for="[start, end] in edges" :key="end" :class="{ traversed: visited.includes(end) }">
        <path class="rail" :d="edgePath(start, end)" />
        <path v-if="visited.includes(end)" class="signal" :d="edgePath(start, end)" />
      </g>
      <g v-for="(value, i) in values" :key="value" :transform="'translate(' + positions[i]!.join(' ') + ')'" :class="{ traversed: visited.includes(i) }">
        <circle r="6"/><text y="-13" text-anchor="middle">a[{{ i }}] = {{ value }}</text>
      </g>
    </svg>
    <div class="trace-caption" aria-live="polite"><span>比较路径</span><b>{{ visited.map(i => values[i]).join(" → ") }}</b><span>{{ visited.length }} 次比较</span></div>
  </figure>
</template>

<style scoped>
.search-trace { margin:0; min-width:0; }
figcaption,.trace-caption { display:flex; gap:10px; align-items:center; flex-wrap:wrap; font-size:13px; }
figcaption { padding-bottom:10px; justify-content:space-between; border-bottom:1px solid var(--line); }
figcaption strong { color:var(--ink); font-size:16px; } label { color:var(--muted); }
select { margin-left:5px; min-height:40px; padding:3px 6px; color:var(--ink); border:1px solid var(--line); background:var(--surface-raised); font:inherit; }
svg { display:block; width:100%; height:auto; }
.rail,.signal { fill:none; stroke-linecap:round; stroke-linejoin:round; }
.rail { stroke:var(--muted); stroke-width:1.6; } .traversed .rail { stroke:var(--ink); stroke-width:3; }
.signal { stroke:var(--trace-signal); stroke-width:2; }
circle { fill:var(--surface); stroke:var(--muted); stroke-width:2; } .traversed circle { fill:var(--surface-raised); stroke:var(--trace-signal); stroke-width:3; }
text { fill:var(--muted); font:14px Consolas,monospace; } .traversed text { fill:var(--ink); font-weight:700; }
.trace-caption { border-top:1px solid var(--line); padding:12px 0; color:var(--muted); }
.trace-caption b { color:var(--ink); font:600 15px Consolas,monospace; }
.trace-caption span:last-child { margin-inline-start:auto; }
</style>
