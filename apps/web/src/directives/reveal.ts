import type { Directive } from "vue";

/**
 * v-reveal: stagger children into view the first time a container scrolls
 * into the viewport. Disabled instantly under reduced motion.
 */
const observer = typeof IntersectionObserver === "undefined"
  ? null
  : new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("reveal-ready");
        observer?.unobserve(entry.target);
      }
    },
    { threshold: 0.1, rootMargin: "0px 0px -6% 0px" },
  );

export const revealDirective: Directive<HTMLElement> = {
  mounted(el) {
    if (document.documentElement.dataset.motion === "reduced") {
      el.classList.add("reveal-ready");
      return;
    }
    el.classList.add("reveal");
    observer?.observe(el);
  },
  unmounted(el) {
    observer?.unobserve(el);
  },
};
