import { describe, expect, it } from "vitest";
import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import type { ClassroomBeat } from "../../services/api";
import { boardItems, readBoardNotes } from "./boardTools";
import ClassroomBoard from "./ClassroomBoard.vue";
import ClassroomCodeExample from "./ClassroomCodeExample.vue";

const beat = {
  id: "loop", board_title: "循环", eyebrow: "第一步", board_explanation: "重复执行缩进代码。",
  board_points: ["先确定循环范围", "易错提醒：不要漏掉冒号"],
  board_code: "for number in range(5):\n    print(number)", board_trace: ["从 0 开始", "依次输出到 4"],
} as ClassroomBeat;

describe("classroom board tools", () => {
  it("displays a short example in full without a meaningless expand button", async () => {
    const html = await renderToString(createSSRApp(ClassroomCodeExample, { code: beat.board_code }));
    expect(html).toContain(beat.board_code);
    expect(html).not.toContain("<button");
  });
  it("collapses only long examples and states how many lines can be expanded", async () => {
    const code = Array.from({ length: 10 }, (_, i) => `print(${i})`).join("\n");
    const html = await renderToString(createSSRApp(ClassroomCodeExample, { code }));
    expect(html).toContain("展开全部 10 行");
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain("print(7)");
    expect(html).not.toContain("print(8)");
  });
  it("keeps explanation, points, code, traces and mistakes in teaching order", () => {
    const items = boardItems(beat);
    expect(items.map(item => item.kind)).toEqual(["explanation", "point", "code", "trace", "trace", "mistake"]);
    expect(items.at(-1)?.text).toBe("不要漏掉冒号");
  });
  it("renders saved highlights and pinned laser locations instead of relying on transient DOM", async () => {
    const id = boardItems(beat)[1]!.id;
    const html = await renderToString(createSSRApp(ClassroomBoard, { beat, notes: { highlights: [id], pins: { [id]: { x: 30, y: 40 } } } }));
    expect(html).toContain('data-highlighted="true"');
    expect(html).toContain("left:30%;top:40%");
    expect(html).toContain("已固定的激光定位");
  });
  it("ignores corrupt annotations without throwing away a valid classroom draft", () => {
    expect(readBoardNotes(undefined)).toEqual({});
    expect(readBoardNotes({ a: { highlights: [3, "point:hello"], pins: { bad: { x: -1, y: 10 }, good: { x: 4, y: 6 } } }, b: null }))
      .toEqual({ a: { highlights: ["point:hello"], pins: { good: { x: 4, y: 6 } } } });
  });
});
