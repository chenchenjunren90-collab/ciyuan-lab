import { describe, expect, it } from "vitest";

import type { KeyValueStorage } from "../../uiPreferences";
import type { ClassroomBeat } from "../../services/api";
import {
  classroomSessionKey,
  loadClassroomSession,
  refreshSessionLectures,
  restoredSessionIndex,
  saveClassroomSession,
  type ClassroomSessionDraft,
} from "./classroomSession";

function memoryStorage(initial: Record<string, string> = {}): KeyValueStorage {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

function sessionDraft(): ClassroomSessionDraft {
  return {
    version: 1,
    contentRevision: 2,
    savedAt: "2026-08-31T09:00:00.000Z",
    lessonId: "python-list-filter-01",
    currentIndex: 3,
    furthestIndex: 4,
    selectedChoice: "B",
    checkpointResult: null,
    checkpointDrafts: {
      "beat-filter": { selectedChoice: "B", checkpointResult: null },
    },
    messages: [{ id: 1, role: "student", name: "我", content: "我的理解是……", kind: "student" }],
    practiceCode: "print('保留草稿')",
    homeworkCode: "",
    practiceResult: null,
    homeworkResult: null,
    hint: "先检查循环条件。",
    lessonComplete: false,
    diagnosticResult: null,
    diagnosticAnswers: { "PY-DIAG-01": "B" },
    baselineOpen: false,
    assessmentStarted: true,
    assessmentIndex: 2,
    assessmentResultVisible: false,
    retakeActive: false,
    learningPlan: null,
    classroomView: "code",
    selectedMaterialId: "",
    isPaused: true,
    sessionBeatSnapshot: [],
  };
}

describe("classroom session persistence", () => {
  const beat = (id: string): ClassroomBeat => ({
    id, phase: "concept", speaker: "teacher", eyebrow: "", title: id, message: "讲解",
    board_title: id, board_explanation: "", board_points: [], board_code: "", board_trace: [],
    action: "continue", checkpoint: null,
  });

  it("keeps the saved step when today's generated lesson has a different order", () => {
    const draft = { ...sessionDraft(), currentIndex: 1, sessionBeatSnapshot: [beat("intro"), beat("choice")] };
    expect(restoredSessionIndex(draft, [beat("choice"), beat("intro")])).toBe(1);
  });

  it("refreshes old lecture content without replacing progress, questions or lesson order", () => {
    const question: ClassroomBeat = { ...beat("choice"), action: "choice" };
    const welcome: ClassroomBeat = { ...beat("intro"), phase: "welcome", message: "本次编排理由" };
    const old = [welcome, question, beat("example"), beat("custom")];
    const updated = { ...beat("example"), board_code: "print('Hello')", board_trace: ["输出 Hello"] };
    const result = refreshSessionLectures(old, [updated, { ...question, title: "新版问题" }, beat("intro")]);
    expect(result.map(item => item.id)).toEqual(old.map(item => item.id));
    expect(result[0]).toEqual(welcome);
    expect(result[1]).toEqual(question);
    expect(result[2]).toEqual(updated);
    expect(result[3]).toEqual(old[3]);
  });

  it("maps a previous content revision by beat ID and clamps removed steps", () => {
    const draft = { ...sessionDraft(), contentRevision: 1, currentIndex: 1, sessionBeatSnapshot: [beat("intro"), beat("choice")] };
    expect(restoredSessionIndex(draft, [beat("choice"), beat("intro")])).toBe(0);
    expect(restoredSessionIndex(draft, [beat("new-intro")])).toBe(0);
    expect(restoredSessionIndex(draft, [])).toBe(0);
  });

  it("preserves an unsent question and its intended classroom role", () => {
    const storage = memoryStorage();
    const draft: ClassroomSessionDraft = { ...sessionDraft(), dialogueText: "这一步为什么报错？", dialogueRole: "ta" };
    saveClassroomSession(storage, "learner-a", draft);
    expect(loadClassroomSession(storage, "learner-a")).toEqual(draft);
  });

  it("restores assessment, classroom and code progress for the same learner", () => {
    const storage = memoryStorage();
    const draft = sessionDraft();
    saveClassroomSession(storage, "learner-a", draft);

    expect(loadClassroomSession(storage, "learner-a")).toEqual(draft);
    expect(loadClassroomSession(storage, "learner-b")).toBeNull();
  });

  it("drops a corrupt draft instead of resetting the page with partial data", () => {
    const key = classroomSessionKey("learner-a");
    const storage = memoryStorage({ [key]: JSON.stringify({ version: 1, lessonId: "python-list-filter-01" }) });

    expect(loadClassroomSession(storage, "learner-a")).toBeNull();
    expect(storage.getItem(key)).toBeNull();
  });
});
