import { describe, expect, it } from "vitest";
import { beginnerDiagnosticAnswers } from "./beginnerDiagnostic";
import type { DiagnosticQuiz } from "./api";

const quiz: DiagnosticQuiz = {
  course_id: "python", phase: "initial", title: "摸底", instructions: "如实回答",
  items: ["one", "two"].map(exercise_id => ({
    exercise_id, title: "题目", prompt: "问题", concept_ids: [], skill_atoms: [],
    options: [{ id: "A", text: "选项" }, { id: "UNKNOWN", text: "我不知道" }],
  })),
};

describe("beginner diagnostic shortcut", () => {
  it("records unanswered questions as UNKNOWN for every course", () => {
    for (const course_id of ["c", "python", "data_structures"] as const) {
      expect(beginnerDiagnosticAnswers({ ...quiz, course_id }, {})).toEqual({ one: "UNKNOWN", two: "UNKNOWN" });
    }
  });
  it("preserves answers, ignores stale question IDs, and does not mutate a draft", () => {
    const draft = { one: "A", stale: "A" };
    expect(beginnerDiagnosticAnswers(quiz, draft)).toEqual({ one: "A", two: "UNKNOWN" });
    expect(draft).toEqual({ one: "A", stale: "A" });
  });
  it("does not skip reassessments or submit an empty or missing quiz", () => {
    expect(beginnerDiagnosticAnswers({ ...quiz, phase: "reassessment" }, {})).toBeNull();
    expect(beginnerDiagnosticAnswers({ ...quiz, items: [] }, {})).toBeNull();
    expect(beginnerDiagnosticAnswers(null, {})).toBeNull();
  });
  it("rejects unsupported options rather than manufacturing answers", () => {
    expect(beginnerDiagnosticAnswers({ ...quiz, items: quiz.items.map(item => ({ ...item, options: [{ id: "A", text: "选项" }] })) }, {})).toBeNull();
    expect(beginnerDiagnosticAnswers(quiz, { one: "invalid" })).toBeNull();
  });
  it("can retry the same explicit unknown answers without changing them", () => {
    const first = beginnerDiagnosticAnswers(quiz, {})!;
    expect(beginnerDiagnosticAnswers(quiz, first)).toEqual(first);
  });
});
