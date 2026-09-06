<script setup lang="ts">
import { hasLearningEvidence, measuredMastery, qaFeedbackLabel, readSavedIds, serviceFailure, verificationUnavailable } from "../../services/workspaceState";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import {
  ApiError,
  api,
  type ClassroomBeat,
  type ClassroomCheckpointResult,
  type ClassroomCodeTask as ClassroomCodeTaskData,
  type ClassroomLesson,
  type ClassroomRole,
  type ClassroomSelfProfileResponse,
  type DiagnosticQuiz,
  type DiagnosticAnalysis,
  type DiagnosticLearningBlock,
  type DiagnosticSubmissionResult,
  type LearnerProfile,
  type SubmissionResult,
} from "../../services/api";
import SafeMarkdown from "../SafeMarkdown.vue";
import ThemeToggle from "../ThemeToggle.vue";
import ClassroomCodeTask from "./ClassroomCodeTask.vue";
import {
  loadClassroomSession,
  refreshSessionLectures,
  restoredSessionIndex,
  saveClassroomSession,
  type ClassroomSessionDraft,
  type ClassroomWorkspaceView,
  type PersistedClassroomMessage,
} from "./classroomSession";
import ClassroomPlanPreview from "./ClassroomPlanPreview.vue";
import LessonBeatContent from "./LessonBeatContent.vue";

const props = defineProps<{ studentId: string; genericMode?: boolean; darkTheme: boolean }>();
const dispatch = defineEmits<{
  profileUpdated: [profile: LearnerProfile];
  profileResolved: [profile: LearnerProfile | null];
  openKnowledgeMap: [];
  requestGenericMode: [];
  requestAssessment: [];
  focusChanged: [active: boolean];
  openProjects: [];
  toggleTheme: [];
}>();
let componentActive = true;
// Detached classrooms must not overwrite the newly selected account or course.
const emit = ((...args: unknown[]) => {
  if (componentActive) (dispatch as (...args: unknown[]) => void)(...args);
}) as typeof dispatch;

function preferredScrollBehavior(): ScrollBehavior {
  return document.documentElement.dataset.motion === "reduced" ? "auto" : "smooth";
}

type MessageRole = ClassroomRole | "student";
type ClassroomMessage = PersistedClassroomMessage;

const FIRST_LESSON_ID = "python-list-filter-01";
const SECOND_LESSON_ID = "python-dict-lookup-02";
const activeLessonId = ref(FIRST_LESSON_ID);
const lesson = ref<ClassroomLesson | null>(null);
const currentIndex = ref(0);
const furthestIndex = ref(0);
const loading = ref(true);
const initializing = ref(false);
const learningContextError = ref("");
const contextLoading = ref(false);
const error = ref("");
const selectedChoice = ref("");
const checkpointResult = ref<ClassroomCheckpointResult | null>(null);
const checkpointDrafts = ref<Record<string, {
  selectedChoice: string;
  checkpointResult: ClassroomCheckpointResult | null;
}>>({});
const messages = ref<ClassroomMessage[]>([]);
const messageCounter = ref(0);
const messageList = ref<HTMLElement | null>(null);
const practiceCode = ref("");
const homeworkCode = ref("");
const practiceResult = ref<SubmissionResult | null>(null);
const homeworkResult = ref<SubmissionResult | null>(null);
const submitting = ref(false);
const hint = ref("");
const hintLoading = ref(false);
const dialogueRole = ref<ClassroomRole>("teacher");
const dialogueText = ref("");
const dialogueLoading = ref(false);
const dialogueError = ref("");
const dialogueComposer = ref<HTMLTextAreaElement | null>(null);
const lessonComplete = ref(false);
const learnerProfile = ref<LearnerProfile | null>(null);
const hasObjectiveProfile = computed(() => hasLearningEvidence(learnerProfile.value));
const diagnostic = ref<DiagnosticQuiz | null>(null);
const diagnosticResult = ref<DiagnosticSubmissionResult | null>(null);
const diagnosticAnswers = ref<Record<string, string>>({});
const baselineOpen = ref(false);
const baselineLoading = ref(false);
const diagnosticLoading = ref(true);
const learningPlan = ref<ClassroomLesson | null>(null);
const planLoading = ref(false);
const dailyMinutes = ref(30);
// 与后端 /api/v1/classroom/sessions/next 的 daily_minutes 校验范围保持一致。
const DAILY_MINUTES_MIN = 20;
const DAILY_MINUTES_MAX = 120;
// 规划面板双模式：简易版只保留“每天可投入”，其余按助教建议默认值；完整版可逐项自定义。
const planDetailMode = ref<"simple" | "full">("simple");
const DEFAULT_PLAN_GOAL = "按课程顺序稳步推进，独立完成每道练习";
const preferredModeLabel = computed(() => ({
  step_by_step: "老师分步带着学",
  example_first: "先看例子再归纳",
  practice_first: "先动手再补知识",
} as const)[preferredMode.value]);
const weeklyDays = ref(5);
const planGoal = ref("先打牢 Python 基础，再完成一项可运行的小项目");
const preferredMode = ref<"step_by_step" | "example_first" | "practice_first">("step_by_step");
const planConfirmed = ref(false);
const uiFeedback = ref("");
const feedbackTone = computed<"info" | "success" | "warning" | "error">(() => {
  const message = uiFeedback.value;
  if (/(失败|不可用|无法|错误|请求失败)/.test(message)) return "error";
  if (/(尚未通过|依据不足|请先|不足|稍候)/.test(message)) return "warning";
  if (/(已通过|完成|已建立|已生成|已更新|已保存|已记录|已恢复)/.test(message)) return "success";
  return "info";
});
let feedbackDismissTimer: ReturnType<typeof setTimeout> | null = null;
const baselinePanel = ref<HTMLElement | null>(null);
const assessmentStarted = ref(false);
const assessmentIndex = ref(0);
const assessmentResultVisible = ref(false);
const retakeActive = ref(false);
const selfDescription = ref("");
const selfDescriptionFocused = ref(false);
const selfProfile = ref<ClassroomSelfProfileResponse | null>(null);
const selfProfileLoading = ref(false);
const progressExplanationOpen = ref(false);
const diagnosticAnalysis = ref<DiagnosticAnalysis | null>(null);
const classroomView = ref<ClassroomWorkspaceView>("lecture");
const selectedMaterialId = ref("");
const exitDialogOpen = ref(false);
const exitDialog = ref<HTMLElement | null>(null);
let exitReturnFocus: HTMLElement | null = null;
watch(exitDialogOpen, async (open) => {
  if (open) {
    exitReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    await nextTick();
    exitDialog.value?.focus();
  } else {
    await nextTick();
    if (exitReturnFocus?.isConnected) exitReturnFocus.focus();
    exitReturnFocus = null;
  }
});
function handleExitKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") { event.preventDefault(); exitDialogOpen.value = false; return; }
  if (event.key !== "Tab") return;
  const buttons = exitDialog.value?.querySelectorAll<HTMLButtonElement>("button:not([disabled])");
  if (!buttons?.length) return;
  const first = buttons[0]!;
  const last = buttons[buttons.length - 1]!;
  if (event.shiftKey && (document.activeElement === first || document.activeElement === exitDialog.value)) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === exitDialog.value)) {
    event.preventDefault(); first.focus();
  }
}
const isPaused = ref(false);
const boardCodeExpanded = ref(false);
const materialCodeExpanded = ref(false);
const sessionBeatSnapshot = ref<ClassroomBeat[]>([]);
const planBuildButton = ref<HTMLButtonElement | null>(null);
const planProgressStep = ref(0);
const PLAN_PROGRESS_LABELS = ["正在读取学习证据", "正在检查前置知识", "正在组合本次课堂"] as const;
const SELF_DESCRIPTION_EXAMPLE = "例如：我学过变量和 for 循环，能看懂简单代码，但不太会自己拆题；希望以后能完成数据分析小项目。";
let planProgressTimer: ReturnType<typeof setInterval> | null = null;
let sessionReady = false;

const planProgressMessage = computed(() => (
  PLAN_PROGRESS_LABELS[Math.max(0, planProgressStep.value - 1)] ?? "正在准备个性化课程"
));

function clearPlanProgress(): void {
  if (planProgressTimer !== null) clearInterval(planProgressTimer);
  planProgressTimer = null;
  planProgressStep.value = 0;
}

function startPlanProgress(): void {
  clearPlanProgress();
  planProgressStep.value = 1;
  planProgressTimer = setInterval(() => {
    planProgressStep.value = Math.min(PLAN_PROGRESS_LABELS.length, planProgressStep.value + 1);
  }, 900);
}

function blockToBeat(block: DiagnosticLearningBlock, index: number): ClassroomBeat {
  return {
    id: `adaptive-${block.block_id}`,
    phase: index === 0 ? "concept" : "discussion",
    speaker: "teacher",
    eyebrow: `个性化补缺 ${String(index + 1).padStart(2, "0")} · ${block.estimated_minutes} 分钟`,
    title: block.title,
    message: `${block.reason} ${block.summary}`,
    board_title: block.title,
    board_explanation: block.summary,
    board_points: block.key_points.length
      ? block.key_points
      : block.skill_atoms.map((atom) => atom.label),
    board_code: block.example_code,
    board_trace: block.example_steps,
    action: "continue",
    checkpoint: null,
  };
}

const selectedLearningBlocks = computed(() => {
  const sourceBlocks = diagnosticAnalysis.value?.learning_blocks ?? [];
  const lessonIds = new Set(lesson.value?.knowledge_point_ids ?? []);
  const blocks = lesson.value?.delivery_mode === "adaptive"
    ? sourceBlocks.filter((block) => lessonIds.has(block.knowledge_point_id))
    : sourceBlocks;
  if (!blocks.length) return [];
  const teachingBudget = Math.max(8, dailyMinutes.value - 12);
  let used = 0;
  const selected: DiagnosticLearningBlock[] = [];
  for (const block of blocks) {
    if (selected.length && used + block.estimated_minutes > teachingBudget) break;
    selected.push(block);
    used += block.estimated_minutes;
  }
  return selected.length ? selected : blocks.slice(0, 1);
});

const selectedMaterial = computed(() => {
  const blocks = selectedLearningBlocks.value;
  return blocks.find((block) => block.block_id === selectedMaterialId.value) ?? blocks[0] ?? null;
});

const generatedPersonalizedBeats = computed<ClassroomBeat[]>(() => {
  if (!lesson.value) return [];
  if (lesson.value.delivery_mode === "adaptive") return lesson.value.beats;
  if (props.genericMode || averageMastery.value === null) return lesson.value.beats;
  const score = lessonTargetMastery.value ?? averageMastery.value;
  const all = lesson.value.beats;
  const welcome = all.filter((beat) => beat.phase === "welcome");
  const practice = all.filter((beat) => beat.phase === "practice");
  const closing = all.filter((beat) => beat.phase === "summary" || beat.phase === "homework");
  let instruction = selectedLearningBlocks.value.length
    ? selectedLearningBlocks.value.map(blockToBeat)
    : all.filter((beat) => ["concept", "discussion", "debug"].includes(beat.phase));

  const selfLevel = selfProfile.value?.level;
  if (!selectedLearningBlocks.value.length && (score >= 72 || selfLevel === "experienced")) {
    instruction = instruction.filter((beat) => beat.phase === "debug").slice(-1);
  } else if (!selectedLearningBlocks.value.length && (score >= 45 || selfLevel === "developing")) {
    instruction = instruction.slice(1);
  }
  if (!selectedLearningBlocks.value.length) {
    const instructionLimit = dailyMinutes.value <= 20 ? 1 : dailyMinutes.value < 40 ? 2 : instruction.length;
    instruction = instruction.slice(-Math.max(1, instructionLimit));
  }

  if (!selectedLearningBlocks.value.length && preferredMode.value === "example_first") {
    instruction = [...instruction].sort((left, right) => {
      const order = { debug: 0, discussion: 1, concept: 2 } as Record<string, number>;
      return (order[left.phase] ?? 9) - (order[right.phase] ?? 9);
    });
  }
  const assembled = preferredMode.value === "practice_first"
    ? [...welcome, ...practice, ...instruction, ...closing]
    : [...welcome, ...instruction, ...practice, ...closing];
  return assembled.filter((beat, index) => assembled.findIndex((item) => item.id === beat.id) === index);
});
const personalizedBeats = computed<ClassroomBeat[]>(() => (
  sessionBeatSnapshot.value.length ? sessionBeatSnapshot.value : generatedPersonalizedBeats.value
));
const currentBeat = computed<ClassroomBeat | null>(() => personalizedBeats.value[currentIndex.value] ?? null);
watch([dailyMinutes, weeklyDays, preferredMode, planGoal, selfProfile], () => {
  learningPlan.value = null;
});
const currentBoardMistakes = computed(() => currentBeat.value?.board_points
  .filter((point) => point.startsWith("易错提醒："))
  .map((point) => point.slice("易错提醒：".length)) ?? []);
const currentBoardPoints = computed(() => currentBeat.value?.board_points
  .filter((point) => !point.startsWith("易错提醒：")) ?? []);
const activeRole = computed<ClassroomRole>(() => currentBeat.value?.speaker ?? "teacher");
const progress = computed(() => {
  if (!personalizedBeats.value.length) return 0;
  if (lessonComplete.value) return 100;
  return Math.round(furthestIndex.value / personalizedBeats.value.length * 100);
});
const isPracticeAccepted = computed(() => practiceResult.value?.verification?.accepted === true);
const isHomeworkAccepted = computed(() => homeworkResult.value?.verification?.accepted === true);
const canAdvance = computed(() => {
  const action = currentBeat.value?.action;
  if (action === "choice") return checkpointResult.value?.accepted === true;
  if (action === "practice") return isPracticeAccepted.value;
  if (action === "homework") return isHomeworkAccepted.value;
  return true;
});
const averageMastery = computed(() => {
  const items = measuredMastery(learnerProfile.value);
  return items.length
    ? Math.round(items.reduce((sum, item) => sum + item.score, 0) / items.length * 100)
    : null;
});
const lessonTargetMastery = computed(() => {
  if (!lesson.value || !learnerProfile.value) return null;
  const ids = new Set(lesson.value.knowledge_point_ids);
  const items = learnerProfile.value.mastery.filter((item) => ids.has(item.knowledge_point_id));
  return items.length
    ? Math.round(items.reduce((sum, item) => sum + item.score, 0) / items.length * 100)
    : null;
});
const masteryEvidenceCount = computed(() => (
  learnerProfile.value?.mastery.reduce((sum, item) => sum + item.evidence_count, 0) ?? 0
));
const baselineComplete = computed(() => diagnostic.value?.items.every(
  (item) => Boolean(diagnosticAnswers.value[item.exercise_id]),
) ?? false);
const assessmentProgress = computed(() => {
  const total = diagnostic.value?.items.length ?? 0;
  return total ? Math.round(Object.keys(diagnosticAnswers.value).length / total * 100) : 0;
});
const currentDiagnosticItem = computed(() => diagnostic.value?.items[assessmentIndex.value] ?? null);
const hasRetakeDraft = computed(() => (
  diagnostic.value?.phase === "reassessment"
  && (assessmentIndex.value > 0 || Object.keys(diagnosticAnswers.value).length > 0)
));
const retakeEntryLabel = computed(() => hasRetakeDraft.value ? "继续上次重测" : "重新测评");
const learningTrack = computed(() => {
  const score = selfProfile.value?.level === "newcomer" ? 0 : (averageMastery.value ?? 0);
  if (score >= 70) return {
    name: "挑战进阶路线",
    summary: "基础概念掌握较稳，将从 Debug、重构和综合应用切入。",
    startIndex: 2,
    pace: "35–45 分钟/次",
  };
  if (score >= 40) return {
    name: "核心提升路线",
    summary: "保留关键讲解，增加随堂验证，重点补齐薄弱知识点。",
    startIndex: 1,
    pace: "25–35 分钟/次",
  };
  return {
    name: "基础陪伴路线",
    summary: "从生活化例子和逐步练习开始，老师每段都会停下来确认。",
    startIndex: 0,
    pace: "20–30 分钟/次",
  };
});
const personalizedSession = computed(() => {
  const score = selfProfile.value?.level === "newcomer"
    ? 0
    : (lessonTargetMastery.value ?? averageMastery.value ?? 0);
  const lessonName = lesson.value?.title ?? "Python 学习课";
  const modeLabel = ({
    step_by_step: "老师分步引导",
    example_first: "例题先行",
    practice_first: "先练后讲",
  } as const)[preferredMode.value];
  if (score >= 70) return {
    title: `${lessonName} · 挑战验证`,
    focus: `${modeLabel}；减少重复讲解，用 Debug、代码验证和迁移任务证明掌握`,
    lessonCount: personalizedBeats.value.length,
  };
  if (score >= 40) return {
    title: `${lessonName} · 核心提升`,
    focus: `${modeLabel}；保留关键讲解和同伴讨论，提高真实动手比例`,
    lessonCount: personalizedBeats.value.length,
  };
  return {
    title: `${lessonName} · 基础陪伴`,
    focus: `${modeLabel}；从生活化例子开始，小步讲解、频繁确认，再进入代码练习`,
    lessonCount: personalizedBeats.value.length,
  };
});
const latestTeacherMessage = computed(() => [...messages.value].reverse().find((message) => message.role === "teacher") ?? null);
const latestTeacherQuestion = computed(() => [...messages.value].reverse().find((message) => (
  message.role === "student" && message.target === "teacher" && message.kind === "student"
)) ?? null);
const conversationMessages = computed(() => messages.value.filter((message) => (
  message.kind === "student" || message.kind === "reply"
)));
const peerRoles: ClassroomRole[] = ["peer_cautious", "peer_debugger", "peer_summarizer"];

const roleMeta: Record<MessageRole, { name: string; icon: string; color: string }> = {
  teacher: { name: "林老师", icon: "林", color: "#b4233b" },
  ta: { name: "助教小程", icon: "程", color: "#8b5a2b" },
  peer_cautious: { name: "小禾", icon: "禾", color: "#4f7b63" },
  peer_debugger: { name: "阿拓", icon: "拓", color: "#ba5a3a" },
  peer_summarizer: { name: "宁宁", icon: "宁", color: "#7b628f" },
  student: { name: "我", icon: "我", color: "#c51632" },
};

watch(() => messages.value.length, async () => {
  await nextTick();
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight;
});

function showFeedback(message: string): void {
  if (feedbackDismissTimer) clearTimeout(feedbackDismissTimer);
  uiFeedback.value = message;
  feedbackDismissTimer = setTimeout(() => {
    uiFeedback.value = "";
    feedbackDismissTimer = null;
  }, 5_000);
}

function dismissFeedback(): void {
  if (feedbackDismissTimer) clearTimeout(feedbackDismissTimer);
  feedbackDismissTimer = null;
  uiFeedback.value = "";
}

function savePlanPreferences(): void {
  localStorage.setItem(`ciyuan-plan:${props.studentId}:python`, JSON.stringify({
    dailyMinutes: dailyMinutes.value,
    weeklyDays: weeklyDays.value,
    planGoal: planGoal.value,
    preferredMode: preferredMode.value,
    selfDescription: selfDescription.value,
    selfProfile: selfProfile.value,
    diagnosticAnalysis: diagnosticAnalysis.value,
    planDetailMode: planDetailMode.value,
  }));
}

function planConfirmationKey(): string {
  return `ciyuan-plan-confirmed:${props.studentId}:python`;
}

