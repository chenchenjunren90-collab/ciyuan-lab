export type CourseId = "c" | "python" | "data_structures";

export interface HealthResponse { status: "ok"; service: string; version: string }
export interface CourseSummary {
  id: CourseId; title: string; status: string;
  target_core_concepts: number; implemented_core_concepts: number;
  features: Record<string, string>;
}
export interface KnowledgePoint {
  id: string; title: string; difficulty: "beginner" | "intermediate" | "advanced";
  prerequisites: string[]; concepts: string[]; source_refs: string[];
}
export interface KnowledgePointDetail extends KnowledgePoint {
  course: CourseId; estimated_minutes: number; learning_objectives: string[];
  lesson: {
    summary?: string; key_points?: string[]; examples?: string[]; common_mistakes?: string[];
    learning_sequence?: Array<{ title: string; content: string }>;
    worked_example?: { problem: string; steps: string[]; code: string; reflection: string };
    checkpoint?: { prompt: string; guidance: string };
  };
  assessment_ids: string[]; status: string;
}
export interface ActivitySummary {
  id: string; title: string; course: CourseId;
  type: "objective" | "short_answer" | "code" | "debug" | "project";
  difficulty: string; estimated_minutes: number; concept_ids: string[]; source_refs: string[];
  learning_stage: "diagnostic" | "in_class" | "after_class" | "challenge" | null;
}
export interface ActivityDetail extends ActivitySummary {
  prompt: string | null; summary: string | null; requirements: string[]; deliverables: string[];
  evaluation: {
    mode: string;
    options?: Array<{ id: string; text: string }>;
    runtime?: { language: "c" | "python" };
    starter_code?: string;
    tests?: Array<{ id: string; visibility: "public"; input: string; expected_output: string }>;
  };
  computer_science_objectives: string[]; business_context_objectives: string[];
  scenario_scope: string | null; scenario_provider: string | null;
  data_classification: string | null; fallback_source_refs: string[];
  audience: string | null; scaffolding: string[];
  input_format: string | null; output_format: string | null; constraints: string[];
  public_examples: Array<{ input: string; expected_output: string; explanation: string }>;
  reflection_prompt: string | null; source_adaptation: Record<string, string>;
  status: string;
}
export interface ScenarioContext {
  project_id: string; course_id: CourseId;
  mode: "tuoling" | "fixed_synthetic";
  provider_status: "live" | "disabled" | "fallback";
  context: string; constraints: string[]; source_refs: string[];
  data_classification: string; notice: string;
}
export interface GeneratedScenarioProject {
  title: string; scenario_context: string; tasks: string[]; constraints: string[];
  deliverables: string[]; source_refs: string[]; computer_science_objectives: string[];
  data_classification: "synthetic"; ai_generated_notice: string;
  provider: string; model: string; degraded: boolean;
  dataset: {
    filename: string; columns: string[];
    rows: Array<Record<string, string | number | boolean | null>>; sha256: string;
  };
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
export type DiagnosticPhase = "initial" | "reassessment";
export interface DiagnosticSkillAtom {
  id: string; knowledge_point_id: string; label: string;
}
export interface DiagnosticPrerequisiteGap {
  downstream_id: string; downstream_title: string;
  missing_prerequisite_id: string; missing_prerequisite_title: string; reason: string;
}
export interface DiagnosticLearningBlock {
  block_id: string; knowledge_point_id: string; title: string; reason: string;
  estimated_minutes: number; skill_atoms: DiagnosticSkillAtom[]; summary: string;
  key_points: string[]; example_problem: string; example_steps: string[]; example_code: string;
}
export interface DiagnosticAnalysis {
  course_core_nodes: number; course_skill_atoms: number;
  assessed_core_nodes: number; assessed_skill_atoms: number;
  evidence_scope: "knowledge_point_proxy"; non_linear_profile: boolean;
  prerequisite_gaps: DiagnosticPrerequisiteGap[];
  demonstrated_knowledge_point_ids: string[]; focus_knowledge_point_ids: string[];
  learning_blocks: DiagnosticLearningBlock[];
}
export interface DiagnosticQuiz {
  course_id: CourseId; phase: DiagnosticPhase; title: string; instructions: string;
  items: Array<{
    exercise_id: string; title: string; prompt: string; concept_ids: string[];
    skill_atoms: DiagnosticSkillAtom[];
    options: Array<{ id: string; text: string }>;
  }>;
}
export interface DiagnosticSubmissionResult extends AssessmentResult {
  phase: DiagnosticPhase; correct_count: number; unknown_count: number; total_count: number;
  item_results: Array<{ exercise_id: string; knowledge_point_id: string; correct: boolean; unknown: boolean; skill_atom_ids: string[] }>;
  analysis: DiagnosticAnalysis;
}
export interface QaResponse {
  status: "answered" | "insufficient_evidence"; answer: string;
  citations: Array<{
    source_id: string; chunk_id: string; score: number;
    source_type?: "course" | "online"; source_title?: string | null; source_url?: string | null;
  }>;
  trace: Array<{
    component: "retrieval" | "course_tutor" | "quality_supervisor";
    status: "completed" | "degraded" | "blocked"; detail: string;
  }>;
}
export type ClassroomRole = "teacher" | "ta" | "peer_cautious" | "peer_debugger" | "peer_summarizer";
export interface ClassroomDialogueTurn {
  role: ClassroomRole | "student";
  content: string;
}
export type ClassroomPhase = "welcome" | "concept" | "discussion" | "debug" | "practice" | "summary" | "homework";
export interface ClassroomPersona {
  role: ClassroomRole; display_name: string; tagline: string; tone: string;
}
export interface ClassroomChoice { id: string; text: string }
export interface ClassroomBeat {
  id: string; phase: ClassroomPhase; speaker: ClassroomRole; eyebrow: string; title: string;
  message: string; board_title: string; board_explanation: string; board_points: string[];
  board_code: string; board_trace: string[];
  action: "continue" | "choice" | "practice" | "homework" | "complete";
  checkpoint: { prompt: string; choices: ClassroomChoice[] } | null;
}
export interface ClassroomCodeTask {
  exercise_id: string; title: string; prompt: string; difficulty: string; estimated_minutes: number;
  input_format: string; output_format: string; constraints: string[]; starter_code: string;
  public_examples: Array<{ input: string; expected_output: string; explanation: string }>;
}
export interface ClassroomLesson {
  lesson_id: string; course_id: "python"; title: string; subtitle: string; duration_minutes: number;
  knowledge_point_ids: string[]; unlock_title: string; cast: ClassroomPersona[];
  beats: ClassroomBeat[]; practice: ClassroomCodeTask; homework: ClassroomCodeTask;
  delivery_mode: "scripted" | "adaptive"; stage_id: string; stage_index: number;
  total_stages: number; stage_title: string; stage_outcome: string; planning_reason: string;
  focus_skill_atoms: string[]; unlocked_project_ids: string[];
}
export interface ClassroomCheckpointResult {
  accepted: boolean; feedback: string; reply_role: ClassroomRole;
  reply_display_name: string; reply_message: string;
}
export interface ClassroomDialogueResponse {
  status: "answered" | "insufficient_evidence"; role: ClassroomRole; display_name: string;
  question_scope: "current_lesson" | "python_course_extension" | "outside_course" | "undetermined";
  scope_notice: string | null; suggested_knowledge_point_ids: string[];
  answer: string; citations: QaResponse["citations"]; trace: QaResponse["trace"];
}
export interface ClassroomSelfProfileResponse {
  level: "newcomer" | "beginner" | "developing" | "experienced";
  level_label: string; confidence: "low" | "medium" | "high"; course_fit: string;
  recommended_start: string; matched_knowledge_point_ids: string[]; signals: string[];
  advisor_message: string; citations: QaResponse["citations"]; trace: QaResponse["trace"];
}
export type ClassroomSelfProfileLevel = ClassroomSelfProfileResponse["level"];
export interface HintResponse {
  activity_id: string; level: 1 | 2 | 3; hint: string;
  focus_concept_ids: string[]; source_refs: string[]; answer_revealed: false;
}
export interface ProjectSubmissionResponse {
  submission_id: string; project_id: string; status: "evidence_recorded"; feedback: string;
  evidence_checklist: Array<{ item: string; present: boolean; detail: string }>;
  mastery_unchanged: MasteryState[];
}
export interface SubmissionResult {
  verification: { accepted: boolean; passed_tests: number; total_tests: number; diagnostics: string[] } | null;
  feedback: string; citations: Array<{ source_id: string; chunk_id: string; score: number }>;
  mastery_updated: MasteryState[]; next_activity: NextActivity;
}
export interface GeneratedCodeProblem {
  problem_id: string; course_id: "python"; title: string; prompt: string;
  concept_ids: string[]; difficulty: "beginner" | "intermediate" | "advanced";
  constraints: string[];
  public_examples: Array<{ input: string; expected_output: string }>;
  starter_code: string; hints: string[]; generation_notice: string;
}
export interface GeneratedProblemSubmissionResponse {
  problem: GeneratedCodeProblem;
  verification: { accepted: boolean; passed_tests: number; total_tests: number; diagnostics: string[] };
  feedback: string; profile: LearnerProfile; next_problem: GeneratedCodeProblem;
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message) }
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const configuredTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? "10000");
const defaultTimeoutMs = Number.isFinite(configuredTimeoutMs) && configuredTimeoutMs > 0
  ? configuredTimeoutMs
  : 10000;
