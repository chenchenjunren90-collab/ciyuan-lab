<script setup lang="ts">
defineProps<{ dark: boolean }>();
const emit = defineEmits<{ toggle: [] }>();
</script>

<template>
  <button
    class="theme-toggle"
    type="button"
    role="switch"
    :aria-checked="dark"
    :aria-label="dark ? '切换为红白模式' : '切换为紫黑模式'"
    :title="dark ? '切换为红白模式' : '切换为紫黑模式'"
    @click="emit('toggle')"
  >
    <span class="toggle-track" aria-hidden="true">
      <span class="toggle-glow"></span>
      <span class="toggle-thumb">
        <svg class="toggle-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4.2"/>
          <path d="M12 2.5v2.4m0 14.2v2.4M2.5 12h2.4m14.2 0h2.4M4.9 4.9l1.7 1.7m10.8 10.8 1.7 1.7M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7"/>
        </svg>
        <svg class="toggle-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20.4 14.2A8.3 8.3 0 0 1 9.8 3.6a8.3 8.3 0 1 0 10.6 10.6Z"/>
        </svg>
      </span>
      <i class="toggle-star star-a"></i>
      <i class="toggle-star star-b"></i>
      <i class="toggle-star star-c"></i>
    </span>
    <span class="toggle-label">{{ dark ? "紫黑模式" : "红白模式" }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 44px;
  padding: 7px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--ink);
  background: var(--surface-raised);
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color .25s ease, box-shadow .25s ease, transform .12s ease;
}
.theme-toggle:hover {
  border-color: color-mix(in srgb, var(--accent) 55%, var(--line));
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 12%, transparent),
    0 10px 24px color-mix(in srgb, var(--accent) 18%, transparent);
}
.theme-toggle:active { transform: scale(.955); }

.toggle-track {
  position: relative;
  width: 52px;
  height: 28px;
  flex: 0 0 auto;
  border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--line));
  border-radius: 999px;
  background: var(--surface-muted);
  transition: background .35s ease, border-color .35s ease;
  overflow: hidden;
}
.theme-toggle[aria-checked="true"] .toggle-track {
  background: color-mix(in srgb, var(--accent) 24%, var(--surface-muted));
  border-color: var(--accent);
}
.toggle-glow {
  position: absolute;
  inset: -6px;
  border-radius: inherit;
  background: radial-gradient(60% 100% at 50% 50%, color-mix(in srgb, var(--accent) 30%, transparent), transparent 70%);
  opacity: 0;
  transition: opacity .35s ease;
}
.theme-toggle[aria-checked="true"] .toggle-glow { opacity: 1; }

.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--accent-contrast);
  background: linear-gradient(135deg, var(--accent-bright), var(--accent-dark));
  box-shadow: 0 2px 8px color-mix(in srgb, var(--accent) 45%, transparent);
  transition: transform .38s cubic-bezier(.34, 1.45, .5, 1);
}
.theme-toggle[aria-checked="true"] .toggle-thumb { transform: translateX(24px); }

.toggle-sun, .toggle-moon {
  position: absolute;
  transition: transform .38s ease, opacity .28s ease;
}
.toggle-sun { opacity: 1; transform: rotate(0deg) scale(1); }
.toggle-moon { opacity: 0; transform: rotate(-70deg) scale(.4); }
.theme-toggle[aria-checked="true"] .toggle-sun { opacity: 0; transform: rotate(90deg) scale(.4); }
.theme-toggle[aria-checked="true"] .toggle-moon { opacity: 1; transform: rotate(0deg) scale(1); }

.toggle-star {
  position: absolute;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--accent-bright);
  opacity: 0;
  transition: opacity .3s ease, transform .45s ease;
}
.star-a { top: 6px; right: 9px; }
.star-b { bottom: 6px; right: 15px; }
.star-c { top: 10px; right: 22px; }
.theme-toggle[aria-checked="true"] .toggle-star {
  opacity: 1;
  animation: star-twinkle 1.6s ease-in-out infinite;
}
.star-a { animation-delay: 0s; }
.star-b { animation-delay: .45s; }
.star-c { animation-delay: .9s; }

.toggle-label { font-weight: 750; }

@keyframes star-twinkle {
  0%, 100% { opacity: .2; transform: scale(.7); }
  50% { opacity: 1; transform: scale(1.15); }
}

@media (max-width: 560px) {
  .theme-toggle { min-width: 44px; padding: 7px 10px; }
  .toggle-label { display: none; }
}

html[data-motion="reduced"] .toggle-thumb,
html[data-motion="reduced"] .toggle-sun,
html[data-motion="reduced"] .toggle-moon { transition: none; }
html[data-motion="reduced"] .toggle-star { animation: none; }
</style>