function loadPlanPreferences(): void {
  try {
    const raw = localStorage.getItem(`ciyuan-plan:${props.studentId}:python`);
    if (!raw) return;
    const value = JSON.parse(raw) as Partial<{
      dailyMinutes: number; weeklyDays: number; planGoal: string;
      preferredMode: typeof preferredMode.value; selfDescription: string;
      selfProfile: ClassroomSelfProfileResponse; diagnosticAnalysis: DiagnosticAnalysis;
      planDetailMode: "simple" | "full";
    }>;
    if (typeof value.dailyMinutes === "number") dailyMinutes.value = Math.min(DAILY_MINUTES_MAX, Math.max(DAILY_MINUTES_MIN, value.dailyMinutes));
    if (typeof value.weeklyDays === "number") weeklyDays.value = Math.min(7, Math.max(1, value.weeklyDays));
    if (typeof value.planGoal === "string" && value.planGoal.trim()) planGoal.value = value.planGoal.trim();
    if (["step_by_step", "example_first", "practice_first"].includes(value.preferredMode ?? "")) preferredMode.value = value.preferredMode!;
    if (typeof value.selfDescription === "string") selfDescription.value = value.selfDescription.slice(0, 1200);
    if (value.selfProfile && typeof value.selfProfile.level_label === "string") selfProfile.value = value.selfProfile;
    if (value.diagnosticAnalysis && Array.isArray(value.diagnosticAnalysis.learning_blocks)) {
      diagnosticAnalysis.value = value.diagnosticAnalysis;
    }
    if (value.planDetailMode === "simple" || value.planDetailMode === "full") {
      planDetailMode.value = value.planDetailMode;
    }
    planConfirmed.value = localStorage.getItem(planConfirmationKey()) === "true";
  } catch {
    showFeedback("上次的学习设置无法读取，已使用建议值。");
  }
}

function buildSessionDraft(): ClassroomSessionDraft | null {
  if (!lesson.value) return null;
  return {
    version: 1,
    contentRevision: 2,
    savedAt: new Date().toISOString(),
    lessonId: lesson.value.lesson_id,
    currentIndex: currentIndex.value,
    furthestIndex: furthestIndex.value,
    selectedChoice: selectedChoice.value,
    checkpointResult: checkpointResult.value,
    checkpointDrafts: checkpointDrafts.value,
    messages: messages.value.slice(-200),
    dialogueText: dialogueText.value,
    dialogueRole: dialogueRole.value,
    practiceCode: practiceCode.value,
    homeworkCode: homeworkCode.value,
    practiceResult: practiceResult.value,
    homeworkResult: homeworkResult.value,
    hint: hint.value,
    lessonComplete: lessonComplete.value,
    diagnosticResult: diagnosticResult.value,
    diagnosticAnswers: diagnosticAnswers.value,
    baselineOpen: baselineOpen.value,
    assessmentStarted: assessmentStarted.value,
    assessmentIndex: assessmentIndex.value,
    assessmentResultVisible: assessmentResultVisible.value,
    retakeActive: retakeActive.value,
    learningPlan: null,
    plannedLesson: learningPlan.value,
    classroomView: classroomView.value,
    selectedMaterialId: selectedMaterialId.value,
    isPaused: isPaused.value,
    sessionBeatSnapshot: sessionBeatSnapshot.value,
  };
}

function persistSession(): void {
  if (!sessionReady || !componentActive) return;
  const draft = buildSessionDraft();
  if (!draft) return;
  try {
    saveClassroomSession(localStorage, props.studentId, draft);
  } catch {
    showFeedback("当前课堂仍可继续，但浏览器存储空间不足，暂时无法自动保存新进度。");
  }
}

function restoreSession(draft: ClassroomSessionDraft): boolean {
  if (!lesson.value || lesson.value.lesson_id !== draft.lessonId) return false;
  const oldBeat = draft.sessionBeatSnapshot[draft.currentIndex];
  sessionBeatSnapshot.value = draft.contentRevision === 2
    ? refreshSessionLectures(draft.sessionBeatSnapshot, generatedPersonalizedBeats.value) : [];
  const beatCount = sessionBeatSnapshot.value.length || generatedPersonalizedBeats.value.length;
  currentIndex.value = restoredSessionIndex(draft, generatedPersonalizedBeats.value);
  furthestIndex.value = Math.min(
    Math.max(currentIndex.value, draft.furthestIndex ?? currentIndex.value),
    Math.max(0, beatCount - 1),
  );
  selectedChoice.value = draft.selectedChoice;
  checkpointResult.value = draft.checkpointResult;
  checkpointDrafts.value = draft.checkpointDrafts ?? (oldBeat ? {
    [oldBeat.id]: {
      selectedChoice: draft.selectedChoice,
      checkpointResult: draft.checkpointResult,
    },
  } : {});
  messages.value = draft.messages;
  dialogueText.value = typeof draft.dialogueText === "string" ? draft.dialogueText.slice(0, 1000) : "";
  dialogueRole.value = draft.dialogueRole && draft.dialogueRole in roleMeta ? draft.dialogueRole : "teacher";
  messageCounter.value = draft.messages.reduce((maximum, message) => Math.max(maximum, message.id), 0);
  practiceCode.value = draft.practiceCode;
  homeworkCode.value = draft.homeworkCode;
  practiceResult.value = draft.practiceResult;
  homeworkResult.value = draft.homeworkResult;
  hint.value = draft.hint;
  lessonComplete.value = draft.lessonComplete;
  diagnosticResult.value = draft.diagnosticResult;
  const validExerciseIds = new Set(diagnostic.value?.items.map((item) => item.exercise_id) ?? []);
  diagnosticAnswers.value = Object.fromEntries(
    Object.entries(draft.diagnosticAnswers).filter(([exerciseId, response]) => (
      (!diagnostic.value || validExerciseIds.has(exerciseId)) && typeof response === "string"
    )),
  );
  baselineOpen.value = draft.baselineOpen;
  assessmentStarted.value = draft.assessmentStarted;
  const assessmentCount = diagnostic.value?.items.length ?? 0;
  assessmentIndex.value = diagnostic.value
    ? Math.min(draft.assessmentIndex, Math.max(0, assessmentCount - 1)) : draft.assessmentIndex;
  assessmentResultVisible.value = draft.assessmentResultVisible;
  retakeActive.value = draft.retakeActive && diagnostic.value?.phase === "reassessment";
  learningPlan.value = draft.plannedLesson ?? null;
  classroomView.value = draft.classroomView === "discussion" ? "lecture" : draft.classroomView;
  selectedMaterialId.value = draft.selectedMaterialId;
  isPaused.value = draft.isPaused;
  return true;
}

watch(() => ({
  lessonId: activeLessonId.value,
  currentIndex: currentIndex.value,
  furthestIndex: furthestIndex.value,
  selectedChoice: selectedChoice.value,
  checkpointResult: checkpointResult.value,
  checkpointDrafts: checkpointDrafts.value,
  messages: messages.value,
  dialogueText: dialogueText.value,
  dialogueRole: dialogueRole.value,
  practiceCode: practiceCode.value,
  homeworkCode: homeworkCode.value,
  practiceResult: practiceResult.value,
  homeworkResult: homeworkResult.value,
  hint: hint.value,
  lessonComplete: lessonComplete.value,
  diagnosticResult: diagnosticResult.value,
  diagnosticAnswers: diagnosticAnswers.value,
  baselineOpen: baselineOpen.value,
  assessmentStarted: assessmentStarted.value,
  assessmentIndex: assessmentIndex.value,
  assessmentResultVisible: assessmentResultVisible.value,
  retakeActive: retakeActive.value,
  learningPlan: learningPlan.value,
  classroomView: classroomView.value,
  selectedMaterialId: selectedMaterialId.value,
  isPaused: isPaused.value,
  sessionBeatSnapshot: sessionBeatSnapshot.value,
}), persistSession, { deep: true });

function pushMessage(
  role: MessageRole,
  content: string,
  kind: ClassroomMessage["kind"],
  review?: ClassroomMessage["review"],
  evidenceCount?: number,
  target?: ClassroomRole,
  scopeNotice?: string,
  suggestedKnowledgePointIds?: string[],
  evidenceSource?: ClassroomMessage["evidenceSource"],
): void {
  messageCounter.value += 1;
  messages.value.push({
    id: messageCounter.value,
    role,
    name: roleMeta[role].name,
    content,
    kind,
    review,
    evidenceCount,
    evidenceSource,
    target,
    scopeNotice,
    suggestedKnowledgePointIds,
  });
}

function announceBeat(): void {
  if (!currentBeat.value) return;
  pushMessage("teacher", currentBeat.value.message, "lesson");
  const peerCommentary: Partial<Record<string, { role: ClassroomRole; message: string }>> = {
    "beat-filter": { role: "peer_cautious", message: "我刚才也把 for 和 if 混在一起了。现在我的理解是：for 负责逐个看，if 才负责决定留不留下。你也是这样想的吗？" },
    "beat-debug": { role: "peer_debugger", message: "我先不抢着改代码，准备把它和普通循环逐步对照。你愿意先猜猜错误最可能藏在哪一段吗？" },
    "beat-summary": { role: "peer_summarizer", message: "我先不直接给总结。你愿意用一句话说说 for、if 和测试各自做什么吗？我再帮你补成课堂笔记。" },
    "dict-beat-lookup": { role: "peer_cautious", message: "我刚才差点直接用方括号查一个不一定存在的键。你觉得默认值应该永远写 0，还是要看这个值在任务里代表什么？" },
    "dict-beat-debug": { role: "peer_debugger", message: "我想先拿一个第一次出现的单词跑一遍。如果第一轮就报错，我们就能确定是默认计数的问题。一起试试吗？" },
    "dict-beat-summary": { role: "peer_summarizer", message: "这次我想把步骤记成“设计键值—处理缺失—累计更新—验证输出”。你会怎样用自己的话总结？" },
  };
  const commentary = peerCommentary[currentBeat.value.id];
  if (commentary) pushMessage(commentary.role, commentary.message, "reply", "approved", 1);
}

async function ensureProfile(isCorrect = true): Promise<void> {
  try {
    const profile = await api.profile(props.studentId, "python");
    if (!componentActive) return;
    learnerProfile.value = profile;
    emit("profileUpdated", profile);
    emit("profileResolved", profile);
  } catch (cause) {
    if (!componentActive) return;
    if (!(cause instanceof ApiError) || cause.status !== 404) throw cause;
    const result = await api.assess(props.studentId, "python", [
      { knowledge_point_id: "PY-LIST-03", is_correct: isCorrect },
    ]);
    if (!componentActive) return;
    learnerProfile.value = result.profile;
    emit("profileUpdated", result.profile);
    emit("profileResolved", result.profile);
  }
}

async function loadLearningContext(): Promise<void> {
  if (contextLoading.value) return;
  contextLoading.value = true;
  try {
    const profile = await api.profile(props.studentId, "python");
    if (!componentActive) return;
    learnerProfile.value = profile;
    learningContextError.value = "";
    emit("profileUpdated", learnerProfile.value);
    emit("profileResolved", learnerProfile.value);
  } catch (cause) {
    if (!componentActive) return;
    if (cause instanceof ApiError && cause.status === 404) {
      learnerProfile.value = null;
      learningContextError.value = "尚未读取到学情档案，已保存的课堂仍可继续；需要时可重试同步。";
      emit("profileResolved", null);
    } else {
      learningContextError.value = "学情同步暂时失败，已保留当前课堂与上次进度。";
    }
  } finally {
    contextLoading.value = false;
  }
  if (componentActive) await loadDiagnosticContext();
}

async function loadDiagnosticContext(): Promise<void> {
  diagnosticLoading.value = true;
  try {
    const quiz = await api.diagnostic("python", hasObjectiveProfile.value ? "reassessment" : "initial");
    if (componentActive) diagnostic.value = quiz;
  } catch (cause) {
    showFeedback(`能力诊断暂时不可用。${serviceFailure(cause)}`);
  } finally {
    diagnosticLoading.value = false;
  }
}

async function startBaseline(): Promise<void> {
  if (!diagnostic.value) {
    showFeedback("正在重新载入能力诊断…");
    await loadDiagnosticContext();
    if (!diagnostic.value) return;
  }
  baselineOpen.value = true;
  if (lessonComplete.value) {
    planConfirmed.value = false;
    localStorage.removeItem(planConfirmationKey());
    emit("focusChanged", false);
  }
  assessmentIndex.value = 0;
  showFeedback(learnerProfile.value ? "已展开阶段重测，完成后会刷新学习计划。" : "已展开能力基线，请依次完成每一道题。");
  await nextTick();
  baselinePanel.value?.scrollIntoView({ behavior: preferredScrollBehavior(), block: "start" });
}

function selectBaselineAnswer(exerciseId: string, response: string, index: number): void {
  diagnosticAnswers.value = { ...diagnosticAnswers.value, [exerciseId]: response };
  showFeedback(response === "UNKNOWN"
    ? `第 ${index + 1} 题已记录为“我不知道”；这不会被误判为已经掌握。`
    : `第 ${index + 1} 题已选择 ${response}，还可随时修改。`
  );
}

async function submitBaseline(): Promise<void> {
  if (!diagnostic.value || !baselineComplete.value || baselineLoading.value) {
    showFeedback("请先完成全部诊断题目。");
    return;
  }
  baselineLoading.value = true;
  showFeedback("正在分析答案并更新学习画像…");
  try {
    const result = await api.submitDiagnostic(
      props.studentId,
      "python",
      diagnostic.value.phase,
      diagnostic.value.items.map((item) => ({
        exercise_id: item.exercise_id,
        response: diagnosticAnswers.value[item.exercise_id] ?? "",
      })),
    );
    if (!componentActive) return;
    diagnosticResult.value = result;
    diagnosticAnalysis.value = result.analysis;
    savePlanPreferences();
    learnerProfile.value = result.profile;
    emit("profileUpdated", result.profile);
    emit("profileResolved", result.profile);
    baselineOpen.value = false;
    retakeActive.value = false;
    assessmentResultVisible.value = true;
    learningPlan.value = null;
    planConfirmed.value = false;
    localStorage.removeItem(planConfirmationKey());
    diagnosticAnswers.value = {};
    await loadDiagnosticContext();
    showFeedback(`能力基线已建立：${result.correct_count}/${result.total_count}，助教已获得最新学情。`);
  } catch (cause) {
    showFeedback(cause instanceof Error ? cause.message : "能力基线提交失败，请重试。");
  } finally {
    baselineLoading.value = false;
  }
}

async function beginAssessment(): Promise<void> {
  if (!diagnostic.value) {
    showFeedback("正在重新载入能力诊断…");
    await loadDiagnosticContext();
    if (!diagnostic.value) {
      showFeedback("能力诊断暂时不可用，请稍后重试。");
      return;
    }
  }
  if (selfDescription.value.trim().length >= 8 && !selfProfile.value) {
    await analyzeSelfDescription();
  }
  assessmentStarted.value = true;
  assessmentIndex.value = 0;
  showFeedback("摸底测试已开始；答案只用于生成你的学习路径。 ");
}

async function restartAssessment(): Promise<void> {
  if (diagnosticLoading.value || baselineLoading.value) {
    showFeedback("能力诊断正在准备或提交，请稍候。");
    return;
  }
  if (hasRetakeDraft.value) {
    assessmentResultVisible.value = false;
    assessmentStarted.value = true;
    retakeActive.value = true;
    baselineOpen.value = false;
    showFeedback(`已恢复上次重测，从第 ${assessmentIndex.value + 1} 题继续；已选答案都还在。`);
    return;
  }
  diagnosticLoading.value = true;
  showFeedback("正在准备一组新的阶段重测题…");
  try {
    const quiz = await api.diagnostic("python", "reassessment");
    if (!componentActive) return;
    diagnostic.value = quiz;
    assessmentResultVisible.value = false;
    assessmentStarted.value = true;
    retakeActive.value = true;
    baselineOpen.value = false;
    assessmentIndex.value = 0;
    diagnosticAnswers.value = {};
    showFeedback("阶段重测已重新开始；不确定时请选择“我不知道”，不要靠猜测作答。");
  } catch (cause) {
    showFeedback(`阶段重测载入失败，当前课堂已保留。${serviceFailure(cause)}`);
  } finally {
    diagnosticLoading.value = false;
  }
}

function cancelRetake(): void {
  retakeActive.value = false;
  showFeedback("已暂存本次重测；下次点击“继续上次重测”会回到当前题，原有学习画像暂不改变。");
}

function useSelfDescriptionTemplate(value: string): void {
  selfDescription.value = value;
  selfProfile.value = null;
  savePlanPreferences();
  showFeedback("已填入学习经历示例，你可以继续修改后交给助教判断。");
}

function updateSelfDescription(): void {
  selfProfile.value = null;
  savePlanPreferences();
}

async function analyzeSelfDescription(): Promise<void> {
  const description = selfDescription.value.trim();
  if (description.length < 8) {
    showFeedback("请至少用一句完整的话描述学过什么、做过什么或哪里容易卡住。");
    return;
  }
  if (selfProfileLoading.value) return;
  selfProfileLoading.value = true;
  showFeedback("助教正在把你的自述与 Python 课程知识路线进行匹配…");
  try {
    const result = await api.classroomSelfProfile(props.studentId, activeLessonId.value, description);
    if (!componentActive) return;
    selfProfile.value = result;
    savePlanPreferences();
  showFeedback(selfProfile.value.level === "newcomer"
    ? "已记录为零基础倾向；课程规划会以此为主要起点，摸底题只用于细节校正。"
    : `自述初判为“${selfProfile.value.level_label}”；课程规划会先尊重你的学习倾向，再用客观证据细调。`
  );
  } catch (cause) {
    showFeedback(cause instanceof Error ? cause.message : "学习经历分析暂时不可用，请稍后重试。");
  } finally {
    selfProfileLoading.value = false;
  }
}

function previousAssessmentQuestion(): void {
  assessmentIndex.value = Math.max(0, assessmentIndex.value - 1);
  showFeedback(`已返回第 ${assessmentIndex.value + 1} 题。`);
}

function nextAssessmentQuestion(): void {
  if (!currentDiagnosticItem.value || !diagnosticAnswers.value[currentDiagnosticItem.value.exercise_id]) {
    showFeedback("请先选择一个答案，再进入下一题。");
    return;
  }
  if (diagnostic.value && assessmentIndex.value < diagnostic.value.items.length - 1) {
    assessmentIndex.value += 1;
    showFeedback(`已进入第 ${assessmentIndex.value + 1} 题。`);
  }
}

async function enterPersonalizedClassroom(): Promise<void> {
  if (!learningPlan.value) {
    showFeedback("请先让助教根据你的时间与目标生成本次课程安排。");
    return;
  }
  if (!clampDailyMinutes()) {
    return;
  }
  const prepared = learningPlan.value;
  applyLesson(prepared);
  localStorage.setItem(`ciyuan-active-lesson:${props.studentId}:python`, prepared.lesson_id);
  assessmentResultVisible.value = false;
  planConfirmed.value = true;
  isPaused.value = false;
  classroomView.value = "lecture";
  selectedMaterialId.value = selectedLearningBlocks.value[0]?.block_id ?? "";
  emit("focusChanged", true);
  localStorage.setItem(planConfirmationKey(), "true");
  savePlanPreferences();
  currentIndex.value = 0;
  furthestIndex.value = 0;
  checkpointDrafts.value = {};
  selectedChoice.value = "";
  checkpointResult.value = null;
  lockSessionBeats();
  messages.value = [];
  messageCounter.value = 0;
  announceBeat();
  pushMessage("ta", `本次学习“${prepared.title}”，共 ${prepared.beats.length} 个环节。${prepared.planning_reason}`, "lesson");
  showFeedback(`已进入“${personalizedSession.value.title}”，本次内容和节奏已按你的信息重新编排。`);
}

async function requestEnterPersonalizedClassroom(): Promise<void> {
  if (!learningPlan.value || planLoading.value) {
    showFeedback(planLoading.value
      ? `${planProgressMessage.value}，完成后即可进入课堂。`
      : "请先点击“生成专属课程”，助教会结合测评、时间和目标完成编排。"
    );
    await nextTick();
    planBuildButton.value?.scrollIntoView({ behavior: preferredScrollBehavior(), block: "center" });
    planBuildButton.value?.focus({ preventScroll: true });
    return;
  }
  await enterPersonalizedClassroom();
}

function changeClassroomView(view: typeof classroomView.value): void {
  const normalizedView = view === "discussion" ? "lecture" : view;
  classroomView.value = normalizedView;
  const labels = { lecture: "课堂学习", code: "代码练习", materials: "课程资料" } as const;
  showFeedback(`已切换到${labels[normalizedView]}。学习进度和代码草稿不会丢失。`);
}

function handleViewSelect(event: Event): void {
  changeClassroomView((event.target as HTMLSelectElement).value as typeof classroomView.value);
}

function requestEarlyExit(): void {
  exitDialogOpen.value = true;
}

