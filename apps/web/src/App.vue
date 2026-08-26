<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import {
  ApiError, api, fetchApiHealth,
  type ActivityDetail, type ActivitySummary, type CourseId, type CourseSummary,
  type DiagnosticPhase, type DiagnosticQuiz, type DiagnosticSubmissionResult,
  type HintResponse, type KnowledgePoint, type KnowledgePointDetail, type LearnerProfile,
  type NextActivity, type PlanStage, type ProjectSubmissionResponse, type QaResponse,
  type GeneratedCodeProblem, type GeneratedProblemSubmissionResponse,
  type GeneratedScenarioProject, type ScenarioContext, type SubmissionResult
} from "./services/api";

type Tab = "overview" | "path" | "tutor" | "practice";
type ActivityFilter = "all" | "code" | "debug" | "project";
const connection = ref<"connecting" | "online" | "offline">("connecting");
const loading = ref(true);
const notice = ref("");
const tab = ref<Tab>("overview");
const studentId = ref(localStorage.getItem("ciyuan-student-id") ?? "demo-student-01");
const courses = ref<CourseSummary[]>([]);
const courseId = ref<CourseId>("python");
const knowledge = ref<KnowledgePoint[]>([]);
const selectedKnowledge = ref<KnowledgePointDetail | null>(null);
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
const knowledgeQuery = ref("");
const activityFilter = ref<ActivityFilter>("all");
const adaptiveProblem = ref<GeneratedCodeProblem | null>(null);
const adaptiveCode = ref("");
const adaptiveSubmission = ref<GeneratedProblemSubmissionResponse | null>(null);
const adaptiveAttemptIndex = ref(1);
const adaptiveLoading = ref(false);

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
const filteredKnowledge = computed(() => {
  const query = knowledgeQuery.value.trim().toLowerCase();
  if (!query) return knowledge.value;
  return knowledge.value.filter((item) => `${item.id} ${item.title}`.toLowerCase().includes(query));
});
const filteredActivities = computed(() => activityFilter.value === "all"
  ? activities.value
  : activities.value.filter((item) => item.type === activityFilter.value));

function fail(error: unknown): void {
  notice.value = error instanceof Error ? error.message : "操作失败，请稍后重试";
}
function rememberStudent(): void {
  studentId.value = studentId.value.trim() || "demo-student-01";
  localStorage.setItem("ciyuan-student-id", studentId.value);
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

async function loadCourse(id: CourseId): Promise<void> {
  courseId.value = id;
  tab.value = "overview";
  loading.value = true;
  notice.value = "";
  qa.value = null;
  activity.value = null;
  selectedKnowledge.value = null;
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
    try {
      profile.value = await api.profile(studentId.value, id);
      next.value = await api.nextActivity(studentId.value, id);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        profile.value = null; next.value = null; stages.value = [];
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
  if (!diagnostic.value || !diagnosticComplete.value) {
    notice.value = "请完成全部诊断题目后再提交。";
    return;
  }
  rememberStudent(); loading.value = true;
  try {
    const result = await api.submitDiagnostic(
      studentId.value,
      courseId.value,
      diagnosticPhase.value,
      diagnostic.value.items.map((item) => ({
        exercise_id: item.exercise_id,
        response: diagnosticAnswers[item.exercise_id] ?? ""
      }))
    );
    diagnosticResult.value = result;
    profile.value = result.profile; stages.value = result.plan.stages; next.value = result.plan.next_activity;
    tab.value = "path";
    notice.value = `${result.phase === "initial" ? "初始诊断" : "阶段重测"}完成：${result.correct_count}/${result.total_count}，画像和学习路径已更新。`;
  } catch (error) { fail(error) } finally { loading.value = false }
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
  if (!question.value.trim()) return;
  qaLoading.value = true; qa.value = null;
  try { qa.value = await api.ask(studentId.value, courseId.value, question.value.trim()) }
  catch (error) { fail(error) } finally { qaLoading.value = false }
}

async function openActivity(id: string): Promise<void> {
  try {
    activity.value = await api.activity(courseId.value, id);
    answer.value = ""; submission.value = null; scenario.value = null;
    generatedProject.value = null;
    hint.value = null; hintLevel.value = 1; projectSubmission.value = null;
    projectSummary.value = ""; projectRepository.value = ""; projectTests.value = "";
    if (activity.value.type === "project" && activity.value.scenario_scope) {
      scenario.value = await api.scenario(courseId.value, activity.value.id);
    }
    const language = activity.value.evaluation.runtime?.language;
    code.value = language === "c"
      ? "#include <stdio.h>\n\nint main(void) {\n    // 在这里完成程序\n    return 0;\n}\n"
      : language === "python" ? "# 在这里完成程序\n" : "";
    tab.value = "practice";
  } catch (error) { fail(error) }
}

async function openKnowledgePoint(id: string): Promise<void> {
  try { selectedKnowledge.value = await api.knowledgePoint(courseId.value, id); tab.value = "overview" }
  catch (error) { fail(error) }
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
  } catch (error) { fail(error) }
}

async function submitProject(): Promise<void> {
  if (!activity.value || activity.value.type !== "project") return;
  try {
    projectSubmission.value = await api.submitProject(
      studentId.value, courseId.value, activity.value.id,
      {
        artifact_summary: projectSummary.value,
        ...(projectRepository.value.trim() ? { repository_url: projectRepository.value.trim() } : {}),
        test_evidence: projectTests.value.split("\n").map((item) => item.trim()).filter(Boolean)
      }
    );
  } catch (error) { fail(error) }
}

async function generatePersonalizedProject(): Promise<void> {
  if (!activity.value || activity.value.type !== "project" || !projectGoal.value.trim()) return;
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
  } catch (error) { fail(error) } finally { projectGenerating.value = false }
}

