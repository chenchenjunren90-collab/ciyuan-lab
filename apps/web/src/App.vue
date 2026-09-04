<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import {
  ApiError, api, fetchApiHealth,
  type ActivityDetail, type ActivitySummary, type CourseId, type CourseSummary,
  type DiagnosticPhase, type DiagnosticQuiz, type DiagnosticSubmissionResult,
  type HintResponse, type KnowledgePoint, type KnowledgePointDetail, type LearnerProfile,
  type NextActivity, type PlanStage, type ProjectSubmissionResponse, type QaResponse,
  type GeneratedCodeProblem, type GeneratedProblemSubmissionResponse,
  type GeneratedScenarioProject, type ScenarioContext, type SubmissionResult
} from "./services/api";
import PythonFirstLesson from "./components/classroom/PythonFirstLesson.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import WelcomeExperience from "./components/WelcomeExperience.vue";
import {
  DEFAULT_UI_PREFERENCES,
  DISPLAY_NAME_KEY,
  STUDENT_ID_KEY,
  WELCOME_COMPLETE_KEY,
  applyUiPreferences,
  createLocalLearnerId,
  ensureLocalStudentId,
  loadLocalAccounts,
  loadUiPreferences,
  saveLocalAccounts,
  saveUiPreferences,
  type LocalLearnerAccount,
  type UiPreferences,
} from "./uiPreferences";

type Tab = "overview" | "path" | "tutor" | "practice" | "projects" | "classroom";
type ActivityFilter = "all" | "homework" | "code" | "debug" | "project";
type ActivitySort = "recommended" | "catalog" | "shortest";
type KnowledgeState = "mastered" | "learning" | "recommended" | "ready" | "locked" | "unassessed";
const PYTHON_KNOWLEDGE_CHAPTERS = [
  { key: "syntax", order: "01", title: "语言起步", description: "从表达式、变量与控制流建立可运行的程序思维。", prefixes: ["BASE"] },
  { key: "containers", order: "02", title: "数据与容器", description: "用字符串和常用容器组织、查询与转换数据。", prefixes: ["STR", "LIST", "TUPLE", "SET", "DICT", "CONTAINER"] },
  { key: "abstraction", order: "03", title: "函数与抽象", description: "把重复步骤封装成函数、迭代器和可复用模块。", prefixes: ["FUNC", "ITER", "MOD"] },
  { key: "reliability", order: "04", title: "文件与可靠性", description: "处理文件、异常和边界情况，让程序稳定完成任务。", prefixes: ["EXC", "FILE"] },
  { key: "design", order: "05", title: "对象与算法", description: "理解对象建模、复杂度和基本问题求解策略。", prefixes: ["OOP", "ALGO"] },
  { key: "application", order: "06", title: "数据应用", description: "把 Python 能力迁移到结构化数据分析和综合实践。", prefixes: ["DATA"] }
] as const;
const initialQueryTab = new URLSearchParams(window.location.search).get("tab");
const initialTab: Tab = initialQueryTab === "practice" || initialQueryTab === "projects"
  ? initialQueryTab
  : "classroom";
const systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
const systemPrefersDark = ref(systemThemeQuery.matches);
const uiPreferences = reactive<UiPreferences>(loadUiPreferences(localStorage));
const initialStudentId = ensureLocalStudentId(localStorage, () => (
  typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
));
const initialDisplayName = localStorage.getItem(DISPLAY_NAME_KEY)?.trim() || "新同学";
const localAccounts = ref<LocalLearnerAccount[]>(loadLocalAccounts(
  localStorage,
  initialStudentId,
  initialDisplayName,
));
const studentId = ref(initialStudentId);
const displayName = ref(
  localAccounts.value.find((account) => account.id === initialStudentId)?.displayName
    || initialDisplayName,
);
saveLocalAccounts(localStorage, localAccounts.value);
const welcomeOpen = ref(
  uiPreferences.welcomeOnLaunch || localStorage.getItem(WELCOME_COMPLETE_KEY) !== "true"
);
const settingsOpen = ref(false);
const accountSwitching = ref(false);
const connection = ref<"connecting" | "online" | "offline">("connecting");
const loading = ref(true);
const diagnosticSubmitting = ref(false);
const notice = ref("");
const tab = ref<Tab>(initialTab);
const courses = ref<CourseSummary[]>([]);
const courseId = ref<CourseId>("python");
const knowledge = ref<KnowledgePoint[]>([]);
const selectedKnowledge = ref<KnowledgePointDetail | null>(null);
const selectedHomework = ref<ActivitySummary | null>(null);
const activities = ref<ActivitySummary[]>([]);
const profile = ref<LearnerProfile | null>(null);
const next = ref<NextActivity | null>(null);
const stages = ref<PlanStage[]>([]);
const activity = ref<ActivityDetail | null>(null);
const diagnostic = ref<DiagnosticQuiz | null>(null);
const diagnosticPhase = ref<DiagnosticPhase>("initial");
const diagnosticAnswers = reactive<Record<string, string>>({});
const diagnosticResult = ref<DiagnosticSubmissionResult | null>(null);
const question = ref("数据清洗时应该如何处理缺失值和异常记录？");
const qa = ref<QaResponse | null>(null);
const qaLoading = ref(false);
const answer = ref("");
const code = ref("");
const submission = ref<SubmissionResult | null>(null);
const submitting = ref(false);
const scenario = ref<ScenarioContext | null>(null);
const generatedProject = ref<GeneratedScenarioProject | null>(null);
const projectGoal = ref("希望重点练习数据解析、异常处理、模块化设计和自动化测试");
const projectGenerating = ref(false);
const hint = ref<HintResponse | null>(null);
const hintLevel = ref<1 | 2 | 3>(1);
const projectSummary = ref("");
const projectRepository = ref("");
const projectTests = ref("");
const projectSubmission = ref<ProjectSubmissionResponse | null>(null);
const projectSubmitting = ref(false);
const knowledgeQuery = ref("");
const activityFilter = ref<ActivityFilter>("all");
const activitySort = ref<ActivitySort>("recommended");
const activityQuery = ref("");
const lastActivityId = ref("");
const practiceScaffoldLevel = ref(0);
const adaptiveProblem = ref<GeneratedCodeProblem | null>(null);
const adaptiveCode = ref("");
const adaptiveSubmission = ref<GeneratedProblemSubmissionResponse | null>(null);
const adaptiveAttemptIndex = ref(1);
const adaptiveLoading = ref(false);
const selectedKnowledgeLoading = ref(false);
const diagnosticSection = ref<HTMLElement | null>(null);
const knowledgeMapSection = ref<HTMLElement | null>(null);
const knowledgeDetailSection = ref<HTMLElement | null>(null);
const learnerContextResolved = ref(false);
const genericMode = ref(false);
const assessmentWarningOpen = ref(false);
const assessmentWarningDialog = ref<HTMLElement | null>(null);
const assessmentWarningPrimaryAction = ref<HTMLButtonElement | null>(null);
let assessmentWarningReturnFocus: HTMLElement | null = null;
const pendingLearningTab = ref<"classroom" | "practice" | "projects">("classroom");
const classroomFocusMode = ref(false);
const savedProjectIds = ref<string[]>([]);
const workedExampleExpanded = ref(false);

const greeting = computed(() => {
  const hour = new Date().getHours();
  const period = hour < 6 ? "夜深了" : hour < 11 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好";
  return `${period}，${displayName.value}`;
});

function syncSystemTheme(event: MediaQueryListEvent): void {
  systemPrefersDark.value = event.matches;
  applyUiPreferences(document.documentElement, uiPreferences, event.matches);
}

function updateUiPreferences(patch: Partial<UiPreferences>): void {
  Object.assign(uiPreferences, patch);
}

function updateDisplayName(value: string): void {
  displayName.value = value.slice(0, 20);
}

function createExperienceAccountId(): string {
  const seed = typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return createLocalLearnerId(seed);
}

async function switchLocalAccount(id: string): Promise<void> {
  const account = localAccounts.value.find((item) => item.id === id);
  if (!account || id === studentId.value || accountSwitching.value) return;
  accountSwitching.value = true;
  try {
    studentId.value = account.id;
    displayName.value = account.displayName;
    localStorage.setItem(STUDENT_ID_KEY, account.id);
    assessmentWarningOpen.value = false;
    classroomFocusMode.value = false;
    learnerContextResolved.value = false;
    genericMode.value = sessionStorage.getItem(genericModeKey()) === "true";
    await loadCourse(courseId.value);
    notice.value = `已切换到 ${account.displayName}，测评、课堂、练习与项目进度均为独立记录。`;
  } finally {
    accountSwitching.value = false;
  }
}

async function createExperienceAccount(): Promise<void> {
  if (accountSwitching.value) return;
  const account: LocalLearnerAccount = {
    id: createExperienceAccountId(),
    displayName: `体验同学 ${localAccounts.value.length + 1}`,
    createdAt: new Date().toISOString(),
  };
  localAccounts.value = [...localAccounts.value, account];
  saveLocalAccounts(localStorage, localAccounts.value);
  await switchLocalAccount(account.id);
}

function finishWelcome(value: string): void {
  updateDisplayName(value.trim() || "新同学");
  localStorage.setItem(WELCOME_COMPLETE_KEY, "true");
  welcomeOpen.value = false;
  settingsOpen.value = false;
  notice.value = `欢迎你，${displayName.value}。先完成能力摸底，我们再为你生成第一节课。`;
}