function pauseClassroom(markKnown: boolean): void {
  if (markKnown && currentBeat.value) {
    const key = `ciyuan-self-known:${props.studentId}:python`;
    const existing = readSavedIds(localStorage.getItem(key));
    localStorage.setItem(key, JSON.stringify([...new Set([...existing, currentBeat.value.id])]));
  }
  exitDialogOpen.value = false;
  isPaused.value = true;
  emit("focusChanged", false);
  showFeedback(markKnown
    ? "已记录“自述已学过”，但不会冒充测评证据；下次会用短题复核。"
    : "课堂进度、对话和代码草稿都已保留。");
}

function resumeClassroom(): void {
  isPaused.value = false;
  classroomView.value = "lecture";
  emit("focusChanged", true);
  showFeedback("已回到专注课堂，继续从刚才的位置学习。");
}

async function generateLearningPlan(): Promise<void> {
  if (!lesson.value) {
    showFeedback("课堂内容仍在载入，请稍候再生成学习计划。");
    return;
  }
  if (planLoading.value) {
    showFeedback(`${planProgressMessage.value}，请稍候。`);
    return;
  }
  if (!clampDailyMinutes()) {
    return;
  }
  if (!hasObjectiveProfile.value || !learnerProfile.value) {
    showFeedback("请先建立能力基线，助教才能量身安排学习节奏。");
    await startBaseline();
    return;
  }
  planLoading.value = true;
  startPlanProgress();
  learningPlan.value = null;
  planConfirmed.value = false;
  localStorage.removeItem(planConfirmationKey());
  savePlanPreferences();
  showFeedback("助教小程正在结合你的能力画像安排学习节奏…");
  const effectiveGoal = planGoal.value.trim() || DEFAULT_PLAN_GOAL;
  const requestedMinutes = dailyMinutes.value;
  const requestedDays = weeklyDays.value;
  const requestedMode = preferredMode.value;
  const requestedLevel = selfProfile.value?.level;
  try {
    const result = await api.nextClassroomSession(
      props.studentId,
      requestedMinutes,
      requestedMode,
      requestedLevel,
    );
    if (!componentActive) return;
    if (dailyMinutes.value !== requestedMinutes || weeklyDays.value !== requestedDays || preferredMode.value !== requestedMode
      || selfProfile.value?.level !== requestedLevel || (planGoal.value.trim() || DEFAULT_PLAN_GOAL) !== effectiveGoal) {
      showFeedback("学习设置已更改，请按新设置重新编排。");
      return;
    }
    learningPlan.value = result;
    showFeedback(`已编排“${result.title}”，请确认本次目标和学习顺序。`);
  } catch (cause) {
    showFeedback(`课程编排未完成，测评记录已保留。${serviceFailure(cause)}`);
  } finally {
    planLoading.value = false;
    clearPlanProgress();
  }
}

function useSuggestedPace(): void {
  const score = selfProfile.value?.level === "newcomer" ? 0 : (averageMastery.value ?? 0);
  dailyMinutes.value = score >= 70 ? 40 : score >= 40 ? 30 : 25;
  weeklyDays.value = score >= 70 ? 4 : 5;
  showFeedback(`已采用助教建议：每天 ${dailyMinutes.value} 分钟、每周 ${weeklyDays.value} 天；你仍可继续修改。`);
}

function clampDailyMinutes(): boolean {
  const value = dailyMinutes.value;
  if (!Number.isFinite(value)) {
    dailyMinutes.value = DAILY_MINUTES_MIN;
    showFeedback(`每天可投入时间需在 ${DAILY_MINUTES_MIN}–${DAILY_MINUTES_MAX} 分钟之间，已调整为 ${DAILY_MINUTES_MIN} 分钟。`);
    return false;
  }
  if (value < DAILY_MINUTES_MIN || value > DAILY_MINUTES_MAX) {
    const clamped = Math.min(DAILY_MINUTES_MAX, Math.max(DAILY_MINUTES_MIN, Math.round(value)));
    dailyMinutes.value = clamped;
    showFeedback(`每天可投入时间需在 ${DAILY_MINUTES_MIN}–${DAILY_MINUTES_MAX} 分钟之间，已为你调整为 ${clamped} 分钟；如需改回，请重新设置后再生成。`);
    return false;
  }
  return true;
}

function clampWeeklyDays(): boolean {
  const value = weeklyDays.value;
  if (!Number.isFinite(value) || value < 1 || value > 7) {
    weeklyDays.value = Math.min(7, Math.max(1, Math.round(value)));
    showFeedback(`每周学习天数需在 1–7 天之间，已为你调整为 ${weeklyDays.value} 天。`);
    return false;
  }
  return true;
}

async function openDialogue(role: ClassroomRole, starter = ""): Promise<void> {
  if (dialogueLoading.value) return;
  dialogueRole.value = role;
  if (starter) dialogueText.value = starter;
  classroomView.value = "lecture";
  showFeedback(`已选择${roleMeta[role].name}。互动区就在黑板旁，可以边听边问。`);
  await nextTick();
  dialogueComposer.value?.scrollIntoView({ behavior: preferredScrollBehavior(), block: "center" });
  dialogueComposer.value?.focus({ preventScroll: true });
}

function useConversationStarter(role: ClassroomRole, text: string): void {
  void openDialogue(role, text);
}

function selectDialogueRole(role: ClassroomRole): void {
  void openDialogue(role);
}

function lockSessionBeats(): void {
  if (!sessionBeatSnapshot.value.length) {
    sessionBeatSnapshot.value = [...generatedPersonalizedBeats.value];
  }
}

function rememberCurrentCheckpoint(): void {
  if (!currentBeat.value || currentBeat.value.action !== "choice") return;
  checkpointDrafts.value = {
    ...checkpointDrafts.value,
    [currentBeat.value.id]: {
      selectedChoice: selectedChoice.value,
      checkpointResult: checkpointResult.value,
    },
  };
}

function restoreCheckpointForBeat(beat: ClassroomBeat): void {
  const draft = checkpointDrafts.value[beat.id];
  selectedChoice.value = draft?.selectedChoice ?? "";
  checkpointResult.value = draft?.checkpointResult ?? null;
}

function lessonViewForBeat(beat: ClassroomBeat): ClassroomWorkspaceView {
  return ["practice", "homework"].includes(beat.action) ? "code" : "lecture";
}

function goToLessonStep(index: number): void {
  if (submitting.value) { showFeedback("当前答案正在验证，完成后即可切换课堂环节。"); return; }
  if (!personalizedBeats.value.length) return;
  if (index < 0 || index > furthestIndex.value || index === currentIndex.value) {
    if (index > furthestIndex.value) showFeedback("请先完成前面的学习环节，再进入这里。");
    return;
  }
  rememberCurrentCheckpoint();
  currentIndex.value = index;
  const target = personalizedBeats.value[index];
  if (!target) return;
  restoreCheckpointForBeat(target);
  hint.value = "";
  classroomView.value = lessonViewForBeat(target);
  announceBeat();
  showFeedback(`已返回“${target.title}”。之前的答题、代码和学习进度都已保留。`);
}

function applyLesson(value: ClassroomLesson): void {
  dialogueError.value = "";
  activeLessonId.value = value.lesson_id;
  lesson.value = value;
  currentIndex.value = 0;
  furthestIndex.value = 0;
  selectedChoice.value = "";
  checkpointResult.value = null;
  checkpointDrafts.value = {};
  practiceResult.value = null;
  homeworkResult.value = null;
  lessonComplete.value = false;
  hint.value = "";
  hintLoading.value = false;
  sessionBeatSnapshot.value = [];
  messages.value = [];
  messageCounter.value = 0;
  practiceCode.value = value.practice.starter_code;
  homeworkCode.value = value.homework.starter_code;
  announceBeat();
}

async function loadLesson(targetLessonId = activeLessonId.value): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const loaded = await api.classroomLesson(targetLessonId);
    if (componentActive) applyLesson(loaded);
  } catch (cause) {
    error.value = cause instanceof ApiError && cause.status === 404
      ? "暂时无法恢复这节课堂，之前的进度和草稿已保留。请稍后点击“重新准备”。"
      : serviceFailure(cause);
  } finally {
    loading.value = false;
  }
}

async function startNextLesson(): Promise<void> {
  if (!lessonComplete.value || loading.value) return;
  loading.value = true;
  showFeedback("助教正在读取最新代码证据并重新检查知识断层…");
  try {
    const nextLesson = await api.nextClassroomSession(
      props.studentId,
      dailyMinutes.value,
      preferredMode.value,
      selfProfile.value?.level,
    );
    if (!componentActive) return;
    applyLesson(nextLesson);
    localStorage.setItem(
      `ciyuan-active-lesson:${props.studentId}:python`,
      nextLesson.lesson_id,
    );
    classroomView.value = "lecture";
    showFeedback(`已生成新的“${nextLesson.title}”；它来自最新画像，不是固定下一章。`);
  } catch (cause) {
    showFeedback(cause instanceof Error ? cause.message : "下一节课堂生成失败，请重试。");
  } finally {
    loading.value = false;
  }
}

async function submitChoice(): Promise<void> {
  if (!lesson.value || !currentBeat.value || !selectedChoice.value || submitting.value) return;
  submitting.value = true;
  error.value = "";
  const lessonId = lesson.value.lesson_id;
  const beatId = currentBeat.value.id;
  try {
    pushMessage("student", currentBeat.value.checkpoint?.choices.find((item) => item.id === selectedChoice.value)?.text ?? selectedChoice.value, "checkpoint", undefined, undefined, "teacher");
    const result = await api.classroomCheckpoint(
      lessonId,
      beatId,
      selectedChoice.value,
    );
    if (!componentActive || lesson.value?.lesson_id !== lessonId || currentBeat.value?.id !== beatId) return;
    checkpointResult.value = result;
    rememberCurrentCheckpoint();
    pushMessage(checkpointResult.value.reply_role, checkpointResult.value.reply_message, "reply");
  } catch (cause) {
    if (!componentActive) return;
    error.value = cause instanceof ApiError && cause.status === 404
      ? "这次理解检查暂时无法处理，已保留你的选项和课堂进度。请稍后重试。"
      : `理解检查未完成，已选答案已保留。${serviceFailure(cause)}`;
  } finally {
    submitting.value = false;
  }
}

function advance(): void {
  if (submitting.value) { showFeedback("当前答案正在验证，请先查看结果再继续。"); return; }
  if (!lesson.value || !currentBeat.value) {
    showFeedback("课堂内容仍在载入，请稍候再试。");
    return;
  }
  lockSessionBeats();
  if (!canAdvance.value) {
    const requirement = currentBeat.value.action === "choice"
      ? "请先完成本段理解检查。"
      : currentBeat.value.action === "practice"
        ? "请先运行代码并通过课堂任务。"
        : "请先完成并通过课后作业。";
    showFeedback(requirement);
    return;
  }
  if (currentIndex.value >= personalizedBeats.value.length - 1) {
    showFeedback("已经到达本次课堂的最后一个环节。");
    return;
  }
  rememberCurrentCheckpoint();
  currentIndex.value += 1;
  furthestIndex.value = Math.max(furthestIndex.value, currentIndex.value);
  const nextBeat = personalizedBeats.value[currentIndex.value];
  if (!nextBeat) return;
  restoreCheckpointForBeat(nextBeat);
  classroomView.value = lessonViewForBeat(nextBeat);
  hint.value = "";
  announceBeat();
  showFeedback(`林老师已进入“${currentBeat.value?.title ?? "下一环节"}”，课堂完成度同步更新。`);
}

async function submitCode(task: ClassroomCodeTaskData, sourceCode: string, homework = false): Promise<void> {
  if (submitting.value) {
    showFeedback("代码正在运行，请稍候查看测试结果。");
    return;
  }
  if (!sourceCode.trim()) {
    showFeedback("请先在代码区输入或补全代码，再运行提交。");
    return;
  }
  lockSessionBeats();
  submitting.value = true;
  error.value = "";
  showFeedback("代码已提交，正在隔离环境中运行公开样例和隐藏测试…");
  try {
    await ensureProfile(true);
    if (!componentActive) return;
    const result = await api.submit(props.studentId, "python", task.exercise_id, {
      language: "python",
      source_code: sourceCode,
    });
    if (!componentActive) return;
    if (homework) homeworkResult.value = result;
    else practiceResult.value = result;
    if (verificationUnavailable(result)) {
      pushMessage("ta", result.feedback, "reply");
      showFeedback("验证服务暂不可用，本次未产生代码成绩；请稍后重试。");
      return;
    }
    const updatedProfile: LearnerProfile = {
      student_id: props.studentId,
      course_id: "python",
      mastery: result.mastery_updated,
    };
    learnerProfile.value = updatedProfile;
    emit("profileUpdated", updatedProfile);
    emit("profileResolved", updatedProfile);
    if (result.verification?.accepted) {
      const role: ClassroomRole = homework ? "teacher" : "ta";
      pushMessage(
        role,
        homework
          ? "作业通过了。你不是因为点完页面，而是用真实测试留下了新的掌握证据；助教现在可以重算下一节课。"
          : "全部测试通过。我们已经得到一份真实代码证据，可以一起做课堂小结。",
        "reply",
      );
      if (homework) lessonComplete.value = true;
      showFeedback(homework
        ? "课后作业已通过，画像已更新，可以生成下一节个性化课程。"
        : "课堂任务已通过，点击“进入课堂小结”继续。"
      );
    } else {
      pushMessage("peer_debugger", "没关系，报错就是线索。我们先看公开测试和第一条诊断，再决定改哪一行。", "reply");
      showFeedback("代码已经运行，但尚未通过全部测试；请查看诊断信息或向助教要提示。");
    }
  } catch (cause) {
    if (!componentActive) return;
    error.value = `代码提交未完成，草稿已保留。${serviceFailure(cause)}`;
    showFeedback(error.value);
  } finally {
    submitting.value = false;
  }
}

async function requestHint(task: ClassroomCodeTaskData): Promise<void> {
  if (hintLoading.value) {
    showFeedback("助教正在分析当前题目，请稍候。");
    return;
  }
  hintLoading.value = true;
  error.value = "";
  showFeedback("助教正在结合题目要求和你的当前进度准备提示…");
  try {
    const result = await api.hint(props.studentId, "python", task.exercise_id, 1);
    if (!componentActive) return;
    hint.value = result.hint;
    pushMessage("ta", result.hint, "reply");
    showFeedback("助教提示已显示在公开样例下方。");
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "提示暂时不可用。";
    showFeedback(error.value);
  } finally {
    hintLoading.value = false;
  }
}

async function askRole(): Promise<void> {
  const text = dialogueText.value.trim();
  if (!lesson.value || !currentBeat.value) {
    showFeedback("课堂内容仍在载入，请稍候再发送。");
    return;
  }
  if (dialogueLoading.value) {
    showFeedback(`${roleMeta[dialogueRole.value].name}正在回复，请稍候。`);
    return;
  }
  if (!text) {
    showFeedback(`请先输入想对${roleMeta[dialogueRole.value].name}说的话。`);
    dialogueComposer.value?.focus();
    return;
  }
  if (text.length < 2) {
    showFeedback("问题太短，请再补充一点描述后发送。");
    dialogueComposer.value?.focus();
    return;
  }
  const lessonId = lesson.value.lesson_id;
  const role = dialogueRole.value;
  const previousMessage = messages.value.at(-1);
  const retrying = dialogueError.value && previousMessage?.kind === "student"
    && previousMessage.content === text && previousMessage.target === role;
  const history = retrying ? messages.value.slice(0, -1) : messages.value;
  const recentTurns = history.slice(-8).map((message) => ({
    role: message.role,
    content: message.content,
  }));
  dialogueLoading.value = true;
  dialogueError.value = "";
  dialogueText.value = "";
  if (!retrying) pushMessage("student", text, "student", undefined, undefined, role);
  try {
    const result = await api.classroomDialogue(
      props.studentId,
      lessonId,
      currentBeat.value.phase,
      role,
      text,
      recentTurns,
    );
    if (!componentActive || lesson.value?.lesson_id !== lessonId) return;
    const onlineEvidence = result.citations.some((citation) => citation.source_type === "online");
    pushMessage(
      result.role,
      result.answer,
      "reply",
      result.status === "answered" && !result.trace.some((step) => step.status === "degraded") ? "approved" : "limited",
      result.citations.length,
      undefined,
      result.scope_notice ?? undefined,
      result.suggested_knowledge_point_ids,
      onlineEvidence ? "online" : "course",
    );
    const finalTrace = result.trace.at(-1)?.detail ?? "";
    if (result.trace.some((step) => step.status === "degraded")) {
      showFeedback(qaFeedbackLabel(result));
      return;
    }
    showFeedback(result.status === "answered"
      ? onlineEvidence
        ? `${result.display_name}已基于 Python 官方文档联网回答，并通过质量监督。`
        : result.question_scope === "python_course_extension"
        ? `${result.display_name}已做本节外延伸回答；不会改变当前课堂进度。`
        : `${result.display_name}已回答，内容通过质量监督。`
      : finalTrace.includes("安全")
        ? "请求触发安全边界，系统未发布候选回答。"
        : "问题信息或课程依据不足；角色已说明还需要你补充什么。"
    );
  } catch (cause) {
    if (!componentActive || lesson.value?.lesson_id !== lessonId) return;
    const detail = cause instanceof ApiError && cause.status === 404
      ? "当前课堂请求暂时无法处理，请稍后重试；课堂进度会保留。"
      : serviceFailure(cause);
    dialogueError.value = `未收到${roleMeta[role].name}的回复。${detail} 原问题已保留，可再次发送。`;
    if (!dialogueText.value) dialogueText.value = text;
  } finally {
    dialogueLoading.value = false;
  }
}

async function initializeClassroom(): Promise<void> {
  if (initializing.value) return;
  initializing.value = true;
  sessionReady = false;
  try {
    loadPlanPreferences();
    const savedSession = loadClassroomSession(localStorage, props.studentId);
    const savedLesson = savedSession?.lessonId
      ?? localStorage.getItem(`ciyuan-active-lesson:${props.studentId}:python`);
    if (savedLesson === SECOND_LESSON_ID || savedLesson?.startsWith("python-adaptive--")) {
      activeLessonId.value = savedLesson;
    }
    await Promise.all([loadLesson(), loadLearningContext()]);
    if (!componentActive) return;
    const restored = savedSession ? restoreSession(savedSession) : false;
    sessionReady = Boolean(lesson.value);
    persistSession();
    if (restored && planConfirmed.value && !isPaused.value) emit("focusChanged", true);
    if (restored && (assessmentStarted.value || planConfirmed.value || sessionBeatSnapshot.value.length)) {
      showFeedback(isPaused.value
        ? "已恢复上次保存的过程，回来后可从原位置继续。"
        : "已接上上次进度，测评答案、课堂环节、对话和代码草稿都已保留。"
      );
    }
  } finally {
    initializing.value = false;
  }
}

onMounted(initializeClassroom);

onBeforeUnmount(() => {
  persistSession();
  clearPlanProgress();
  if (feedbackDismissTimer) clearTimeout(feedbackDismissTimer);
  emit("focusChanged", false);
  componentActive = false;
});
</script>

