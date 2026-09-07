/**
 * Mouse-follow spotlight for cards marked with [data-spotlight].
 * A single delegated listener updates --mx/--my on the hovered card; the
 * glow itself is drawn by CSS.
 */
export function useSpotlight(): void {
  document.addEventListener("mousemove", (event) => {
    const card = (event.target as HTMLElement | null)?.closest?.("[data-spotlight]");
    if (!(card instanceof HTMLElement)) return;
    const rect = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
    card.style.setProperty("--my", `${event.clientY - rect.top}px`);
  });
}
