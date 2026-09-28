import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { animateState } from "./motion";

describe("state motion does not hold up content or navigation", () => {
  let root: { dataset: { motion: string } };
  let media: { matches: boolean; addEventListener: ReturnType<typeof vi.fn>; removeEventListener: ReturnType<typeof vi.fn> };
  let preferenceChanged: () => void;
  let disconnect: ReturnType<typeof vi.fn>;
  let animation: { cancel: ReturnType<typeof vi.fn>; onfinish: (() => void) | null; oncancel: (() => void) | null };
  let animate: ReturnType<typeof vi.fn>;
  let element: HTMLElement;

  beforeEach(() => {
    root = { dataset: { motion: "full" } };
    media = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() };
    disconnect = vi.fn();
    animation = { cancel: vi.fn(), onfinish: null, oncancel: null };
    animate = vi.fn(() => animation);
    element = { animate } as unknown as HTMLElement;
    vi.stubGlobal("document", { documentElement: root });
    vi.stubGlobal("window", { matchMedia: () => media });
    vi.stubGlobal("MutationObserver", class {
      constructor(callback: () => void) { preferenceChanged = callback; }
      observe = vi.fn();
      disconnect = disconnect;
    });
  });

  afterEach(() => {
    animation.onfinish?.();
    vi.unstubAllGlobals();
  });

  it("honors both system and app reduced motion before starting", () => {
    media.matches = true;
    animateState(element);
    media.matches = false;
    root.dataset.motion = "reduced";
    animateState(element);
    expect(animate).not.toHaveBeenCalled();
  });

  it("cancels immediately when app preference changes during a transition", () => {
    animateState(element);
    root.dataset.motion = "reduced";
    preferenceChanged();
    expect(animation.cancel).toHaveBeenCalledOnce();
    expect(disconnect).toHaveBeenCalledOnce();
    expect(media.removeEventListener).toHaveBeenCalledOnce();
  });

  it("cancels immediately when system preference changes", () => {
    animateState(element);
    media.matches = true;
    media.addEventListener.mock.calls[0]![1]();
    expect(animation.cancel).toHaveBeenCalledOnce();
  });

  it("cancels the old effect on rapid successive state changes", () => {
    animateState(element);
    animateState(element);
    expect(animation.cancel).toHaveBeenCalledOnce();
    expect(animate).toHaveBeenCalledTimes(2);
  });

  it("releases all effect state on completion, leaving existing styles in charge", () => {
    animateState(element);
    animation.onfinish?.();
    expect(animation.cancel).toHaveBeenCalledOnce();
    expect(animation.onfinish).toBeNull();
    expect(disconnect).toHaveBeenCalledOnce();
    expect(animate.mock.calls[0]![1]).not.toHaveProperty("fill");
  });

  it("keeps working when animation is unavailable or throws", () => {
    expect(() => animateState({} as HTMLElement)).not.toThrow();
    animate.mockImplementation(() => { throw new Error("Animation unavailable"); });
    expect(() => animateState(element)).not.toThrow();
  });
});