<template>
  <section class="immersive-lesson" :inert="exitDialogOpen">
    <div v-if="learningContextError && lesson && !loading && !initializing" class="classroom-sync-notice" role="status"><span>{{ learningContextError }}</span><button :disabled="contextLoading" @click="loadLearningContext">{{ contextLoading ? "同步中…" : "重试同步学情" }}</button></div>
    <div v-if="initializing || loading || (diagnosticLoading && !sessionReady)" class="classroom-loading"><i></i><strong>正在读取课程与能力测评…</strong><span>只需几秒，我们先了解你的起点</span></div>
    <div v-else-if="error && !lesson" class="classroom-error"><strong>暂时没能进入教室</strong><p>{{ error }}</p><button @click="initializeClassroom">重新准备</button></div>

    <section v-else-if="retakeActive && diagnostic && currentDiagnosticItem" class="assessment-gate reassessment-gate">
      <header><div><b>阶段能力重测</b><small>{{ diagnostic.items.length }} 道跨层级短题，不计入成绩</small></div><button class="text-button" @click="cancelRetake">稍后再测</button></header>
      <p class="honest-answer-note">请按真实掌握情况作答；不确定时直接选“我不知道”，这样助教才不会把猜对误判为已经学会。</p>
      <div class="single-question">
        <header><span>第 {{ assessmentIndex + 1 }} 题，共 {{ diagnostic.items.length }} 题</span></header>
        <h2>{{ currentDiagnosticItem.prompt }}</h2>
        <div><button v-for="option in currentDiagnosticItem.options" :key="option.id" :class="{ selected: diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" :aria-pressed="diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id" :disabled="baselineLoading" @click="selectBaselineAnswer(currentDiagnosticItem.exercise_id, option.id, assessmentIndex)"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b><span>{{ option.text }}</span><i>✓</i></button></div>
      </div>
      <div class="assessment-navigation"><button class="secondary" :disabled="assessmentIndex === 0" @click="previousAssessmentQuestion">← 上一题</button><button v-if="assessmentIndex < diagnostic.items.length - 1" class="primary" @click="nextAssessmentQuestion">下一题 →</button><button v-else class="primary" :disabled="!baselineComplete || baselineLoading" @click="submitBaseline">{{ baselineLoading ? "正在更新画像…" : "提交重测并更新路线" }}</button></div>
      <footer class="assessment-progress"><div><span>测试进度</span><b>{{ assessmentProgress }}%</b></div><i><span :style="{ width: `${assessmentProgress}%` }"></span></i><small>{{ Object.keys(diagnosticAnswers).length }} / {{ diagnostic.items.length }} 已完成</small></footer>
    </section>

    <section v-else-if="assessmentResultVisible && diagnosticResult" class="assessment-result-screen">
      <header><b>测评已完成</b></header>
      <div class="result-celebration"><i>✓</i><p>摸底完成</p><h2>现在，和助教一起把课表定下来</h2><span>你的学习经历、目标和偏好决定课程主方向；这次短测只负责补充证据、发现断层，不会单独把你推到不合适的难度。</span></div>
      <div class="result-summary">
        <article><small>本次答对</small><strong>{{ diagnosticResult.correct_count }} / {{ diagnosticResult.total_count }}</strong><em v-if="diagnosticResult.unknown_count">其中 {{ diagnosticResult.unknown_count }} 题选择“我不知道”</em></article>
        <article><small>当前掌握度</small><strong>{{ averageMastery ?? 0 }}%</strong></article>
        <article><small>建议路线</small><strong>{{ learningTrack.name }}</strong></article>
        <article><small>助教初始建议</small><strong>{{ learningTrack.pace }}</strong></article>
      </div>
      <section v-if="diagnosticResult.analysis" class="diagnostic-analysis">
        <header><div><b>{{ diagnosticResult.analysis.non_linear_profile ? "发现非线性知识断层" : "已完成原子技能定位" }}</b><p>{{ diagnosticResult.analysis.non_linear_profile ? "系统不会让你从头重学，而是保留已经证明会的内容，只回补缺失前置。" : "本次未发现“后面会、前面缺”的明确证据，仍会优先安排未通过部分。" }}</p></div><span>{{ diagnosticResult.analysis.assessed_skill_atoms }} / {{ diagnosticResult.analysis.course_skill_atoms }} 项技能已取样</span></header>
        <div v-if="diagnosticResult.analysis.prerequisite_gaps.length" class="gap-list"><article v-for="gap in diagnosticResult.analysis.prerequisite_gaps" :key="`${gap.downstream_id}-${gap.missing_prerequisite_id}`"><b>保留：{{ gap.downstream_title }}</b><span>精准回补：{{ gap.missing_prerequisite_title }}</span><p>{{ gap.reason }}</p></article></div>
        <div class="block-list"><span v-for="block in diagnosticResult.analysis.learning_blocks" :key="block.block_id"><b>{{ block.title }}</b>{{ block.skill_atoms.map((atom) => atom.label).join(' · ') }}</span></div>
        <small>40 个主干节点用于稳定导航；{{ diagnosticResult.analysis.course_skill_atoms }} 个原子技能用于测评、组合与个性化编排。单题只提供节点级代理证据，后续仍由课堂检查和代码验证继续校正。</small>
      </section>
      <section class="planning-studio">
        <header><div><h3>和助教小程一起安排学习</h3><p>简易版只需选择每天可投入的时间，其余按助教建议自动设置；想逐项定制可切换完整版。</p></div><div class="plan-mode-switch" role="group" aria-label="规划面板模式"><button :class="{ active: planDetailMode === 'simple' }" @click="planDetailMode = 'simple'; savePlanPreferences()">简易版</button><button :class="{ active: planDetailMode === 'full' }" @click="planDetailMode = 'full'; savePlanPreferences()">完整版</button></div><button class="suggestion-button" @click="useSuggestedPace">采用建议节奏</button></header>
        <div class="preference-grid">
          <label>每天可投入<input v-model.number="dailyMinutes" type="number" :min="DAILY_MINUTES_MIN" :max="DAILY_MINUTES_MAX" step="5" @blur="clampDailyMinutes" /><span>分钟（20–120）</span></label>
          <template v-if="planDetailMode === 'full'">
            <label>每周学习<input v-model.number="weeklyDays" type="number" min="1" max="7" @blur="clampWeeklyDays" /><span>天</span></label>
            <label class="wide">我的阶段目标<input v-model="planGoal" maxlength="120" /></label>
          </template>
        </div>
        <p v-if="planDetailMode === 'simple'" class="plan-simple-note">其余设置已按助教建议自动填好：每周 {{ weeklyDays }} 天 · {{ preferredModeLabel }} · 目标“{{ planGoal.trim() || DEFAULT_PLAN_GOAL }}”。</p>
        <section v-if="planDetailMode === 'full'" class="self-profile-inline"><label>我的学习经历（选填）<textarea v-model="selfDescription" rows="3" maxlength="1200" :placeholder="selfDescriptionFocused ? '' : SELF_DESCRIPTION_EXAMPLE" @focus="selfDescriptionFocused = true" @blur="selfDescriptionFocused = false" @input="updateSelfDescription"></textarea></label><button :disabled="selfProfileLoading || selfDescription.trim().length < 8" @click="analyzeSelfDescription">{{ selfProfileLoading ? "分析中…" : "更新学习倾向" }}</button><div v-if="selfProfile"><b>{{ selfProfile.level_label }}</b><span>{{ selfProfile.course_fit }}；推荐从“{{ selfProfile.recommended_start }}”开始。课程规划优先尊重明确的学习倾向，短测用于细调。</span></div></section>
        <div v-if="planDetailMode === 'full'" class="mode-picker"><span>我更喜欢</span><button :class="{ active: preferredMode === 'step_by_step' }" @click="preferredMode = 'step_by_step'">老师分步带着学</button><button :class="{ active: preferredMode === 'example_first' }" @click="preferredMode = 'example_first'">先看例子再归纳</button><button :class="{ active: preferredMode === 'practice_first' }" @click="preferredMode = 'practice_first'">先动手再补知识</button></div>
        <button ref="planBuildButton" class="primary build-plan" :disabled="planLoading" @click="generateLearningPlan">{{ planLoading ? planProgressMessage : learningPlan ? "按新设置重新编排" : "生成我的专属课程" }} <span>→</span></button>
        <div v-if="planLoading" class="plan-progress" role="status" aria-live="polite"><span v-for="(label, index) in PLAN_PROGRESS_LABELS" :key="label" :class="{ done: index + 1 < planProgressStep, active: index + 1 === planProgressStep }"><i>{{ index + 1 < planProgressStep ? "✓" : index + 1 }}</i>{{ label }}</span></div>
        <ClassroomPlanPreview v-if="learningPlan" :plan="learningPlan" />
        <section v-if="baselineOpen && diagnostic" ref="baselinePanel" class="baseline-panel">
          <header><div><b>{{ diagnostic.title }}</b><span>阶段重测会刷新画像并改变下一节课</span></div><button @click="baselineOpen = false">收起</button></header>
          <div v-if="currentDiagnosticItem" class="single-question"><header><span>第 {{ assessmentIndex + 1 }} 题，共 {{ diagnostic.items.length }} 题</span></header><h2>{{ currentDiagnosticItem.prompt }}</h2><div><button v-for="option in currentDiagnosticItem.options" :key="option.id" :class="{ selected: diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" :aria-pressed="diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id" :disabled="baselineLoading" @click="selectBaselineAnswer(currentDiagnosticItem.exercise_id, option.id, assessmentIndex)"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b><span>{{ option.text }}</span><i>✓</i></button></div></div>
          <footer class="assessment-navigation"><button class="secondary" :disabled="assessmentIndex === 0" @click="previousAssessmentQuestion">← 上一题</button><button v-if="assessmentIndex < diagnostic.items.length - 1" class="primary" @click="nextAssessmentQuestion">下一题 →</button><button v-else class="primary" :disabled="!baselineComplete || baselineLoading" @click="submitBaseline">{{ baselineLoading ? "正在分析…" : "提交并更新学习画像" }}</button></footer>
        </section>
      </section>
      <footer><button class="secondary" @click="restartAssessment">{{ retakeEntryLabel }}</button><button class="primary" :aria-disabled="!learningPlan || planLoading" @click="requestEnterPersonalizedClassroom">确认安排，进入我的课堂 <span>→</span></button></footer>
    </section>

    <section v-else-if="hasObjectiveProfile && !props.genericMode && !planConfirmed && !sessionBeatSnapshot.length" class="returning-planner-gate">
      <header><div><h2>先确认今天怎样学，再进入课堂</h2><p>你的时间、目标和学习偏好，会共同决定本次内容和节奏。</p></div><div class="profile-chip" data-ready="true"><b>{{ averageMastery ?? 0 }}%</b><span>当前掌握度</span></div></header>
      <section class="planning-studio">
        <header><div><span>助教小程 · 可随时修改</span><h3>我的学习设置</h3></div><div class="plan-mode-switch" role="group" aria-label="规划面板模式"><button :class="{ active: planDetailMode === 'simple' }" @click="planDetailMode = 'simple'; savePlanPreferences()">简易版</button><button :class="{ active: planDetailMode === 'full' }" @click="planDetailMode = 'full'; savePlanPreferences()">完整版</button></div><button class="suggestion-button" @click="useSuggestedPace">采用助教建议</button></header>
        <div class="preference-grid"><label>每天可投入<input v-model.number="dailyMinutes" type="number" :min="DAILY_MINUTES_MIN" :max="DAILY_MINUTES_MAX" step="5" @blur="clampDailyMinutes" /><span>分钟（20–120）</span></label><template v-if="planDetailMode === 'full'"><label>每周学习<input v-model.number="weeklyDays" type="number" min="1" max="7" @blur="clampWeeklyDays" /><span>天</span></label><label class="wide">我的阶段目标<input v-model="planGoal" maxlength="120" /></label></template></div>
        <p v-if="planDetailMode === 'simple'" class="plan-simple-note">其余设置已按助教建议自动填好：每周 {{ weeklyDays }} 天 · {{ preferredModeLabel }} · 目标“{{ planGoal.trim() || DEFAULT_PLAN_GOAL }}”。</p>
        <section v-if="planDetailMode === 'full'" class="self-profile-inline"><label>我的学习经历（选填）<textarea v-model="selfDescription" rows="3" maxlength="1200" :placeholder="selfDescriptionFocused ? '' : SELF_DESCRIPTION_EXAMPLE" @focus="selfDescriptionFocused = true" @blur="selfDescriptionFocused = false" @input="updateSelfDescription"></textarea></label><button :disabled="selfProfileLoading || selfDescription.trim().length < 8" @click="analyzeSelfDescription">{{ selfProfileLoading ? "分析中…" : "更新学习倾向" }}</button><div v-if="selfProfile"><b>{{ selfProfile.level_label }}</b><span>{{ selfProfile.course_fit }}；推荐从“{{ selfProfile.recommended_start }}”开始。课程规划优先尊重明确的学习倾向，短测用于细调。</span></div></section>
        <div v-if="planDetailMode === 'full'" class="mode-picker"><span>我更喜欢</span><button :class="{ active: preferredMode === 'step_by_step' }" @click="preferredMode = 'step_by_step'">老师分步带着学</button><button :class="{ active: preferredMode === 'example_first' }" @click="preferredMode = 'example_first'">先看例子再归纳</button><button :class="{ active: preferredMode === 'practice_first' }" @click="preferredMode = 'practice_first'">先动手再补知识</button></div>
        <button ref="planBuildButton" class="primary build-plan" :disabled="planLoading" @click="generateLearningPlan">{{ planLoading ? planProgressMessage : learningPlan ? "按新设置重新编排" : "生成今天的专属课程" }} <span>→</span></button>
        <div v-if="planLoading" class="plan-progress" role="status" aria-live="polite"><span v-for="(label, index) in PLAN_PROGRESS_LABELS" :key="label" :class="{ done: index + 1 < planProgressStep, active: index + 1 === planProgressStep }"><i>{{ index + 1 < planProgressStep ? "✓" : index + 1 }}</i>{{ label }}</span></div>
        <ClassroomPlanPreview v-if="learningPlan" :plan="learningPlan" />
        <section v-if="baselineOpen && diagnostic" ref="baselinePanel" class="baseline-panel">
          <header><div><b>{{ diagnostic.title }}</b><span>阶段重测会刷新画像并改变下一节课</span></div><button @click="baselineOpen = false">收起</button></header>
          <div v-if="currentDiagnosticItem" class="single-question"><header><span>第 {{ assessmentIndex + 1 }} 题，共 {{ diagnostic.items.length }} 题</span></header><h2>{{ currentDiagnosticItem.prompt }}</h2><div><button v-for="option in currentDiagnosticItem.options" :key="option.id" :class="{ selected: diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" :aria-pressed="diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id" :disabled="baselineLoading" @click="selectBaselineAnswer(currentDiagnosticItem.exercise_id, option.id, assessmentIndex)"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b><span>{{ option.text }}</span><i>✓</i></button></div></div>
          <footer class="assessment-navigation"><button class="secondary" :disabled="assessmentIndex === 0" @click="previousAssessmentQuestion">← 上一题</button><button v-if="assessmentIndex < diagnostic.items.length - 1" class="primary" @click="nextAssessmentQuestion">下一题 →</button><button v-else class="primary" :disabled="!baselineComplete || baselineLoading" @click="submitBaseline">{{ baselineLoading ? "正在分析…" : "提交并更新学习画像" }}</button></footer>
        </section>
      </section>
      <footer><button class="secondary" @click="restartAssessment">{{ retakeEntryLabel }}</button><button class="primary" :aria-disabled="!learningPlan || planLoading" @click="requestEnterPersonalizedClassroom">确认安排，进入课堂 <span>→</span></button></footer>
    </section>

    <section v-else-if="!hasObjectiveProfile && !props.genericMode && !(learningContextError && (planConfirmed || sessionBeatSnapshot.length))" class="assessment-gate">
      <header><div><b>能力摸底</b><small>{{ diagnostic?.items.length ?? 12 }} 道跨层级短题，约 8 分钟，不计入成绩</small></div></header>
      <p class="honest-answer-note">这是跨知识点抽样摸底，题号表示测评顺序，不代表教材章节。未抽到的知识点不视为已掌握，后续课堂和练习会继续补充证据。</p>
      <template v-if="!assessmentStarted">
        <div class="assessment-welcome">
          <div><h1>先了解你的 Python 基础</h1><p>你可以先说说学习经历，也可以直接完成几道短题。助教会以客观测评为主、自述为辅，安排合适的起点、讲解节奏和后续练习。</p></div>
        </div>
        <section class="self-profile-card">
          <header><div><b>先说说你的学习起点与偏好（推荐填写）</b><span>课程规划智能体会优先参考这里；如果你说明自己是零基础，就从真正的起点开始，摸底题只用来辅助细调。</span></div><small>最多 1200 字</small></header>
          <div class="self-profile-presets"><button @click="useSelfDescriptionTemplate('我目前基本是零基础，没有系统学过 Python，希望从最基础的运行和输入输出开始。')">我基本没学过</button><button @click="useSelfDescriptionTemplate('我学过变量、if、for 和 while，能看懂简单代码，但自己写时容易卡住。')">学过基础语法</button><button @click="useSelfDescriptionTemplate('我学过列表、字典和函数，做过课程作业，希望加强调试、算法和项目能力。')">做过一些练习</button></div>
          <textarea v-model="selfDescription" rows="4" maxlength="1200" :placeholder="selfDescriptionFocused ? '' : SELF_DESCRIPTION_EXAMPLE" @focus="selfDescriptionFocused = true" @blur="selfDescriptionFocused = false" @input="updateSelfDescription"></textarea>
          <footer><span v-if="!selfProfile">写得越具体，助教越容易找到合适起点；不填写也可以继续，但课程个性化程度会降低。</span><span v-else>已识别学习倾向：<b>{{ selfProfile.level_label }}</b> · {{ selfProfile.course_fit }}</span><button :disabled="selfProfileLoading || selfDescription.trim().length < 8" @click="analyzeSelfDescription">{{ selfProfileLoading ? "助教正在判断…" : selfProfile ? "按新描述重新判断" : "让助教先判断" }}</button></footer>
          <article v-if="selfProfile" class="self-profile-result"><div><small>推荐起点</small><b>{{ selfProfile.recommended_start }}</b></div><p>{{ selfProfile.advisor_message }}</p><small>识别线索：{{ selfProfile.signals.join('、') }} · 可信度 {{ { low: '较低', medium: '中等', high: '较高' }[selfProfile.confidence] }} · ✓ 质量监督已审核</small></article>
        </section>
        <div class="assessment-start-actions"><button class="text-button" @click="emit('requestGenericMode')">暂不测评，先看看课程</button><button class="primary" @click="beginAssessment">开始摸底测试 <span>→</span></button></div>
      </template>
      <template v-else-if="diagnostic && currentDiagnosticItem">
        <div class="single-question">
          <header><span>第 {{ assessmentIndex + 1 }} 题，共 {{ diagnostic.items.length }} 题</span></header>
          <h2>{{ currentDiagnosticItem.prompt }}</h2>
          <div><button v-for="option in currentDiagnosticItem.options" :key="option.id" :class="{ selected: diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" :aria-pressed="diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id" :disabled="baselineLoading" @click="selectBaselineAnswer(currentDiagnosticItem.exercise_id, option.id, assessmentIndex)"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b><span>{{ option.text }}</span><i>✓</i></button></div>
        </div>
        <div class="assessment-navigation"><button class="secondary" :disabled="assessmentIndex === 0" @click="previousAssessmentQuestion">← 上一题</button><button v-if="assessmentIndex < diagnostic.items.length - 1" class="primary" @click="nextAssessmentQuestion">下一题 →</button><button v-else class="primary" :disabled="!baselineComplete || baselineLoading" @click="submitBaseline">{{ baselineLoading ? "正在生成画像…" : "提交测评并生成路线" }}</button></div>
      </template>
      <footer class="assessment-progress"><div><span>测试进度</span><b>{{ assessmentProgress }}%</b></div><i><span :style="{ width: `${assessmentProgress}%` }"></span></i><small>{{ Object.keys(diagnosticAnswers).length }} / {{ diagnostic?.items.length ?? 0 }} 已完成</small></footer>
    </section>

    <section v-else-if="isPaused && lesson" class="paused-classroom">
      <span>课堂已暂停</span><h2>刚才的位置和代码都还在</h2><p>你可以先查看其他页面；回来后会从“{{ currentBeat?.title ?? '当前环节' }}”继续，不会重新开始。</p><button class="primary" @click="resumeClassroom">回到专注课堂 <b>→</b></button>
    </section>

    <template v-else-if="lesson && currentBeat">
      <div v-if="props.genericMode && !hasObjectiveProfile" class="generic-mode-banner"><div><b>正在使用通用课程</b><span>尚未建立能力画像，讲解顺序和练习难度无法按你的水平调整。</span></div><button @click="emit('requestAssessment')">现在去完成测评</button></div>
      <nav class="focus-toolbar" aria-label="课堂工作区切换">
        <div><b>专注课堂</b><span>讲解与互动在同一空间持续进行</span></div>
        <select :value="classroomView" aria-label="选择课堂工作区" @change="handleViewSelect"><option value="lecture">课堂学习</option><option value="code">代码练习</option><option value="materials">课程资料</option></select>
        <div class="focus-view-buttons"><button v-for="item in ([['lecture','课堂'],['code','写代码'],['materials','看资料']] as const)" :key="item[0]" :class="{ active: classroomView === item[0] }" @click="changeClassroomView(item[0])">{{ item[1] }}</button></div>
        <div class="focus-actions"><ThemeToggle :dark="darkTheme" @toggle="emit('toggleTheme')" /><button class="exit-class" @click="requestEarlyExit">提前下课</button></div>
      </nav>
      <header class="lesson-masthead">
        <div>
          <h2>{{ planConfirmed ? personalizedSession.title : lesson.title }}</h2>
          <span>{{ planConfirmed ? `助教已按你的能力、目标与时间编排 · ${personalizedSession.focus}` : lesson.subtitle }}</span>
        </div>
        <aside>
          <small>课堂完成度 · 约 {{ lesson.duration_minutes }} 分钟</small>
          <b>{{ progress }}%</b>
          <i><span :style="{ width: `${progress}%` }"></span></i>
          <button @click="progressExplanationOpen = !progressExplanationOpen">{{ progressExplanationOpen ? "收起说明" : "如何计算" }}</button>
        </aside>
      </header>
      <section v-if="progressExplanationOpen" class="progress-explanation">
        <article><b>课堂完成度 {{ progress }}%</b><p>已完成环节 ÷ 本次个性化课堂环节数。正在学习的环节不提前计入，因此刚进入课堂从 0% 开始。</p><small>当前完成 {{ currentIndex }} / {{ personalizedBeats.length }} 个环节</small></article>
        <article><b>能力掌握度 {{ averageMastery === null ? "尚未测评" : `${averageMastery}%` }}</b><p>只对已经留下测评、练习或代码验证证据的知识点计算平均值；它反映能力证据，不等于看完了多少课程。</p><small>{{ measuredMastery(learnerProfile).length }} 个已测知识点 · {{ masteryEvidenceCount }} 条证据</small></article>
        <button aria-label="关闭计算说明" @click="progressExplanationOpen = false">×</button>
      </section>

      <section v-if="!planConfirmed" class="learning-copilot" aria-label="助教学情规划">
        <header>
          <div><h3>助教小程 · 我的学习节奏</h3><span>可以随时调整学习时间、目标和方式。</span></div>
          <div class="learning-tools">
            <button @click="emit('openKnowledgeMap')">课程知识地图 <span>→</span></button>
            <button class="profile-chip" :data-ready="hasObjectiveProfile" @click="progressExplanationOpen = !progressExplanationOpen">
              <b>{{ hasObjectiveProfile ? `${averageMastery ?? 0}%` : "未测" }}</b>
              <span>{{ hasObjectiveProfile ? "能力掌握度 · 查看算法" : "尚未建立能力基线" }}</span>
            </button>
          </div>
        </header>
        <div class="plan-controls">
          <label>每天投入<input v-model.number="dailyMinutes" type="number" :min="DAILY_MINUTES_MIN" :max="DAILY_MINUTES_MAX" step="5" @blur="clampDailyMinutes" /><span>分钟（20–120）</span></label>
          <label>每周学习<input v-model.number="weeklyDays" type="number" min="1" max="7" @blur="clampWeeklyDays" /><span>天</span></label>
          <label class="plan-goal">本阶段目标<input v-model="planGoal" maxlength="120" /></label>
          <button class="secondary" :disabled="diagnosticLoading" @click="hasObjectiveProfile ? restartAssessment() : startBaseline()">{{ diagnosticLoading ? "诊断载入中…" : diagnostic ? (hasObjectiveProfile ? retakeEntryLabel : "建立能力基线") : "重新载入诊断" }}</button>
          <button class="primary" :disabled="planLoading" @click="generateLearningPlan">{{ planLoading ? "规划中…" : "生成我的学习计划" }}</button>
        </div>
        <details class="self-profile-details">
          <summary><span>补充或修改我的学习经历</span><b>{{ selfProfile?.level_label ?? "待填写" }}</b></summary>
          <section v-if="planDetailMode === 'full'" class="self-profile-inline"><label>告诉助教你学过什么、做过什么、哪里容易卡住<textarea v-model="selfDescription" rows="3" maxlength="1200" placeholder="例如：学过 for 和列表，但遇到代码题不太会拆步骤。" @input="updateSelfDescription"></textarea></label><button :disabled="selfProfileLoading || selfDescription.trim().length < 8" @click="analyzeSelfDescription">{{ selfProfileLoading ? "分析中…" : "更新学习倾向" }}</button><div v-if="selfProfile"><b>{{ selfProfile.level_label }}</b><span>{{ selfProfile.course_fit }}；推荐从“{{ selfProfile.recommended_start }}”开始。课程规划优先尊重明确的学习倾向，短测用于细调。</span></div></section>
        </details>
        <ClassroomPlanPreview v-if="learningPlan" :plan="learningPlan" />
        <section v-if="baselineOpen && diagnostic" ref="baselinePanel" class="baseline-panel">
          <header><div><b>{{ diagnostic.title }}</b><span>每次完成一题，全部提交后更新学习画像</span></div><button @click="baselineOpen = false; showFeedback('阶段重测已收起，已选答案会保留。')">收起</button></header>
          <div v-if="currentDiagnosticItem" class="single-question">
            <header><span>第 {{ assessmentIndex + 1 }} 题，共 {{ diagnostic.items.length }} 题</span></header>
            <h2>{{ currentDiagnosticItem.prompt }}</h2>
            <div><button v-for="option in currentDiagnosticItem.options" :key="option.id" :class="{ selected: diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" :aria-pressed="diagnosticAnswers[currentDiagnosticItem.exercise_id] === option.id" :disabled="baselineLoading" @click="selectBaselineAnswer(currentDiagnosticItem.exercise_id, option.id, assessmentIndex)"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b><span>{{ option.text }}</span><i>✓</i></button></div>
          </div>
          <footer class="assessment-navigation"><button class="secondary" :disabled="assessmentIndex === 0" @click="previousAssessmentQuestion">← 上一题</button><button v-if="assessmentIndex < diagnostic.items.length - 1" class="primary" @click="nextAssessmentQuestion">下一题 →</button><button v-else class="primary" :disabled="!baselineComplete || baselineLoading" @click="submitBaseline">{{ baselineLoading ? "正在分析…" : "提交并更新学习画像" }}</button></footer>
        </section>
      </section>

      <nav class="lesson-steps" aria-label="课堂进度">
        <button
            v-for="(beat, index) in personalizedBeats"
          :key="beat.id"
          type="button"
          :class="{ active: index === currentIndex, done: index < currentIndex, visited: index <= furthestIndex }"
          :disabled="index > furthestIndex"
          :aria-current="index === currentIndex ? 'step' : undefined"
          :aria-label="index === currentIndex ? `当前环节：${beat.title}` : index <= furthestIndex ? `返回环节：${beat.title}` : `尚未解锁：${beat.title}`"
          @click="goToLessonStep(index)"
        ><em>{{ String(index + 1).padStart(2, "0") }}</em><span>{{ beat.title }}</span></button>
      </nav>
      <div class="lesson-history-actions"><button class="secondary" :disabled="currentIndex === 0" @click="goToLessonStep(currentIndex - 1)">← 返回上一环节</button><span>可点击上方已学环节回看，作答和代码不会丢失</span></div>

      <div v-if="classroomView === 'lecture'" class="classroom-layout integrated-learning">
        <section class="teacher-lecture-card">
          <div class="teacher-portrait"><i>林</i></div>
          <div><header><span>林老师</span></header><p v-if="latestTeacherQuestion" class="teacher-question">你刚才问：{{ latestTeacherQuestion.content }}</p><p v-if="latestTeacherMessage?.scopeNotice" class="scope-notice"><b>本节外延伸</b>{{ latestTeacherMessage.scopeNotice }}</p><SafeMarkdown :source="latestTeacherMessage?.content ?? '我们从你的当前起点出发。每讲一小步，我都会停下来等你确认。'" /><footer><span>{{ latestTeacherMessage?.review === "limited" ? "△ 依据有限 · 保守回答" : latestTeacherMessage?.review === "approved" ? `✓ 质量监督已审核 · ${latestTeacherMessage.evidenceCount ?? 0} 条${latestTeacherMessage.evidenceSource === 'online' ? ' Python 官方资料' : '课程依据'}` : "✓ 课程讲义已审核" }}</span><button @click="useConversationStarter('teacher', '老师，我对刚才这一步的理解是：')">向老师提问</button></footer></div>
        </section>
        <div class="classroom-scene" :data-phase="currentBeat.phase">
          <div class="sun-window"><span></span><i></i></div>
          <div class="wall-note">慢慢来，每一次尝试都算数</div>

          <section class="smart-board">
            <header><span>{{ currentBeat.eyebrow }}</span><b>{{ currentBeat.board_title }}</b></header>
            <p v-if="currentBeat.board_explanation" class="board-explanation">{{ currentBeat.board_explanation }}</p>
            <section v-if="currentBoardPoints.length" class="board-key-points"><b>关键要点</b><ul><li v-for="point in currentBoardPoints" :key="point">{{ point }}</li></ul></section>
            <section v-if="currentBeat.board_code" class="board-code-example" :class="{ expanded: boardCodeExpanded }"><b>示例代码</b><button class="code-expand" @click="boardCodeExpanded = !boardCodeExpanded">{{ boardCodeExpanded ? "收起" : "展开" }}</button><pre><code>{{ currentBeat.board_code }}</code></pre></section>
            <div v-if="currentBeat.board_trace.length" class="board-trace"><b>逐步拆解</b><span v-for="step in currentBeat.board_trace" :key="step">{{ step }}</span></div>
            <aside v-if="currentBoardMistakes.length" class="board-mistakes"><b>容易踩坑</b><span v-for="mistake in currentBoardMistakes" :key="mistake">{{ mistake }}</span></aside>
          </section>

          <div class="teacher-zone">
            <div class="classmate teacher" :class="{ speaking: activeRole === 'teacher' }">
              <i>林</i><div><b>林老师</b><small>循循善诱</small></div><span></span>
            </div>
            <div class="teacher-desk"><span>{ }</span><i></i></div>
          </div>

          <div class="desk-row">
            <button class="classmate" :class="{ speaking: activeRole === 'peer_cautious' }" @click="selectDialogueRole('peer_cautious')">
              <i>禾</i><div><b>小禾</b><small>认真提问</small></div><span></span>
            </button>
            <button class="classmate" :class="{ speaking: activeRole === 'peer_debugger' }" @click="selectDialogueRole('peer_debugger')">
              <i>拓</i><div><b>阿拓</b><small>一起排错</small></div><span></span>
            </button>
            <button class="classmate" :class="{ speaking: activeRole === 'peer_summarizer' }" @click="selectDialogueRole('peer_summarizer')">
              <i>宁</i><div><b>宁宁</b><small>整理笔记</small></div><span></span>
            </button>
          </div>
        </div>

        <aside class="conversation-dock" aria-label="课堂互动区">
          <header><div><p>LIVE CLASS</p><h3>{{ currentBeat.phase === "homework" ? "课后互动区" : "课堂互动区" }}</h3><small>左侧黑板是主线。你可以随时向老师追问、让助教判断理解，或和同伴讨论。</small></div><span><i></i>围绕当前环节</span></header>
          <div class="discussion-prompts"><button @click="useConversationStarter('teacher', '老师，请把黑板上的这一步再讲细一点：')">请老师讲细一点</button><button @click="useConversationStarter('ta', '助教，请判断我对当前内容的理解是否到位：')">请助教判断理解</button><button @click="useConversationStarter('peer_cautious', '我对这一步的理解是：')">分享我的理解</button><button @click="useConversationStarter('peer_debugger', '阿拓，我卡在这里，我们一起找找原因：')">一起找错误</button></div>
          <div ref="messageList" class="message-list" aria-live="polite">
            <div v-if="!conversationMessages.length" class="discussion-empty"><b>讲解和互动不再分开</b><span>先跟着左侧黑板学习；遇到不明白的地方，可以立即提问或说出自己的理解。</span></div>
            <article v-for="message in conversationMessages" :key="message.id" :class="[`role-${message.role}`, `kind-${message.kind}`]">
              <i :style="{ background: roleMeta[message.role].color }">{{ roleMeta[message.role].icon }}</i>
              <div><b>{{ message.name }}</b><p v-if="message.scopeNotice" class="scope-notice compact"><b>本节外延伸</b>{{ message.scopeNotice }}</p><SafeMarkdown :source="message.content" /><small v-if="message.review" class="message-audit">{{ message.review === "approved" ? `✓ 已审核 · ${message.evidenceCount ?? 0} 条${message.evidenceSource === 'online' ? ' Python 官方资料' : '课程依据'}` : "△ 依据有限 · 保守回答" }}</small></div>
            </article>
          </div>
          <footer>
            <div class="role-pills">
              <button class="teacher-pill" :class="{ active: dialogueRole === 'teacher' }" @click="selectDialogueRole('teacher')">问林老师</button>
              <button :class="{ active: dialogueRole === 'ta' }" @click="selectDialogueRole('ta')">问助教小程</button>
              <button v-for="person in lesson.cast.filter((item) => peerRoles.includes(item.role))" :key="person.role" :class="{ active: dialogueRole === person.role }" @click="selectDialogueRole(person.role)">{{ person.display_name }}</button>
            </div>
            <p v-if="dialogueError" class="dialogue-error" role="alert">{{ dialogueError }}</p>
            <div class="talk-composer"><textarea ref="dialogueComposer" v-model="dialogueText" :disabled="dialogueLoading" rows="2" maxlength="1000" :placeholder="`和${roleMeta[dialogueRole].name}说说你的想法…`" @keydown.ctrl.enter.prevent="askRole"></textarea><button :disabled="dialogueLoading || !dialogueText.trim()" @click="askRole">{{ dialogueLoading ? "思考中" : dialogueError ? "重试发送" : "发送" }}</button></div>
            <small v-if="dialogueLoading" role="status">{{ roleMeta[dialogueRole].name }}正在查阅课程资料并组织回复…</small>
            <small>回答经过课程资料检索与质量监督</small>
          </footer>
        </aside>
      </div>

      <section v-if="classroomView === 'materials'" class="lesson-materials">
        <aside><header><b>本次课程资料</b><span>由测评缺口动态组合</span></header><button v-for="block in selectedLearningBlocks" :key="block.block_id" :class="{ active: selectedMaterial?.block_id === block.block_id }" @click="selectedMaterialId = block.block_id"><small>{{ block.knowledge_point_id }}</small><b>{{ block.title }}</b><span>{{ block.skill_atoms.map((atom) => atom.label).join(' · ') }}</span></button><p v-if="!selectedLearningBlocks.length">当前使用固定实践课讲义。</p></aside>
        <article v-if="selectedMaterial"><header><span>{{ selectedMaterial.reason }}</span><h2>{{ selectedMaterial.title }}</h2></header><p>{{ selectedMaterial.summary }}</p><section><b>本节要点</b><ul><li v-for="point in selectedMaterial.key_points" :key="point">{{ point }}</li></ul></section><section v-if="selectedMaterial.example_problem"><b>分步例题</b><p>{{ selectedMaterial.example_problem }}</p><ol><li v-for="step in selectedMaterial.example_steps" :key="step">{{ step }}</li></ol><div class="code-heading"><b>示例代码</b><button class="code-expand" @click="materialCodeExpanded = !materialCodeExpanded">{{ materialCodeExpanded ? "收起" : "展开" }}</button></div><pre v-if="selectedMaterial.example_code" :class="{ expanded: materialCodeExpanded }"><code>{{ selectedMaterial.example_code }}</code></pre></section><small>课程包版本化内容 · 质量监督可追溯</small></article>
        <article v-else class="material-empty"><h2>{{ currentBeat.board_title }}</h2><p>{{ currentBeat.board_explanation }}</p><ul><li v-for="point in currentBeat.board_points" :key="point">{{ point }}</li></ul><pre v-if="currentBeat.board_code"><code>{{ currentBeat.board_code }}</code></pre></article>
      </section>

      <section v-if="classroomView === 'code' && !['practice', 'homework'].includes(currentBeat.action)" class="code-standby"><b>代码区会在动手环节开放</b><p>当前还在“{{ currentBeat.title }}”。先完成老师这一小段讲解，进入随堂练习后会自动切换到代码区。</p><button class="secondary" @click="changeClassroomView('lecture')">返回听课</button></section>

      <section v-if="classroomView === 'lecture' || (classroomView === 'code' && ['practice', 'homework'].includes(currentBeat.action))" class="lesson-action" :data-action="currentBeat.action">
        <div v-if="error" class="inline-error" @click="error = ''">{{ error }}<span>×</span></div>

        <template v-if="currentBeat.action === 'choice' && currentBeat.checkpoint">
          <header><div><p>停一下，轮到你</p><h3>{{ currentBeat.checkpoint.prompt }}</h3></div><span>没有计时，想清楚再选</span></header>
          <div class="checkpoint-options">
            <button v-for="choice in currentBeat.checkpoint.choices" :key="choice.id" :class="{ selected: selectedChoice === choice.id }" :disabled="submitting || checkpointResult?.accepted" @click="selectedChoice = choice.id; checkpointResult = null"><b>{{ choice.id }}</b><span>{{ choice.text }}</span></button>
          </div>
          <footer><p v-if="checkpointResult" :data-pass="checkpointResult.accepted">{{ checkpointResult.feedback }}</p><button v-if="!checkpointResult?.accepted" class="primary" :disabled="!selectedChoice || submitting" @click="submitChoice">{{ submitting ? "正在听你的回答…" : "说出我的答案" }}</button><button v-else class="primary" @click="advance">继续听讲 <span>→</span></button></footer>
        </template>

        <template v-else-if="currentBeat.action === 'practice'">
          <ClassroomCodeTask
            :task="lesson.practice"
            v-model="practiceCode"
            :result="practiceResult"
            :loading="submitting"
            :hint="hint"
            :hint-loading="hintLoading"
            label="随堂练习"
            @submit="submitCode(lesson.practice, practiceCode)"
            @hint="requestHint(lesson.practice)"
          />
          <footer v-if="isPracticeAccepted" class="continue-bar"><span>课堂任务已通过，学习画像已经更新。</span><button class="primary" @click="advance">进入课堂小结 <span>→</span></button></footer>
        </template>

        <template v-else-if="currentBeat.action === 'homework'">
          <div v-if="lessonComplete" class="lesson-complete">
            <h3>本次个性化课堂完成，做得很好。</h3>
            <p>随堂练习和课后作业都已通过真实测试，画像获得两份新的代码证据。助教不会机械进入固定下一章，而会重新检查薄弱点、前置断层与已掌握内容。</p>
            <div><b>下一步</b>{{ lesson.unlock_title }}</div>
            <footer>
              <button class="secondary" @click="startBaseline">阶段重测并校正画像</button>
              <button v-if="lesson.unlocked_project_ids.length" class="secondary" @click="emit('openProjects')">进入已解锁项目</button>
              <button class="primary" :disabled="loading" @click="startNextLesson">{{ loading ? "正在重算…" : "生成下一节不同的课" }} <span>→</span></button>
            </footer>
          </div>
          <ClassroomCodeTask
            v-else
            :task="lesson.homework"
            v-model="homeworkCode"
            :result="homeworkResult"
            :loading="submitting"
            :hint="hint"
            :hint-loading="hintLoading"
            label="课后作业"
            @submit="submitCode(lesson.homework, homeworkCode, true)"
            @hint="requestHint(lesson.homework)"
          />
        </template>

        <template v-else>
          <header><div><p>{{ currentBeat.eyebrow }}</p><h3>{{ currentBeat.title }}</h3></div><span>老师会等你准备好</span></header>
          <LessonBeatContent :beat="currentBeat" />
          <div class="ready-card"><i>✓</i><div><b>{{ currentBeat.phase === "summary" ? "用自己的话复盘今天的方法" : "准备好后再继续" }}</b><span>{{ currentBeat.phase === "summary" ? lesson.focus_skill_atoms.join("、") : "这里没有自动跳转，也没有催促倒计时" }}</span></div><button class="primary" @click="advance">{{ currentBeat.phase === "summary" ? "领取课后作业" : "我准备好了" }} <span>→</span></button></div>
        </template>
      </section>
    </template>

    <Transition name="feedback-toast">
      <div v-if="uiFeedback" class="global-action-feedback" :data-tone="feedbackTone" :role="feedbackTone === 'error' ? 'alert' : 'status'" aria-live="polite" aria-atomic="true">
        <i></i><span>{{ uiFeedback }}</span><button aria-label="关闭反馈" @click="dismissFeedback">×</button>
      </div>
    </Transition>

    <Teleport to="body">
    <div v-if="exitDialogOpen" class="class-exit-backdrop" role="presentation" @click.self="exitDialogOpen = false">
      <section ref="exitDialog" role="dialog" aria-modal="true" aria-labelledby="class-exit-title" tabindex="-1" @keydown="handleExitKeydown"><span>离开前确认</span><h2 id="class-exit-title">为什么想提前下课？</h2><p>无论怎样选择，当前进度、讨论和代码草稿都会保存。</p><div><button @click="pauseClassroom(true)"><b>这部分我已经学过</b><span>记录为自述，之后用短题复核，不直接算作掌握</span></button><button @click="pauseClassroom(false)"><b>仍然退出课堂</b><span>暂停在当前位置，稍后可以继续</span></button></div><footer><button @click="exitDialogOpen = false">取消退出，继续学习</button></footer></section>
    </div>
    </Teleport>
  </section>
