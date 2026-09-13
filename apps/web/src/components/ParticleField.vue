<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

const canvas = ref<HTMLCanvasElement | null>(null);
const PARTICLE_COUNT = 56;
let raf = 0;
let observer: MutationObserver | null = null;
let accent = "#d61f3d";

interface Particle { x: number; y: number; r: number; vx: number; vy: number; a: number; }

function themeAccent(): string {
  return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#d61f3d";
}

onMounted(() => {
  const reduced = document.documentElement.dataset.motion === "reduced";
  if (reduced) return;
  accent = themeAccent();
  observer = new MutationObserver(() => {
    accent = themeAccent();
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  const ctx = canvas.value?.getContext("2d");
  if (!ctx) return;
  let width = 0;
  let height = 0;
  const particles: Particle[] = [];

  function resize(): void {
    if (!canvas.value) return;
    width = window.innerWidth;
    height = window.innerHeight;
    const ratio = window.devicePixelRatio || 1;
    canvas.value.width = Math.round(width * ratio);
    canvas.value.height = Math.round(height * ratio);
    ctx!.setTransform(ratio, 0, 0, ratio, 0, 0);
    const target = Math.min(
      PARTICLE_COUNT,
      Math.max(24, Math.round((width * height) / 34000)),
    );
    particles.length = 0;
    for (let i = 0; i < target; i += 1) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        r: 0.6 + Math.random() * 1.8,
        vx: (Math.random() - 0.5) * 0.16,
        vy: (Math.random() - 0.5) * 0.16,
        a: 0.12 + Math.random() * 0.4,
      });
    }
  }

  function hexToRgb(hex: string): [number, number, number] {
    const value = hex.replace("#", "");
    const full = value.length === 3 ? value.split("").map((c) => c + c).join("") : value;
    const number = parseInt(full, 16);
    return [(number >> 16) & 255, (number >> 8) & 255, number & 255];
  }

  function tick(): void {
    if (document.hidden) {
      raf = requestAnimationFrame(tick);
      return;
    }
    ctx!.clearRect(0, 0, width, height);
    const [r, g, b] = hexToRgb(accent);
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < -10) p.x = width + 10;
      if (p.x > width + 10) p.x = -10;
      if (p.y < -10) p.y = height + 10;
      if (p.y > height + 10) p.y = -10;
      ctx!.beginPath();
      ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx!.fillStyle = `rgba(${r}, ${g}, ${b}, ${p.a})`;
      ctx!.fill();
    }
    raf = requestAnimationFrame(tick);
  }

  resize();
  window.addEventListener("resize", resize);
  raf = requestAnimationFrame(tick);
  onBeforeUnmount(() => {
    cancelAnimationFrame(raf);
    window.removeEventListener("resize", resize);
    observer?.disconnect();
  });
});
</script>

<template>
  <canvas ref="canvas" class="particle-field" aria-hidden="true"></canvas>
</template>

<style scoped>
.particle-field {
  position: fixed;
  inset: 0;
  z-index: -1;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
html[data-motion="reduced"] .particle-field { display: none; }
</style>
