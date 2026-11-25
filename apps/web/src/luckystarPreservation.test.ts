/// <reference types="node" />
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Foundation files retained from luckystar-2 f731194. Current palettes are covered by workspaceVisual.
const originals = [
  ["styles.css", "c5d9205059b4c83a0a29cb0d035fc4acb79848d4"],
  ["directives/motion.ts", "46cb216936918a0fdd17205aa7f8f5b0c38047fd"],
  ["components/ParticleField.vue", "18eb28d855e8da64074aa3d5435f824a1b6c41cc"],
  ["composables/useSpotlight.ts", "f250996813809b8b60b9b13250ab53de52450865"],
  ["directives/reveal.ts", "41980a4b53bc2be3d87e6039bc0d0f7fbdbdf3a3"],
  ["directives/ripple.ts", "e36471d947e1175b0cf27a387f630451110c4683"],
  ["components/CountUp.vue", "202b907b80f30a303eb99eef59d504f266f7c526"],
] as const;

describe("luckystar original presentation stays intact", () => {
  it.each(originals)("preserves %s from the agreed branch", (path, expected) => {
    const source = readFileSync(new URL(path, import.meta.url), "utf8").replace(/\r\n/g, "\n");
    const hash = createHash("sha1").update(`blob ${Buffer.byteLength(source)}\0`).update(source).digest("hex");
    expect(hash).toBe(expected);
  });
  it("loads only the scoped compatibility layer after the original styles", () => {
    const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    expect(main).toContain('import "./luckystar-adapter.css"');
    expect(main).not.toContain('import "./workspace.css"');
    const app = readFileSync(new URL("./App.vue", import.meta.url), "utf8");
    expect(app).not.toContain("<ParticleField");
    expect(app).not.toContain("useSpotlight()");
    expect(app).not.toContain('class="aurora"');
    const compatibility = readFileSync(new URL("./luckystar-adapter.css", import.meta.url), "utf8");
    expect(compatibility).not.toMatch(/(?:\.reveal|\.tech-orb|\[data-spotlight\])[^}]*animation\s*:\s*none/);
  });
});
