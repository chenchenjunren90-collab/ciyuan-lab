import type { ObjectDirective } from "vue";

const running = new WeakMap<HTMLElement, () => void>();

/** Presentation only: never delay state updates, replace nodes, or intercept input. */
export function animateState(el: HTMLElement, board = false): void {
  running.get(el)?.();
  const root = document.documentElement;
  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (root.dataset.motion === "reduced" || preference.matches || typeof el.animate !== "function") return;

  let animation: Animation;
  try {
    animation = el.animate(
      board
        ? [{ opacity: .75, clipPath: "inset(0 0 8px 0)" }, { opacity: 1, clipPath: "inset(0)" }]
        : [{ opacity: .65 }, { opacity: 1 }],
      { duration: board ? 280 : 200, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
    );
  } catch {
    // Unsupported animation APIs must never affect a lesson or navigation.
    return;
  }
  const stop = () => {
    animation.onfinish = null;
    animation.oncancel = null;
    observer.disconnect();
    preference.removeEventListener("change", onPreference);
    running.delete(el);
    animation.cancel();
  };
  const onPreference = () => {
    if (root.dataset.motion === "reduced" || preference.matches) stop();
  };
  const observer = new MutationObserver(onPreference);
  observer.observe(root, { attributes: true, attributeFilter: ["data-motion"] });
  preference.addEventListener("change", onPreference);
  animation.onfinish = stop;
  animation.oncancel = stop;
  running.set(el, stop);
}

/** `.change` skips entrance; the binding is the actual state/result to observe. */
export const motionDirective: ObjectDirective<HTMLElement, unknown> = {
  mounted(el, binding) {
    if (!binding.modifiers.change) animateState(el, binding.modifiers.board);
  },
  updated(el, binding) {
    if (!Object.is(binding.value, binding.oldValue)) animateState(el, binding.modifiers.board);
  },
  beforeUnmount(el) {
    running.get(el)?.();
  },
};
