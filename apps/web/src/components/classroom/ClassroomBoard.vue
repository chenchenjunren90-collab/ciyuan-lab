<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { ClassroomBeat } from "../../services/api";
import { boardItems, type BoardNotes } from "./boardTools";
import ClassroomCodeExample from "./ClassroomCodeExample.vue";

const props = defineProps<{ beat: ClassroomBeat; notes?: BoardNotes }>();
const emit = defineEmits<{ annotate: [notes: BoardNotes] }>();
const tool = ref<"laser" | "highlight" | null>(null);
const shownCount = ref<number | null>(null);
const laser = ref<{ x: number; y: number } | null>(null);
const viewport = ref<HTMLElement | null>(null);
const items = computed(() => boardItems(props.beat));
const notes = computed<BoardNotes>(() => props.notes ?? { highlights: [], pins: {} });
const visibleItems = computed(() => shownCount.value === null ? items.value : items.value.slice(0, shownCount.value));
const hasNotes = computed(() => items.value.some(item => notes.value.highlights.includes(item.id) || notes.value.pins[item.id]));
const toolHint = computed(() => tool.value === "laser"
  ? "移动光点指示位置；点击板书固定光点，再点一次取消。定位会随课堂记录保存。"
  : tool.value === "highlight" ? "点击要点、代码或步骤标记重点，再点一次取消。高亮会随课堂记录保存。"
  : "选择工具标记板书，或按自己的节奏分步阅读。标记保存在当前浏览器。" );

watch(() => props.beat.id, () => { shownCount.value = null; laser.value = null; });
watch(shownCount, async (count, previous) => {
  await nextTick();
  if (viewport.value) viewport.value.scrollTop = count !== null && previous !== null && count > previous ? viewport.value.scrollHeight : 0;
});
watch(() => props.beat.id, () => { if (viewport.value) viewport.value.scrollTop = 0; });
function selectTool(next: "laser" | "highlight") {
  tool.value = tool.value === next ? null : next;
  laser.value = null;
}
function mark(id: string, event?: MouseEvent) {
  if (!tool.value) return;
  const next = { highlights: [...notes.value.highlights], pins: { ...notes.value.pins } };
  if (tool.value === "highlight") {
    next.highlights = next.highlights.includes(id) ? next.highlights.filter(value => value !== id) : [...next.highlights, id];
  } else if (next.pins[id]) {
    delete next.pins[id];
  } else {
    const row = (event?.currentTarget as HTMLElement | undefined)?.closest<HTMLElement>("[data-board-item]");
    const rect = row?.getBoundingClientRect();
    next.pins[id] = rect && event && event.detail > 0
      ? { x: Math.min(100, Math.max(0, (event.clientX - rect.left) / rect.width * 100)), y: Math.min(100, Math.max(0, (event.clientY - rect.top) / rect.height * 100)) }
      : { x: 97, y: 50 };
  }
  emit("annotate", next);
}
function markContent(id: string, event: MouseEvent) {
  if ((event.target as HTMLElement).closest("button, a, input, textarea")) return;
  mark(id, event);
}
function moveLaser(event: PointerEvent) {
  if (tool.value !== "laser" || event.pointerType === "touch") return;
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  laser.value = { x: event.clientX - rect.left, y: event.clientY - rect.top };
}
function clearNotes() {
  const current = new Set(items.value.map(item => item.id));
  emit("annotate", { highlights: notes.value.highlights.filter(id => !current.has(id)), pins: Object.fromEntries(Object.entries(notes.value.pins).filter(([id]) => !current.has(id))) });
  laser.value = null;
}
</script>