function replayWelcome(): void {
  settingsOpen.value = false;
  welcomeOpen.value = true;
}

function resetUiPreferences(): void {
  Object.assign(uiPreferences, DEFAULT_UI_PREFERENCES);
  notice.value = "界面外观已恢复默认设置。";
}

watch(uiPreferences, (value) => {
  saveUiPreferences(localStorage, value);
  applyUiPreferences(document.documentElement, value, systemPrefersDark.value);
}, { deep: true, immediate: true });

const viewportIsMobile = ref(window.innerWidth < 768);
function syncViewport(): void {
  viewportIsMobile.value = window.innerWidth < 768;
}
const resolvedDevice = computed(() => (
  uiPreferences.deviceMode === "auto"
    ? (viewportIsMobile.value ? "mobile" : "desktop")
    : uiPreferences.deviceMode
));
watch(resolvedDevice, (value) => {
  document.documentElement.dataset.deviceResolved = value;
}, { immediate: true });

watch(displayName, (value) => {
  const normalized = value.trim() || "新同学";
  localStorage.setItem(DISPLAY_NAME_KEY, normalized);
  localAccounts.value = localAccounts.value.map((account) => (
    account.id === studentId.value ? { ...account, displayName: normalized } : account
  ));
  saveLocalAccounts(localStorage, localAccounts.value);
});

let noticeTimer: ReturnType<typeof setTimeout> | undefined;
watch(notice, (value) => {
  if (noticeTimer) clearTimeout(noticeTimer);
  if (value) noticeTimer = setTimeout(() => { notice.value = ""; }, 5000);
});

const selectedCourse = computed(() => courses.value.find((item) => item.id === courseId.value));
const diagnosticComplete = computed(() => diagnostic.value?.items.every(
  (item) => Boolean(diagnosticAnswers[item.exercise_id])
) ?? false);
const masteryMap = computed(() => Object.fromEntries((profile.value?.mastery ?? []).map((item) => [item.knowledge_point_id, item])));
const averageMastery = computed(() => {
  const items = profile.value?.mastery ?? [];
  return items.length ? Math.round(items.reduce((sum, item) => sum + item.score, 0) / items.length * 100) : 0;
});
const masteredCount = computed(() => (profile.value?.mastery ?? []).filter((item) => item.score >= .6).length);
const knowledgeSubskillCount = computed(() => knowledge.value.reduce((sum, item) => sum + item.concepts.length, 0));
const knowledgePrerequisiteCount = computed(() => knowledge.value.reduce((sum, item) => sum + item.prerequisites.length, 0));
const knowledgeChapterCount = computed(() => courseId.value === "python"
  ? PYTHON_KNOWLEDGE_CHAPTERS.filter((chapter) => knowledge.value.some((item) => (
      (chapter.prefixes as readonly string[]).includes(knowledgePrefix(item.id))
    ))).length
  : knowledge.value.length ? 1 : 0
);
const filteredKnowledge = computed(() => {
  const query = knowledgeQuery.value.trim().toLowerCase();
  if (!query) return knowledge.value;
  return knowledge.value.filter((item) => `${item.id} ${item.title} ${item.concepts.join(" ")}`.toLowerCase().includes(query));
});
const knowledgeChapters = computed(() => {
  const visibleIds = new Set(filteredKnowledge.value.map((item) => item.id));
  const hasQuery = Boolean(knowledgeQuery.value.trim());
  const definitions = courseId.value === "python"
    ? PYTHON_KNOWLEDGE_CHAPTERS
    : [{
        key: "course", order: "01", title: selectedCourse.value?.title ?? "课程知识",
        description: "按照前置关系和学习证据逐步推进。",
        prefixes: [] as readonly string[]
      }];
  return definitions.map((definition) => {
    const prefixes = definition.prefixes as readonly string[];
    const allItems = knowledge.value
      .filter((item) => prefixes.length === 0 || prefixes.includes(knowledgePrefix(item.id)))
      .sort((left, right) => {
        const leftGroup = prefixes.indexOf(knowledgePrefix(left.id));
        const rightGroup = prefixes.indexOf(knowledgePrefix(right.id));
        return leftGroup - rightGroup || left.id.localeCompare(right.id);
      });
    return {
      ...definition,
      items: allItems.filter((item) => visibleIds.has(item.id)),
      total: allItems.length,
      mastered: allItems.filter((item) => (masteryScore(item.id) ?? 0) >= .6).length,
      subskills: allItems.reduce((sum, item) => sum + item.concepts.length, 0)
    };
  }).filter((chapter) => chapter.total > 0 && (!hasQuery || chapter.items.length > 0));
});
function activityRecommendationScore(item: ActivitySummary): number {
  let score = 0;
  if (next.value?.activity_type !== "concept" && next.value?.activity_id === item.id) score += 100;
  const evidence = item.concept_ids.map((id) => masteryScore(id));
  if (evidence.length) {
    score += evidence.reduce<number>((sum, value) => sum + (value === null ? .45 : 1 - value), 0) / evidence.length * 40;
  }
  if (item.learning_stage === "after_class") score += 8;
  if (item.difficulty === "beginner") score += averageMastery.value < 50 ? 8 : 2;
  if (item.difficulty === "intermediate") score += averageMastery.value >= 50 ? 8 : 1;
  return score;
}
const recommendedActivities = computed(() => activities.value
  .filter((item) => item.type !== "project")
  .sort((left, right) => activityRecommendationScore(right) - activityRecommendationScore(left)
    || left.estimated_minutes - right.estimated_minutes)
  .slice(0, 3));
const lastActivity = computed(() => activities.value.find((item) => item.id === lastActivityId.value) ?? null);
const filteredActivities = computed(() => {
  const query = activityQuery.value.trim().toLowerCase();
  let items = activities.value.filter((item) => {
    if (item.type === "project") return false;
    const matchesFilter = activityFilter.value === "all"
      || (activityFilter.value === "homework" && item.learning_stage === "after_class")
      || item.type === activityFilter.value;
    const matchesQuery = !query
      || `${item.id} ${item.title} ${item.concept_ids.join(" ")}`.toLowerCase().includes(query);
    return matchesFilter && matchesQuery;
  });
  if (activitySort.value === "shortest") {
    items = [...items].sort((left, right) => left.estimated_minutes - right.estimated_minutes || left.id.localeCompare(right.id));
  } else if (activitySort.value === "catalog") {
    items = [...items].sort((left, right) => left.id.localeCompare(right.id));
  } else {
    items = [...items].sort((left, right) => activityRecommendationScore(right) - activityRecommendationScore(left)
      || left.estimated_minutes - right.estimated_minutes);
  }
  return items;
});
const projectActivities = computed(() => activities.value.filter((item) => item.type === "project"));
const stageProjectOrder = [
  "PY-PROJ-STAGE-CONTROL-01",
  "PY-PROJ-STAGE-CONTAINER-01",
  "PY-PROJ-STAGE-RELIABLE-01",
];
const stageProjects = computed(() => projectActivities.value
  .filter((item) => item.id.startsWith("PY-PROJ-STAGE-"))
  .sort((left, right) => stageProjectOrder.indexOf(left.id) - stageProjectOrder.indexOf(right.id)));
const comprehensiveProjects = computed(() => projectActivities.value.filter((item) => !item.id.startsWith("PY-PROJ-STAGE-")));
const savedProjects = computed(() => savedProjectIds.value
  .map((id) => projectActivities.value.find((item) => item.id === id))
  .filter((item): item is ActivitySummary => Boolean(item)));

function projectReadiness(item: ActivitySummary): { ready: boolean; completed: number; total: number } {
  const completed = item.concept_ids.filter((id) => (masteryScore(id) ?? 0) >= .6).length;
  return { ready: item.concept_ids.length > 0 && completed === item.concept_ids.length, completed, total: item.concept_ids.length };
}

function practiceHistoryKey(): string {
  return `ciyuan-last-activity:${studentId.value}:${courseId.value}`;
}

function projectIndexKey(): string {
  return `ciyuan-project-index:${studentId.value}:${courseId.value}`;
}

function projectDraftKey(projectId: string): string {
  return `ciyuan-project-draft:${studentId.value}:${courseId.value}:${projectId}`;
}

function rememberProject(projectId: string): void {
  savedProjectIds.value = [...new Set([projectId, ...savedProjectIds.value])];
  localStorage.setItem(projectIndexKey(), JSON.stringify(savedProjectIds.value));
}

function restoreProjectWorkspace(projectId: string): void {
  try {
    const raw = localStorage.getItem(projectDraftKey(projectId));
    if (!raw) return;
    const draft = JSON.parse(raw) as {
      summary?: string; repository?: string; tests?: string; goal?: string;
    };
    projectSummary.value = draft.summary ?? "";
    projectRepository.value = draft.repository ?? "";
    projectTests.value = draft.tests ?? "";
    projectGoal.value = draft.goal ?? projectGoal.value;
  } catch {
    localStorage.removeItem(projectDraftKey(projectId));
  }
}

function persistProjectWorkspace(): void {
  if (!activity.value || activity.value.type !== "project") return;
  localStorage.setItem(projectDraftKey(activity.value.id), JSON.stringify({
    summary: projectSummary.value,
    repository: projectRepository.value,
    tests: projectTests.value,
    goal: projectGoal.value,
  }));
  rememberProject(activity.value.id);
}

