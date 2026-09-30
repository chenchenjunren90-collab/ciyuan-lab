/// <reference types="node" />
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const stylesheet = readFileSync(fileURLToPath(new URL("./typography.css", import.meta.url)), "utf8");

describe("reading typography", () => {
  it("loads two local, non-blocking real font weights", () => {
    expect(stylesheet.match(/font-display: swap/g)).toHaveLength(2);
    expect(stylesheet).not.toMatch(/https?:\/\//);
    for (const weight of [400, 600]) {
      const font = readFileSync(fileURLToPath(new URL(`./assets/fonts/noto-sans-sc-${weight}.woff`, import.meta.url)));
      expect(font.subarray(0, 4).toString()).toBe("wOFF");
      expect(font.byteLength).toBeLessThan(300_000);
    }
  });

  it("separates caption, control, reading, and heading roles in scalable units", () => {
    const sizes = ["caption", "label", "body", "subtitle", "section", "page", "intro"].map(role => {
      const declaration = stylesheet.match(new RegExp(`--type-${role}: ([\\d.]+)rem`));
      expect(declaration, role).not.toBeNull();
      return Number(declaration![1]);
    });
    expect(sizes).toEqual([...sizes].sort((a, b) => a - b));
    expect(sizes[2]).toBe(1);
    expect(stylesheet).not.toMatch(/!important|\bzoom\s*:|text-size-adjust\s*:\s*none/);
  });

  it("keeps code monospaced and narrows heading sizes without shrinking reading copy", () => {
    expect(stylesheet).toContain("font-family: var(--font-data)");
    const mobile = stylesheet.split("@media (max-width: 760px)")[1];
    expect(mobile).toContain("font-size: var(--type-body)");
    expect(mobile).not.toContain("--type-body:");
    expect(mobile).not.toContain(".single-question h2");
  });
});