const configuredAiTimeoutMs = Number(import.meta.env.VITE_AI_TIMEOUT_MS ?? "90000");
const aiTimeoutMs = Number.isFinite(configuredAiTimeoutMs) && configuredAiTimeoutMs > 0
  ? configuredAiTimeoutMs
  : 90000;

async function request<T>(
  path: string,
  options: RequestInit = {},
  fetcher: typeof fetch = fetch,
  timeoutMs: number = defaultTimeoutMs
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetcher(`${apiBaseUrl}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers
      },
      signal: controller.signal
    });
    if (!response.ok) {
      let message = `请求失败（${response.status}）`;
      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") {
          message = payload.detail;
        } else if (
          Array.isArray(payload.detail) && payload.detail.length
          && typeof payload.detail[0] === "object" && payload.detail[0] !== null
          && "msg" in payload.detail[0]
          && typeof (payload.detail[0] as { msg: unknown }).msg === "string"
        ) {
          message = `参数不合法：${(payload.detail[0] as { msg: string }).msg}`;
        }
      } catch { /* Keep a stable message for non-JSON failures. */ }
      throw new ApiError(response.status, message);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "请求超时，请检查服务状态后重试");
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}

export function fetchApiHealth(
  fetcher: typeof fetch = fetch,
  timeoutMs: number = defaultTimeoutMs
): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health", {}, fetcher, timeoutMs);
}

export const api = {
  courses: () => request<CourseSummary[]>("/api/v1/courses"),
  knowledgePoints: (courseId: CourseId) =>
    request<{ course_id: CourseId; items: KnowledgePoint[] }>(`/api/v1/courses/${courseId}/knowledge-points`),
  knowledgePoint: (courseId: CourseId, knowledgePointId: string) =>
    request<KnowledgePointDetail>(`/api/v1/courses/${courseId}/knowledge-points/${knowledgePointId}`),
  activities: (
    courseId: CourseId,
    filters: { knowledgePointId?: string; learningStage?: ActivitySummary["learning_stage"] } = {}
  ) => {
    const params = new URLSearchParams();
    if (filters.knowledgePointId) params.set("knowledge_point_id", filters.knowledgePointId);
    if (filters.learningStage) params.set("learning_stage", filters.learningStage);
    const query = params.toString();
    return request<ActivitySummary[]>(
      `/api/v1/courses/${courseId}/activities${query ? `?${query}` : ""}`
    );
  },
  activity: (courseId: CourseId, activityId: string) =>
    request<ActivityDetail>(`/api/v1/courses/${courseId}/activities/${activityId}`),
  scenario: (courseId: CourseId, projectId: string) =>
    request<ScenarioContext>(`/api/v1/courses/${courseId}/projects/${projectId}/scenario`),
  generateScenarioProject: (
    courseId: CourseId,
    payload: {
      template_project_id: string; learner_goal: string; target_concept_ids: string[];
      difficulty: "beginner" | "intermediate" | "advanced"; estimated_minutes: number;
    }
  ) => request<GeneratedScenarioProject>(`/api/v1/courses/${courseId}/scenario-projects/generate`, {
    method: "POST", body: JSON.stringify({ course_id: courseId, ...payload })
  }, fetch, aiTimeoutMs),
  profile: (studentId: string, courseId: CourseId) =>
    request<LearnerProfile>(`/api/v1/profile?student_id=${encodeURIComponent(studentId)}&course_id=${courseId}`),
  nextActivity: (studentId: string, courseId: CourseId) =>
    request<NextActivity>(
      `/api/v1/next-activity?student_id=${encodeURIComponent(studentId)}&course_id=${courseId}`,
      {}, fetch, aiTimeoutMs
    ),
  assess: (studentId: string, courseId: CourseId, answers: Array<{ knowledge_point_id: string; is_correct: boolean }>) =>
    request<AssessmentResult>("/api/v1/assessments", {
      method: "POST", body: JSON.stringify({ student_id: studentId, course_id: courseId, answers })
    }, fetch, aiTimeoutMs),
  diagnostic: (courseId: CourseId, phase: DiagnosticPhase) =>
    request<DiagnosticQuiz>(`/api/v1/diagnostics?course_id=${courseId}&phase=${phase}`),
  submitDiagnostic: (
    studentId: string, courseId: CourseId, phase: DiagnosticPhase,
    answers: Array<{ exercise_id: string; response: string }>
  ) => request<DiagnosticSubmissionResult>("/api/v1/diagnostics/submissions", {
    method: "POST", body: JSON.stringify({ student_id: studentId, course_id: courseId, phase, answers })
  }, fetch, aiTimeoutMs),
  generateAdaptiveProblem: (studentId: string, courseId: CourseId, attemptIndex: number) =>
    request<GeneratedCodeProblem>("/api/v1/adaptive-problems/generate", {
      method: "POST", body: JSON.stringify({
        student_id: studentId, course_id: courseId, attempt_index: attemptIndex
      })
    }),
  submitAdaptiveProblem: (studentId: string, problemId: string, sourceCode: string) =>
    request<GeneratedProblemSubmissionResponse>(
      `/api/v1/adaptive-problems/${encodeURIComponent(problemId)}/submissions`,
      { method: "POST", body: JSON.stringify({ student_id: studentId, source_code: sourceCode }) },
      fetch,
      aiTimeoutMs
    ),
  ask: (studentId: string, courseId: CourseId, question: string) => request<QaResponse>("/api/v1/qa", {
    method: "POST", body: JSON.stringify({ student_id: studentId, course_id: courseId, question })
  }, fetch, aiTimeoutMs),
  classroomLesson: (lessonId: string) =>
    request<ClassroomLesson>(`/api/v1/classroom/lessons/${encodeURIComponent(lessonId)}`),
  nextClassroomSession: (
    studentId: string,
    dailyMinutes: number,
    preferredMode: "step_by_step" | "example_first" | "practice_first",
    selfProfileLevel?: ClassroomSelfProfileLevel,
  ) => {
    const params = new URLSearchParams({
      student_id: studentId,
      daily_minutes: String(dailyMinutes),
      preferred_mode: preferredMode,
    });
    if (selfProfileLevel) params.set("self_profile_level", selfProfileLevel);
    return request<ClassroomLesson>(`/api/v1/classroom/sessions/next?${params.toString()}`, {}, fetch, aiTimeoutMs);
  },
  classroomCheckpoint: (lessonId: string, beatId: string, response: string) =>
    request<ClassroomCheckpointResult>("/api/v1/classroom/checkpoints", {
      method: "POST", body: JSON.stringify({ lesson_id: lessonId, beat_id: beatId, response })
    }),
  classroomDialogue: (
    studentId: string, lessonId: string, phase: ClassroomPhase,
    role: ClassroomRole, message: string, recentTurns: ClassroomDialogueTurn[] = []
  ) => request<ClassroomDialogueResponse>("/api/v1/classroom/dialogue", {
    method: "POST", body: JSON.stringify({
      student_id: studentId, lesson_id: lessonId, phase, role, message,
      recent_turns: recentTurns.slice(-8).map((turn) => ({
        role: turn.role,
        content: turn.content.slice(0, 500),
      })),
    })
  }, fetch, aiTimeoutMs),
  classroomSelfProfile: (studentId: string, lessonId: string, description: string) =>
    request<ClassroomSelfProfileResponse>("/api/v1/classroom/self-profile", {
      method: "POST", body: JSON.stringify({
        student_id: studentId, lesson_id: lessonId, description
      })
    }, fetch, aiTimeoutMs),
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
  }, fetch, aiTimeoutMs)
};
