import type {
  ClassroomBeat,
  ClassroomCheckpointResult,
  ClassroomDialogueResponse,
  ClassroomRole,
  DiagnosticSubmissionResult,
  SubmissionResult,
} from "../../services/api";
import type { KeyValueStorage } from "../../uiPreferences";

export type ClassroomWorkspaceView = "lecture" | "discussion" | "code" | "materials";

export interface PersistedClassroomMessage {
  id: number;
  role: ClassroomRole | "student";
  name: string;
  content: string;
  kind: "lesson" | "reply" | "student" | "checkpoint";
  review?: "approved" | "limited";
  evidenceCount?: number;
  evidenceSource?: "course" | "online";
  target?: ClassroomRole;
  scopeNotice?: string;
  suggestedKnowledgePointIds?: string[];
}

export interface ClassroomSessionDraft {
  version: 1;
  contentRevision?: number;
  savedAt: string;
  lessonId: string;
  currentIndex: number;
  furthestIndex?: number;
  selectedChoice: string;
  checkpointResult: ClassroomCheckpointResult | null;
  checkpointDrafts?: Record<string, {
    selectedChoice: string;
    checkpointResult: ClassroomCheckpointResult | null;
  }>;
  messages: PersistedClassroomMessage[];
  practiceCode: string;
  homeworkCode: string;
  practiceResult: SubmissionResult | null;
  homeworkResult: SubmissionResult | null;
  hint: string;
  lessonComplete: boolean;
  diagnosticResult: DiagnosticSubmissionResult | null;
  diagnosticAnswers: Record<string, string>;
  baselineOpen: boolean;
  assessmentStarted: boolean;
  assessmentIndex: number;
  assessmentResultVisible: boolean;
  retakeActive: boolean;
  learningPlan: ClassroomDialogueResponse | null;
  classroomView: ClassroomWorkspaceView;
  selectedMaterialId: string;
  isPaused: boolean;
  sessionBeatSnapshot: ClassroomBeat[];
}

const WORKSPACE_VIEWS: ClassroomWorkspaceView[] = ["lecture", "discussion", "code", "materials"];

export function classroomSessionKey(studentId: string): string {
  return `ciyuan-classroom-session-v1:${studentId}:python`;
}

export function loadClassroomSession(
  storage: KeyValueStorage,
  studentId: string,
): ClassroomSessionDraft | null {
  const key = classroomSessionKey(studentId);
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const candidate = JSON.parse(raw) as Partial<ClassroomSessionDraft>;
    const valid = candidate.version === 1
      && typeof candidate.savedAt === "string"
      && typeof candidate.lessonId === "string"
      && Number.isInteger(candidate.currentIndex) && (candidate.currentIndex ?? -1) >= 0
      && typeof candidate.selectedChoice === "string"
      && Array.isArray(candidate.messages)
      && typeof candidate.practiceCode === "string"
      && typeof candidate.homeworkCode === "string"
      && typeof candidate.hint === "string"
      && typeof candidate.lessonComplete === "boolean"
      && typeof candidate.diagnosticAnswers === "object" && candidate.diagnosticAnswers !== null
      && typeof candidate.baselineOpen === "boolean"
      && typeof candidate.assessmentStarted === "boolean"
      && Number.isInteger(candidate.assessmentIndex) && (candidate.assessmentIndex ?? -1) >= 0
      && typeof candidate.assessmentResultVisible === "boolean"
      && typeof candidate.retakeActive === "boolean"
      && WORKSPACE_VIEWS.includes(candidate.classroomView as ClassroomWorkspaceView)
      && typeof candidate.selectedMaterialId === "string"
      && typeof candidate.isPaused === "boolean"
      && Array.isArray(candidate.sessionBeatSnapshot);
    if (!valid) throw new Error("invalid classroom session");
    return candidate as ClassroomSessionDraft;
  } catch {
    storage.removeItem(key);
    return null;
  }
}

export function saveClassroomSession(
  storage: KeyValueStorage,
  studentId: string,
  draft: ClassroomSessionDraft,
): void {
  storage.setItem(classroomSessionKey(studentId), JSON.stringify(draft));
}

export function clearClassroomSession(storage: KeyValueStorage, studentId: string): void {
  storage.removeItem(classroomSessionKey(studentId));
}