<template>
  <section class="classroom-board" aria-label="课堂板书">
    <header class="board-heading"><h3>{{ beat.board_title }}</h3><span>{{ beat.eyebrow }}</span></header>
    <div class="board-tools" role="group" aria-label="板书工具">
      <button type="button" :aria-pressed="tool === 'laser'" @click="selectTool('laser')"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="5"/><path d="M10 1v3m0 12v3M1 10h3m12 0h3"/></svg>激光笔</button>
      <button type="button" :aria-pressed="tool === 'highlight'" @click="selectTool('highlight')"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m6 13 7-10 4 3-7 10-4-3Zm0 0-3 4h6M2 19h16"/></svg>高亮笔</button>
      <button type="button" :aria-pressed="shownCount !== null" :disabled="items.length < 2" @click="shownCount = shownCount === null ? 1 : null"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 9 6-9 6Z"/></svg>{{ shownCount === null ? '分步演示' : '显示全部' }}</button>
      <button type="button" class="clear-notes" :disabled="!hasNotes" @click="clearNotes">清除本页标记</button>
    </div>
    <p class="board-tool-hint" role="status">{{ toolHint }}</p>
    <div v-if="shownCount !== null" class="board-step-controls" aria-label="分步阅读">
      <button type="button" :disabled="shownCount <= 1" @click="shownCount = Math.max(1, shownCount - 1)">上一步</button>
      <span role="status" aria-live="polite">第 {{ shownCount }} / {{ items.length }} 步</span>
      <button type="button" :disabled="shownCount >= items.length" @click="shownCount = Math.min(items.length, shownCount + 1)">下一步</button>
    </div>
    <div ref="viewport" class="board-viewport" tabindex="0" aria-label="板书内容，可上下滚动" @scroll="laser = null">
    <div class="board-content" :data-tool="tool" @pointermove="moveLaser" @pointerleave="laser = null">
      <div v-for="item in visibleItems" :key="item.id" class="board-item" :data-board-item="item.id" :data-highlighted="notes.highlights.includes(item.id)" @click="markContent(item.id, $event)">
        <button v-if="tool" class="mark-item" type="button" :aria-label="`${tool === 'highlight' ? '高亮' : '定位'}${item.label}`" :aria-pressed="tool === 'highlight' ? notes.highlights.includes(item.id) : !!notes.pins[item.id]" @click.stop="mark(item.id)">{{ tool === 'highlight' ? '标记' : '定位' }}</button>
        <ClassroomCodeExample v-if="item.kind === 'code'" :code="item.text" />
        <template v-else><span v-if="item.kind !== 'explanation'" class="board-item-label">{{ item.label }}</span><p>{{ item.text }}</p></template>
        <i v-if="notes.pins[item.id]" class="board-pin" :style="{ left: `${notes.pins[item.id]!.x}%`, top: `${notes.pins[item.id]!.y}%` }" aria-label="已固定的激光定位"></i>
      </div>
      <i v-if="laser" class="board-laser" :style="{ left: `${laser.x}px`, top: `${laser.y}px` }" aria-hidden="true"></i>
    </div>
    </div>
  </section>
</template>

<style scoped>
.classroom-board { min-width: 0; padding: 24px; border: 1px solid var(--line); border-radius: 8px; color: var(--ink); background: var(--surface-raised); }
.board-heading h3 { margin: 0; font-size: 22px; line-height: 1.35; }
.board-heading > span { display: block; margin-top: 7px; font-size: 12px; color: var(--muted); }
.board-tools { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 20px; }
button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 36px; padding: 7px 10px; border: 1px solid var(--line); border-radius: 6px; color: var(--ink); background: var(--surface-raised); font: inherit; font-size: 12px; cursor: pointer; }
button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent-ink); }
button[aria-pressed="true"] { color: var(--accent-ink); border-color: var(--accent); background: var(--accent-pale); }
button:disabled { opacity: .5; cursor: default; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.clear-notes { margin-left: auto; }
.board-tool-hint { margin: 10px 0 16px; color: var(--muted); font-size: 12px; line-height: 1.6; }
.board-step-controls { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-block: 1px solid var(--line); margin-bottom: 12px; }
.board-step-controls span { font-size: 13px; font-variant-numeric: tabular-nums; }
.board-viewport { max-height: 460px; overflow: auto; overscroll-behavior: contain; scrollbar-width: thin; scrollbar-color: var(--muted) var(--surface-raised); }
.board-viewport:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.board-content { position: relative; display: grid; gap: 8px; }
.board-content[data-tool] .board-item { cursor: crosshair; }
.board-item { position: relative; min-width: 0; padding: 10px 12px; border: 1px solid transparent; border-radius: 6px; }
.board-item p { margin: 4px 0 0; font-size: 14px; line-height: 1.8; overflow-wrap: anywhere; }
.board-item-label { font-size: 12px; color: var(--muted); font-weight: 700; }
.board-item[data-highlighted="true"] { color: #322611; background: #fff0ae; border-color: #b58b2d; }
.board-item[data-highlighted="true"] .board-item-label { color: #644b19; }
.board-item[data-highlighted="true"] { --ink: #322611; --muted: #644b19; --surface-muted: #f8e397; --surface-raised: #fff0ae; }
.mark-item { float: right; margin: 0 0 6px 10px; min-height: 30px; font-size: 11px; }
.board-pin, .board-laser { position: absolute; z-index: 3; width: 12px; height: 12px; border: 2px solid #fff; border-radius: 50%; background: #da2439; transform: translate(-50%, -50%); pointer-events: none; box-shadow: 0 2px 5px #0005; }
.board-pin { width: 14px; height: 14px; }
@media (max-width: 600px) { .classroom-board { padding: 16px; } .board-heading h3 { font-size: 19px; } .clear-notes { margin-left: 0; } .board-item { padding: 8px; } button { min-height: 40px; } }
</style>
