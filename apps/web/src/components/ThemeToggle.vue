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
.theme-switch button { display:inline-flex; align-items:center; justify-content:center; gap:6px; }
.theme-switch span { font:18px/1 system-ui,sans-serif; }
@media(max-width:420px) { .theme-switch span { display:none; } }
</style>
