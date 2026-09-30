<script setup lang="ts">
defineProps<{ busy: boolean; disabled?: boolean }>();
defineEmits<{ skip: [] }>();
</script>

<template>
  <div class="beginner-shortcut">
    <button type="button" :disabled="busy || disabled" :aria-busy="busy" @click="$emit('skip')">{{ busy ? '正在准备学习起点…' : '我没学过 / 我是新手，一键跳过做题' }}</button>
    <p>未答题将按“我不知道”提交，已选答案保留。后续通过课堂练习逐步确认掌握情况。</p>
  </div>
</template>

<style scoped>
.beginner-shortcut { margin: 16px 0; }
.beginner-shortcut button { min-height: 44px; max-width: 100%; padding: 10px 14px; border: 1px solid var(--line); border-radius: 8px; color: var(--accent-ink); background: var(--surface-raised); font: inherit; font-size: 14px; cursor: pointer; }
.beginner-shortcut button:disabled { opacity: .55; cursor: wait; }
.beginner-shortcut button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.beginner-shortcut p { margin: 8px 0 0; color: var(--muted); font-size: 12px; line-height: 1.6; }
</style>
