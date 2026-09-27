import { describe, expect, it } from "vitest";
import { buildTrace, parseTraceInput } from "./algorithmTrace";

describe("deterministic teaching models", () => {
  it("parses empty, signed and Chinese comma input without interpreting code", () => {
    expect(parseTraceInput("")).toEqual([]);
    expect(parseTraceInput("-3，0 5")).toEqual([-3, 0, 5]);
    for (const text of ["1e3", "1;alert(1)", "3.4", "1000", Array(13).fill("1").join(" ")]) expect(() => parseTraceInput(text)).toThrow();
  });
  it("swaps objects through fixed symbolic pointers", () => {
    const frames = buildTrace("pointer", [-7, 9]).frames;
    expect(frames.at(-1)?.cells).toEqual(["9", "-7"]);
    expect(frames.at(-1)?.variables).toMatchObject({ p: "&a", q: "&b" });
    expect(frames[0]?.cells).toEqual(["-7", "9"]);
    expect(() => buildTrace("pointer", [])).toThrow();
  });
  it("handles empty arrays without dereferencing a zero-th element", () => {
    expect(buildTrace("array", []).frames.at(-1)?.output).toBe("0");
    expect(buildTrace("array", [2, -2, 5]).frames.at(-1)?.output).toBe("5");
    expect(buildTrace("memory", []).frames.at(-1)?.variables.p).toBe("NULL");
  });
  it("distinguishes stack order from queue order", () => {
    expect(buildTrace("stack", [1, 2, 3]).frames.at(-1)?.output).toBe("3 2 1");
    expect(buildTrace("queue", [1, 2, 3]).frames.at(-1)?.output).toBe("1 2 3");
    expect(buildTrace("queue", []).frames.at(-1)?.cells).toEqual([]);
  });
  it.each([[[], 2, "-1"], [[2], 2, "0"], [[1, 2, 2, 2, 8], 2, "1"], [[1, 3], 9, "-1"], [[1, 3], -2, "-1"]])("finds first occurrence in %j", (values, target, expected) => {
    expect(buildTrace("binary", values as number[], target as number).frames.at(-1)?.output).toBe(expected);
  });
  it("rejects unsorted binary inputs and preserves insertion-sort input", () => {
    expect(() => buildTrace("binary", [3, 1])).toThrow();
    const values = [5, -1, 5, 0];
    const trace = buildTrace("insertion", values);
    expect(values).toEqual([5, -1, 5, 0]);
    expect(trace.frames.at(-1)?.cells).toEqual(["-1", "0", "5", "5"]);
    expect(trace.frames[0]?.cells).toEqual(["5", "-1", "5", "0"]);
  });
  it("BFS marks on discovery, handles the cycle and reports unreachable vertex", () => {
    const final = buildTrace("bfs", []).frames.at(-1)!;
    expect(final.output).toBe("0 1 2 3");
    expect(final.variables.distance).toBe("0, 1, 1, 2, -1");
    expect(final.cells[4]).toBe("4: 未发现");
  });
});
