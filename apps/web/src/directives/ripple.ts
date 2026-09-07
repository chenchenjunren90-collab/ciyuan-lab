import type { Directive } from "vue";

/**
 * v-ripple: expanding press wave on pointerdown. Skipped under reduced motion.
 */
export const rippleDirective: Directive<HTMLElement> = {
  mounted(el) {
    el.classList.add("ripple-host");
    el.addEventListener("pointerdown", (event) => {
      if (document.documentElement.dataset.motion === "reduced") return;
      const rect = el.getBoundingClientRect();
      const wave = document.createElement("span");
      wave.className = "ripple-wave";
      const size = Math.max(rect.width, rect.height) * 1.7;
      wave.style.width = `${size}px`;
      wave.style.height = `${size}px`;
      wave.style.left = `${event.clientX - rect.left - size / 2}px`;
      wave.style.top = `${event.clientY - rect.top - size / 2}px`;
      el.appendChild(wave);
      window.setTimeout(() => wave.remove(), 700);
    });
  },
};
