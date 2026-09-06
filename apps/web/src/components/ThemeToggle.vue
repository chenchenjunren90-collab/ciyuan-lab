<script setup lang="ts">
defineProps<{ dark: boolean }>();
const emit = defineEmits<{ toggle: [] }>();
</script>

<template>
  <button class="theme-toggle" type="button" :aria-label="dark ? '切换为白色模式' : '切换为深色模式'" :title="dark ? '切换为白色模式' : '切换为深色模式'" @click="emit('toggle')">
    <svg v-if="dark" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>
    <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/></svg>
    <span>{{ dark ? '白色模式' : '深色模式' }}</span>
  </button>
</template>

<style scoped>
.theme-toggle { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 44px; padding: 8px 11px; border: 1px solid var(--line); border-radius: 8px; color: var(--ink); background: var(--surface-raised); font-size: 12px; font-weight: 700; white-space: nowrap; }
.theme-toggle:hover { border-color: var(--accent); color: var(--accent-ink); background: var(--accent-pale); }
.theme-toggle svg { flex: 0 0 auto; }
@media (max-width: 520px) { .theme-toggle { min-width: 44px; padding: 8px; } .theme-toggle span { display: none; } }
</style>
