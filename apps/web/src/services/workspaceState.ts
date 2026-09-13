import {
  ApiError, type api, type CourseId, type CourseSummary, type KnowledgePoint,
  type ActivitySummary, type LearnerProfile, type NextActivity, type DiagnosticQuiz,
  type QaResponse,
} from "./api";

export function measuredMastery(profile: LearnerProfile | null) {
  return (profile?.mastery ?? []).filter((item) => (
    item.evidence_count > 0 && Number.isFinite(item.score) && item.score >= 0 && item.score <= 1
  ));
}

export function hasLearningEvidence(profile: LearnerProfile | null): boolean {
  return measuredMastery(profile).length > 0;
}

export function serviceFailure(error: unknown): string {
  if (error instanceof ApiError && error.status >= 500) {
    return "服务暂时不可用，请稍后重试；未载入的数据不会计为学习结果。";
  }
  if (error instanceof TypeError) return "无法连接课程服务，请检查网络后重试。";
  return error instanceof Error ? error.message : "操作失败，请稍后重试。";
}

export function qaFeedbackLabel(result: QaResponse): string {
  const degraded = result.trace.some((step) => step.status === "degraded");
  if (result.status !== "answered") return degraded ? "服务暂不可用" : "依据不足";
  return degraded ? "已降级 · 请核对课程依据" : "已通过质量检查";
}

export function verificationUnavailable(result: { verification: { diagnostics: string[] } | null }): boolean {
  return result.verification?.diagnostics.some((detail) => detail.includes("验证服务暂不可用")) ?? false;
}

export interface CourseWorkspace {
  courses: CourseSummary[];
  knowledge: KnowledgePoint[];
  activities: ActivitySummary[];
  profile: LearnerProfile | null;
  next: NextActivity | null;
  diagnostic: DiagnosticQuiz | null;
  catalogError: string;
  learningError: string;
}

type WorkspaceApi = Pick<typeof api,
  "courses" | "knowledgePoints" | "activities" | "profile" | "nextActivity" | "diagnostic"
>;

/** Keep public course content usable when learning persistence is unavailable. */
export async function loadCourseWorkspace(
  client: WorkspaceApi, studentId: string, courseId: CourseId,
): Promise<CourseWorkspace> {
  const [courses, knowledge, activities, profile] = await Promise.allSettled([
    client.courses(), client.knowledgePoints(courseId), client.activities(courseId),
    client.profile(studentId, courseId),
  ]);
  const state: CourseWorkspace = {
    courses: courses.status === "fulfilled" ? courses.value : [],
    knowledge: knowledge.status === "fulfilled" ? knowledge.value.items : [],
    activities: activities.status === "fulfilled" ? activities.value : [],
    profile: profile.status === "fulfilled" ? profile.value : null,
    next: null, diagnostic: null, catalogError: "", learningError: "",
  };
  const catalogFailure = [courses, knowledge, activities].find((result) => result.status === "rejected");
  if (catalogFailure?.status === "rejected") state.catalogError = serviceFailure(catalogFailure.reason);
  if (profile.status === "rejected"
    && !(profile.reason instanceof ApiError && profile.reason.status === 404)) {
    state.learningError = serviceFailure(profile.reason);
  }
  const [next, diagnostic] = await Promise.allSettled([
    hasLearningEvidence(state.profile)
      ? client.nextActivity(studentId, courseId) : Promise.resolve(null),
    client.diagnostic(courseId, hasLearningEvidence(state.profile) ? "reassessment" : "initial"),
  ]);
  if (next.status === "fulfilled") state.next = next.value;
  else state.learningError ||= serviceFailure(next.reason);
  if (diagnostic.status === "fulfilled") state.diagnostic = diagnostic.value;
  else state.learningError ||= serviceFailure(diagnostic.reason);
  return state;
}

/** Tokens bind async responses to the latest course/account selection. */
export function createRequestScope() {
  let revision = 0;
  return {
    begin: () => ++revision,
    capture: () => revision,
    isCurrent: (token: number) => token === revision,
    invalidate: () => { revision += 1; },
  };
}

/** Storage is user editable and may belong to an older UI version. */
export function readProjectDraft(raw: string | null, defaultGoal: string) {
  const empty = { summary: "", repository: "", tests: "", goal: defaultGoal };
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    if (!value || typeof value !== "object" || Array.isArray(value)) return empty;
    const draft = value as Record<string, unknown>;
    return Object.fromEntries(Object.entries(empty).map(([key, fallback]) => [
      key, typeof draft[key] === "string" ? draft[key] : fallback,
    ])) as typeof empty;
  } catch { return empty; }
}

export function readSavedIds(raw: string | null): string[] {
  try {
    const value: unknown = JSON.parse(raw ?? "[]");
    return Array.isArray(value) ? [...new Set(value.filter((id): id is string => typeof id === "string"))] : [];
  } catch { return []; }
}
