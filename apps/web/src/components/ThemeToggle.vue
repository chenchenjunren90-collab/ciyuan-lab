<script setup lang="ts">
import type { PaletteId } from "../uiPreferences";
defineProps<{ theme: PaletteId }>();
const emit = defineEmits<{ select: [theme: PaletteId] }>();
</script>

<template>
  <div class="theme-switch segment-rail" role="group" aria-label="界面主题">
    <button type="button" :aria-pressed="theme === 'light'" @click="emit('select', 'light')"><span aria-hidden="true">☼</span>浅色</button>
    <button type="button" :aria-pressed="theme === 'dusk'" @click="emit('select', 'dusk')"><span aria-hidden="true">☾</span>暗色</button>
  </div>
</template>

<style scoped>
.theme-switch { flex:none; }
.theme-switch button { position:relative; display:inline-flex; align-items:center; justify-content:center; gap:4px; }
.theme-switch span { font-size:.875rem; line-height:1; }
@media (pointer:coarse) {
  .theme-switch button::before { content:""; position:absolute; inset:-6px 0; }
}
@media(max-width:420px) { .theme-switch span { display:none; } }
</style>
