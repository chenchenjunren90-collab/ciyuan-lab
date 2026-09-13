<script setup lang="ts">
withDefaults(defineProps<{ person?: string }>(), { person: "teacher" });
</script>

<template>
  <svg class="classroom-portrait" viewBox="0 0 96 112" aria-hidden="true" focusable="false">
    <template v-if="person === 'teacher' || person === 'ta'">
      <path d="M31 34c-1-17 8-24 18-24 14 0 22 11 18 26l-3 12c-2 6-6 10-11 12v8l17 8c9 4 15 13 17 36H9c2-22 7-31 18-36l16-8v-8c-7-3-10-10-12-18-4-1-5-7 0-8Z"/>
      <path d="m37 70 11 10 11-10-6 23-5-7-5 7Z" class="portrait-cut"/>
      <path d="m45 89 3-3 3 3 2 23H43Z" class="portrait-cut"/>
    </template>
    <template v-else-if="person === 'peer_cautious'">
      <path d="M27 38C22 18 35 9 48 9s25 10 22 29l-4 20 8 13-15 2v-9h-5v7c2 4 7 6 16 9 10 4 15 15 17 32H9c2-17 7-28 17-32 9-3 14-5 16-9v-8h-5v11l-17-3 10-16-3-17Z"/>
      <path d="M35 31c7 0 13-6 16-12 3 9 7 12 12 14l-3 15c-2 7-7 12-12 12S36 52 35 44Z" class="portrait-cut"/>
      <path d="m37 76 11 8 11-8-4 16H41Z" class="portrait-cut"/>
    </template>
    <template v-else-if="person === 'peer_debugger'">
      <path d="m30 34-5-13 12-3 4-10 10 7 13-3 7 16-5 13c3 2 1 7-2 8-2 7-5 11-11 14v8l16 8c12 5 17 14 19 33H8c2-19 7-28 19-33l16-8v-8c-6-3-10-9-11-16-5-1-6-9-2-11Z"/>
      <path d="m34 75 14 8 14-8-5 22-9-10-9 10Z" class="portrait-cut"/>
    </template>
    <template v-else>
      <path d="M30 39C20 30 23 16 37 12c3-10 18-10 22-1 15 4 19 18 9 30l-4 9c-2 7-6 11-11 13v8l16 8c12 5 17 14 19 33H8c2-19 7-28 19-33l16-8v-8c-8-4-11-10-13-24Z"/>
      <path d="M36 77c8 6 16 6 24 0l-4 12H40Z" class="portrait-cut"/>
    </template>
  </svg>
</template>

<style scoped>
.classroom-portrait { display: block; width: 68px; height: 80px; flex: 0 0 auto; fill: #181b1e; --portrait-paper: #eee9df; background: var(--portrait-paper); border-radius: 8px; }
.portrait-cut { fill: var(--portrait-paper); }
</style>
