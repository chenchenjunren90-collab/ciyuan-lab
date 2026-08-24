export type CourseId = "c" | "python" | "data_structures";

export interface HealthResponse { status: "ok"; service: string; version: string }
export interface CourseSummary {
  id: CourseId; title: string; status: string;
  target_core_concepts: number; implemented_core_concepts: number;
  features: Record<string, string>;
}
export interface KnowledgePoint {
  id: string; title: string; difficulty: "beginner" | "intermediate" | "advanced";
  prerequisites: string[]; source_refs: string[];
}
export interface ActivitySummary {
  id: string; title: string; course: CourseId;
  type: "objective" | "short_answer" | "code" | "debug" | "project";
  difficulty: string; estimated_minutes: number; concept_ids: string[]; source_refs: string[];
}
export interface ActivityDetail extends ActivitySummary {
  prompt: string | null; summary: string | null; requirements: string[]; deliverables: string[];
  evaluation: {
    mode: string;
    options?: Array<{ id: string; text: string }>;
    runtime?: { language: "c" | "python" };
    tests?: Array<{ id: string; visibility: "public"; input: string; expected_output: string }>;
  };
  computer_science_objectives: string[]; business_context_objectives: string[];
}
export interface MasteryState {
  knowledge_point_id: string; score: number; evidence_count: number; updated_at: string | null;
}
export interface LearnerProfile { student_id: string; course_id: CourseId; mastery: MasteryState[] }
export interface NextActivity {
  activity_id: string;
  activity_type: "concept" | ActivitySummary["type"];
  reason: string;
}
export interface PlanStage {
  stage: string; objective: string; knowledge_point_ids: string[]; reason: string;
}
export interface AssessmentResult {
  profile: LearnerProfile;
  plan: { student_id: string; course_id: CourseId; stages: PlanStage[]; next_activity: NextActivity };
}
export interface QaResponse {
  status: "answered" | "insufficient_evidence"; answer: string;
  citations: Array<{ source_id: string; chunk_id: string; score: number }>;
}
export interface SubmissionResult {
  verification: { accepted: boolean; passed_tests: number; total_tests: number; diagnostics: string[] } | null;
  feedback: string; citations: Array<{ source_id: string; chunk_id: string; score: number }>;
  mastery_updated: MasteryState[]; next_activity: NextActivity;
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message) }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options: RequestInit = {}, fetcher: typeof fetch = fetch): Promise<T> {
  const response = await fetcher(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers
    }
  });
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch { /* Keep a stable message for non-JSON failures. */ }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export function fetchApiHealth(fetcher: typeof fetch = fetch): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health", {}, fetcher);
}

export const api = {
  courses: () => request<CourseSummary[]>("/api/v1/courses"),
  knowledgePoints: (courseId: CourseId) =>
    request<{ course_id: CourseId; items: KnowledgePoint[] }>(`/api/v1/courses/${courseId}/knowledge-points`),
  activities: (courseId: CourseId) => request<ActivitySummary[]>(`/api/v1/courses/${courseId}/activities`),
  activity: (courseId: CourseId, activityId: string) =>
    request<ActivityDetail>(`/api/v1/courses/${courseId}/activities/${activityId}`),
  profile: (studentId: string, courseId: CourseId) =>
    request<LearnerProfile>(`/api/v1/profile?student_id=${encodeURIComponent(studentId)}&course_id=${courseId}`),
  nextActivity: (studentId: string, courseId: CourseId) =>
    request<NextActivity>(`/api/v1/next-activity?student_id=${encodeURIComponent(studentId)}&course_id=${courseId}`),
  assess: (studentId: string, courseId: CourseId, answers: Array<{ knowledge_point_id: string; is_correct: boolean }>) =>
    request<AssessmentResult>("/api/v1/assessments", {
      method: "POST", body: JSON.stringify({ student_id: studentId, course_id: courseId, answers })
    }),
  ask: (studentId: string, courseId: CourseId, question: string) => request<QaResponse>("/api/v1/qa", {
    method: "POST", body: JSON.stringify({ student_id: studentId, course_id: courseId, question })
  }),
  submit: (
    studentId: string, courseId: CourseId, exerciseId: string,
    payload: { response?: string; language?: "c" | "python"; source_code?: string }
  ) => request<SubmissionResult>(`/api/v1/exercises/${exerciseId}/submissions?course_id=${courseId}`, {
    method: "POST", body: JSON.stringify({ student_id: studentId, ...payload })
  })
};
