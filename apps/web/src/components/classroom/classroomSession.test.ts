import { describe, expect, it } from "vitest";

import type { KeyValueStorage } from "../../uiPreferences";
import {
  classroomSessionKey,
  loadClassroomSession,
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
