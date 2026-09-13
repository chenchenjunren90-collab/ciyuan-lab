<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { CODE_PREVIEW_LINES } from "./boardTools";
const props = defineProps<{ code: string }>();
const expanded = ref(false);
const lines = computed(() => props.code.trimEnd().split("\n"));
const canExpand = computed(() => lines.value.length > CODE_PREVIEW_LINES);
const visibleCode = computed(() => expanded.value ? props.code : lines.value.slice(0, CODE_PREVIEW_LINES).join("\n"));
watch(() => props.code, () => { expanded.value = false; });
</script>

<template>
  <section v-if="code.trim()" class="classroom-code-example">
    <header><b>示例代码</b><button v-if="canExpand" type="button" :aria-expanded="expanded" @click="expanded = !expanded">{{ expanded ? '收起代码' : `展开全部 ${lines.length} 行` }}</button></header>
    <pre><code>{{ visibleCode }}</code></pre>
    <small v-if="canExpand && !expanded">当前显示前 {{ CODE_PREVIEW_LINES }} 行</small>
  </section>
</template>

<style scoped>
.classroom-code-example { min-width: 0; }
header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
b { color: var(--ink); font-size: 13px; }
button { padding: 7px 10px; border: 1px solid var(--line); border-radius: 6px; color: var(--accent-ink); background: var(--surface-raised); cursor: pointer; font: inherit; font-size: 12px; }
button:hover { border-color: var(--accent); }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
pre { margin: 9px 0 0; padding: 14px; max-width: 100%; overflow-x: auto; border-radius: 6px; background: var(--surface-muted); color: var(--ink); scrollbar-width: thin; scrollbar-color: var(--muted) var(--surface-muted); }
code { font: 13px/1.75 Consolas, "Cascadia Mono", monospace; white-space: pre; }
small { display: block; margin-top: 7px; color: var(--muted); font-size: 12px; }
</style>
