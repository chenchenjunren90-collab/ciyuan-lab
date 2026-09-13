<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

const props = withDefaults(defineProps<{ value: number | string; duration?: number }>(), {
  duration: 900,
});

const display = ref<number | string>(props.value);
let frame = 0;

function animateTo(target: number): void {
  const reduced = document.documentElement.dataset.motion === "reduced";
  const from = typeof display.value === "number" ? display.value : 0;
  if (reduced || !Number.isFinite(from) || !Number.isFinite(target) || from === target) {
    display.value = target;
    return;
  }
  cancelAnimationFrame(frame);
  const started = performance.now();
  const duration = Math.max(200, props.duration);
  const tick = (now: number) => {
    const progress = Math.min(1, (now - started) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    display.value = Math.round(from + (target - from) * eased);
    if (progress < 1) frame = requestAnimationFrame(tick);
  };
  frame = requestAnimationFrame(tick);
}

watch(
  () => props.value,
  (value) => {
    if (typeof value === "number") animateTo(value);
    else display.value = value;
  },
);

onMounted(() => {
  if (typeof props.value === "number") animateTo(props.value);
});
</script>

<template>
  <span class="count-up">{{ display }}</span>
</template>