</template>

<style scoped>
.immersive-lesson { min-width: 0; display: grid; gap: 18px; color: #30252a; }
.classroom-loading, .classroom-error { min-height: 520px; display: grid; place-items: center; align-content: center; gap: 10px; border: 1px solid #eedfe1; border-radius: 22px; background: #fffaf7; }
.classroom-loading i { width: 34px; height: 34px; border: 3px solid #f1d7d8; border-top-color: #b4233b; border-radius: 50%; animation: spin .8s linear infinite; }
.classroom-loading strong { font-size: 17px; }.classroom-loading span { color: #8c7d82; font-size: 12px; }
.classroom-error button { padding: 9px 18px; border: 0; border-radius: 9px; color: #fff; background: #b4233b; }
.lesson-masthead { display: flex; align-items: end; justify-content: space-between; gap: 24px; padding: 24px 28px; overflow: hidden; border: 1px solid #eadbdd; border-radius: 22px; background: radial-gradient(circle at 88% 10%, #ffe9d2 0 10%, transparent 35%), linear-gradient(135deg, #fffaf7, #fff 48%, #fff3f2); box-shadow: 0 18px 50px #7720330d; }
.lesson-masthead p { margin: 0 0 6px; color: #b4233b; font: 800 12px Consolas, monospace; letter-spacing: .18em; }.lesson-masthead h2 { margin: 0; font-size: 26px; }.lesson-masthead div > span { display: block; margin-top: 7px; color: #796b70; font-size: 12px; }
.lesson-masthead aside { width: 220px; display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 5px 12px; }.lesson-masthead aside small { color: #8b7c81; }.lesson-masthead aside b { color: #b4233b; font-size: 22px; }.lesson-masthead aside i { grid-column: 1 / -1; height: 6px; overflow: hidden; border-radius: 99px; background: #f1dedf; }.lesson-masthead aside i span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #c51632, #e27765); }
.lesson-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(112px, 1fr)); gap: 7px; }.lesson-steps > button { min-width: 0; display: grid; gap: 3px; padding: 10px; border: 1px solid #ece3e4; border-radius: 11px; color: #a09599; background: #fff; text-align: left; cursor: default; }.lesson-steps > button.visited { cursor: pointer; }.lesson-steps > button:disabled { opacity: .58; }.lesson-steps > button em { font: normal 12px Consolas; }.lesson-steps > button span { overflow: hidden; font-size: 12px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }.lesson-steps > button.active { color: #8f1428; border-color: #cf8792; background: #fff4f4; box-shadow: inset 0 -2px #c51632; }.lesson-steps > button.done { color: #577863; border-color: #d6e5da; background: #f5fbf7; }.lesson-steps > button.visited:hover { transform: translateY(-1px); border-color: #cf8792; }.lesson-history-actions { display: flex; align-items: center; gap: 12px; margin-top: 9px; }.lesson-history-actions button { padding: 8px 11px; border: 1px solid #dfd2d4; border-radius: 9px; color: #8f2032; background: #fff; font-size: 12px; font-weight: 800; }.lesson-history-actions button:disabled { color: #b8adb0; cursor: not-allowed; }.lesson-history-actions span { color: #8e8286; font-size: 12px; }
.classroom-layout { min-height: 620px; display: grid; grid-template-columns: minmax(540px, 1.45fr) minmax(320px, .8fr); overflow: hidden; border: 1px solid #e4d9d8; border-radius: 24px; background: #fff; box-shadow: 0 22px 65px #3c1c250e; }
.classroom-scene { position: relative; min-height: 620px; padding: 54px 34px 28px; overflow: hidden; border-right: 1px solid #e7dcda; background: linear-gradient(180deg, #fbf4e9 0 63%, #d9b99b 63% 65%, #c69671 65%); }
.classroom-scene::after { content: ""; position: absolute; inset: 65% 0 0; opacity: .28; background-image: linear-gradient(90deg, #6f3d201c 1px, transparent 1px), linear-gradient(#6f3d201c 1px, transparent 1px); background-size: 48px 38px; transform: perspective(160px) rotateX(5deg); }
.sun-window { position: absolute; top: 24px; right: 25px; width: 160px; height: 112px; overflow: hidden; border: 8px solid #fff; border-radius: 5px 18px 5px 5px; background: linear-gradient(#bce0ea 0 58%, #b8c99d 58%); box-shadow: 0 10px 28px #6b543120; }.sun-window::before, .sun-window::after { content: ""; position: absolute; background: #fff; }.sun-window::before { left: 48%; width: 6px; height: 100%; }.sun-window::after { top: 51%; width: 100%; height: 6px; }.sun-window span { position: absolute; top: 12px; left: 18px; width: 30px; height: 30px; border-radius: 50%; background: #ffd881; box-shadow: 0 0 28px #ffc85c; }.sun-window i { position: absolute; right: -15px; bottom: -20px; width: 90px; height: 56px; border-radius: 50%; background: #769b6c; }.sun-window small { position: absolute; z-index: 2; right: 6px; bottom: 4px; padding: 3px 6px; border-radius: 5px; color: #635940; background: #fff9; font-size: 12px; }
.wall-note { position: absolute; top: 25px; left: 32px; padding: 8px 12px; border: 1px solid #ead6bd; border-radius: 8px; color: #8a5e40; background: #fff8e9; font-size: 12px; transform: rotate(-1deg); }
.smart-board { position: relative; z-index: 2; width: calc(100% - 170px); min-height: 330px; max-height: 470px; overflow-y: auto; padding: 20px 22px; border: 10px solid #6e5140; border-radius: 10px; color: #edf8f0; background: linear-gradient(145deg, #23443b, #17352e); box-shadow: inset 0 0 35px #081b14, 0 14px 28px #60422a24; }.smart-board::-webkit-scrollbar { width: 9px; }.smart-board::-webkit-scrollbar-track { border-radius: 99px; background: #17352e; }.smart-board::-webkit-scrollbar-thumb { border-radius: 99px; background: #ffffff35; }.smart-board { scrollbar-width: thin; scrollbar-color: #ffffff40 #17352e; }.smart-board header span { display: block; color: #e4c999; font: 700 12px Consolas; letter-spacing: .12em; }.smart-board header b { display: block; margin-top: 7px; font-size: 18px; }.smart-board pre { margin: 8px 0 0; padding: 12px 14px; overflow: auto; border: 1px solid #ffffff18; border-radius: 8px; background: #071f19a8; }.smart-board code { color: #fff4d4; font: 12px/1.65 Consolas, monospace; }.smart-board ul { margin: 8px 0 0; padding: 0; display: grid; gap: 7px; list-style: none; }.smart-board li { color: #d8ebe1; font-size: 12px; line-height: 1.55; }.smart-board li::before { content: "·"; margin-right: 8px; color: #f0c76f; font-weight: 900; }.board-key-points,.board-code-example { margin-top: 13px; }.board-key-points > b,.board-code-example > b { color: #f6caa2; font-size: 12px; }
.teacher-zone { position: relative; z-index: 3; height: 122px; display: flex; align-items: end; justify-content: space-between; padding: 6px 34px 0 80px; }.teacher-desk { width: 125px; height: 52px; position: relative; border-radius: 5px 5px 2px 2px; color: #fbddaa; background: #855b3e; box-shadow: 0 8px 14px #56341f28; }.teacher-desk span { position: absolute; top: -35px; left: 28px; width: 48px; height: 34px; display: grid; place-items:center; border: 4px solid #55525c; border-radius: 4px; color: #ffcad1; background: #22252c; font: 800 12px Consolas; }.teacher-desk i { position: absolute; right: 10px; top: -14px; width: 10px; height: 16px; border-radius: 2px 2px 5px 5px; background: #b8d4c4; }
.desk-row { position: relative; z-index: 4; display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; align-items: end; }.classmate { position: relative; min-width: 0; display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid #b77c5548; border-radius: 12px 12px 5px 5px; color: #5b4032; background: linear-gradient(#f6dec7, #d7ae8c); box-shadow: 0 10px 15px #6b3c2222; text-align: left; }.classmate > i { width: 34px; height: 34px; flex: 0 0 auto; display: grid; place-items: center; border: 3px solid #fff8; border-radius: 50%; color: #fff; background: #6f8d75; font: normal 800 12px serif; box-shadow: 0 3px 8px #4b2d1f24; }.classmate:nth-child(2) > i { background: #c76a4e; }.classmate:nth-child(3) > i { background: #8b7195; }.classmate.ta > i { background: #a06e43; }.classmate div { min-width: 0; }.classmate b, .classmate small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.classmate b { font-size: 12px; }.classmate small { margin-top: 3px; color: #8b6957; font-size: 12px; }.classmate > span { position: absolute; top: -8px; right: 10px; width: 10px; height: 10px; border: 3px solid #fff; border-radius: 50%; background: #c8b7aa; }.classmate.speaking { border-color: #c51632; background: linear-gradient(#fff1df, #efc7a5); transform: translateY(-5px); box-shadow: 0 0 0 4px #c5163215, 0 16px 25px #6b3c2230; }.classmate.speaking > span { background: #d51c39; box-shadow: 0 0 0 5px #d51c3920; animation: pulse 1.5s infinite; }.classmate.teacher { width: 165px; background: linear-gradient(#f5e5d9, #d5b9a3); }
.conversation-dock { min-height: 620px; display: grid; grid-template-rows: auto 1fr auto; background: #fffcfa; }.conversation-dock > header { display: flex; justify-content: space-between; gap: 15px; padding: 20px; border-bottom: 1px solid #eee2e0; }.conversation-dock header p { margin: 0 0 5px; color: #b4233b; font: 700 12px Consolas; letter-spacing: .14em; }.conversation-dock header h3 { margin: 0; font-size: 15px; }.conversation-dock header > span { height: fit-content; display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 99px; color: #65756b; background: #eef6f0; font-size: 12px; }.conversation-dock header > span i { width: 6px; height: 6px; border-radius: 50%; background: #49a26c; box-shadow: 0 0 0 4px #49a26c17; }
.message-list { max-height: 410px; min-height: 340px; overflow: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }.message-list article { display: grid; grid-template-columns: 31px 1fr; align-items: start; gap: 9px; }.message-list article > i { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 9px; color: #fff; font: normal 700 12px serif; }.message-list article > div { padding: 10px 11px; border: 1px solid #eee3e2; border-radius: 4px 13px 13px; background: #fff; box-shadow: 0 5px 16px #3c1c2508; }.message-list article b { color: #7b6069; font-size: 12px; }.message-list article p { margin: 5px 0 0; color: #4e4548; font-size: 12px; line-height: 1.7; white-space: pre-wrap; }.message-list article.role-student { grid-template-columns: 1fr 31px; }.message-list article.role-student > i { grid-column: 2; }.message-list article.role-student > div { grid-column: 1; grid-row: 1; border-color: #f0cdd2; border-radius: 13px 4px 13px 13px; background: #fff4f4; }
.conversation-dock > footer { padding: 13px; border-top: 1px solid #eee2e0; background: #fff; }.role-pills { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }.role-pills button { padding: 4px 7px; border: 1px solid #eadfe0; border-radius: 99px; color: #8c7d82; background: #fff; font-size: 12px; }.role-pills button.active { color: #a6132c; border-color: #dba5ad; background: #fff2f3; }.talk-composer { display: grid; grid-template-columns: 1fr auto; gap: 7px; }.talk-composer textarea { padding: 9px 10px; resize: none; border: 1px solid #dfd4d4; border-radius: 9px; color: #40383a; background: #fffcfb; font-size: 12px; }.talk-composer button { padding: 0 13px; border: 0; border-radius: 9px; color: #fff; background: #b4233b; font-size: 12px; }.talk-composer button:disabled { opacity: .5; }.conversation-dock > footer > small { display: block; margin-top: 6px; color: #aaa0a3; font-size: 12px; }
.lesson-action { padding: 24px; border: 1px solid #e5d9d8; border-radius: 22px; background: #fff; box-shadow: 0 16px 45px #3c1c250a; }.lesson-action > header { display: flex; align-items: start; justify-content: space-between; gap: 20px; }.lesson-action header p { margin: 0 0 5px; color: #b4233b; font: 800 12px Consolas; letter-spacing: .14em; }.lesson-action header h3 { margin: 0; font-size: 17px; }.lesson-action header > span { color: #9a8d91; font-size: 12px; }.inline-error { margin-bottom: 14px; padding: 9px 12px; border-radius: 8px; color: #9f2837; background: #fff0f1; font-size: 12px; }.inline-error span { float: right; }
.checkpoint-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 18px 0; }.checkpoint-options button { display: flex; align-items: center; gap: 10px; padding: 13px; border: 1px solid #e6dada; border-radius: 12px; color: #62565a; background: #fffdfc; text-align: left; }.checkpoint-options button b { width: 28px; height: 28px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 8px; color: #a31d32; background: #fff0f2; }.checkpoint-options button span { font-size: 12px; line-height: 1.45; }.checkpoint-options button.selected { border-color: #cc7c89; background: #fff5f5; box-shadow: 0 0 0 3px #c5163210; }.lesson-action > footer { display: flex; align-items: center; justify-content: flex-end; gap: 14px; }.lesson-action > footer p { margin: 0 auto 0 0; color: #a03a48; font-size: 12px; }.lesson-action > footer p[data-pass="true"] { color: #28794f; }
.primary { padding: 10px 17px; border: 0; border-radius: 9px; color: #fff; background: linear-gradient(135deg, #cc1936, #a70f27); box-shadow: 0 8px 18px #b5163030; font-size: 12px; font-weight: 700; }.primary:disabled { opacity: .5; box-shadow: none; }.primary span { margin-left: 7px; }
.ready-card { margin-top: 16px; display: flex; align-items: center; gap: 12px; padding: 15px; border: 1px solid #e8dedd; border-radius: 13px; background: #fffaf7; }.ready-card > i { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 50%; color: #657b69; background: #e6f1e8; font-style: normal; }.ready-card div { flex: 1; }.ready-card b, .ready-card span { display: block; }.ready-card b { font-size: 12px; }.ready-card div span { margin-top: 4px; color: #8d8084; font-size: 12px; }
.continue-bar { margin-top: 15px; padding-top: 15px; border-top: 1px solid #e8dddd; }.continue-bar > span { margin-right: auto; color: #397456; font-size: 12px; }
.lesson-complete { margin-bottom: 18px; padding: 27px; border: 1px solid #d7e4d9; border-radius: 16px; background: radial-gradient(circle at 90% 10%, #ffe6b8, transparent 25%), linear-gradient(135deg, #f5fbf6, #fff); }.lesson-complete > span { color: #508063; font: 800 12px Consolas; letter-spacing: .16em; }.lesson-complete h3 { margin: 8px 0; font-size: 22px; }.lesson-complete p { max-width: 650px; color: #657069; font-size: 12px; line-height: 1.7; }.lesson-complete div { width: fit-content; padding: 9px 12px; border-radius: 9px; color: #715a38; background: #fff2d8; font-size: 12px; }.lesson-complete div b { margin-right: 9px; }
.lesson-complete footer { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 18px; }.lesson-complete footer .secondary { padding: 9px 13px; border: 1px solid #bfd6c6; border-radius: 9px; color: #426f53; background: #fff; font-size: 12px; font-weight: 800; }
@keyframes spin { to { transform: rotate(360deg); } } @keyframes pulse { 50% { box-shadow: 0 0 0 8px #d51c3908; } }
@media (max-width: 1120px) { .classroom-layout { grid-template-columns: 1fr; }.classroom-scene { border-right: 0; border-bottom: 1px solid #e7dcda; }.conversation-dock { min-height: 520px; }.message-list { max-height: 330px; } }
@media (max-width: 760px) { .lesson-masthead { min-width: 0; align-items: start; flex-direction: column; padding: 20px; }.lesson-masthead > div { min-width: 0; }.lesson-masthead h2 { font-size: 22px; line-height: 1.25; }.lesson-masthead aside { width: 100%; min-width: 0; }.lesson-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }.classroom-layout, .classroom-scene, .conversation-dock { min-width: 0; }.classroom-scene { min-height: 660px; padding-inline: 18px; }.smart-board { width: 100%; margin-top: 100px; }.sun-window { top: 20px; right: 18px; }.desk-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }.checkpoint-options { grid-template-columns: 1fr; } }
html[data-device-resolved="mobile"] .classroom-layout { grid-template-columns: 1fr; } html[data-device-resolved="mobile"] .classroom-scene { border-right: 0; border-bottom: 1px solid #e7dcda; } html[data-device-resolved="mobile"] .conversation-dock { min-height: 520px; } html[data-device-resolved="mobile"] .message-list { max-height: 330px; } html[data-device-resolved="mobile"] .lesson-masthead { min-width: 0; align-items: start; flex-direction: column; padding: 20px; } html[data-device-resolved="mobile"] .lesson-masthead > div { min-width: 0; } html[data-device-resolved="mobile"] .lesson-masthead h2 { font-size: 22px; line-height: 1.25; } html[data-device-resolved="mobile"] .lesson-masthead aside { width: 100%; min-width: 0; } html[data-device-resolved="mobile"] .lesson-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); } html[data-device-resolved="mobile"] .classroom-layout, html[data-device-resolved="mobile"] .classroom-scene, html[data-device-resolved="mobile"] .conversation-dock { min-width: 0; } html[data-device-resolved="mobile"] .classroom-scene { min-height: 660px; padding-inline: 18px; } html[data-device-resolved="mobile"] .smart-board { width: 100%; margin-top: 100px; } html[data-device-resolved="mobile"] .sun-window { top: 20px; right: 18px; } html[data-device-resolved="mobile"] .desk-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } html[data-device-resolved="mobile"] .checkpoint-options { grid-template-columns: 1fr; } html[data-device-resolved="mobile"] .classroom-layout > .teacher-lecture-card { grid-template-columns: 1fr; } html[data-device-resolved="mobile"] .teacher-portrait { justify-items: start; } html[data-device-resolved="mobile"] .teacher-lecture-card footer { align-items: flex-start; flex-direction: column; } html[data-device-resolved="mobile"] .lesson-materials { grid-template-columns: 1fr; } html[data-device-resolved="mobile"] .lesson-materials > aside { border-right: 0; border-bottom: 1px solid #eee4e5; }
.learning-copilot { display: grid; gap: 14px; padding: 21px 23px; border: 1px solid #e7dadd; border-radius: 20px; background: linear-gradient(135deg, #fff 0 65%, #fff5f4); box-shadow: 0 14px 38px #6e1b2a0a; }
.learning-copilot > header { display: flex; align-items: center; justify-content: space-between; gap: 20px; }.learning-copilot > header p { margin: 0 0 4px; color: #b4233b; font: 800 12px Consolas, monospace; letter-spacing: .16em; }.learning-copilot > header h3 { margin: 0; font-size: 18px; }.learning-copilot > header div > span { display: block; margin-top: 5px; color: #8e8085; font-size: 12px; }
.profile-chip { min-width: 145px; padding: 10px 13px; border: 1px solid #ead0d4; border-radius: 12px; color: #9d2337; background: #fff5f6; text-align: right; }.profile-chip[data-ready="true"] { color: #387657; border-color: #cee3d5; background: #f3faf5; }.profile-chip b, .profile-chip span { display: block; }.profile-chip b { font-size: 20px; }.profile-chip span { margin-top: 2px; font-size: 12px; }
.learning-tools { display: flex; align-items: center; gap: 9px; }.learning-tools > button { padding: 9px 11px; border: 1px solid #e2c6ca; border-radius: 9px; color: #962139; background: #fff9f9; font-size: 12px; font-weight: 800; white-space: nowrap; }.learning-tools > button:hover { border-color: #c85e70; background: #fff; transform: translateY(-1px); }.learning-tools > button span { margin-left: 5px; }
.plan-controls { display: grid; grid-template-columns: 140px 140px minmax(230px, 1fr) auto auto; align-items: end; gap: 9px; }.plan-controls label { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 5px; color: #75696d; font-size: 12px; font-weight: 700; }.plan-controls label > input { grid-column: 1; width: 100%; min-width: 0; padding: 9px 10px; border: 1px solid #e2d7d8; border-radius: 8px; color: #3e3538; background: #fffdfc; outline: none; }.plan-controls label > span { grid-column: 2; grid-row: 2; color: #9a8d91; }.plan-controls .plan-goal { grid-template-columns: 1fr; }.plan-controls .plan-goal input { grid-column: 1; }.plan-controls input:focus { border-color: #c85b6c; box-shadow: 0 0 0 3px #c5163210; }.plan-controls button { min-height: 36px; padding: 8px 12px; border-radius: 8px; white-space: nowrap; font-size: 12px; font-weight: 800; }.plan-controls .secondary { border: 1px solid #d7aab1; color: #9e1930; background: #fff5f6; }
.plan-controls .secondary:disabled { opacity: .58; cursor: wait; }
.global-action-feedback { position: fixed; z-index: 90; right: 24px; bottom: 24px; width: min(420px, calc(100vw - 32px)); display: flex; align-items: center; gap: 10px; padding: 13px 14px; border: 1px solid #e5d8d9; border-radius: 13px; color: #514649; background: #fffdfcf2; box-shadow: 0 18px 55px #3c101d26; backdrop-filter: blur(14px); font-size: 12px; line-height: 1.55; }.global-action-feedback > i { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; background: #4b9b6b; box-shadow: 0 0 0 4px #4b9b6b15; }.global-action-feedback > span { flex: 1; }.global-action-feedback button { flex: 0 0 auto; padding: 3px 6px; border: 0; color: #8f7d82; background: transparent; font-size: 15px; }.feedback-toast-enter-active, .feedback-toast-leave-active { transition: opacity .18s ease, transform .18s ease; }.feedback-toast-enter-from, .feedback-toast-leave-to { opacity: 0; transform: translateY(8px); }
.plan-result { position: relative; padding: 16px 17px 30px; border: 1px solid #d9e5dc; border-radius: 14px; background: #f8fcf9; }.plan-result[data-status="insufficient_evidence"] { border-color: #ead9c0; background: #fffaf2; }.plan-result > header div { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }.plan-result header b { font-size: 12px; }.plan-result header span { color: #8a9690; font-size: 12px; }.plan-result :deep(.safe-markdown) { color: #4f5c55; font-size: 12px; }.audit-mark, .message-audit { color: #8ba095; font-size: 12px; font-weight: 600; letter-spacing: .03em; opacity: .72; }.audit-mark { position: absolute; right: 14px; bottom: 10px; }
.baseline-panel { scroll-margin-top: 20px; padding: 17px; border: 1px solid #e8cbd0; border-radius: 14px; background: #fff9f8; animation: panel-in .2s ease-out; }.baseline-panel > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }.baseline-panel > header b, .baseline-panel > header span { display: block; }.baseline-panel > header b { font-size: 13px; }.baseline-panel > header span { margin-top: 4px; color: #8d7f84; font-size: 12px; }.baseline-panel > header button { border: 0; color: #9a5964; background: transparent; font-size: 12px; }.baseline-questions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }.baseline-questions article { padding: 12px; border: 1px solid #ece2e2; border-radius: 11px; background: #fff; }.baseline-questions p { min-height: 38px; margin: 0 0 9px; font-size: 12px; line-height: 1.5; }.baseline-questions p em { margin-right: 7px; color: #ba2039; font: normal 12px Consolas; }.baseline-questions article > div { display: grid; gap: 5px; }.baseline-questions button { display: flex; align-items: center; gap: 7px; padding: 7px 8px; border: 1px solid transparent; border-radius: 7px; color: #62585b; background: #f6f3f3; text-align: left; font-size: 12px; }.baseline-questions button b { color: #a62a3e; }.baseline-questions button.selected { border-color: #d48b97; color: #951a2f; background: #fff0f2; box-shadow: inset 2px 0 #c51632; }.baseline-panel > footer { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-top: 13px; padding-top: 12px; border-top: 1px solid #eadfe0; }.baseline-panel > footer span { color: #8f8387; font-size: 12px; }
.message-list article :deep(.safe-markdown) { margin-top: 5px; color: #4e4548; font-size: 12px; }.message-list .message-audit { display: block; margin-top: 7px; text-align: right; }
@keyframes panel-in { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
@media (max-width: 1120px) { .plan-controls { grid-template-columns: 1fr 1fr; }.plan-controls .plan-goal { grid-column: 1 / -1; } }
@media (max-width: 760px) { .learning-copilot > header { align-items: stretch; flex-direction: column; }.learning-tools { align-items: stretch; flex-direction: column-reverse; }.profile-chip { text-align: left; }.plan-controls, .baseline-questions { grid-template-columns: 1fr; }.plan-controls .plan-goal { grid-column: auto; } }
.assessment-gate, .assessment-result-screen { width: min(100%, 1080px); min-height: 0; display: grid; align-content: start; gap: 20px; margin: 0 auto; padding: clamp(24px, 3vw, 40px); overflow: hidden; border: 1px solid #e8dfe1; border-radius: 22px; background: radial-gradient(circle at 92% 8%, #ffe9e6 0 8%, transparent 28%), linear-gradient(145deg, #fff, #fffaf9); box-shadow: 0 20px 55px #5513220d; }
.assessment-gate > header, .assessment-result-screen > header { padding-bottom: 14px; border-bottom: 1px solid #eee5e6; }.assessment-gate > header div { display: flex; align-items: baseline; gap: 12px; }.assessment-gate > header b { font-size: 18px; }.assessment-gate > header small { color: #7e7377; font-size: 12px; }
.assessment-welcome { max-width: 760px; padding: 24px 0 12px; }.assessment-welcome h1 { margin: 0; font-size: clamp(30px, 4vw, 46px); line-height: 1.16; letter-spacing: -.045em; }.assessment-welcome p { max-width: 700px; margin: 18px 0 0; color: #665b5f; font-size: 14px; line-height: 1.85; }
.assessment-start-actions, .assessment-navigation { width: min(100%, 760px); display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 0 auto; }.assessment-start-actions .text-button { padding: 9px 0; border: 0; color: #766a6e; background: transparent; font-size: 12px; text-decoration: underline; text-underline-offset: 3px; }.assessment-start-actions .primary, .assessment-navigation .primary, .assessment-result-screen footer .primary { padding: 12px 18px; font-size: 12px; }.assessment-navigation .secondary, .assessment-result-screen footer .secondary { padding: 11px 15px; border: 1px solid #e2d3d5; border-radius: 9px; color: #655b5f; background: #fff; font-size: 12px; }.assessment-navigation .secondary:disabled { opacity: .45; }
.single-question { max-width: 760px; width: 100%; margin: 4px auto; }.single-question > header { display: flex; align-items: center; }.single-question > header span { color: #a41d34; font-size: 12px; font-weight: 800; }.single-question h2 { margin: 14px 0 20px; font-size: clamp(24px, 3vw, 32px); line-height: 1.35; letter-spacing: -.025em; }.single-question > div { display: grid; gap: 10px; }.single-question button { display: grid; grid-template-columns: 38px 1fr 24px; align-items: center; gap: 12px; padding: 13px 16px; border: 1px solid #e9e1e2; border-radius: 12px; color: #4f4649; background: #fff; text-align: left; }.single-question button:hover { border-color: #d9aab2; transform: translateX(3px); box-shadow: 0 10px 25px #6813230a; }.single-question button b { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 9px; color: #a42338; background: #fff1f2; font-size: 12px; }.single-question button span { font-size: 13px; line-height: 1.55; }.single-question button i { color: transparent; font-style: normal; }.single-question button.selected { border-color: #c96575; background: #fff5f5; box-shadow: inset 4px 0 #bf1934, 0 12px 30px #6813230d; }.single-question button.selected i { color: #3c9666; }
.single-question button.unknown { border-style: dashed; color: #766c70; background: #fbf9f9; }.single-question button.unknown b { color: #6d6266; background: #f0ecec; }.single-question button.unknown.selected { border-style: solid; border-color: #9c858a; background: #f5f1f1; box-shadow: inset 4px 0 #817075, 0 12px 30px #3d30330d; }
.honest-answer-note { width: min(100%, 760px); margin: 0 auto; padding: 11px 14px; border: 1px solid var(--line); border-radius: 10px; color: var(--muted); background: var(--surface-muted); font-size: 12px; line-height: 1.7; }.reassessment-gate > header { display: flex; align-items: center; justify-content: space-between; }.reassessment-gate > header .text-button { border: 0; color: #8c777c; background: transparent; text-decoration: underline; text-underline-offset: 3px; }
.assessment-progress { width: min(100%, 760px); display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 8px 15px; margin: 2px auto 0; padding-top: 16px; border-top: 1px solid #eee5e6; }.assessment-progress div { display: flex; justify-content: space-between; grid-column: 1 / -1; color: #786d71; font-size: 12px; }.assessment-progress div b { color: #ae1b34; font-size: 12px; }.assessment-progress > i { height: 7px; overflow: hidden; border-radius: 99px; background: #eee7e8; }.assessment-progress > i span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #be1732, #ef7182); }.assessment-progress > small { color: #807579; font-size: 12px; }
.assessment-result-screen > header b { color: #3b8c60; font: 800 18px Consolas; }.result-celebration { text-align: center; }.result-celebration i { width: 54px; height: 54px; display: grid; place-items: center; margin: 0 auto 15px; border-radius: 50%; color: #fff; background: #3d9867; box-shadow: 0 0 0 10px #3d986712; font-style: normal; }.result-celebration p { margin: 0 0 5px; color: #478461; font-size: 12px; font-weight: 800; }.result-celebration h2 { margin: 0; font-size: clamp(28px, 4vw, 44px); }.result-celebration > span { display: block; max-width: 650px; margin: 12px auto 0; color: #776b6f; font-size: 12px; line-height: 1.75; }.result-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }.result-summary article { padding: 17px; border: 1px solid #e9e1e2; border-radius: 13px; background: #fff; }.result-summary small, .result-summary strong { display: block; }.result-summary small { color: #998e91; font-size: 12px; }.result-summary strong { margin-top: 8px; font-size: 15px; }.assessment-result-screen > section:not(.planning-studio) { padding: 20px; border-radius: 15px; background: #f8f6f6; }.assessment-result-screen > section:not(.planning-studio) h3 { margin: 0 0 7px; }.assessment-result-screen > section:not(.planning-studio) > p { color: #74696d; font-size: 12px; }.assessment-result-screen > section:not(.planning-studio) > div { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }.assessment-result-screen > section:not(.planning-studio) span { display: grid; gap: 4px; padding: 11px; border-radius: 9px; color: #655c5f; background: #fff; font-size: 12px; }.assessment-result-screen > section:not(.planning-studio) span b { color: #a21b32; font-size: 12px; }.assessment-result-screen > footer { display: flex; justify-content: flex-end; gap: 10px; }
.result-summary article > em { display: block; margin-top: 6px; color: #8a7277; font-size: 12px; font-style: normal; line-height: 1.5; }
.generic-mode-banner { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 15px; border: 1px solid #efd8b8; border-radius: 12px; color: #735b36; background: #fffaf0; }.generic-mode-banner b, .generic-mode-banner span { display: block; }.generic-mode-banner b { font-size: 12px; }.generic-mode-banner span { margin-top: 3px; color: #907b5c; font-size: 12px; }.generic-mode-banner button { padding: 8px 11px; border: 1px solid #dfc49d; border-radius: 8px; color: #76531e; background: #fff; font-size: 12px; font-weight: 800; }
.assessment-result-screen > .planning-studio, .returning-planner-gate .planning-studio { display: grid; gap: 15px; padding: 22px; border: 1px solid #e6d8db; border-radius: 18px; background: linear-gradient(145deg, #fff, #fff8f7); }.returning-planner-gate { min-height: 650px; display: grid; align-content: start; gap: 22px; padding: clamp(28px, 5vw, 56px); border: 1px solid #e8dfe1; border-radius: 28px; background: radial-gradient(circle at 90% 8%, #ffe8e6, transparent 28%), #fff; box-shadow: 0 26px 75px #5513220e; }.returning-planner-gate > header { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding-bottom: 20px; border-bottom: 1px solid #eee4e5; }.returning-planner-gate > header span { color: #b4233b; font: 800 12px Consolas; letter-spacing: .15em; }.returning-planner-gate > header h2 { margin: 8px 0; font-size: clamp(27px, 3.6vw, 42px); }.returning-planner-gate > header p { margin: 0; color: #766a6e; font-size: 12px; }.returning-planner-gate > footer { display: flex; justify-content: flex-end; gap: 10px; }.returning-planner-gate > footer .secondary { padding: 11px 15px; border: 1px solid #e2d3d5; border-radius: 9px; color: #786c70; background: #fff; font-size: 12px; }.planning-studio > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }.planning-studio > header span { color: #b4233b; font: 800 12px Consolas; letter-spacing: .14em; }.planning-studio > header h3 { margin: 6px 0; font-size: 18px; }.planning-studio > header p { margin: 0; color: #827579; font-size: 12px; }.suggestion-button { padding: 8px 11px; border: 1px solid #dab7bd; border-radius: 8px; color: #9f2337; background: #fff; font-size: 12px; white-space: nowrap; }.plan-mode-switch { display: flex; gap: 4px; padding: 3px; border: 1px solid #eadcde; border-radius: 9px; background: #f7f1f2; }.plan-mode-switch button { padding: 6px 11px; border: 0; border-radius: 7px; color: #8b7d81; background: transparent; font-size: 12px; font-weight: 800; }.plan-mode-switch button.active { color: #9d1c32; background: #fff; box-shadow: 0 2px 8px #4e10200f; }.plan-simple-note { margin: 0; padding: 9px 12px; border-radius: 9px; color: #5f7165; background: #f1f8f3; font-size: 12px; line-height: 1.6; }.preference-grid { display: grid; grid-template-columns: 150px 150px minmax(260px, 1fr); gap: 10px; }.preference-grid label { position: relative; display: grid; gap: 6px; color: #76696e; font-size: 12px; font-weight: 800; }.preference-grid input { min-width: 0; padding: 10px 12px; border: 1px solid #e2d5d7; border-radius: 9px; background: #fff; outline: none; }.preference-grid label > span { position: absolute; right: 10px; bottom: 11px; color: #9d9194; font-size: 12px; }.preference-grid input:focus { border-color: #c85b6c; box-shadow: 0 0 0 3px #c5163210; }.mode-picker { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; }.mode-picker > span { margin-right: 4px; color: #897b80; font-size: 12px; }.mode-picker button { padding: 7px 10px; border: 1px solid #e5dbdc; border-radius: 99px; color: #7c6f73; background: #fff; font-size: 12px; }.mode-picker button.active { color: #a51b32; border-color: #d58a96; background: #fff1f3; box-shadow: inset 0 0 0 1px #d58a9625; }.build-plan { justify-self: end; }.planning-studio .plan-result { padding: 15px 16px 28px; }.session-preview { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 15px; border: 1px solid #d7e6dc; border-radius: 12px; background: #f6fbf7; }.session-preview small, .session-preview b, .session-preview span { display: block; }.session-preview small { color: #5d8a6d; font-size: 12px; font-weight: 800; }.session-preview b { margin: 4px 0; font-size: 12px; }.session-preview span { color: #6f7f75; font-size: 12px; }.session-preview > strong { color: #3e7855; font-size: 12px; white-space: nowrap; }
.classroom-layout > .teacher-lecture-card { grid-column: 1 / -1; display: grid; grid-template-columns: auto 1fr; gap: 15px; padding: 19px 22px; border-bottom: 1px solid #eadcdd; background: linear-gradient(105deg, #fff8f7, #fff 58%); }.teacher-portrait { display: grid; justify-items: center; align-content: center; gap: 5px; }.teacher-portrait i { width: 54px; height: 54px; display: grid; place-items: center; border-radius: 16px; color: #fff; background: linear-gradient(145deg, #cf203c, #901026); box-shadow: 0 9px 22px #8d10282c; font: normal 800 18px serif; }.teacher-portrait span { color: #9e7d84; font-size: 12px; }.teacher-lecture-card > div:last-child { min-width: 0; }.teacher-lecture-card header { display: flex; align-items: center; gap: 12px; }.teacher-lecture-card header span { color: #b4233b; font-size: 12px; font-weight: 800; }.teacher-lecture-card header b { color: #8c7b80; font-size: 12px; font-weight: 600; }.teacher-lecture-card :deep(.safe-markdown) { margin-top: 8px; color: #3d3337; font-size: 13px; line-height: 1.85; }.teacher-lecture-card footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; padding-top: 9px; border-top: 1px dashed #eadcdd; }.teacher-lecture-card footer span { color: #998b90; font-size: 12px; }.teacher-lecture-card footer button { padding: 7px 10px; border: 1px solid #d9aeb5; border-radius: 8px; color: #9f1d33; background: #fff; font-size: 12px; font-weight: 800; }
.teacher-question { margin: 9px 0 0; padding: 8px 10px; border: 1px solid var(--accent); border-radius: 8px; color: var(--accent-ink); background: var(--accent-pale); font-size: 12px; line-height: 1.6; }
.conversation-dock > header small { display: block; max-width: 260px; margin-top: 4px; color: #9b8e92; font-size: 12px; line-height: 1.5; }.discussion-prompts { display: flex; flex-wrap: wrap; gap: 5px; padding: 9px 12px; border-bottom: 1px solid #eee2e0; background: #fffaf8; }.discussion-prompts button { padding: 6px 8px; border: 1px solid #ead9d8; border-radius: 99px; color: #8a515b; background: #fff; font-size: 12px; }.discussion-prompts button:hover { color: #a3142d; border-color: #d79aa4; }.discussion-empty { display: grid; place-items: center; align-content: center; min-height: 150px; padding: 26px; color: #8d7f84; text-align: center; }.discussion-empty b { color: #675b5f; font-size: 12px; }.discussion-empty span { max-width: 270px; margin-top: 8px; font-size: 12px; line-height: 1.7; }.role-pills .teacher-pill { color: #a21c32; border-color: #d8a6ae; background: #fff4f5; font-weight: 800; }
.self-profile-card { display: grid; gap: 12px; width: min(100%, 860px); margin: 4px auto 18px; padding: 18px; border: 1px solid #e8dcde; border-radius: 16px; background: #fffdfc; box-shadow: 0 14px 35px #54101f08; }.self-profile-card > header { display: flex; justify-content: space-between; gap: 16px; }.self-profile-card > header b, .self-profile-card > header span { display: block; }.self-profile-card > header b { font-size: 14px; }.self-profile-card > header span { margin-top: 5px; color: #7f7277; font-size: 12px; line-height: 1.55; }.self-profile-card > header small { color: #a09397; font-size: 12px; white-space: nowrap; }.self-profile-presets { display: flex; flex-wrap: wrap; gap: 7px; }.self-profile-presets button { padding: 7px 10px; border: 1px solid #e5d7d9; border-radius: 99px; color: #885560; background: #fff; font-size: 12px; }.self-profile-card > textarea, .self-profile-inline textarea { width: 100%; padding: 12px 14px; resize: vertical; border: 1px solid #dfd2d5; border-radius: 11px; color: #443b3e; background: #fff; font: 12px/1.75 inherit; outline: none; }.self-profile-card > textarea:focus, .self-profile-inline textarea:focus { border-color: #c96676; box-shadow: 0 0 0 3px #c5163210; }.self-profile-card > footer { display: flex; align-items: center; justify-content: space-between; gap: 14px; }.self-profile-card > footer span { color: #75686d; font-size: 12px; line-height: 1.5; }.self-profile-card > footer button, .self-profile-inline > button { padding: 9px 12px; border: 1px solid #d49aa4; border-radius: 9px; color: #9d1c32; background: #fff; font-size: 12px; font-weight: 800; white-space: nowrap; }.self-profile-card button:disabled, .self-profile-inline button:disabled { opacity: .45; }.self-profile-result { display: grid; grid-template-columns: 150px 1fr; gap: 10px 16px; padding: 13px 14px; border-radius: 11px; color: #476b56; background: #f1f8f3; }.self-profile-result small, .self-profile-result b { display: block; }.self-profile-result div small { font-size: 12px; }.self-profile-result div b { margin-top: 4px; color: #315d43; font-size: 12px; }.self-profile-result p { margin: 0; font-size: 12px; line-height: 1.7; }.self-profile-result > small { grid-column: 1 / -1; color: #6e8a78; font-size: 12px; }
.self-profile-inline { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 10px; padding: 13px; border: 1px solid #eadfe0; border-radius: 12px; background: #fffdfc; }.self-profile-inline label { display: grid; gap: 6px; color: #75696d; font-size: 12px; font-weight: 800; }.self-profile-inline > div { grid-column: 1 / -1; display: grid; gap: 4px; padding: 10px 12px; border-radius: 9px; background: #f2f8f4; }.self-profile-inline > div b { color: #386448; font-size: 12px; }.self-profile-inline > div span { color: #627469; font-size: 12px; line-height: 1.55; }
.self-profile-card > textarea::placeholder, .self-profile-inline textarea::placeholder { color: #a89ca0; opacity: .64; }
.plan-progress { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 11px; border: 1px solid #eadfe1; border-radius: 11px; background: #fffafa; }.plan-progress span { display: flex; align-items: center; gap: 7px; color: #9a8e92; font-size: 12px; }.plan-progress i { width: 20px; height: 20px; display: grid; flex: 0 0 auto; place-items: center; border-radius: 50%; color: #9e8f93; background: #eee7e8; font-style: normal; font-weight: 800; }.plan-progress span.active { color: #a11c33; font-weight: 800; }.plan-progress span.active i { color: #fff; background: #bd1a34; box-shadow: 0 0 0 4px #bd1a3412; }.plan-progress span.done { color: #477158; }.plan-progress span.done i { color: #fff; background: #4e8b65; }
.self-profile-details { overflow: hidden; border: 1px solid #e9dfe0; border-radius: 11px; background: #fff; }.self-profile-details summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; color: #76696d; cursor: pointer; font-size: 12px; }.self-profile-details summary b { color: #a12338; }.self-profile-details[open] summary { border-bottom: 1px solid #eee4e5; background: #fff9f8; }.self-profile-details .self-profile-inline { border: 0; border-radius: 0; }
.lesson-masthead aside button { grid-column: 1 / -1; justify-self: end; padding: 0; border: 0; color: #9e5763; background: transparent; font-size: 12px; text-decoration: underline; }.progress-explanation { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 14px 42px 14px 14px; border: 1px solid #e6dadd; border-radius: 14px; background: #fff; box-shadow: 0 12px 35px #4c0f1b0a; }.progress-explanation article { padding: 12px; border-radius: 10px; background: #faf7f7; }.progress-explanation b { color: #8f1c31; font-size: 12px; }.progress-explanation p { margin: 6px 0; color: #665b5f; font-size: 12px; line-height: 1.65; }.progress-explanation small { color: #8c7f83; font-size: 12px; }.progress-explanation > button { position: absolute; top: 9px; right: 12px; border: 0; color: #9b8c90; background: transparent; font-size: 18px; }.profile-chip { border: 0; text-align: left; } button.profile-chip { cursor: pointer; }
.smart-board .board-explanation { margin: 10px 0; color: #f1e9e0; font-size: 12px; line-height: 1.85; }.board-trace { display: grid; gap: 5px; margin-top: 11px; padding-top: 10px; border-top: 1px solid #ffffff24; }.board-trace b { color: #f6caa2; font-size: 12px; }.board-trace span { position: relative; padding-left: 14px; color: #dfd5cc; font: 12px/1.65 Consolas, monospace; }.board-trace span::before { content: "→"; position: absolute; left: 0; color: #ef9e74; }.board-mistakes { display: grid; gap: 5px; margin-top: 11px; padding: 10px 12px; border: 1px solid #f3b58745; border-radius: 8px; background: #552f213d; }.board-mistakes b { color: #ffd2ae; font-size: 12px; }.board-mistakes span { color: #f1d9cb; font-size: 12px; line-height: 1.55; }.board-mistakes span::before { content: "!"; display: inline-grid; width: 14px; height: 14px; margin-right: 7px; place-items: center; border-radius: 50%; color: #40251c; background: #f0bd82; font-weight: 900; }.board-code-example { position: relative; }.board-code-example .code-expand { position: absolute; top: -2px; right: 0; padding: 3px 10px; border: 1px solid #ffffff2e; border-radius: 999px; color: #e4c999; background: #ffffff10; font-size: 12px; cursor: pointer; }.board-code-example .code-expand:hover { background: #ffffff1c; }.board-code-example pre { max-height: 210px; overflow: auto; }.board-code-example.expanded pre { max-height: none; overflow: visible; white-space: pre-wrap; word-break: break-word; }
.scope-notice { display: flex; align-items: flex-start; gap: 7px; margin: 7px 0 9px; padding: 8px 10px; border: 1px solid #e8cf9c; border-radius: 9px; background: #fff9ec; color: #765c2b; font-size: 12px; line-height: 1.55; }.scope-notice > b { flex: 0 0 auto; color: #a06017; font-size: 12px; letter-spacing: .04em; }.scope-notice.compact { margin: 5px 0 7px; padding: 6px 8px; }
@media (max-width: 760px) { .assessment-gate, .assessment-result-screen { min-height: 600px; padding: 24px 18px; }.assessment-welcome { grid-template-columns: 1fr; gap: 24px; }.assessment-gate > header, .assessment-result-screen > header, .generic-mode-banner { align-items: flex-start; flex-direction: column; }.result-summary, .assessment-result-screen > section:not(.planning-studio) > div { grid-template-columns: 1fr 1fr; }.assessment-navigation { flex-wrap: wrap; }.assessment-navigation > span { width: 100%; order: -1; } }
@media (max-width: 760px) { .returning-planner-gate { padding: 24px 18px; }.returning-planner-gate > header, .planning-studio > header { align-items: flex-start; flex-direction: column; }.preference-grid, .self-profile-result, .progress-explanation, .plan-progress { grid-template-columns: 1fr; }.self-profile-card > footer, .self-profile-inline { align-items: stretch; grid-template-columns: 1fr; flex-direction: column; }.self-profile-inline > div { grid-column: auto; }.classroom-layout > .teacher-lecture-card { grid-template-columns: 1fr; }.teacher-portrait { justify-items: start; }.teacher-lecture-card footer { align-items: flex-start; flex-direction: column; } }
.desk-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.diagnostic-analysis { display: grid; gap: 13px; padding: 18px; border: 1px solid #e4d8da; border-radius: 15px; background: #fff; }
.diagnostic-analysis > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }.diagnostic-analysis > header b { color: #a21b32; font-size: 13px; }.diagnostic-analysis > header p { margin: 6px 0 0; color: #6f6367; font-size: 12px; }.diagnostic-analysis > header > span { padding: 7px 10px; border-radius: 99px; color: #37684a; background: #eef7f1; font-size: 12px; white-space: nowrap; }
.gap-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }.gap-list article { padding: 12px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-pale); }.gap-list b, .gap-list span { display: block; font-size: 12px; }.gap-list span { margin-top: 5px; color: var(--accent-ink); font-weight: 800; }.gap-list p { margin: 7px 0 0; color: var(--muted); font-size: 12px; line-height: 1.6; }
.block-list { display: flex; flex-wrap: wrap; gap: 7px; }.block-list span { display: grid; gap: 4px; padding: 9px 11px; border: 1px solid #e8dfe0; border-radius: 9px; color: #796d71; background: #fbf9f9; font-size: 12px; }.block-list b { color: #4a3e42; font-size: 12px; }.diagnostic-analysis > small { color: #8d8084; font-size: 12px; line-height: 1.6; }
.focus-toolbar { position: sticky; z-index: 20; top: 10px; display: grid; grid-template-columns: auto auto 1fr auto; align-items: center; gap: 14px; padding: 11px 13px; border: 1px solid #e5d7d9; border-radius: 14px; background: #fffefdf2; box-shadow: 0 12px 34px #45101c12; backdrop-filter: blur(14px); }.focus-toolbar > div:first-child b, .focus-toolbar > div:first-child span { display: block; }.focus-toolbar > div:first-child b { font-size: 12px; }.focus-toolbar > div:first-child span { margin-top: 2px; color: #918488; font-size: 12px; }.focus-toolbar select { display: none; padding: 8px; border: 1px solid #dfd2d4; border-radius: 8px; background: #fff; }.focus-view-buttons { display: flex; justify-self: center; gap: 5px; padding: 4px; border-radius: 10px; background: #f4eff0; }.focus-view-buttons button { padding: 7px 12px; border: 0; border-radius: 7px; color: #75696d; background: transparent; font-size: 12px; }.focus-view-buttons button.active { color: #9f1730; background: #fff; box-shadow: 0 3px 10px #4e10200d; font-weight: 800; }.exit-class { padding: 7px 10px; border: 1px solid #e2cfd2; border-radius: 8px; color: #8d5660; background: #fff; font-size: 12px; }
.classroom-layout.integrated-learning .conversation-dock { min-width: 0; }.classroom-layout.integrated-learning .message-list { min-height: 300px; }
.lesson-materials { min-height: 620px; display: grid; grid-template-columns: 290px minmax(0, 1fr); overflow: hidden; border: 1px solid #e5d9da; border-radius: 22px; background: #fff; box-shadow: 0 18px 55px #40101b0a; }.lesson-materials > aside { display: grid; align-content: start; gap: 7px; padding: 18px; border-right: 1px solid #eee4e5; background: #fbf8f8; }.lesson-materials aside header { margin-bottom: 7px; }.lesson-materials aside header b, .lesson-materials aside header span { display: block; }.lesson-materials aside header b { font-size: 13px; }.lesson-materials aside header span { margin-top: 4px; color: #928589; font-size: 12px; }.lesson-materials aside button { display: grid; gap: 4px; padding: 11px; border: 1px solid transparent; border-radius: 10px; color: #5f5558; background: transparent; text-align: left; }.lesson-materials aside button small { color: #a62a3e; font: 12px Consolas; }.lesson-materials aside button b { font-size: 12px; }.lesson-materials aside button span { color: #887b7f; font-size: 12px; line-height: 1.5; }.lesson-materials aside button.active { border-color: #dfbcc2; background: #fff; box-shadow: inset 3px 0 #bd1b35; }.lesson-materials > article { padding: clamp(24px, 4vw, 52px); }.lesson-materials article header span { color: #a3263b; font-size: 12px; }.lesson-materials article h2 { margin: 8px 0 20px; font-size: 28px; }.lesson-materials article > p { color: #5d5256; font-size: 13px; line-height: 1.9; }.lesson-materials article section { margin-top: 22px; padding-top: 18px; border-top: 1px solid #eee5e6; }.lesson-materials article li { margin: 8px 0; color: #655b5e; font-size: 12px; line-height: 1.7; }.lesson-materials pre { max-height: 240px; padding: 16px; overflow: auto; border-radius: 11px; color: #f8ebdf; background: #1d2c29; }.lesson-materials pre.expanded { max-height: none; overflow: visible; white-space: pre-wrap; word-break: break-word; }.lesson-materials .code-heading { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }.lesson-materials .code-heading b { color: #a3263b; font-size: 12px; }.lesson-materials .code-expand { padding: 4px 11px; border: 1px solid #ead9d8; border-radius: 999px; color: #8a515b; background: #fff; font-size: 12px; cursor: pointer; }.lesson-materials article > small { display: block; margin-top: 24px; color: #9b8f92; font-size: 12px; text-align: right; }
.code-standby, .paused-classroom { min-height: 500px; display: grid; place-items: center; align-content: center; gap: 12px; padding: 30px; border: 1px solid #e6dbdc; border-radius: 22px; background: #fff; text-align: center; }.code-standby b, .paused-classroom h2 { margin: 0; font-size: 24px; }.code-standby p, .paused-classroom p { max-width: 620px; margin: 0; color: #786c70; font-size: 12px; line-height: 1.75; }.code-standby .secondary { padding: 9px 13px; border: 1px solid #dfd2d4; border-radius: 8px; background: #fff; }.paused-classroom > span { color: #a22037; font-size: 12px; font-weight: 800; }
.class-exit-backdrop { position: fixed; z-index: 100; inset: 0; display: grid; place-items: center; padding: 20px; background: #24131880; backdrop-filter: blur(6px); }.class-exit-backdrop > section { width: min(100%, 560px); padding: 26px; border-radius: 20px; background: #fff; box-shadow: 0 30px 90px #16060a40; }.class-exit-backdrop > section > span { color: #a82239; font-size: 12px; font-weight: 800; }.class-exit-backdrop h2 { margin: 7px 0; font-size: 25px; }.class-exit-backdrop p { color: #776a6e; font-size: 12px; }.class-exit-backdrop section > div { display: grid; gap: 9px; margin: 20px 0; }.class-exit-backdrop section > div button { display: grid; gap: 4px; padding: 13px; border: 1px solid #e7dcde; border-radius: 11px; color: #493e42; background: #fff; text-align: left; }.class-exit-backdrop section > div button:hover { border-color: #d49ba5; background: #fff8f8; }.class-exit-backdrop section > div button b { font-size: 12px; }.class-exit-backdrop section > div button span { color: #8b7e82; font-size: 12px; }.class-exit-backdrop footer { text-align: right; }.class-exit-backdrop footer button { padding: 9px 12px; border: 0; border-radius: 8px; color: #fff; background: #ad1931; }
@media (max-width: 760px) { .diagnostic-analysis > header { flex-direction: column; }.gap-list { grid-template-columns: 1fr; }.focus-toolbar { grid-template-columns: 1fr auto auto; }.focus-toolbar select { display: block; }.focus-view-buttons { display: none; }.lesson-materials { grid-template-columns: 1fr; }.lesson-materials > aside { border-right: 0; border-bottom: 1px solid #eee4e5; }.lesson-materials > aside button { display: none; }.lesson-materials > aside button.active { display: grid; }.global-action-feedback { right: 16px; bottom: 16px; } }

/* Appearance tokens own every instructional surface; outcome colors stay semantic. */
.classroom-sync-notice { display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; padding:12px; border:1px solid var(--line); border-radius:8px; color:var(--muted); background:var(--surface-muted); font-size:13px; }
.classroom-sync-notice button { padding:8px 12px; min-height:44px; border:1px solid var(--line); border-radius:6px; color:var(--accent-ink); background:var(--surface-raised); }
.conversation-dock .dialogue-error { margin:8px 0; padding:10px 12px; border:1px solid var(--danger); border-radius:8px; color:var(--danger); background:var(--surface-raised); font-size:13px; line-height:1.6; }
.immersive-lesson { color: var(--ink); }
:is(
  .classroom-loading,.lesson-masthead,.lesson-steps > button,.learning-copilot,
  .assessment-gate,.assessment-result-screen,.returning-planner-gate,.planning-studio,
  .self-profile-card,.self-profile-inline,.diagnostic-analysis,.baseline-panel,
  .conversation-dock,.conversation-dock > footer,.lesson-action,.ready-card,
  .lesson-materials,.code-standby,.paused-classroom,.progress-explanation,
  .focus-toolbar,.teacher-lecture-card,.class-exit-backdrop > section,
  .global-action-feedback
) { color: var(--ink); border-color: var(--line); background: var(--surface-raised); box-shadow: none; }
.classroom-loading i { border-color: var(--line); border-top-color: var(--accent); }
:is(
  .lesson-history-actions button,.message-list article > div,.role-pills button,
  .discussion-prompts button,.single-question button,.checkpoint-options button,
  .mode-picker button,.suggestion-button,.self-profile-presets button,
  .plan-mode-switch,.plan-mode-switch button,.plan-progress,.progress-explanation article,
  .result-summary article,.assessment-result-screen > section:not(.planning-studio),
  .assessment-result-screen > section:not(.planning-studio) span,
  .self-profile-details,.block-list span,.focus-view-buttons,.focus-view-buttons button,
  .exit-class,.lesson-materials aside button,.class-exit-backdrop section > div button
) { color: var(--ink); border-color: var(--line); background: var(--surface-muted); box-shadow: none; }
:is(
  .classroom-loading span,.lesson-history-actions span,.message-list article p,
  .conversation-dock > header small,.discussion-empty,.discussion-empty span,
  .assessment-welcome p,.single-question button span,.result-summary small,
  .assessment-result-screen > section:not(.planning-studio) > p,
  .planning-studio > header p,.returning-planner-gate > header p,
  .preference-grid label,.mode-picker > span,.plan-progress span,
  .progress-explanation p,.progress-explanation small,.focus-toolbar > div:first-child span
) { color: var(--muted); }
:is(
  .lesson-masthead p,.lesson-masthead aside b,.conversation-dock header p,
  .message-list article b,.lesson-action header p,.single-question > header span,
  .single-question button b,.assessment-progress div b,.returning-planner-gate > header span,
  .planning-studio > header span,.self-profile-details summary b,.progress-explanation b,
  .diagnostic-analysis > header b,.lesson-materials aside button small,
  .lesson-materials article header span,.lesson-materials .code-heading b
) { color: var(--accent-ink); }
:is(
  .lesson-steps > button.active,.role-pills button.active,.single-question button.selected,
  .checkpoint-options button.selected,.mode-picker button.active,.plan-mode-switch button.active,
  .focus-view-buttons button.active,.lesson-materials aside button.active
) { color: var(--accent-ink); border-color: var(--accent); background: var(--accent-pale); box-shadow: inset 2px 0 var(--accent); }
.lesson-history-actions button:hover,
.discussion-prompts button:hover,
.single-question button:hover { color: var(--accent-ink); border-color: var(--accent); background: var(--accent-pale); }
.discussion-prompts { border-color: var(--line); background: var(--surface-muted); }
.message-list article.role-student > div { border-color: var(--accent); background: var(--accent-pale); }
.talk-composer textarea { color: var(--ink); border-color: var(--line); background: var(--surface-muted); }
.talk-composer textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb,var(--accent) 18%,transparent); }
.talk-composer button,
.teacher-portrait i,
.plan-progress span.active i,
.class-exit-backdrop footer button { color: var(--accent-contrast); background: var(--accent); box-shadow: none; }
.plan-progress span.active { color: var(--accent-ink); }
.assessment-progress > i { background: var(--surface-muted); }
.assessment-progress > i span { background: var(--accent); }
.progress-explanation > button { color: var(--muted); }
.lesson-materials > aside { border-color: var(--line); background: var(--surface-muted); }
.teacher-lecture-card :deep(.safe-markdown) { color: var(--ink); }
.teacher-question { color: var(--accent-ink); border-color: var(--accent); background: var(--accent-pale); }
.gap-list article { border-left-color: var(--accent); background: var(--accent-pale); }
.gap-list span { color: var(--accent-ink); }
.class-exit-backdrop section > div button:hover { border-color: var(--accent); background: var(--accent-pale); }
.global-action-feedback > i { background: var(--accent); box-shadow: 0 0 0 4px color-mix(in srgb,var(--accent) 14%,transparent); }
.global-action-feedback[data-tone="success"] > i { background: var(--green); box-shadow: 0 0 0 4px color-mix(in srgb,var(--green) 14%,transparent); }
.global-action-feedback[data-tone="warning"] { border-color: color-mix(in srgb,var(--warning) 58%,var(--line)); background: color-mix(in srgb,var(--warning) 8%,var(--surface-raised)); }
.global-action-feedback[data-tone="warning"] > i { background: var(--warning); box-shadow: 0 0 0 4px color-mix(in srgb,var(--warning) 14%,transparent); }
.global-action-feedback[data-tone="error"] { border-color: color-mix(in srgb,var(--danger) 64%,var(--line)); background: color-mix(in srgb,var(--danger) 8%,var(--surface-raised)); }
.global-action-feedback[data-tone="error"] > i { background: var(--danger); box-shadow: 0 0 0 4px color-mix(in srgb,var(--danger) 14%,transparent); }
</style>
