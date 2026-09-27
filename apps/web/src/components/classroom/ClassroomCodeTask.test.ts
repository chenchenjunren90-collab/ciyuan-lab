import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import { describe, expect, it } from "vitest";
import ClassroomCodeTask from "./ClassroomCodeTask.vue";

const props = {
  task: {
    exercise_id: "C-PTR-01-C1", title: "指针交换", prompt: "交换两个整数",
    difficulty: "beginner", estimated_minutes: 20,
    input_format: "两个整数", output_format: "交换结果", constraints: [],
    starter_code: "", public_examples: [],
  },
  modelValue: "", result: null, loading: false,
  hint: "", hintLoading: false, label: "随堂练习",
};

describe("shared classroom code editor", () => {
  it("keeps the existing Python language default", async () => {
    const html = await renderToString(createSSRApp(ClassroomCodeTask, props));
    expect(html).toContain("main.py");
    expect(html).toContain("Python 3.11");
  });
  it("labels C exercises with their real runtime", async () => {
    const html = await renderToString(createSSRApp(ClassroomCodeTask, { ...props, language: "c" }));
    expect(html).toContain("main.c");
    expect(html).toContain("C17");
    expect(html).not.toContain("main.py");
  });
  it("does not claim the assistant is still working after all hints are shown", async () => {
    const html = await renderToString(createSSRApp(ClassroomCodeTask, { ...props, hintExhausted: true }));
    expect(html).toContain("已展示全部三级提示");
    expect(html).not.toContain("助教正在分析");
  });
});
