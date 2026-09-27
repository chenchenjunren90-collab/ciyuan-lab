import type { ActivityDetail, ClassroomCodeTask, CourseId, KnowledgePoint, KnowledgePointDetail, LearnerProfile } from "../../services/api";

export type FoundationCourse = Exclude<CourseId, "python">;
export const courseNames: Record<FoundationCourse, string> = { c: "C 语言", data_structures: "数据结构" };
export const chapters: Record<FoundationCourse, Array<{ title: string; prefixes: string[] }>> = {
  c: [
    { title: "从程序到数据", prefixes: ["BASE", "MAIN"] },
    { title: "控制流与函数", prefixes: ["CTRL", "FUNC"] },
    { title: "数组、字符串与指针", prefixes: ["ARRAY", "STR", "PTR"] },
    { title: "内存与数据组织", prefixes: ["MEM", "TYPE", "QUAL", "BIT"] },
    { title: "文件与标准库", prefixes: ["IO", "STD"] },
    { title: "工程与调试", prefixes: ["MOD", "PP", "ERR", "DEBUG", "TEST", "STYLE"] },
  ],
  data_structures: [
    { title: "模型与复杂度", prefixes: ["FOUND"] },
    { title: "线性结构", prefixes: ["LINEAR", "STACK", "QUEUE"] },
    { title: "树与堆", prefixes: ["TREE", "HEAP"] },
    { title: "图与遍历", prefixes: ["GRAPH"] },
    { title: "查找、排序与散列", prefixes: ["SEARCH", "SORT", "HASH", "SET", "MAP"] },
    { title: "设计与评价", prefixes: ["DESIGN", "EVAL"] },
  ],
};

/** Stable prerequisite order. Unknown prerequisites/cycles are reported, never silently unlocked. */
export function orderKnowledge(points: KnowledgePoint[]): KnowledgePoint[] {
  const remaining = new Map(points.map(point => [point.id, point]));
  if (points.some(point => point.prerequisites.some(id => !remaining.has(id)))) {
    throw new Error("课程包含未登记的前置知识，请联系课程维护者。");
  }
  const result: KnowledgePoint[] = [];
  while (remaining.size) {
    const ready = [...remaining.values()].filter(point => point.prerequisites.every(id => !remaining.has(id)))
      .sort((a, b) => a.id.localeCompare(b.id));
    if (!ready.length) throw new Error("课程前置关系存在循环，请联系课程维护者。");
    for (const point of ready) { result.push(point); remaining.delete(point.id); }
  }
  return result;
}

export function recommendPoint(points: KnowledgePoint[], profile: LearnerProfile | null): string {
  const ordered = orderKnowledge(points);
  const mastered = new Set(profile?.mastery.filter(item => item.evidence_count > 0 && item.score >= .6).map(item => item.knowledge_point_id));
  return ordered.find(point => !mastered.has(point.id) && point.prerequisites.every(id => mastered.has(id)))?.id
    ?? ordered.find(point => !mastered.has(point.id))?.id ?? ordered[0]?.id ?? "";
}

export function lessonScenes(point: KnowledgePointDetail): Array<{ title: string; content: string }> {
  return point.lesson.learning_sequence?.length ? point.lesson.learning_sequence : [
    { title: "概念与适用条件", content: point.lesson.summary ?? "课程讲解尚未提供。" },
    ...(point.lesson.key_points ?? []).map((content, i) => ({ title: `推演要点 ${i + 1}`, content })),
    { title: "检查边界", content: (point.lesson.common_mistakes ?? []).join("\n\n") },
  ];
}

export function asCodeTask(activity: ActivityDetail): ClassroomCodeTask {
  return {
    exercise_id: activity.id, title: activity.title, prompt: activity.prompt ?? "",
    difficulty: activity.difficulty, estimated_minutes: activity.estimated_minutes,
    input_format: activity.input_format ?? "按题面和公开样例读取标准输入。",
    output_format: activity.output_format ?? "按公开样例输出，不添加提示文字。",
    constraints: activity.constraints,
    starter_code: activity.evaluation.starter_code ?? (activity.evaluation.runtime?.language === "c"
      ? "#include <stdio.h>\n\nint main(void) {\n    /* 在这里完成程序 */\n    return 0;\n}\n" : "# 在这里完成程序\n"),
    public_examples: activity.public_examples.length ? activity.public_examples
      : (activity.evaluation.tests ?? []).map(test => ({ ...test, explanation: "公开测试样例" })),
  };
}

export function readLessonPosition(storage: Pick<Storage, "getItem">, key: string): string {
  try { const value = storage.getItem(key); return value && /^(C|DS)-[A-Z]+-\d+$/.test(value) ? value : ""; }
  catch { return ""; }
}
