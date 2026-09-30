<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { PALETTES, type PaletteId } from "../uiPreferences";

const props = defineProps<{ theme: PaletteId }>();
const emit = defineEmits<{ select: [theme: PaletteId] }>();
const preview = ref<PaletteId | null>(null);
const previewStyle = ref({ left: "0px", top: "0px" });
const palette = computed(() => PALETTES.find((item) => item.id === preview.value));
let dismissTimer: ReturnType<typeof setTimeout> | undefined;
function showPreview(id: PaletteId, event: Event): void {
  clearTimeout(dismissTimer);
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  previewStyle.value = {
    left: `${Math.max(8, Math.min(window.innerWidth - 200, rect.left + rect.width / 2 - 96))}px`,
    top: `${Math.max(4, rect.top - 40)}px`,
  };
  preview.value = id;
}
function select(id: PaletteId, event: Event): void {
  emit("select", id);
  showPreview(id, event);
  dismissTimer = setTimeout(() => { preview.value = null; }, 1400);
}
function navigate(event: KeyboardEvent, index: number): void {
  const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
  if (!direction && event.key !== "Home" && event.key !== "End") return;
  event.preventDefault();
  const next = event.key === "Home" ? 0 : event.key === "End" ? 3 : (index + direction + 4) % 4;
  const buttons = (event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>("button");
  buttons?.[next]?.focus();
  emit("select", PALETTES[next]!.id);
}
onBeforeUnmount(() => clearTimeout(dismissTimer));
</script>

<template>
  <div class="palette-selector" role="radiogroup" aria-label="配色方案" @mouseleave="preview = null" @focusout="preview = null" @keydown.esc="preview = null">
    <button v-for="(item, index) in PALETTES" :key="item.id" type="button"
      class="palette-option" role="radio" :aria-checked="theme === item.id"
      :aria-label="item.label" :tabindex="theme === item.id ? 0 : -1"
      :style="{ '--swatch-base': item.background, '--swatch-accent': item.accent }"
      @pointerenter="showPreview(item.id, $event)" @focus="showPreview(item.id, $event)"
      @click="select(item.id, $event)" @keydown="navigate($event, index)">
      <span class="palette-swatch" aria-hidden="true"><i></i>
        <svg v-if="theme === item.id" viewBox="0 0 16 16" fill="none"><path d="m4 8 2.5 2.5L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </span>
      <span class="palette-name"><span>{{ item.label }}</span></span>
    </button>
    <Teleport to="body">
      <Transition name="palette-preview">
        <div v-if="palette" class="palette-preview" :style="previewStyle" aria-hidden="true">
          <div class="preview-colors"><i :style="{ background: palette.background }"></i><i :style="{ background: palette.accent }"></i></div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.palette-selector { display: inline-flex; width: max-content; max-width: 100%; align-items: center; gap: 2px; padding: 4px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface-raised); }
.palette-option { display: inline-flex; align-items: center; justify-content: center; gap: 0; min-width: 44px; min-height: 44px; padding: 8px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; transition: background .24s ease, color .24s ease; }
.palette-option:hover { background: var(--surface-muted); }
.palette-option[aria-checked="true"] { color: var(--accent-ink); background: var(--accent-pale); }
.palette-option:focus-visible { outline: 2px solid var(--accent-ink); outline-offset: 2px; }
.palette-swatch { position: relative; display: block; flex: 0 0 24px; width: 24px; height: 24px; overflow: hidden; border-radius: 8px; background: var(--swatch-base); border: 1px solid color-mix(in srgb, var(--ink) 30%, transparent); transform: rotate(-8deg); transition: transform .35s cubic-bezier(.2,.8,.2,1); }
.palette-swatch i { display: block; position: absolute; inset: 0 0 0 50%; background: var(--swatch-accent); }
.palette-option[aria-checked="true"] .palette-swatch { transform: rotate(0) scale(1.08); }
.palette-swatch svg { position: absolute; inset: 4px; width: 14px; height: 14px; border-radius: 50%; color: #fff; background: #15151b; }
.palette-name { display: grid; grid-template-columns: 0fr; opacity: 0; transition: grid-template-columns .35s cubic-bezier(.2,.8,.2,1), opacity .2s ease, margin .35s ease; }
.palette-name > span { overflow: hidden; white-space: nowrap; font-size: 12px; font-weight: 700; }
.palette-option[aria-checked="true"] .palette-name { grid-template-columns: 1fr; opacity: 1; margin-left: 8px; }
.palette-preview { position: fixed; z-index: 750; width: 192px; padding: 4px; border: 1px solid var(--line); border-radius: 12px; color: var(--ink); background: var(--surface-raised); box-shadow: 0 8px 24px #0003; pointer-events: none; transform-origin: center bottom; }
.preview-colors { display: flex; height: 22px; overflow: hidden; border-radius: 6px; border: 1px solid var(--line); }
.preview-colors i:first-child { flex: 3; }
.preview-colors i:last-child { flex: 2; }
.palette-preview > span { display: block; margin-top: 5px; font-size: 11px; text-align: center; }
.palette-preview-enter-active,.palette-preview-leave-active { transition: transform .22s cubic-bezier(.2,.8,.2,1), opacity .18s ease; }
.palette-preview-enter-from,.palette-preview-leave-to { transform: translateY(6px) scale(.94); opacity: 0; }
:global(html[data-motion="reduced"]) .palette-selector *, :global(html[data-motion="reduced"]) .palette-preview { transition: none; }
@media (prefers-reduced-motion: reduce) { .palette-selector *, .palette-preview { transition: none; } }
@media (max-width: 560px) { .palette-name { display: none; } }
</style>
