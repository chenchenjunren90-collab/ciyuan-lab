/// <reference types="node" />
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { PALETTES } from "./uiPreferences";

const themes = readFileSync(fileURLToPath(new URL("./themes.css", import.meta.url)), "utf8");
function luminance(hex: string): number {
  const rgb = hex.slice(1).match(/.{2}/g)!.map(channel => {
    const value = parseInt(channel, 16) / 255;
    return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
  });
  return rgb[0]! * .2126 + rgb[1]! * .7152 + rgb[2]! * .0722;
}
function contrast(a: string, b: string): number {
  const values = [luminance(a), luminance(b)].sort((a, b) => a - b);
  return (values[1]! + .05) / (values[0]! + .05);
}

describe("workspace appearance", () => {
  it("uses local heading and body fonts with a Chinese fallback", () => {
    const css = readFileSync(new URL("./typography.css", import.meta.url), "utf8");
    expect(css).toContain('--font-body: "DM Sans"');
    expect(css).toContain('--font-display: "Barlow Condensed", "DengXian Light"');
    for (const name of ["barlow-condensed-light", "dm-sans"]) {
      const bytes = readFileSync(new URL("./assets/fonts/" + name + ".woff2", import.meta.url));
      expect(bytes.toString("ascii", 0, 4)).toBe("wOF2");
    }
  });
  for (const palette of PALETTES) {
    it(`${palette.id} keeps text, controls and swatches in one accessible palette`, () => {
      const block = themes.match(new RegExp(`html\\[data-palette="${palette.id}"\\] \\{([^}]+)\\}`))![1]!;
      const token = (name: string) => block.match(new RegExp(`--${name}:(#[\\da-f]{6});`, "i"))![1]!;
      expect(token("surface")).toBe(palette.background);
      expect(token("accent")).toBe(palette.accent);
      for (const surface of ["surface", "surface-raised", "surface-muted"]) {
        expect(contrast(token("ink"), token(surface)), `body on ${surface}`).toBeGreaterThanOrEqual(4.5);
        expect(contrast(token("muted"), token(surface)), `caption on ${surface}`).toBeGreaterThanOrEqual(4.5);
      }
      expect(contrast(token("accent-contrast"), token("accent")), "primary action").toBeGreaterThanOrEqual(4.5);
      expect(contrast(token("ink"), token("surface-raised")), "raised action").toBeGreaterThanOrEqual(4.5);
      expect(contrast(token("accent-ink"), token("accent-pale")), "selected control").toBeGreaterThanOrEqual(4.5);
    });
  }
});
