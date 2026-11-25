<script setup lang="ts">
import { computed } from "vue";
import { PALETTES, type PaletteId } from "../uiPreferences";
const props = defineProps<{ theme: PaletteId }>();
const emit = defineEmits<{ select: [theme: PaletteId] }>();
const next = computed(() => PALETTES.find(item => item.id !== props.theme)!);
</script>

<template>
  <button type="button" class="theme-switch" role="switch" aria-label="暮紫沉蓝暗色模式"
    :aria-checked="theme === 'dusk'" :title="'切换至' + next.label" @click="emit('select', next.id)">
    <span class="mode-icon" aria-hidden="true">◐</span>{{ theme === 'dusk' ? '暗色' : '浅色' }}
  </button>
</template>

<style scoped>
.theme-switch { display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:44px; padding:7px 12px; font:inherit; font-size:14px; background:var(--surface-raised); border:1px solid var(--line); color:var(--ink); cursor:pointer; border-radius:3px; }
.theme-switch:hover { border-color:var(--ink); }
.theme-switch:focus-visible { outline:2px solid var(--accent-ink); outline-offset:2px; }
.mode-icon { font:20px/1 system-ui,sans-serif; }
</style>
