/// <reference types="node" />
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const stylesheet = readFileSync(fileURLToPath(new URL("./typography.css", import.meta.url)), "utf8");

describe("reading typography", () => {
  it("ships variable Song glyphs for Chinese lessons and Latin text from the app origin", () => {
    expect(stylesheet).toContain('@import "@fontsource-variable/noto-serif-sc"');
    const fontCssPath = createRequire(import.meta.url).resolve("@fontsource-variable/noto-serif-sc");
    const fontCss = readFileSync(fontCssPath, "utf8");
    expect(fontCss).not.toMatch(/https?:\/\//);
    const blocks = fontCss.match(/@font-face\s*\{[^}]+\}/g)!;
    for (const char of "词元研究所二分查找指针Python26") {
      const cp = char.codePointAt(0)!;
      const block = blocks.find(face => (face.match(/U\+([a-f\d]+)(?:-([a-f\d]+))?/gi) ?? []).some(range => {
        const [low, high = low] = range.slice(2).split("-");
        return cp >= parseInt(low!, 16) && cp <= parseInt(high!, 16);
      }));
      expect(block, char).toBeDefined();
      expect(block).toContain("font-display: swap");
      expect(block).toContain("font-weight: 200 900");
      const file = block!.match(/src: url\(([^)]+)\)/)![1]!;
      expect(readFileSync(resolve(dirname(fontCssPath), file)).toString("ascii", 0, 4)).toBe("wOF2");
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
    expect(stylesheet).toContain("font-family: var(--font-code)");
    const mobile = stylesheet.split("@media (max-width: 760px)")[1];
    expect(mobile).toContain("font-size: var(--type-body)");
    expect(mobile).not.toContain("--type-body:");
    expect(mobile).not.toContain(".single-question h2");
  });
});