async function submit(): Promise<void> {
  if (!activity.value) return;
  const isCode = activity.value.type === "code" || activity.value.type === "debug";
  try {
    submission.value = await api.submit(studentId.value, courseId.value, activity.value.id,
      isCode ? { language: activity.value.evaluation.runtime?.language, source_code: code.value } : { response: answer.value });
    profile.value = { student_id: studentId.value, course_id: courseId.value, mastery: submission.value.mastery_updated };
    next.value = submission.value.next_activity;
  } catch (error) { fail(error) }
}

onMounted(async () => {
  try {
    await fetchApiHealth(); connection.value = "online";
    courses.value = await api.courses(); await loadCourse(courseId.value);
  } catch (error) { connection.value = "offline"; fail(error) }
  finally { loading.value = false }
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span>&lt;/&gt;</span><div><strong>词元研究所</strong><small>CIYUAN · CODE LAB</small></div></div>
      <nav class="course-nav">
        <p>我的课程</p>
        <button v-for="item in courses" :key="item.id" :class="{ active: courseId === item.id }" @click="loadCourse(item.id)">
          <b>{{ item.id === "data_structures" ? "DS" : item.id.toUpperCase() }}</b>
          <span><strong>{{ item.title }}</strong><small>{{ item.implemented_core_concepts }} 个知识点</small></span>
        </button>
      </nav>
      <div class="sidebar-progress"><div><span>课程进度</span><strong>{{ masteredCount }}/{{ knowledge.length }}</strong></div><i><span :style="{ width: `${knowledge.length ? masteredCount / knowledge.length * 100 : 0}%` }"></span></i><small>由测评、练习和代码验证持续更新</small></div>
      <div class="school-note"><b>AI + 经管实践</b><p>计算机课程是核心，财经场景仅进入课后综合项目。</p></div>
      <div class="connection" :data-state="connection"><i></i> API {{ connection === "online" ? "服务正常" : connection === "offline" ? "未连接" : "连接中" }}</div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div><p class="eyebrow">PERSONAL LEARNING TERMINAL / {{ courseId.toUpperCase() }}</p><h1>{{ selectedCourse?.title ?? "课程工作台" }}</h1><div class="system-status"><span><i></i>课程知识库在线</span><span><i></i>三智能体协作</span><span><i></i>确定性代码验证</span></div></div>
        <label>学习者会话<input v-model="studentId" aria-label="学习者会话标识" @change="rememberStudent" /><small>LOCAL PROFILE</small></label>
      </header>
      <div v-if="notice" class="notice" role="status" aria-live="polite" @click="notice = ''">{{ notice }}<span>×</span></div>
      <nav class="tabs">
        <button :class="{ active: tab === 'overview' }" :aria-current="tab === 'overview' ? 'page' : undefined" @click="tab = 'overview'"><span>01</span>课程概览</button>
        <button :class="{ active: tab === 'path' }" :aria-current="tab === 'path' ? 'page' : undefined" @click="tab = 'path'"><span>02</span>学习路径</button>
        <button :class="{ active: tab === 'tutor' }" :aria-current="tab === 'tutor' ? 'page' : undefined" @click="tab = 'tutor'"><span>03</span>AI 辅导</button>
        <button :class="{ active: tab === 'practice' }" :aria-current="tab === 'practice' ? 'page' : undefined" @click="tab = 'practice'"><span>04</span>练习工坊</button>
      </nav>
      <div v-if="loading" class="loading" role="status" aria-live="polite"><i></i>正在同步课程与学情数据…</div>

      <template v-else-if="tab === 'overview'">
        <section class="hero-card">
          <div><p class="eyebrow">CURRENT COURSE / BUILD YOUR SKILL TREE</p><h2>理解知识。编写代码。验证能力。</h2><p>三智能体协同制定路径、提供有依据的辅导，并在输出前执行质量门禁。</p>
            <button v-if="next" @click="openNextActivity">继续下一项学习</button>
            <button v-else @click="notice = '请完成下方快速能力基线'">建立能力基线</button>
          </div>
          <div class="mastery-orbit" :style="{ '--mastery': `${averageMastery * 3.6}deg` }"><div><strong>{{ averageMastery }}%</strong><span>当前已测知识<br />平均掌握度</span></div></div>
        </section>
        <section class="metrics">
          <article><span>课程知识点</span><strong>{{ knowledge.length }}</strong><small>统一课程包</small></article>
          <article><span>已有证据</span><strong>{{ profile?.mastery.length ?? 0 }}</strong><small>测评与练习记录</small></article>
          <article><span>达到掌握</span><strong>{{ masteredCount }}</strong><small>分数 ≥ 60%</small></article>
          <article><span>实践活动</span><strong>{{ activities.length }}</strong><small>练习与综合项目</small></article>
        </section>
        <section v-if="diagnostic" class="panel assessment">
          <header><div><p class="eyebrow">{{ diagnostic.phase === "initial" ? "DIAGNOSTIC" : "REASSESSMENT" }}</p><h2>{{ diagnostic.title }}</h2></div><p>{{ diagnostic.instructions }}</p></header>
          <div class="diagnostic-list">
            <article v-for="(item, index) in diagnostic.items" :key="item.exercise_id">
              <header><em>{{ String(index + 1).padStart(2, "0") }}</em><div><strong>{{ item.prompt }}</strong><small>{{ item.concept_ids.join(" · ") }}</small></div></header>
              <div><button v-for="option in item.options" :key="option.id" :class="{ active: diagnosticAnswers[item.exercise_id] === option.id }" @click="diagnosticAnswers[item.exercise_id] = option.id"><b>{{ option.id }}</b>{{ option.text }}</button></div>
            </article>
          </div>
          <footer class="diagnostic-actions"><span>{{ Object.keys(diagnosticAnswers).length }} / {{ diagnostic.items.length }} 已作答</span><button class="primary" :disabled="!diagnosticComplete" @click="submitDiagnostic">{{ diagnostic.phase === "initial" ? "提交诊断并生成路径" : "提交重测并更新画像" }}</button></footer>
          <div v-if="diagnosticResult" class="diagnostic-result"><strong>本轮 {{ diagnosticResult.correct_count }} / {{ diagnosticResult.total_count }}</strong><span>结果已转化为学习证据，画像和后续路径已经刷新。</span><button v-if="diagnosticResult.phase === 'initial'" @click="loadDiagnostic('reassessment')">准备阶段重测</button></div>
        </section>
        <section class="panel">
          <header><div><p class="eyebrow">KNOWLEDGE MAP</p><h2>核心知识地图</h2></div><p>课程内容保持计算机专业主线，难度与前置关系由统一 Schema 管理。</p></header>
          <div class="knowledge-toolbar"><label><span>⌕</span><input v-model="knowledgeQuery" placeholder="搜索知识点名称或 ID" aria-label="搜索知识点" /></label><small>显示 {{ filteredKnowledge.length }} / {{ knowledge.length }} 个节点</small></div>
          <div class="knowledge-grid">
            <article v-for="item in filteredKnowledge" :key="item.id" :class="{ selected: selectedKnowledge?.id === item.id }" role="button" tabindex="0" @click="openKnowledgePoint(item.id)" @keydown.enter="openKnowledgePoint(item.id)"><div><b :data-level="item.difficulty">{{ difficulty(item.difficulty) }}</b><small>{{ item.id }}</small></div><h3>{{ item.title }}</h3><i><span :style="{ width: `${(masteryScore(item.id) ?? 0) * 100}%` }"></span></i><p>{{ masteryScore(item.id) !== null ? `掌握度 ${Math.round((masteryScore(item.id) ?? 0) * 100)}%` : "尚未建立学习证据" }}</p></article>
          </div>
          <div v-if="!filteredKnowledge.length" class="empty compact">没有匹配的知识点，请尝试其他关键词。</div>
          <section v-if="selectedKnowledge" class="lesson-detail">
            <header><div><span>{{ selectedKnowledge.id }}</span><h3>{{ selectedKnowledge.title }}</h3></div><button @click="selectedKnowledge = null">关闭</button></header>
            <p>{{ selectedKnowledge.lesson.summary }}</p>
            <div><article><b>学习目标</b><ul><li v-for="item in selectedKnowledge.learning_objectives" :key="item">{{ item }}</li></ul></article><article><b>关键要点</b><ul><li v-for="item in selectedKnowledge.lesson.key_points" :key="item">{{ item }}</li></ul></article><article><b>常见误区</b><ul><li v-for="item in selectedKnowledge.lesson.common_mistakes" :key="item">{{ item }}</li></ul></article></div>
            <section v-if="selectedKnowledge.lesson.learning_sequence?.length" class="lesson-sequence"><b>建议学习顺序</b><ol><li v-for="step in selectedKnowledge.lesson.learning_sequence" :key="step.title"><strong>{{ step.title }}</strong><span>{{ step.content }}</span></li></ol></section>
            <section v-if="selectedKnowledge.lesson.worked_example" class="worked-example"><header><b>分步例题</b><span>{{ selectedKnowledge.lesson.worked_example.problem }}</span></header><ol><li v-for="step in selectedKnowledge.lesson.worked_example.steps" :key="step">{{ step }}</li></ol><pre><code>{{ selectedKnowledge.lesson.worked_example.code }}</code></pre><p>{{ selectedKnowledge.lesson.worked_example.reflection }}</p></section>
            <section v-if="selectedKnowledge.lesson.checkpoint" class="lesson-checkpoint"><b>立即检验</b><p>{{ selectedKnowledge.lesson.checkpoint.prompt }}</p><small>{{ selectedKnowledge.lesson.checkpoint.guidance }}</small></section>
          </section>
        </section>
      </template>

      <template v-else-if="tab === 'path'">
        <section v-if="profile" class="split-layout">
          <div class="panel path-panel"><header><div><p class="eyebrow">ADAPTIVE PATH</p><h2>个性化学习路径</h2></div><p>由掌握度和前置关系驱动，不由模型自由编造。</p></header>
            <div v-if="stages.length" class="stage-list"><article v-for="(stage, index) in stages" :key="stage.stage"><em>{{ index + 1 }}</em><div><small>{{ stage.stage }}</small><h3>{{ stage.objective }}</h3><p>{{ stage.reason }}</p><b v-for="id in stage.knowledge_point_ids" :key="id">{{ id }}</b></div></article></div>
            <div v-else class="empty">当前路径来自实时下一任务推荐；重新建立能力基线可生成三阶段计划。</div>
          </div>
          <aside class="next-card"><p class="eyebrow">NEXT BEST ACTION</p><span>{{ activityType(next?.activity_type ?? "concept") }}</span><h2>{{ next?.activity_id ?? "等待规划" }}</h2><p>{{ next?.reason }}</p><button v-if="next" @click="openNextActivity">进入学习活动</button></aside>
        </section>
        <section v-else class="panel empty">请先在课程概览完成快速能力基线。</section>
      </template>

      <template v-else-if="tab === 'tutor'">
        <section class="tutor-layout">
          <div class="panel tutor"><header><div><p class="eyebrow">GROUNDED TUTOR</p><h2>有依据的课程辅导</h2></div><p>回答必须来自已审核课程资料；依据不足时明确拒答。</p></header>
            <div class="chat"><article><b>课程辅导智能体</b><p>可以询问当前课程的概念、边界、调试思路或算法前提。</p></article><article v-if="qa" :data-status="qa.status"><b>{{ qa.status === "answered" ? "已通过质量监督" : "依据不足" }}</b><p>{{ qa.answer || "当前资料不足以支持这个问题，我不会编造答案。" }}</p><div><span v-for="citation in qa.citations" :key="citation.chunk_id">{{ citation.source_id }} · {{ Math.round(citation.score * 100) }}%</span></div><ol class="trace"><li v-for="step in qa.trace" :key="`${step.component}-${step.status}`" :data-status="step.status"><b>{{ step.component }}</b><span>{{ step.detail }}</span></li></ol></article></div>
            <div class="composer"><textarea v-model="question" rows="3"></textarea><button class="primary" :disabled="qaLoading" @click="ask">{{ qaLoading ? "检索中…" : "发送问题" }}</button></div>
          </div>
          <aside class="agent-stack"><div class="agent-title"><span>AGENT PIPELINE</span><b>实时协作轨迹</b></div><article><em>01</em><div><strong>学情规划智能体</strong><p>选择合法的下一活动</p></div><i>READY</i></article><article class="active"><em>02</em><div><strong>课程辅导智能体</strong><p>基于 RAG 组织讲解</p></div><i>ACTIVE</i></article><article><em>03</em><div><strong>质量监督智能体</strong><p>检查引用、安全与事实</p></div><i>GUARD</i></article></aside>
        </section>
      </template>

      <template v-else>
        <section v-if="courseId === 'python'" class="panel adaptive-lab">
          <header><div><p class="eyebrow">ADAPTIVE CODE LAB</p><h2>个性化 Python 编程挑战</h2></div><p>根据真实测评与代码证据选择薄弱点；题目变式由规则生成，答案由隐藏测试判定。</p></header>
          <div v-if="!profile" class="adaptive-empty"><strong>先完成能力诊断</strong><span>建立初始画像后，系统才能选择你的薄弱知识点。</span><button class="primary" @click="tab = 'overview'">前往诊断</button></div>
          <div v-else-if="!adaptiveProblem" class="adaptive-empty"><strong>准备生成第一道个性化题目</strong><span>系统优先选择掌握度最低且已有可靠题型的知识点。</span><button class="primary" :disabled="adaptiveLoading" @click="generateAdaptiveProblem()">{{ adaptiveLoading ? "生成中…" : "生成我的新题" }}</button></div>
          <template v-else>
            <div class="adaptive-heading"><div><span v-for="concept in adaptiveProblem.concept_ids" :key="concept">{{ concept }}</span><h3>{{ adaptiveProblem.title }}</h3></div><b>{{ difficulty(adaptiveProblem.difficulty) }}</b></div>
            <p class="prompt">{{ adaptiveProblem.prompt }}</p>
            <div class="adaptive-spec"><section><strong>约束</strong><ul><li v-for="item in adaptiveProblem.constraints" :key="item">{{ item }}</li></ul></section><section><strong>公开样例</strong><div v-for="(item, index) in adaptiveProblem.public_examples" :key="index"><code>输入：{{ item.input }}</code><code>输出：{{ item.expected_output }}</code></div></section></div>
            <div class="editor"><header><i></i><i></i><i></i><b>python · deterministic hidden tests</b></header><textarea v-model="adaptiveCode" spellcheck="false"></textarea></div>
            <footer class="adaptive-actions"><small>{{ adaptiveProblem.generation_notice }}</small><button class="primary" :disabled="adaptiveLoading || !adaptiveCode.trim()" @click="submitAdaptiveProblem">{{ adaptiveLoading ? "验证中…" : "运行并提交" }}</button></footer>
            <div v-if="adaptiveSubmission" class="verification" :data-pass="adaptiveSubmission.verification.accepted"><strong>{{ adaptiveSubmission.verification.accepted ? "挑战通过，画像已更新" : "尚未通过隐藏测试" }}</strong><p>{{ adaptiveSubmission.feedback }}</p><small>通过 {{ adaptiveSubmission.verification.passed_tests }} / {{ adaptiveSubmission.verification.total_tests }} 个测试</small><button v-if="adaptiveSubmission.verification.accepted" class="primary" @click="generateAdaptiveProblem(true)">进入下一道变式题</button></div>
          </template>
        </section>
        <section class="practice-layout">
          <aside class="panel activity-list"><header><div><p class="eyebrow">ACTIVITIES</p><h2>练习工坊</h2></div><small>{{ filteredActivities.length }} 项</small></header><div class="activity-filters"><button v-for="item in ([['all','全部'],['code','编程'],['debug','Debug'],['project','项目']] as const)" :key="item[0]" :class="{ active: activityFilter === item[0] }" :aria-pressed="activityFilter === item[0]" @click="activityFilter = item[0]">{{ item[1] }}</button></div><div class="activity-scroll"><button v-for="item in filteredActivities" :key="item.id" :class="{ active: activity?.id === item.id }" @click="openActivity(item.id)"><span>{{ activityType(item.type) }}</span><strong>{{ item.title }}</strong><small>{{ item.id }} · {{ item.estimated_minutes }} 分钟</small></button><p v-if="!filteredActivities.length" class="empty compact">当前课程暂无此类活动</p></div></aside>
          <div class="panel activity-workspace"><template v-if="activity"><div class="activity-title"><div><span>{{ activityType(activity.type) }}</span><h2>{{ activity.title }}</h2><small>{{ activity.id }}</small></div><b>{{ difficulty(activity.difficulty) }}</b></div><p class="prompt">{{ activity.prompt || activity.summary }}</p>
            <section v-if="scenario" class="scenario-card" :data-mode="scenario.mode"><header><div><span>固定合成场景</span><strong>经管背景只服务课程综合实践</strong></div><b>隐私安全</b></header><p>{{ scenario.context }}</p><ul><li v-for="item in scenario.constraints" :key="item">{{ item }}</li></ul><footer><span v-for="source in scenario.source_refs" :key="source">{{ source }}</span><small>{{ scenario.notice }}</small></footer></section>
            <section v-if="activity.type === 'project'" class="project-generator"><header><div><small>PERSONALIZED PROJECT</small><h3>按当前能力生成综合项目</h3></div><b>不发送身份信息</b></header><label>你希望重点提升什么？<textarea v-model="projectGoal" rows="3"></textarea></label><button class="primary" :disabled="projectGenerating" @click="generatePersonalizedProject">{{ projectGenerating ? "生成中…" : "生成我的项目" }}</button>
              <article v-if="generatedProject"><header><div><small>{{ generatedProject.degraded ? "固定安全版本" : `${generatedProject.provider} · ${generatedProject.model}` }}</small><h3>{{ generatedProject.title }}</h3></div><b>AI生成内容</b></header><p>{{ generatedProject.scenario_context }}</p><div class="generated-columns"><section><strong>任务</strong><ol><li v-for="item in generatedProject.tasks" :key="item">{{ item }}</li></ol></section><section><strong>约束</strong><ul><li v-for="item in generatedProject.constraints" :key="item">{{ item }}</li></ul></section></div><div class="dataset-preview"><strong>固定合成数据 · {{ generatedProject.dataset.filename }}</strong><div><table><thead><tr><th v-for="column in generatedProject.dataset.columns" :key="column">{{ column }}</th></tr></thead><tbody><tr v-for="(row, index) in generatedProject.dataset.rows" :key="index"><td v-for="column in generatedProject.dataset.columns" :key="column">{{ row[column] ?? "—" }}</td></tr></tbody></table></div><small>SHA-256：{{ generatedProject.dataset.sha256 }}</small></div><footer><span v-for="source in generatedProject.source_refs" :key="source">{{ source }}</span><small>{{ generatedProject.ai_generated_notice }}</small></footer></article>
            </section>
            <section v-if="activity.type === 'project'" class="project-objectives"><div><b>计算机能力目标</b><span v-for="item in activity.computer_science_objectives" :key="item">{{ item }}</span></div><div v-if="activity.business_context_objectives.length"><b>场景理解目标</b><span v-for="item in activity.business_context_objectives" :key="item">{{ item }}</span></div></section>
            <div v-if="activity.evaluation.options" class="options"><label v-for="option in activity.evaluation.options" :key="option.id" :class="{ selected: answer === option.id }"><input v-model="answer" type="radio" :value="option.id" /><b>{{ option.id }}</b><span>{{ option.text }}</span></label></div>
            <div v-else-if="activity.type === 'code' || activity.type === 'debug'" class="editor"><header><i></i><i></i><i></i><b>{{ activity.evaluation.runtime?.language }} · isolated sandbox</b></header><textarea v-model="code" spellcheck="false"></textarea></div>
            <section v-else-if="activity.type === 'project'" class="project-submit"><label>实现与验证说明<textarea v-model="projectSummary" rows="6" placeholder="说明模块设计、关键算法、异常处理和测试结果（至少 30 字）"></textarea></label><label>代码仓库或制品链接（可选）<input v-model="projectRepository" placeholder="https://gitee.com/..." /></label><label>测试证据（每行一条）<textarea v-model="projectTests" rows="4" placeholder="pytest: 12 passed&#10;边界输入：空文件返回明确错误"></textarea></label><button class="primary" @click="submitProject">记录项目证据</button></section>
            <textarea v-else v-model="answer" class="answer-box" rows="7" placeholder="输入你的回答…"></textarea><button v-if="activity.type !== 'project'" class="primary" @click="submit">提交并验证</button>
            <section class="hint-box"><button @click="requestHint">{{ hint ? `继续提示（${hintLevel}/3）` : "获取分层提示" }}</button><p v-if="hint"><b>第 {{ hint.level }} 层提示</b>{{ hint.hint }}</p></section>
            <div v-if="submission" class="verification" :data-pass="submission.verification?.accepted ?? false"><strong>{{ submission.verification?.accepted ? "验证通过" : "反馈已生成" }}</strong><p>{{ submission.feedback }}</p><small v-if="submission.verification">通过 {{ submission.verification.passed_tests }} / {{ submission.verification.total_tests }} 个测试</small></div>
            <div v-if="projectSubmission" class="verification" data-pass="true"><strong>项目证据已记录</strong><p>{{ projectSubmission.feedback }}</p><ul><li v-for="item in projectSubmission.evidence_checklist" :key="item.item"><b>{{ item.present ? "✓" : "!" }} {{ item.item }}</b> — {{ item.detail }}</li></ul></div>
          </template><div v-else class="empty">从左侧选择一道练习，或按照学习路径进入推荐活动。</div></div>
        </section>
      </template>
    </main>
  </div>
</template>
