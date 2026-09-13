import { describe, expect, it } from "vitest";
import { selectDialogueHistory } from "./dialogueHistory";

describe("bounded classroom history retrieval", () => {
  it("recalls an earlier relevant question and reply while preserving the latest turns", () => {
    const history = [
      { role: "student" as const, content: "range 的步长可以是负数吗？", kind: "student" },
      { role: "teacher" as const, content: "range(5, 0, -1) 是递减序列。", kind: "reply" },
      ...Array.from({ length: 14 }, (_, i) => ({ role: "student" as const, content: `讨论变量 ${i}`, kind: "student" })),
    ];
    const selected = selectDialogueHistory(history, "刚才 range 的步长例子再解释一下");
    expect(selected).toHaveLength(8);
    expect(selected[0]!.content).toContain("负数");
    expect(selected[1]!.content).toContain("range(5");
    expect(selected.at(-1)!.content).toBe("讨论变量 13");
  });
  it("excludes scripted lecture chatter and bounds code without removing indentation", () => {
    const selected = selectDialogueHistory([
      { role: "teacher", content: "完整学习闭环", kind: "lecture" },
      { role: "student", content: "```python\nfor i in range(3):\n    print(i)\n```", kind: "student" },
      { role: "teacher", content: "a".repeat(1800), kind: "reply" },
    ], "为什么");
    expect(selected).toHaveLength(2);
    expect(selected[0]!.content).toContain("\n    print");
    expect(selected[1]!.content).toHaveLength(1500);
  });
});
