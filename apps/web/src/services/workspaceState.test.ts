import { describe, expect, it, vi } from "vitest";
import { ApiError, type CourseSummary, type DiagnosticQuiz, type KnowledgePoint, type LearnerProfile, type QaResponse } from "./api";
import { createRequestScope, hasLearningEvidence, loadCourseWorkspace, measuredMastery, qaFeedbackLabel, readProjectDraft, readSavedIds, verificationUnavailable } from "./workspaceState";

describe("persisted project workspaces", () => {
  it("restores each project's complete draft without sharing goals", () => {
    const a = JSON.stringify({ summary: "项目 A", repository: "https://example.com/a", tests: "3 passed", goal: "异常处理" });
    const b = JSON.stringify({ summary: "项目 B" });
    expect(readProjectDraft(a, "默认目标")).toEqual({ summary: "项目 A", repository: "https://example.com/a", tests: "3 passed", goal: "异常处理" });
    expect(readProjectDraft(b, "默认目标")).toEqual({ summary: "项目 B", repository: "", tests: "", goal: "默认目标" });
    expect(readProjectDraft(a, "默认目标").goal).toBe("异常处理");
  });
  it.each([null, "{broken", "null", "[]", '"old version"'])("recovers invalid draft storage: %s", (raw) => {
    expect(readProjectDraft(raw, "默认目标")).toEqual({ summary: "", repository: "", tests: "", goal: "默认目标" });
  });
  it("rejects malformed field types without discarding valid text", () => {
    expect(readProjectDraft('{"summary":42,"repository":{},"tests":"1 passed","goal":null}', "默认目标"))
      .toEqual({ summary: "", repository: "", tests: "1 passed", goal: "默认目标" });
    expect(readSavedIds('["A",null,42,"B","A"]')).toEqual(["A", "B"]);
    expect(readSavedIds('{"A":true}')).toEqual([]);
    expect(readSavedIds("broken")).toEqual([]);
  });
});

const profile: LearnerProfile = {
  student_id: "test-student", course_id: "python",
  mastery: [{ knowledge_point_id: "PY-LIST-03", score: .7, evidence_count: 1, updated_at: null }],
};
function client() {
  return {
    courses: vi.fn().mockResolvedValue([{ id: "python", title: "Python" }] as CourseSummary[]),
    knowledgePoints: vi.fn().mockResolvedValue({ course_id: "python", items: [{ id: "PY-LIST-03" }] as KnowledgePoint[] }),
    activities: vi.fn().mockResolvedValue([]),
    profile: vi.fn().mockResolvedValue(profile),
    nextActivity: vi.fn().mockResolvedValue({ activity_id: "PY-LIST-03", activity_type: "concept", reason: "依据测评" }),
    diagnostic: vi.fn().mockResolvedValue({ course_id: "python", phase: "initial", items: [] } as unknown as DiagnosticQuiz),
  };
}

describe("course workspace and evidence boundaries", () => {
  it("keeps course data and an initial diagnostic usable during database failure", async () => {
    const api = client();
    api.profile.mockRejectedValue(new ApiError(503, "database down"));
    const state = await loadCourseWorkspace(api, "test-student", "python");
    expect(state.knowledge).toHaveLength(1);
    expect(state.catalogError).toBe("");
    expect(state.learningError).toContain("暂时不可用");
    expect(state.profile).toBeNull();
    expect(api.nextActivity).not.toHaveBeenCalled();
    expect(api.diagnostic).toHaveBeenCalledWith("python", "initial");
  });
  it("treats a missing profile as unassessed, not a service failure", async () => {
    const api = client();
    api.profile.mockRejectedValue(new ApiError(404, "not found"));
    const state = await loadCourseWorkspace(api, "test-student", "c");
    expect(state.learningError).toBe("");
    expect(api.diagnostic).toHaveBeenCalledWith("c", "initial");
  });
  it("does not mistake an empty legacy self-report profile for a completed assessment", async () => {
    const api = client();
    api.profile.mockResolvedValue({ ...profile, mastery: [] });
    await loadCourseWorkspace(api, "test-student", "python");
    expect(api.nextActivity).not.toHaveBeenCalled();
    expect(api.diagnostic).toHaveBeenCalledWith("python", "initial");
  });
  it("selects reassessment and the server's next activity after objective evidence", async () => {
    const api = client();
    const state = await loadCourseWorkspace(api, "test-student", "python");
    expect(api.diagnostic).toHaveBeenCalledWith("python", "reassessment");
    expect(state.next?.activity_id).toBe("PY-LIST-03");
    expect(state.profile).toEqual(profile);
  });
  it("separates catalog failures from learning service failures", async () => {
    const api = client();
    api.knowledgePoints.mockRejectedValue(new ApiError(503, "unavailable"));
    const state = await loadCourseWorkspace(api, "test-student", "python");
    expect(state.catalogError).not.toBe("");
    expect(state.knowledge).toEqual([]);
    expect(state.profile).toEqual(profile);
  });
  it("keeps the profile when planning fails instead of claiming it does not exist", async () => {
    const api = client();
    api.nextActivity.mockRejectedValue(new ApiError(503, "unavailable"));
    const state = await loadCourseWorkspace(api, "test-student", "python");
    expect(state.profile).toEqual(profile);
    expect(state.next).toBeNull();
    expect(state.learningError).not.toBe("");
    expect(state.catalogError).toBe("");
  });
  it("excludes priors, non-finite scores and invalid ranges from measured mastery", () => {
    const entries = [
      ...profile.mastery,
      { ...profile.mastery[0]!, score: .9, evidence_count: 0 },
      { ...profile.mastery[0]!, score: Number.NaN },
      { ...profile.mastery[0]!, score: 2 },
    ];
    expect(measuredMastery({ ...profile, mastery: entries })).toEqual(profile.mastery);
    expect(hasLearningEvidence({ ...profile, mastery: entries.slice(1) })).toBe(false);
    expect(hasLearningEvidence(null)).toBe(false);
  });
  it("invalidates pending requests even when a learner returns to the same course", () => {
    const scope = createRequestScope();
    const firstPython = scope.begin();
    scope.begin();
    const secondPython = scope.begin();
    expect(scope.isCurrent(firstPython)).toBe(false);
    expect(scope.isCurrent(secondPython)).toBe(true);
    expect(scope.capture()).toBe(secondPython);
    scope.invalidate();
    expect(scope.isCurrent(secondPython)).toBe(false);
  });
});

describe("backend feedback presentation", () => {
  const qa: QaResponse = { status: "answered", answer: "证据摘录", citations: [], trace: [] };
  it("does not claim semantic approval for an evidence-only fallback", () => {
    expect(qaFeedbackLabel({ ...qa, trace: [{ component: "course_tutor", status: "degraded", detail: "证据摘录" }] })).toContain("已降级");
  });
  it("distinguishes a retrieval outage from insufficient knowledge", () => {
    expect(qaFeedbackLabel({ ...qa, status: "insufficient_evidence", trace: [{ component: "retrieval", status: "degraded", detail: "连接失败" }] })).toBe("服务暂不可用");
    expect(qaFeedbackLabel({ ...qa, status: "insufficient_evidence" })).toBe("依据不足");
  });
  it("distinguishes unavailable verification from a student's code failure", () => {
    expect(verificationUnavailable({ verification: { diagnostics: ["验证服务暂不可用：隔离运行环境未就绪"] } })).toBe(true);
    expect(verificationUnavailable({ verification: { diagnostics: ["隐藏测试未通过"] } })).toBe(false);
    expect(verificationUnavailable({ verification: null })).toBe(false);
  });
});