function restorePracticeHistory(): void {
  lastActivityId.value = localStorage.getItem(practiceHistoryKey()) ?? "";
  try {
    savedProjectIds.value = JSON.parse(localStorage.getItem(projectIndexKey()) ?? "[]") as string[];
  } catch {
    savedProjectIds.value = [];
  }
}

watch([projectSummary, projectRepository, projectTests, projectGoal], persistProjectWorkspace);

function fail(error: unknown): void {
  notice.value = error instanceof ApiError && error.status === 500
    ? "学情数据库尚未启动：当前可浏览课程与沉浸课堂，画像更新和代码判题暂不可用。"
    : error instanceof Error ? error.message : "操作失败，请稍后重试";
}
function openClassroom(): void {
  if (courseId.value === "python" && !learnerContextResolved.value) {
    notice.value = "正在读取能力画像，请稍后再进入课堂。";
    return;
  }
  if (courseId.value === "python" && learnerContextResolved.value && !profile.value && !genericMode.value) {
    pendingLearningTab.value = "classroom";
    assessmentWarningOpen.value = true;
    return;
  }
  notice.value = "";
  tab.value = courseId.value === "python" ? "classroom" : "overview";
}
function onClassroomFocusChanged(active: boolean): void {
  classroomFocusMode.value = active;
  notice.value = active ? "已进入专注课堂；可从课堂顶部切换听课、交流、代码和资料。" : "课堂已暂停，学习进度已经保存。";
}
function openPractice(): void {
  if (courseId.value === "python" && !learnerContextResolved.value) {
    notice.value = "正在读取能力画像；评估完成前暂不进入个性化练习。";
    return;
  }
  if (courseId.value === "python" && learnerContextResolved.value && !profile.value && !genericMode.value) {
    pendingLearningTab.value = "practice";
    assessmentWarningOpen.value = true;
    return;
  }
  notice.value = "已进入练习工坊，可从题目列表或个性化挑战开始。";
  if (activity.value?.type === "project") activity.value = null;
  tab.value = "practice";
}
function openProjects(): void {
  if (courseId.value === "python" && !learnerContextResolved.value) {
    notice.value = "正在读取能力画像；稍后会显示每个项目的解锁依据。";
    return;
  }
  if (courseId.value === "python" && learnerContextResolved.value && !profile.value && !genericMode.value) {
    pendingLearningTab.value = "projects";
    assessmentWarningOpen.value = true;
    return;
  }
  notice.value = "已进入项目实战；可以预览全部项目，达到前置能力后开始挑战。";
  tab.value = "projects";
}
function genericModeKey(): string {
  return `ciyuan-generic-mode:${studentId.value}:python`;
}
function onProfileResolved(value: LearnerProfile | null): void {
  learnerContextResolved.value = true;
  profile.value = value;
  if (value) {
    genericMode.value = false;
    sessionStorage.removeItem(genericModeKey());
  }
}
function requestGenericMode(destination: "classroom" | "practice" | "projects" = "classroom"): void {
  pendingLearningTab.value = destination;
  assessmentWarningOpen.value = true;
}
function closeAssessmentWarning(): void {
  assessmentWarningOpen.value = false;
}
function handleAssessmentWarningKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    closeAssessmentWarning();
    return;
  }
  if (event.key !== "Tab" || !assessmentWarningDialog.value) return;
  const focusable = Array.from(
    assessmentWarningDialog.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
  if (!focusable.length) return;
  const first = focusable[0]!;
  const last = focusable[focusable.length - 1]!;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
function continueWithGenericCourse(): void {
  genericMode.value = true;
  sessionStorage.setItem(genericModeKey(), "true");
  assessmentWarningOpen.value = false;
  tab.value = pendingLearningTab.value;
  notice.value = "已进入通用课程模式；完成能力测评后可随时切换为个性化路线。";
}
function goToAssessment(): void {
  genericMode.value = false;
  sessionStorage.removeItem(genericModeKey());
  assessmentWarningOpen.value = false;
  tab.value = "classroom";
  notice.value = "已返回摸底测试，完成后将自动生成个性化第一课。";
}

watch(assessmentWarningOpen, async (open) => {
  if (open) {
    assessmentWarningReturnFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    await nextTick();
    assessmentWarningPrimaryAction.value?.focus();
    return;
  }
  await nextTick();
  if (assessmentWarningReturnFocus?.isConnected) assessmentWarningReturnFocus.focus();
  assessmentWarningReturnFocus = null;
});
async function startBaseline(): Promise<void> {
  if (!diagnostic.value) {
    notice.value = "能力诊断尚未载入，请稍后重试。";
    return;
  }
  notice.value = "能力基线已定位：请完成下方诊断题，提交后会立即更新画像。";
  await nextTick();
  diagnosticSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function openKnowledgeMap(): Promise<void> {
  tab.value = "overview";
  notice.value = "已打开课程知识地图；点击任一节点会自动定位到详细讲解。";
  await nextTick();
  knowledgeMapSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function rememberStudent(): Promise<void> {
  studentId.value = studentId.value.trim() || createExperienceAccountId();
  localStorage.setItem(STUDENT_ID_KEY, studentId.value);
  assessmentWarningOpen.value = false;
  learnerContextResolved.value = false;
  genericMode.value = sessionStorage.getItem(genericModeKey()) === "true";
  await loadCourse(courseId.value);
}
function difficulty(value: string): string {
  return ({ beginner: "入门", intermediate: "进阶", advanced: "挑战" } as Record<string, string>)[value] ?? value;
}
function activityType(value: string): string {
  return ({ concept: "知识学习", objective: "客观题", short_answer: "简答题", code: "编程题", debug: "Debug", project: "综合项目" } as Record<string, string>)[value] ?? value;
}
function masteryScore(id: string): number | null {
  return masteryMap.value[id]?.score ?? null;
}

function knowledgePrefix(id: string): string {
  return id.split("-")[1] ?? "OTHER";
}

function knowledgeState(item: KnowledgePoint): KnowledgeState {
  const score = masteryScore(item.id);
  if (score !== null && score >= .6) return "mastered";
  if (next.value?.activity_type === "concept" && next.value.activity_id === item.id) return "recommended";
  if (score !== null) return "learning";
  if (!profile.value) return "unassessed";
  const prerequisitesReady = item.prerequisites.every((id) => (masteryScore(id) ?? 0) >= .6);
  return prerequisitesReady ? "ready" : "locked";
}

function knowledgeStateLabel(item: KnowledgePoint): string {
  return ({
    mastered: "已掌握", learning: "学习中", recommended: "推荐下一步",
    ready: "可以开始", locked: "建议先学前置", unassessed: "等待评估"
  } as Record<KnowledgeState, string>)[knowledgeState(item)];
}

function knowledgeEvidenceText(item: KnowledgePoint): string {
  const score = masteryScore(item.id);
  if (score !== null) return `掌握度 ${Math.round(score * 100)}%`;
  if (!profile.value) return "完成摸底后生成个性化状态";
  const missing = item.prerequisites.filter((id) => (masteryScore(id) ?? 0) < .6);
  if (missing.length) return `建议先完成 ${missing.slice(0, 2).join("、")}${missing.length > 2 ? " 等" : ""}`;
  return item.prerequisites.length ? "前置知识已满足" : "可直接开始学习";
}

async function loadCourse(id: CourseId): Promise<void> {
  courseId.value = id;
  restorePracticeHistory();
  if (id === "python") {
    learnerContextResolved.value = false;
    profile.value = null;
    genericMode.value = sessionStorage.getItem(genericModeKey()) === "true";
  }
  if (tab.value !== "practice") tab.value = id === "python" ? "classroom" : "overview";
  loading.value = true;
  notice.value = "";
  qa.value = null;
  activity.value = null;
  selectedKnowledge.value = null;
  selectedHomework.value = null;
  scenario.value = null;
  generatedProject.value = null;
  submission.value = null;
  adaptiveProblem.value = null;
  adaptiveSubmission.value = null;
  adaptiveCode.value = "";
  adaptiveAttemptIndex.value = 1;
  try {
    const [kpResult, activityResult] = await Promise.all([api.knowledgePoints(id), api.activities(id)]);
    knowledge.value = kpResult.items;
    activities.value = activityResult;
    // The direct classroom preview can render its scripted lesson before the
    // persistence services are started. Code evidence and profile updates still
    // require the normal database-backed endpoints when the learner submits.
    if (id === "python" && tab.value === "classroom") {
      profile.value = null; next.value = null; stages.value = [];
      return;
    }
    try {
      profile.value = await api.profile(studentId.value, id);
      if (id === "python") onProfileResolved(profile.value);
      next.value = await api.nextActivity(studentId.value, id);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        profile.value = null; next.value = null; stages.value = [];
        if (id === "python") onProfileResolved(null);
      } else throw error;
    }
    await loadDiagnostic(profile.value ? "reassessment" : "initial");
  } catch (error) { fail(error) } finally { loading.value = false }
}

async function loadDiagnostic(phase: DiagnosticPhase): Promise<void> {
  diagnosticPhase.value = phase;
  diagnostic.value = await api.diagnostic(courseId.value, phase);
  diagnosticResult.value = null;
  Object.keys(diagnosticAnswers).forEach((key) => delete diagnosticAnswers[key]);
}

async function submitDiagnostic(): Promise<void> {
  if (diagnosticSubmitting.value) return;
  if (!diagnostic.value || !diagnosticComplete.value) {
    notice.value = "请完成全部诊断题目后再提交。";
    return;
  }
  const currentDiagnostic = diagnostic.value;
  localStorage.setItem(STUDENT_ID_KEY, studentId.value);
  diagnosticSubmitting.value = true;
  try {
    const result = await api.submitDiagnostic(
      studentId.value,
      courseId.value,
      diagnosticPhase.value,
      currentDiagnostic.items.map((item) => ({
        exercise_id: item.exercise_id,
        response: diagnosticAnswers[item.exercise_id] ?? ""
      }))
    );
    diagnosticResult.value = result;
    profile.value = result.profile; stages.value = result.plan.stages; next.value = result.plan.next_activity;
    tab.value = "overview";
    notice.value = `${result.phase === "initial" ? "初始诊断" : "阶段重测"}完成：${result.correct_count}/${result.total_count}，画像和学习路径已更新。`;
  } catch (error) { fail(error) } finally { diagnosticSubmitting.value = false }
}

async function generateAdaptiveProblem(useNext = false): Promise<void> {
  if (courseId.value !== "python" || !profile.value) {
    notice.value = "请先完成 Python 能力诊断，再生成个性化编程题。";
    return;
  }
  rememberStudent(); adaptiveLoading.value = true;
  try {
    const problem = useNext && adaptiveSubmission.value
      ? adaptiveSubmission.value.next_problem
      : await api.generateAdaptiveProblem(studentId.value, courseId.value, adaptiveAttemptIndex.value);
    adaptiveProblem.value = problem;
    adaptiveCode.value = problem.starter_code;
    adaptiveSubmission.value = null;
    tab.value = "practice";
  } catch (error) { fail(error) } finally { adaptiveLoading.value = false }
}

async function submitAdaptiveProblem(): Promise<void> {
  if (!adaptiveProblem.value || !adaptiveCode.value.trim()) return;
  adaptiveLoading.value = true;
  try {
    const result = await api.submitAdaptiveProblem(
      studentId.value, adaptiveProblem.value.problem_id, adaptiveCode.value
    );
    adaptiveSubmission.value = result;
    profile.value = result.profile;
    adaptiveAttemptIndex.value += 1;
    notice.value = result.verification.accepted
      ? "隐藏测试全部通过，学习画像已更新，并已准备下一道变式题。"
      : "代码尚未通过全部测试，请根据诊断信息继续调试。";
  } catch (error) { fail(error) } finally { adaptiveLoading.value = false }
}

async function ask(): Promise<void> {
  const trimmed = question.value.trim();
  if (!trimmed) return;
  if (trimmed.length < 2) {
    notice.value = "问题太短，请补充一点描述后再提问。";
    return;
  }
  qaLoading.value = true; qa.value = null;
  try { qa.value = await api.ask(studentId.value, courseId.value, trimmed) }
  catch (error) { fail(error) } finally { qaLoading.value = false }
}

async function openActivity(id: string, destination: "practice" | "projects" = "practice"): Promise<void> {
  notice.value = "正在载入练习内容…";
  try {
    activity.value = await api.activity(courseId.value, id);
    lastActivityId.value = id;
    localStorage.setItem(practiceHistoryKey(), id);
    answer.value = ""; submission.value = null; scenario.value = null;
    generatedProject.value = null;
    hint.value = null; hintLevel.value = 1; projectSubmission.value = null;
    practiceScaffoldLevel.value = 0;
    projectSummary.value = ""; projectRepository.value = ""; projectTests.value = "";
    if (
      activity.value.type === "project"
      && activity.value.scenario_scope === "post_course_finance_practice"
    ) {
      scenario.value = await api.scenario(courseId.value, activity.value.id);
    }
    if (activity.value.type === "project") {
      rememberProject(activity.value.id);
      restoreProjectWorkspace(activity.value.id);
    }
    const language = activity.value.evaluation.runtime?.language;
    code.value = activity.value.evaluation.starter_code ?? (language === "c"
      ? "#include <stdio.h>\n\nint main(void) {\n    // 在这里完成程序\n    return 0;\n}\n"
      : language === "python" ? "# 在这里完成程序\n" : "");
    tab.value = destination;
    notice.value = `已打开“${activity.value.title}”，可以开始作答。`;
  } catch (error) { fail(error) }
}

async function openKnowledgePoint(id: string): Promise<void> {
  selectedKnowledgeLoading.value = true;
  notice.value = `正在打开知识点 ${id}…`;
  try {
    const [knowledgePoint, homework] = await Promise.all([
      api.knowledgePoint(courseId.value, id),
      api.activities(courseId.value, { knowledgePointId: id, learningStage: "after_class" })
    ]);
    selectedKnowledge.value = knowledgePoint;
    selectedHomework.value = homework[0] ?? null;
    tab.value = "overview";
    await nextTick();
    knowledgeDetailSection.value?.scrollIntoView({ behavior: "smooth", block: "center" });
    notice.value = `已展开“${selectedKnowledge.value.title}”，详情已定位到当前视口。`;
  } catch (error) { fail(error) }
  finally { selectedKnowledgeLoading.value = false }
}

function revealNextScaffold(): void {
  if (!activity.value?.scaffolding.length) {
    notice.value = "这道题暂时没有额外提示，请先根据公开样例拆分步骤。";
    return;
  }
  practiceScaffoldLevel.value = Math.min(
    practiceScaffoldLevel.value + 1,
    activity.value.scaffolding.length
  );
  notice.value = `已展开第 ${practiceScaffoldLevel.value} 层提示。`;
}

async function openNextActivity(): Promise<void> {
  if (!next.value) return;
  if (next.value.activity_type === "concept") await openKnowledgePoint(next.value.activity_id);
  else await openActivity(next.value.activity_id);
}

async function requestHint(): Promise<void> {
  if (!activity.value) return;
  try {
    hint.value = await api.hint(studentId.value, courseId.value, activity.value.id, hintLevel.value);
    if (hintLevel.value < 3) hintLevel.value = (hintLevel.value + 1) as 1 | 2 | 3;
    notice.value = `第 ${hint.value.level} 层提示已生成。`;
  } catch (error) { fail(error) }
}

async function submitProject(): Promise<void> {
  if (!activity.value || activity.value.type !== "project" || projectSubmitting.value) return;
  if (projectSummary.value.trim().length < 30) {
    notice.value = "实现与验证说明至少需要 30 个字，请补充后再提交。";
    return;
  }
  projectSubmitting.value = true;
  try {
    projectSubmission.value = await api.submitProject(
      studentId.value, courseId.value, activity.value.id,
      {
        artifact_summary: projectSummary.value,
        ...(projectRepository.value.trim() ? { repository_url: projectRepository.value.trim() } : {}),
        test_evidence: projectTests.value.split("\n").map((item) => item.trim()).filter(Boolean).slice(0, 20)
      }
    );
    notice.value = "项目证据已记录，质量检查结果已显示在下方。";
  } catch (error) { fail(error) } finally { projectSubmitting.value = false }
}

async function generatePersonalizedProject(): Promise<void> {
  if (!activity.value || activity.value.type !== "project") return;
  if (!projectGoal.value.trim()) {
    notice.value = "请先填写你希望重点提升的目标。";
    return;
  }
  if (projectGoal.value.trim().length < 5) {
    notice.value = "目标描述太短，请写清楚希望重点提升什么（至少 5 个字）。";
    return;
  }
  const supportedDifficulty = ["beginner", "intermediate", "advanced"] as const;
  const requestedDifficulty = supportedDifficulty.includes(activity.value.difficulty as typeof supportedDifficulty[number])
    ? activity.value.difficulty as typeof supportedDifficulty[number]
    : "intermediate";
  const targetConceptIds = [...activity.value.concept_ids]
    .sort((left, right) => (masteryScore(left) ?? 0) - (masteryScore(right) ?? 0))
    .slice(0, 3);
  projectGenerating.value = true;
  try {
    generatedProject.value = await api.generateScenarioProject(courseId.value, {
      template_project_id: activity.value.id,
      learner_goal: projectGoal.value.trim(),
      target_concept_ids: targetConceptIds,
      difficulty: requestedDifficulty,
      estimated_minutes: Math.min(480, Math.max(30, activity.value.estimated_minutes))
    });
    notice.value = "个性化综合项目已生成，并完成安全与来源检查。";
  } catch (error) { fail(error) } finally { projectGenerating.value = false }
}

async function submit(): Promise<void> {
  if (!activity.value || submitting.value) return;
  const isCode = activity.value.type === "code" || activity.value.type === "debug";
  if (isCode && !code.value.trim()) {
    notice.value = "请先编写代码再提交验证。";
    return;
  }
  if (!isCode && !answer.value.trim()) {
    notice.value = "请先输入你的回答再提交。";
    return;
  }
  submitting.value = true;
  try {
    submission.value = await api.submit(studentId.value, courseId.value, activity.value.id,
      isCode ? { language: activity.value.evaluation.runtime?.language, source_code: code.value } : { response: answer.value });
    profile.value = { student_id: studentId.value, course_id: courseId.value, mastery: submission.value.mastery_updated };
    next.value = submission.value.next_activity;
    notice.value = submission.value.verification?.accepted ? "验证通过，学习画像已更新。" : "已返回可操作的验证反馈，请继续修改。";
  } catch (error) { fail(error) } finally { submitting.value = false }
}

onMounted(async () => {
  systemThemeQuery.addEventListener("change", syncSystemTheme);
  window.addEventListener("resize", syncViewport);
  try {
    await fetchApiHealth(); connection.value = "online";
    courses.value = await api.courses(); await loadCourse(courseId.value);
  } catch (error) { connection.value = "offline"; fail(error) }
  finally { loading.value = false }
});

onBeforeUnmount(() => {
  systemThemeQuery.removeEventListener("change", syncSystemTheme);
  window.removeEventListener("resize", syncViewport);
});
</script>

<template>
  <WelcomeExperience
    v-if="welcomeOpen"
    :display-name="displayName"
    :device-mode="uiPreferences.deviceMode"
    @start="finishWelcome"
    @settings="settingsOpen = true"
    @update-device="updateUiPreferences({ deviceMode: $event })"
  />
  <SettingsPanel
    :open="settingsOpen"
    :display-name="displayName"
    :preferences="uiPreferences"
    :accounts="localAccounts"
    :current-student-id="studentId"
    @close="settingsOpen = false"
    @update="updateUiPreferences"
    @update-name="updateDisplayName"
    @switch-account="switchLocalAccount"
    @create-account="createExperienceAccount"
    @replay="replayWelcome"
    @reset="resetUiPreferences"
  />
  <div v-if="!welcomeOpen" class="app-shell" :class="{ 'classroom-focus': classroomFocusMode, 'device-mobile': resolvedDevice === 'mobile' }">
    <aside v-if="!classroomFocusMode" class="sidebar">
      <div class="brand"><span>&lt;/&gt;</span><div><strong>词元研究所</strong></div></div>
      <nav class="course-nav">
        <p>我的课程</p>
        <button v-for="item in courses" :key="item.id" :class="{ active: courseId === item.id }" @click="loadCourse(item.id)">
          <b>{{ item.id === "data_structures" ? "DS" : item.id.toUpperCase() }}</b>
          <span><strong>{{ item.title }}</strong></span>
        </button>
      </nav>
      <div class="sidebar-progress"><div><span>课程进度</span><strong>{{ masteredCount }}/{{ knowledge.length }}</strong></div><i><span :style="{ width: `${knowledge.length ? masteredCount / knowledge.length * 100 : 0}%` }"></span></i><small>由测评、练习和代码验证持续更新</small></div>
      <div class="connection" :data-state="connection"><i></i> API {{ connection === "online" ? "服务正常" : connection === "offline" ? "未连接" : "连接中" }}</div>
    </aside>

    <main class="workspace">
      <header v-if="!classroomFocusMode" class="topbar">
        <div><span>{{ greeting }}</span><h1>{{ selectedCourse?.title ?? "课程工作台" }}</h1></div>
        <button class="settings-trigger" aria-label="打开个性化设置" @click="settingsOpen = true"><i>◐</i><span>界面设置</span></button>
      </header>
      <div v-if="notice" class="notice" role="status" aria-live="polite" @click="notice = ''">{{ notice }}<span>×</span></div>
      <nav v-if="!classroomFocusMode" class="tabs">
        <button :class="{ active: tab === 'classroom' || tab === 'overview' }" :aria-current="tab === 'classroom' || tab === 'overview' ? 'page' : undefined" @click="openClassroom">{{ courseId === 'python' ? '沉浸课堂' : '课程学习' }}</button>
        <button :class="{ active: tab === 'practice' }" :aria-current="tab === 'practice' ? 'page' : undefined" @click="openPractice">练习工坊</button>
        <button v-if="courseId === 'python'" :class="{ active: tab === 'projects' }" :aria-current="tab === 'projects' ? 'page' : undefined" @click="openProjects">项目实战</button>
      </nav>
      <div v-if="loading" class="loading" role="status" aria-live="polite"><i></i>正在同步课程与学情数据…</div>

      <template v-else-if="tab === 'overview'">
        <section class="hero-card">
          <div><h2>理解知识。编写代码。验证能力。</h2><p>课堂助教结合学情安排节奏，质量监督在后台检查依据、安全与事实。</p>
            <button v-if="next" @click="openNextActivity">继续下一项学习</button>
            <button v-else @click="startBaseline">建立能力基线</button>
          </div>
          <div class="mastery-orbit" :style="{ '--mastery': `${averageMastery * 3.6}deg` }"><div><strong>{{ averageMastery }}%</strong><span>当前已测知识<br />平均掌握度</span></div></div>
        </section>
        <section v-if="courseId === 'python'" class="classroom-invitation">
          <div><h3>不是再开一个聊天框，来真正上一节课。</h3><p>林老师会分段讲解并停下来等你；三位同学会和你一起提问、试错和总结，最后用隐藏测试证明掌握。</p></div>
          <aside><i>林</i><i>禾</i><i>拓</i><i>宁</i><button @click="openClassroom">进入温暖的 Python 教室 <b>→</b></button></aside>
        </section>
        <section class="metrics">
          <article><span>课程知识点</span><strong>{{ knowledge.length }}</strong><small>统一课程包</small></article>
          <article><span>已有证据</span><strong>{{ profile?.mastery.length ?? 0 }}</strong><small>测评与练习记录</small></article>
          <article><span>达到掌握</span><strong>{{ masteredCount }}</strong><small>分数 ≥ 60%</small></article>
          <article><span>实践活动</span><strong>{{ activities.length }}</strong><small>练习与综合项目</small></article>
        </section>
        <section v-if="diagnostic" ref="diagnosticSection" class="panel assessment baseline-target">
          <header><div><h2>{{ diagnostic.title }}</h2></div><p>{{ diagnostic.instructions }}</p></header>
          <div class="diagnostic-list">
            <article v-for="(item, index) in diagnostic.items" :key="item.exercise_id">
              <header><em>{{ String(index + 1).padStart(2, "0") }}</em><div><strong>{{ item.prompt }}</strong><small>{{ item.concept_ids.join(" · ") }}</small></div></header>
              <div><button v-for="option in item.options" :key="option.id" :class="{ active: diagnosticAnswers[item.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" @click="diagnosticAnswers[item.exercise_id] = option.id"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b>{{ option.text }}</button></div>
            </article>
          </div>
          <footer class="diagnostic-actions"><span>{{ Object.keys(diagnosticAnswers).length }} / {{ diagnostic.items.length }} 已作答</span><button class="primary" :disabled="!diagnosticComplete || diagnosticSubmitting" @click="submitDiagnostic">{{ diagnosticSubmitting ? "正在生成个性化路径…" : diagnostic.phase === "initial" ? "提交诊断并生成路径" : "提交重测并更新画像" }}</button></footer>
          <div v-if="diagnosticResult" class="diagnostic-result"><strong>本轮 {{ diagnosticResult.correct_count }} / {{ diagnosticResult.total_count }}</strong><span>结果已转化为学习证据；{{ diagnosticResult.unknown_count ? `“我不知道” ${diagnosticResult.unknown_count} 题已安排回补。` : "画像和后续路径已经刷新。" }}</span><button v-if="diagnosticResult.phase === 'initial'" @click="loadDiagnostic('reassessment')">准备阶段重测</button></div>
        </section>
        <section ref="knowledgeMapSection" class="panel knowledge-map-target">
          <header><div><span class="eyebrow">COURSE LEARNING ROADMAP</span><h2>{{ selectedCourse?.title ?? "课程" }} · 知识路线</h2></div><p>先看全局，再按前置关系逐步推进；每个节点都连接讲解、练习与学习证据。</p></header>
          <div class="knowledge-map-summary">
            <article><strong>{{ knowledgeChapterCount }}</strong><span>学习阶段</span></article>
            <article><strong>{{ knowledge.length }}</strong><span>核心节点</span></article>
            <article><strong>{{ knowledgeSubskillCount }}</strong><span>细分技能</span></article>
            <article><strong>{{ knowledgePrerequisiteCount }}</strong><span>前置关系</span></article>
          </div>
          <div class="knowledge-toolbar"><label><span>⌕</span><input v-model="knowledgeQuery" placeholder="搜索节点、技能或 ID" aria-label="搜索知识节点或细分技能" /></label><small>显示 {{ filteredKnowledge.length }} / {{ knowledge.length }} 个核心节点</small></div>
          <div class="knowledge-legend" aria-label="知识节点状态说明">
            <span data-state="mastered">已掌握</span><span data-state="learning">学习中</span><span data-state="recommended">推荐下一步</span><span data-state="ready">可以开始</span><span data-state="locked">建议先学前置</span><span data-state="unassessed">等待评估</span>
          </div>
          <div class="knowledge-roadmap">
            <section v-for="chapter in knowledgeChapters" :key="chapter.key" class="knowledge-chapter">
              <header>
                <em>{{ chapter.order }}</em>
                <div><small>阶段 {{ chapter.order }} · {{ chapter.subskills }} 项细分技能</small><h3>{{ chapter.title }}</h3><p>{{ chapter.description }}</p></div>
                <aside><strong>{{ chapter.mastered }}/{{ chapter.total }}</strong><span>核心节点已掌握</span><i><b :style="{ width: `${chapter.total ? chapter.mastered / chapter.total * 100 : 0}%` }"></b></i></aside>
              </header>
              <div class="knowledge-lane">
                <article v-for="item in chapter.items" :key="item.id" :class="[`state-${knowledgeState(item)}`, { selected: selectedKnowledge?.id === item.id }]">
                  <button type="button" :aria-label="`${item.title}，${knowledgeStateLabel(item)}`" :aria-busy="selectedKnowledgeLoading && selectedKnowledge?.id === item.id" @click="openKnowledgePoint(item.id)">
                    <header><span>{{ knowledgeStateLabel(item) }}</span><small>{{ item.id }} · {{ difficulty(item.difficulty) }}</small></header>
                    <h4>{{ item.title }}</h4>
                    <div class="knowledge-subskills"><span v-for="concept in item.concepts.slice(0, 3)" :key="concept">{{ concept }}</span><b v-if="item.concepts.length > 3">+{{ item.concepts.length - 3 }}</b></div>
                    <footer><i><b :style="{ width: `${(masteryScore(item.id) ?? 0) * 100}%` }"></b></i><span>{{ knowledgeEvidenceText(item) }}</span><b>查看节点 →</b></footer>
                  </button>
                </article>
              </div>
            </section>
          </div>
          <div v-if="!filteredKnowledge.length" class="empty compact">没有匹配的知识点，请尝试其他关键词。</div>
           <section v-if="selectedKnowledge" ref="knowledgeDetailSection" class="lesson-detail" :aria-busy="selectedKnowledgeLoading">
             <header><div><span>{{ selectedKnowledge.id }}</span><h3>{{ selectedKnowledge.title }}</h3></div><button @click="selectedKnowledge = null; notice = '知识点详情已收起。'">关闭</button></header>
            <p>{{ selectedKnowledge.lesson.summary }}</p>
            <section class="lesson-concepts"><b>本节点包含 {{ selectedKnowledge.concepts.length }} 项细分技能</b><div><span v-for="concept in selectedKnowledge.concepts" :key="concept">{{ concept }}</span></div></section>
            <div><article><b>学习目标</b><ul><li v-for="item in selectedKnowledge.learning_objectives" :key="item">{{ item }}</li></ul></article><article><b>关键要点</b><ul><li v-for="item in selectedKnowledge.lesson.key_points" :key="item">{{ item }}</li></ul></article><article><b>常见误区</b><ul><li v-for="item in selectedKnowledge.lesson.common_mistakes" :key="item">{{ item }}</li></ul></article></div>
            <section v-if="selectedKnowledge.lesson.learning_sequence?.length" class="lesson-sequence"><b>建议学习顺序</b><ol><li v-for="step in selectedKnowledge.lesson.learning_sequence" :key="step.title"><strong>{{ step.title }}</strong><span>{{ step.content }}</span></li></ol></section>
            <section v-if="selectedKnowledge.lesson.worked_example" class="worked-example" :class="{ expanded: workedExampleExpanded }"><header><b>分步例题</b><span>{{ selectedKnowledge.lesson.worked_example.problem }}</span></header><ol><li v-for="step in selectedKnowledge.lesson.worked_example.steps" :key="step">{{ step }}</li></ol><div class="code-heading"><b>示例代码</b><button class="code-expand" @click="workedExampleExpanded = !workedExampleExpanded">{{ workedExampleExpanded ? "收起" : "展开" }}</button></div><pre><code>{{ selectedKnowledge.lesson.worked_example.code }}</code></pre><p>{{ selectedKnowledge.lesson.worked_example.reflection }}</p></section>
            <section v-if="selectedKnowledge.lesson.checkpoint" class="lesson-checkpoint"><b>立即检验</b><p>{{ selectedKnowledge.lesson.checkpoint.prompt }}</p><small>{{ selectedKnowledge.lesson.checkpoint.guidance }}</small></section>
            <section v-if="selectedHomework" class="lesson-homework-link"><div><b>与本节匹配的课后练习</b><h4>{{ selectedHomework.title }}</h4><span>{{ selectedHomework.estimated_minutes }} 分钟 · {{ difficulty(selectedHomework.difficulty) }} · 含公开样例与隐藏测试</span></div><button class="primary" @click="openActivity(selectedHomework.id)">去完成本节作业 <b>→</b></button></section>
          </section>
        </section>
      </template>

      <template v-else-if="tab === 'path'">
        <section v-if="profile" class="split-layout">
          <div class="panel path-panel"><header><div><h2>个性化学习路径</h2></div><p>由掌握度和前置关系驱动，不由模型自由编造。</p></header>
            <div v-if="stages.length" class="stage-list"><article v-for="(stage, index) in stages" :key="stage.stage"><em>{{ index + 1 }}</em><div><small>{{ stage.stage }}</small><h3>{{ stage.objective }}</h3><p>{{ stage.reason }}</p><b v-for="id in stage.knowledge_point_ids" :key="id">{{ id }}</b></div></article></div>
            <div v-else class="empty">当前路径来自实时下一任务推荐；重新建立能力基线可生成三阶段计划。</div>
          </div>
          <aside class="next-card"><span>{{ activityType(next?.activity_type ?? "concept") }}</span><h2>{{ next?.activity_id ?? "等待规划" }}</h2><p>{{ next?.reason }}</p><button v-if="next" @click="openNextActivity">进入学习活动</button></aside>
        </section>
        <section v-else class="panel empty">请先在课程概览完成快速能力基线。</section>
      </template>

      <template v-else-if="tab === 'tutor'">
        <section class="tutor-layout">
          <div class="panel tutor"><header><div><h2>有依据的课程辅导</h2></div><p>回答必须来自已审核课程资料；依据不足时明确拒答。</p></header>
            <div class="chat"><article><b>课程辅导智能体</b><p>可以询问当前课程的概念、边界、调试思路或算法前提。</p></article><article v-if="qa" :data-status="qa.status"><b>{{ qa.status === "answered" ? "已通过质量监督" : "依据不足" }}</b><p>{{ qa.answer || "当前资料不足以支持这个问题，我不会编造答案。" }}</p><div><span v-for="citation in qa.citations" :key="citation.chunk_id">{{ citation.source_id }} · {{ Math.round(citation.score * 100) }}%</span></div><ol class="trace"><li v-for="step in qa.trace" :key="`${step.component}-${step.status}`" :data-status="step.status"><b>{{ step.component }}</b><span>{{ step.detail }}</span></li></ol></article></div>
            <div class="composer"><textarea v-model="question" rows="3" maxlength="1000"></textarea><button class="primary" :disabled="qaLoading" @click="ask">{{ qaLoading ? "检索中…" : "发送问题" }}</button></div>
          </div>
            <aside class="agent-stack"><div class="agent-title"><b>智能体协作状态</b></div><article><em>01</em><div><strong>学情规划智能体</strong><p>选择合法的下一活动</p></div><i>待命</i></article><article class="active"><em>02</em><div><strong>课程辅导智能体</strong><p>根据课程资料组织讲解</p></div><i>工作中</i></article><article><em>03</em><div><strong>质量监督智能体</strong><p>检查引用、安全与事实</p></div><i>监督中</i></article></aside>
        </section>
      </template>

      <template v-else-if="tab === 'projects'">
        <section class="project-center-hero">
          <div><span>Python 项目实战</span><h2>把课程能力组合成真正可运行的作品</h2><p>阶段项目对应刚完成的课程能力，综合项目把算法、文件处理与程序可靠性放进脱敏财经场景。核心考核始终是计算机能力。</p></div>
          <aside><strong>{{ projectActivities.length }}</strong><span>个可浏览项目</span><small>{{ savedProjects.length }} 个已加入“我的项目”</small></aside>
        </section>

        <section class="project-shelf">
          <header><div><span>01</span><h3>阶段项目</h3><p>在关键阶段结束后进行一次稳定、可重复的综合验证。</p></div></header>
          <div><article v-for="item in stageProjects" :key="item.id" :data-ready="projectReadiness(item).ready"><header><span>{{ projectReadiness(item).ready ? '已解锁' : '可预览' }}</span><small>{{ projectReadiness(item).completed }}/{{ projectReadiness(item).total }} 项前置能力</small></header><h4>{{ item.title }}</h4><p>{{ item.concept_ids.join(' · ') }}</p><footer><small>{{ item.estimated_minutes }} 分钟 · {{ difficulty(item.difficulty) }}</small><button @click="openActivity(item.id, 'projects')">{{ projectReadiness(item).ready ? '开始项目' : '查看要求' }} →</button></footer></article></div>
          <p v-if="!stageProjects.length" class="empty compact">阶段项目正在载入。</p>
        </section>

        <section class="project-shelf comprehensive">
          <header><div><span>02</span><h3>综合项目</h3><p>财经内容只提供应用语境，评分聚焦 Python、算法、文件处理、测试与可追溯性。</p></div></header>
          <div><article v-for="item in comprehensiveProjects" :key="item.id" :data-ready="projectReadiness(item).ready"><header><span>脱敏合成场景</span><small>{{ projectReadiness(item).completed }}/{{ projectReadiness(item).total }} 项前置能力</small></header><h4>{{ item.title }}</h4><p>{{ item.concept_ids.join(' · ') }}</p><footer><small>{{ item.estimated_minutes }} 分钟 · {{ difficulty(item.difficulty) }}</small><button @click="openActivity(item.id, 'projects')">查看项目 →</button></footer></article></div>
        </section>

        <section class="project-shelf mine">
          <header><div><span>03</span><h3>我的项目</h3><p>草稿、仓库地址和测试记录保存在当前浏览器中，提交后写入学习证据。</p></div></header>
          <div v-if="savedProjects.length"><article v-for="item in savedProjects" :key="item.id"><header><span>已有本地进度</span><small>{{ item.id }}</small></header><h4>{{ item.title }}</h4><p>继续完善实现说明、代码链接与测试证据。</p><footer><small>自动保存</small><button @click="openActivity(item.id, 'projects')">继续项目 →</button></footer></article></div>
          <p v-else class="empty compact">打开任一项目后，它会自动出现在这里。</p>
        </section>

        <section v-if="activity?.type === 'project'" class="project-workspace panel">
          <header class="activity-title"><div><span>{{ activity.id.startsWith('PY-PROJ-STAGE-') ? '阶段项目' : '综合项目' }}</span><h2>{{ activity.title }}</h2><small>{{ activity.id }}</small></div><button class="secondary" @click="activity = null">收起工作区</button></header>
          <p class="prompt">{{ activity.summary }}</p>
          <div class="project-brief"><section><b>你要完成</b><ol><li v-for="item in activity.requirements" :key="item">{{ item }}</li></ol></section><section><b>提交成果</b><ul><li v-for="item in activity.deliverables" :key="item">{{ item }}</li></ul></section></div>
          <section class="project-objectives"><div><b>计算机能力目标</b><span v-for="item in activity.computer_science_objectives" :key="item">{{ item }}</span></div><div v-if="activity.business_context_objectives.length"><b>场景理解目标</b><span v-for="item in activity.business_context_objectives" :key="item">{{ item }}</span></div></section>
          <section v-if="scenario" class="scenario-card" :data-mode="scenario.mode"><header><div><span>固定合成场景</span><strong>不包含真实个人或业务数据</strong></div><b>隐私安全</b></header><p>{{ scenario.context }}</p><ul><li v-for="item in scenario.constraints" :key="item">{{ item }}</li></ul><footer><span v-for="source in scenario.source_refs" :key="source">{{ source }}</span><small>{{ scenario.notice }}</small></footer></section>
          <section v-if="activity.scenario_scope === 'post_course_finance_practice'" class="project-generator"><header><div><h3>让智能体按当前能力生成项目变体</h3></div><b>不发送身份信息</b></header><label>你希望重点提升什么？<textarea v-model="projectGoal" rows="3" maxlength="500"></textarea></label><button class="primary" :disabled="projectGenerating" @click="generatePersonalizedProject">{{ projectGenerating ? '生成中…' : '生成我的项目变体' }}</button><article v-if="generatedProject"><header><div><small>{{ generatedProject.degraded ? '固定安全版本' : `${generatedProject.provider} · ${generatedProject.model}` }}</small><h3>{{ generatedProject.title }}</h3></div><b>AI 生成内容</b></header><p>{{ generatedProject.scenario_context }}</p><div class="generated-columns"><section><strong>任务</strong><ol><li v-for="item in generatedProject.tasks" :key="item">{{ item }}</li></ol></section><section><strong>约束</strong><ul><li v-for="item in generatedProject.constraints" :key="item">{{ item }}</li></ul></section></div></article></section>
          <section class="project-submit"><label>实现与验证说明<textarea v-model="projectSummary" rows="6" maxlength="4000" placeholder="说明模块设计、关键算法、异常处理和测试结果（至少 30 字）"></textarea></label><label>代码仓库或制品链接（可选）<input v-model="projectRepository" maxlength="1000" placeholder="https://gitee.com/..." /></label><label>测试证据（每行一条）<textarea v-model="projectTests" rows="4" placeholder="pytest: 12 passed&#10;边界输入：空文件返回明确错误"></textarea></label><div class="project-save-note">草稿自动保存到“我的项目”</div><button class="primary" :disabled="projectSubmitting" @click="submitProject">{{ projectSubmitting ? "记录中…" : "记录项目证据" }}</button></section>
          <div v-if="projectSubmission" class="verification" data-pass="true"><strong>项目证据已记录</strong><p>{{ projectSubmission.feedback }}</p><ul><li v-for="item in projectSubmission.evidence_checklist" :key="item.item"><b>{{ item.present ? '✓' : '!' }} {{ item.item }}</b> — {{ item.detail }}</li></ul></div>
        </section>
      </template>

      <template v-else-if="tab === 'practice'">
        <section v-if="courseId === 'python'" class="panel adaptive-lab">
          <header><div><h2>个性化 Python 编程挑战</h2></div><p>根据真实测评与代码证据选择薄弱点；题目变式由规则生成，答案由隐藏测试判定。</p></header>
          <div v-if="!profile" class="adaptive-empty"><strong>先完成能力诊断</strong><span>建立初始画像后，系统才能选择你的薄弱知识点。</span><button class="primary" @click="tab = 'overview'">前往诊断</button></div>
          <div v-else-if="!adaptiveProblem" class="adaptive-empty"><strong>准备生成第一道个性化题目</strong><span>系统优先选择掌握度最低且已有可靠题型的知识点。</span><button class="primary" :disabled="adaptiveLoading" @click="generateAdaptiveProblem()">{{ adaptiveLoading ? "生成中…" : "生成我的新题" }}</button></div>
          <template v-else>
            <div class="adaptive-heading"><div><span v-for="concept in adaptiveProblem.concept_ids" :key="concept">{{ concept }}</span><h3>{{ adaptiveProblem.title }}</h3></div><b>{{ difficulty(adaptiveProblem.difficulty) }}</b></div>
            <p class="prompt">{{ adaptiveProblem.prompt }}</p>
            <div class="adaptive-spec"><section><strong>约束</strong><ul><li v-for="item in adaptiveProblem.constraints" :key="item">{{ item }}</li></ul></section><section><strong>公开样例</strong><div v-for="(item, index) in adaptiveProblem.public_examples" :key="index"><code>输入：{{ item.input }}</code><code>输出：{{ item.expected_output }}</code></div></section></div>
            <div class="editor"><header><i></i><i></i><i></i><b>Python · 隐藏测试验证</b></header><textarea v-model="adaptiveCode" spellcheck="false"></textarea></div>
            <footer class="adaptive-actions"><small>{{ adaptiveProblem.generation_notice }}</small><button class="primary" :disabled="adaptiveLoading || !adaptiveCode.trim()" @click="submitAdaptiveProblem">{{ adaptiveLoading ? "验证中…" : "运行并提交" }}</button></footer>
            <div v-if="adaptiveSubmission" class="verification" :data-pass="adaptiveSubmission.verification.accepted"><strong>{{ adaptiveSubmission.verification.accepted ? "挑战通过，画像已更新" : "尚未通过隐藏测试" }}</strong><p>{{ adaptiveSubmission.feedback }}</p><small>通过 {{ adaptiveSubmission.verification.passed_tests }} / {{ adaptiveSubmission.verification.total_tests }} 个测试</small><button v-if="adaptiveSubmission.verification.accepted" class="primary" @click="generateAdaptiveProblem(true)">进入下一道变式题</button></div>
          </template>
        </section>
        <section class="practice-compass panel">
          <div v-if="lastActivity" class="continue-card"><span>继续上次</span><div><b>{{ lastActivity.title }}</b><small>{{ lastActivity.estimated_minutes }} 分钟 · {{ activityType(lastActivity.type) }}</small></div><button class="primary" @click="openActivity(lastActivity.id)">继续作答 <b>→</b></button></div>
          <div class="recommend-strip"><header><span>按当前画像推荐</span><small>优先薄弱知识、下一任务与适合难度</small></header><button v-for="(item, index) in recommendedActivities" :key="item.id" @click="openActivity(item.id)"><em>0{{ index + 1 }}</em><span><b>{{ item.title }}</b><small>{{ item.concept_ids.slice(0, 2).join(' · ') }} · {{ item.estimated_minutes }} 分钟</small></span></button></div>
        </section>
        <section class="practice-layout">
          <aside class="panel activity-list">
            <header><div><h2>练习工坊</h2><p>搜索题目，或按推荐顺序继续</p></div><small>{{ filteredActivities.length }} 项</small></header>
            <label class="activity-search"><span>⌕</span><input v-model="activityQuery" type="search" placeholder="搜索题目、编号或知识点" aria-label="搜索练习" /><button v-if="activityQuery" aria-label="清空搜索" @click="activityQuery = ''">×</button></label>
            <div class="activity-sort"><button :class="{ active: activitySort === 'recommended' }" @click="activitySort = 'recommended'">为我推荐</button><button :class="{ active: activitySort === 'shortest' }" @click="activitySort = 'shortest'">用时较短</button><button :class="{ active: activitySort === 'catalog' }" @click="activitySort = 'catalog'">课程顺序</button></div>
            <div class="activity-filters"><button v-for="item in ([['all','全部'],['homework','课后'],['code','编程'],['debug','排错']] as const)" :key="item[0]" :class="{ active: activityFilter === item[0] }" :aria-pressed="activityFilter === item[0]" @click="activityFilter = item[0]">{{ item[1] }}</button></div>
            <div class="activity-scroll"><button v-for="item in filteredActivities" :key="item.id" :class="{ active: activity?.id === item.id }" @click="openActivity(item.id)"><span>{{ item.learning_stage === 'after_class' ? '课后练习' : activityType(item.type) }}</span><strong>{{ item.title }}</strong><small>{{ item.id }} · {{ item.estimated_minutes }} 分钟</small></button><p v-if="!filteredActivities.length" class="empty compact">没有找到匹配练习，试试更短的关键词或清空筛选。</p></div>
          </aside>
          <div class="panel activity-workspace"><template v-if="activity"><div class="activity-title"><div><span>{{ activityType(activity.type) }}</span><h2>{{ activity.title }}</h2><small>{{ activity.id }}</small></div><b>{{ difficulty(activity.difficulty) }}</b></div><p class="prompt">{{ activity.prompt || activity.summary }}</p>
            <section v-if="activity.learning_stage === 'after_class'" class="beginner-task-brief"><header><div><small>本节知识 → 课后迁移</small><h3>先读懂任务，再开始写代码</h3></div><b>中文初学者版</b></header><div class="task-io"><article><span>输入是什么</span><p>{{ activity.input_format }}</p></article><article><span>需要输出</span><p>{{ activity.output_format }}</p></article></div><div v-if="activity.public_examples.length" class="task-examples"><b>先看一个公开样例</b><article v-for="(example, index) in activity.public_examples" :key="index"><div><code>输入\n{{ example.input }}</code><code>输出\n{{ example.expected_output }}</code></div><p>{{ example.explanation }}</p></article></div><ul class="task-constraints"><li v-for="item in activity.constraints" :key="item">{{ item }}</li></ul></section>
            <section v-if="scenario" class="scenario-card" :data-mode="scenario.mode"><header><div><span>固定合成场景</span><strong>经管背景只服务课程综合实践</strong></div><b>隐私安全</b></header><p>{{ scenario.context }}</p><ul><li v-for="item in scenario.constraints" :key="item">{{ item }}</li></ul><footer><span v-for="source in scenario.source_refs" :key="source">{{ source }}</span><small>{{ scenario.notice }}</small></footer></section>
            <section v-if="activity.type === 'project'" class="project-generator"><header><div><h3>按当前能力生成综合项目</h3></div><b>不发送身份信息</b></header><label>你希望重点提升什么？<textarea v-model="projectGoal" rows="3" maxlength="500"></textarea></label><button class="primary" :disabled="projectGenerating" @click="generatePersonalizedProject">{{ projectGenerating ? "生成中…" : "生成我的项目" }}</button>
              <article v-if="generatedProject"><header><div><small>{{ generatedProject.degraded ? "固定安全版本" : `${generatedProject.provider} · ${generatedProject.model}` }}</small><h3>{{ generatedProject.title }}</h3></div><b>AI生成内容</b></header><p>{{ generatedProject.scenario_context }}</p><div class="generated-columns"><section><strong>任务</strong><ol><li v-for="item in generatedProject.tasks" :key="item">{{ item }}</li></ol></section><section><strong>约束</strong><ul><li v-for="item in generatedProject.constraints" :key="item">{{ item }}</li></ul></section></div><div class="dataset-preview"><strong>固定合成数据 · {{ generatedProject.dataset.filename }}</strong><div><table><thead><tr><th v-for="column in generatedProject.dataset.columns" :key="column">{{ column }}</th></tr></thead><tbody><tr v-for="(row, index) in generatedProject.dataset.rows" :key="index"><td v-for="column in generatedProject.dataset.columns" :key="column">{{ row[column] ?? "—" }}</td></tr></tbody></table></div><small>SHA-256：{{ generatedProject.dataset.sha256 }}</small></div><footer><span v-for="source in generatedProject.source_refs" :key="source">{{ source }}</span><small>{{ generatedProject.ai_generated_notice }}</small></footer></article>
            </section>
            <section v-if="activity.type === 'project'" class="project-objectives"><div><b>计算机能力目标</b><span v-for="item in activity.computer_science_objectives" :key="item">{{ item }}</span></div><div v-if="activity.business_context_objectives.length"><b>场景理解目标</b><span v-for="item in activity.business_context_objectives" :key="item">{{ item }}</span></div></section>
            <div v-if="activity.evaluation.options" class="options"><label v-for="option in activity.evaluation.options" :key="option.id" :class="{ selected: answer === option.id }"><input v-model="answer" type="radio" :value="option.id" /><b>{{ option.id }}</b><span>{{ option.text }}</span></label></div>
            <div v-else-if="activity.type === 'code' || activity.type === 'debug'" class="editor"><header><i></i><i></i><i></i><b>{{ activity.evaluation.runtime?.language }} · 隔离运行环境</b></header><textarea v-model="code" spellcheck="false"></textarea></div>
            <section v-if="activity.learning_stage === 'after_class' && activity.scaffolding.length" class="local-scaffolding"><header><div><b>卡住时再看提示</b><span>提示逐级展开，不直接给完整答案</span></div><button @click="revealNextScaffold" :disabled="practiceScaffoldLevel >= activity.scaffolding.length">{{ practiceScaffoldLevel ? '再看一步' : '看第一步' }}</button></header><ol v-if="practiceScaffoldLevel"><li v-for="(step, index) in activity.scaffolding.slice(0, practiceScaffoldLevel)" :key="step"><em>{{ index + 1 }}</em><span>{{ step }}</span></li></ol></section>
            <section v-else-if="activity.type === 'project'" class="project-submit"><label>实现与验证说明<textarea v-model="projectSummary" rows="6" maxlength="4000" placeholder="说明模块设计、关键算法、异常处理和测试结果（至少 30 字）"></textarea></label><label>代码仓库或制品链接（可选）<input v-model="projectRepository" maxlength="1000" placeholder="https://gitee.com/..." /></label><label>测试证据（每行一条）<textarea v-model="projectTests" rows="4" placeholder="pytest: 12 passed&#10;边界输入：空文件返回明确错误"></textarea></label><button class="primary" :disabled="projectSubmitting" @click="submitProject">{{ projectSubmitting ? "记录中…" : "记录项目证据" }}</button></section>
            <textarea v-else v-model="answer" class="answer-box" rows="7" placeholder="输入你的回答…"></textarea><button v-if="activity.type !== 'project'" class="primary" :disabled="submitting" @click="submit">{{ submitting ? "验证中…" : "提交并验证" }}</button>
            <section class="hint-box"><button @click="requestHint">{{ hint ? `继续提示（${hintLevel}/3）` : "获取分层提示" }}</button><p v-if="hint"><b>第 {{ hint.level }} 层提示</b>{{ hint.hint }}</p></section>
            <div v-if="submission" class="verification" :data-pass="submission.verification?.accepted ?? false"><strong>{{ submission.verification?.accepted ? "验证通过" : "反馈已生成" }}</strong><p>{{ submission.feedback }}</p><small v-if="submission.verification">通过 {{ submission.verification.passed_tests }} / {{ submission.verification.total_tests }} 个测试</small></div>
            <section v-if="submission && activity.reflection_prompt" class="practice-reflection"><b>提交后复盘</b><p>{{ activity.reflection_prompt }}</p><span>先用一句话说明本次错误或通过的关键原因，再进入下一题。</span></section>
            <div v-if="projectSubmission" class="verification" data-pass="true"><strong>项目证据已记录</strong><p>{{ projectSubmission.feedback }}</p><ul><li v-for="item in projectSubmission.evidence_checklist" :key="item.item"><b>{{ item.present ? "✓" : "!" }} {{ item.item }}</b> — {{ item.detail }}</li></ul></div>
          </template><div v-else class="empty">从左侧选择一道练习，或按照学习路径进入推荐活动。</div></div>
        </section>
      </template>

      <template v-else>
        <PythonFirstLesson
          :key="studentId"
          :student-id="studentId"
          :generic-mode="genericMode"
          @profile-updated="profile = $event"
          @profile-resolved="onProfileResolved"
          @open-knowledge-map="openKnowledgeMap"
          @request-generic-mode="requestGenericMode('classroom')"
          @request-assessment="goToAssessment"
          @focus-changed="onClassroomFocusChanged"
          @open-projects="openProjects"
        />
      </template>
    </main>
    <div v-if="assessmentWarningOpen" class="modal-backdrop" role="presentation" @click.self="closeAssessmentWarning">
      <section ref="assessmentWarningDialog" class="assessment-warning" role="dialog" aria-modal="true" aria-labelledby="assessment-warning-title" @keydown="handleAssessmentWarningKeydown">
        <h2 id="assessment-warning-title">还没有足够信息为你定制课程</h2>
        <p>如果现在继续，平台仍可提供通用讲解和基础练习，但无法根据你的 Python 水平调整第一课起点、讲解速度、每日计划和后续题目难度。</p>
        <ul><li>可能重复你已经掌握的内容</li><li>也可能跳过你需要补齐的基础</li><li>后续推荐暂时不会写入个性化画像</li></ul>
        <div><button class="text-button" @click="closeAssessmentWarning">取消</button><button class="secondary" @click="continueWithGenericCourse">仍然继续通用课程</button><button ref="assessmentWarningPrimaryAction" class="primary" @click="goToAssessment">先完成约 8 分钟摸底 <b>→</b></button></div>
      </section>
    </div>
  </div>
</template>
