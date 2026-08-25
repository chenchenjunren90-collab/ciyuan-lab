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
export interface KnowledgePointDetail extends KnowledgePoint {
  course: CourseId; estimated_minutes: number; learning_objectives: string[];
  concepts: string[];
  lesson: { summary?: string; key_points?: string[]; examples?: string[]; common_mistakes?: string[] };
  assessment_ids: string[]; status: string;
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
  scenario_scope: string | null; scenario_provider: string | null;
  data_classification: string | null; fallback_source_refs: string[];
}
export interface ScenarioContext {
  project_id: string; course_id: CourseId;
  mode: "tuoling" | "fixed_synthetic";
  provider_status: "live" | "disabled" | "fallback";
  context: string; constraints: string[]; source_refs: string[];
  data_classification: string; notice: string;
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
  trace: Array<{
    component: "retrieval" | "course_tutor" | "quality_supervisor";
    status: "completed" | "degraded" | "blocked"; detail: string;
  }>;
}
export interface HintResponse {
  activity_id: string; level: 1 | 2 | 3; hint: string;
  focus_concept_ids: string[]; source_refs: string[]; answer_revealed: false;
}
export interface ProjectSubmissionResponse {
  submission_id: string; project_id: string; status: "received_for_review"; feedback: string;
  review_checklist: Array<{ item: string; present: boolean; detail: string }>;
  mastery_unchanged: MasteryState[];
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
  knowledgePoint: (courseId: CourseId, knowledgePointId: string) =>
    request<KnowledgePointDetail>(`/api/v1/courses/${courseId}/knowledge-points/${knowledgePointId}`),
  activities: (courseId: CourseId) => request<ActivitySummary[]>(`/api/v1/courses/${courseId}/activities`),
  activity: (courseId: CourseId, activityId: string) =>
    request<ActivityDetail>(`/api/v1/courses/${courseId}/activities/${activityId}`),
  scenario: (courseId: CourseId, projectId: string) =>
    request<ScenarioContext>(`/api/v1/courses/${courseId}/projects/${projectId}/scenario`),
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
  hint: (studentId: string, courseId: CourseId, activityId: string, level: 1 | 2 | 3) =>
    request<HintResponse>(`/api/v1/activities/${activityId}/hint?course_id=${courseId}`, {
      method: "POST", body: JSON.stringify({ student_id: studentId, level })
    }),
  submitProject: (
    studentId: string, courseId: CourseId, projectId: string,
    payload: { artifact_summary: string; repository_url?: string; test_evidence: string[] }
  ) => request<ProjectSubmissionResponse>(`/api/v1/projects/${projectId}/submissions?course_id=${courseId}`, {
    method: "POST", body: JSON.stringify({ student_id: studentId, ...payload })
  }),
  submit: (
    studentId: string, courseId: CourseId, exerciseId: string,
    payload: { response?: string; language?: "c" | "python"; source_code?: string }
  ) => request<SubmissionResult>(`/api/v1/exercises/${exerciseId}/submissions?course_id=${courseId}`, {
    method: "POST", body: JSON.stringify({ student_id: studentId, ...payload })
  })
};
