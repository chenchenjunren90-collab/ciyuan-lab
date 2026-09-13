import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import { describe, expect, it, vi } from "vitest";
import type { ClassroomBeat, ClassroomLesson } from "../../services/api";
import LessonBeatContent from "./LessonBeatContent.vue";
import ClassroomPlanPreview from "./ClassroomPlanPreview.vue";

// This test checks the lecture's data wiring. Browser-only Markdown sanitization
// is not exercised by the Node SSR renderer and is not bypassed in production.
vi.mock("../SafeMarkdown.vue", async () => {
  const { defineComponent, h } = await import("vue");
  return { default: defineComponent({
    props: { source: String },
    setup: (props) => () => h("p", props.source),
  }) };
});

const beat: ClassroomBeat = {
  id: "adaptive-example--PY-BASE-05", phase: "concept", speaker: "teacher",
  eyebrow: "第二步", title: "跟着例子逐行看", message: "先预测，再运行",
  board_title: "温度与外套", board_explanation: "条件成立时执行缩进代码块。",
  board_points: ["先检查边界"], board_code: "temperature = 12\nprint(temperature)",
  board_trace: ["第 1 行保存 12", "第 2 行输出 12"], action: "continue", checkpoint: null,
};

describe("visible classroom teaching material", () => {
  it("renders the explanation, full example and every trace step, not only a title", async () => {
    const html = await renderToString(createSSRApp(LessonBeatContent, { beat }));
    for (const content of [beat.board_explanation, beat.board_code, ...beat.board_points, ...beat.board_trace]) {
      expect(html).toContain(content);
    }
    expect(html).toMatch(/<pre[^>]*><code/);
  });

  it("shows substantive recap with its reflection steps", async () => {
    const html = await renderToString(createSSRApp(LessonBeatContent, {
      beat: { ...beat, phase: "summary" },
    }));
    expect(html).toContain("复盘与下一步");
    expect(html).toContain("先检查边界");
  });

  it("shows the actual planned lesson and prerequisite reason without dialogue error labels", async () => {
    const plan = {
      title: "条件语句", subtitle: "本节目标", planning_reason: "后续学习列表；本节先补齐条件判断。",
      beats: [beat], duration_minutes: 30,
    } as ClassroomLesson;
    const html = await renderToString(createSSRApp(ClassroomPlanPreview, { plan }));
    expect(html).toContain(plan.planning_reason);
    expect(html).toContain(plan.title);
    expect(html).toContain(beat.title);
    expect(html).not.toContain("0 条课程依据");
    expect(html).not.toContain("服务暂不可用");
  });
});
