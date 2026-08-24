<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import {
  ApiError, api, fetchApiHealth,
  type ActivityDetail, type ActivitySummary, type CourseId, type CourseSummary,
  type KnowledgePoint, type LearnerProfile, type NextActivity, type PlanStage,
  type QaResponse, type ScenarioContext, type SubmissionResult
} from "./services/api";

type Tab = "overview" | "path" | "tutor" | "practice";
const connection = ref<"connecting" | "online" | "offline">("connecting");
const loading = ref(true);
const notice = ref("");
const tab = ref<Tab>("overview");
const studentId = ref(localStorage.getItem("ciyuan-student-id") ?? "demo-student-01");
const courses = ref<CourseSummary[]>([]);
const courseId = ref<CourseId>("python");
const knowledge = ref<KnowledgePoint[]>([]);
const activities = ref<ActivitySummary[]>([]);
const profile = ref<LearnerProfile | null>(null);
const next = ref<NextActivity | null>(null);
const stages = ref<PlanStage[]>([]);
const activity = ref<ActivityDetail | null>(null);
const selfCheck = reactive<Record<string, boolean>>({});
const question = ref("数据清洗时应该如何处理缺失值和异常记录？");
const qa = ref<QaResponse | null>(null);
const qaLoading = ref(false);
const answer = ref("");
const code = ref("");
const submission = ref<SubmissionResult | null>(null);
const scenario = ref<ScenarioContext | null>(null);

const selectedCourse = computed(() => courses.value.find((item) => item.id === courseId.value));
const baselineItems = computed(() => knowledge.value.slice(0, 8));
const masteryMap = computed(() => Object.fromEntries((profile.value?.mastery ?? []).map((item) => [item.knowledge_point_id, item])));
const averageMastery = computed(() => {
  const items = profile.value?.mastery ?? [];
  return items.length ? Math.round(items.reduce((sum, item) => sum + item.score, 0) / items.length * 100) : 0;
});
const masteredCount = computed(() => (profile.value?.mastery ?? []).filter((item) => item.score >= .6).length);

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
  loading.value = true;
  notice.value = "";
  qa.value = null;
  activity.value = null;
  scenario.value = null;
  submission.value = null;
  try {
    const [kpResult, activityResult] = await Promise.all([api.knowledgePoints(id), api.activities(id)]);
    knowledge.value = kpResult.items;
    activities.value = activityResult;
    Object.keys(selfCheck).forEach((key) => delete selfCheck[key]);
    baselineItems.value.forEach((item) => { selfCheck[item.id] = false });
    try {
      profile.value = await api.profile(studentId.value, id);
      next.value = await api.nextActivity(studentId.value, id);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        profile.value = null; next.value = null; stages.value = [];
      } else throw error;
    }
  } catch (error) { fail(error) } finally { loading.value = false }
}

async function createBaseline(): Promise<void> {
  rememberStudent(); loading.value = true;
  try {
    const result = await api.assess(studentId.value, courseId.value, baselineItems.value.map((item) => ({
      knowledge_point_id: item.id, is_correct: selfCheck[item.id] ?? false
    })));
    profile.value = result.profile; stages.value = result.plan.stages; next.value = result.plan.next_activity;
    tab.value = "path"; notice.value = "能力基线已建立，个性化学习路径已生成。";
  } catch (error) { fail(error) } finally { loading.value = false }
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
      <div class="brand"><span>词</span><div><strong>词元研究所</strong><small>CIYUAN LAB</small></div></div>
      <nav class="course-nav">
        <p>我的课程</p>
        <button v-for="item in courses" :key="item.id" :class="{ active: courseId === item.id }" @click="loadCourse(item.id)">
          <b>{{ item.id === "data_structures" ? "DS" : item.id.toUpperCase() }}</b>
          <span><strong>{{ item.title }}</strong><small>{{ item.implemented_core_concepts }} 个知识点</small></span>
        </button>
      </nav>
      <div class="school-note"><b>AI + 经管实践</b><p>计算机课程是核心，财经场景仅进入课后综合项目。</p></div>
      <div class="connection" :data-state="connection"><i></i> API {{ connection === "online" ? "服务正常" : connection === "offline" ? "未连接" : "连接中" }}</div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div><p class="eyebrow">PERSONAL LEARNING WORKSPACE</p><h1>{{ selectedCourse?.title ?? "课程工作台" }}</h1></div>
        <label>学习者标识<input v-model="studentId" @change="rememberStudent" /></label>
      </header>
      <div v-if="notice" class="notice" @click="notice = ''">{{ notice }}<span>×</span></div>
      <nav class="tabs">
        <button :class="{ active: tab === 'overview' }" @click="tab = 'overview'">课程概览</button>
        <button :class="{ active: tab === 'path' }" @click="tab = 'path'">学习路径</button>
        <button :class="{ active: tab === 'tutor' }" @click="tab = 'tutor'">AI 辅导</button>
        <button :class="{ active: tab === 'practice' }" @click="tab = 'practice'">练习工坊</button>
      </nav>
      <div v-if="loading" class="loading"><i></i>正在同步课程与学情数据…</div>

      <template v-else-if="tab === 'overview'">
        <section class="hero-card">
          <div><p class="eyebrow">CURRENT COURSE</p><h2>从知识理解，到代码验证，再到综合应用</h2><p>三智能体协同制定路径、提供有依据的辅导，并在输出前执行质量门禁。</p>
            <button v-if="next" @click="openActivity(next.activity_id)">继续下一项学习</button>
            <button v-else @click="notice = '请完成下方快速能力基线'">建立能力基线</button>
          </div>
          <div class="mastery-orbit"><strong>{{ averageMastery }}%</strong><span>当前已测知识<br />平均掌握度</span></div>
        </section>
        <section class="metrics">
          <article><span>课程知识点</span><strong>{{ knowledge.length }}</strong><small>统一课程包</small></article>
          <article><span>已有证据</span><strong>{{ profile?.mastery.length ?? 0 }}</strong><small>测评与练习记录</small></article>
          <article><span>达到掌握</span><strong>{{ masteredCount }}</strong><small>分数 ≥ 60%</small></article>
          <article><span>实践活动</span><strong>{{ activities.length }}</strong><small>练习与综合项目</small></article>
        </section>
        <section v-if="!profile" class="panel assessment">
          <header><div><p class="eyebrow">BASELINE</p><h2>快速能力基线</h2></div><p>请按真实情况标记前 8 个知识点，初版据此生成起始路径。</p></header>
          <div class="assessment-list">
            <div v-for="(item, index) in baselineItems" :key="item.id"><em>{{ String(index + 1).padStart(2, "0") }}</em><span><strong>{{ item.title }}</strong><small>{{ item.id }}</small></span>
              <div><button :class="{ active: !selfCheck[item.id] }" @click="selfCheck[item.id] = false">需学习</button><button :class="{ active: selfCheck[item.id] }" @click="selfCheck[item.id] = true">已掌握</button></div>
            </div>
          </div><button class="primary" @click="createBaseline">生成个性化路径</button>
        </section>
        <section class="panel">
          <header><div><p class="eyebrow">KNOWLEDGE MAP</p><h2>核心知识地图</h2></div><p>课程内容保持计算机专业主线，难度与前置关系由统一 Schema 管理。</p></header>
          <div class="knowledge-grid">
            <article v-for="item in knowledge" :key="item.id"><div><b :data-level="item.difficulty">{{ difficulty(item.difficulty) }}</b><small>{{ item.id }}</small></div><h3>{{ item.title }}</h3><i><span :style="{ width: `${(masteryScore(item.id) ?? 0) * 100}%` }"></span></i><p>{{ masteryScore(item.id) !== null ? `掌握度 ${Math.round((masteryScore(item.id) ?? 0) * 100)}%` : "尚未建立学习证据" }}</p></article>
          </div>
        </section>
      </template>

      <template v-else-if="tab === 'path'">
        <section v-if="profile" class="split-layout">
          <div class="panel path-panel"><header><div><p class="eyebrow">ADAPTIVE PATH</p><h2>个性化学习路径</h2></div><p>由掌握度和前置关系驱动，不由模型自由编造。</p></header>
            <div v-if="stages.length" class="stage-list"><article v-for="(stage, index) in stages" :key="stage.stage"><em>{{ index + 1 }}</em><div><small>{{ stage.stage }}</small><h3>{{ stage.objective }}</h3><p>{{ stage.reason }}</p><b v-for="id in stage.knowledge_point_ids" :key="id">{{ id }}</b></div></article></div>
            <div v-else class="empty">当前路径来自实时下一任务推荐；重新建立能力基线可生成三阶段计划。</div>
          </div>
          <aside class="next-card"><p class="eyebrow">NEXT BEST ACTION</p><span>{{ activityType(next?.activity_type ?? "concept") }}</span><h2>{{ next?.activity_id ?? "等待规划" }}</h2><p>{{ next?.reason }}</p><button v-if="next" @click="openActivity(next.activity_id)">进入学习活动</button></aside>
        </section>
        <section v-else class="panel empty">请先在课程概览完成快速能力基线。</section>
      </template>

      <template v-else-if="tab === 'tutor'">
        <section class="tutor-layout">
          <div class="panel tutor"><header><div><p class="eyebrow">GROUNDED TUTOR</p><h2>有依据的课程辅导</h2></div><p>回答必须来自已审核课程资料；依据不足时明确拒答。</p></header>
            <div class="chat"><article><b>课程辅导智能体</b><p>可以询问当前课程的概念、边界、调试思路或算法前提。</p></article><article v-if="qa" :data-status="qa.status"><b>{{ qa.status === "answered" ? "已通过质量监督" : "依据不足" }}</b><p>{{ qa.answer || "当前资料不足以支持这个问题，我不会编造答案。" }}</p><div><span v-for="citation in qa.citations" :key="citation.chunk_id">{{ citation.source_id }} · {{ Math.round(citation.score * 100) }}%</span></div></article></div>
            <div class="composer"><textarea v-model="question" rows="3"></textarea><button class="primary" :disabled="qaLoading" @click="ask">{{ qaLoading ? "检索中…" : "发送问题" }}</button></div>
          </div>
          <aside class="agent-stack"><article><em>01</em><div><strong>学情规划智能体</strong><p>选择合法的下一活动</p></div></article><article class="active"><em>02</em><div><strong>课程辅导智能体</strong><p>基于 RAG 组织讲解</p></div></article><article><em>03</em><div><strong>质量监督智能体</strong><p>检查引用、安全与事实</p></div></article></aside>
        </section>
      </template>

      <template v-else>
        <section class="practice-layout">
          <aside class="panel activity-list"><header><div><p class="eyebrow">ACTIVITIES</p><h2>练习工坊</h2></div></header><button v-for="item in activities" :key="item.id" :class="{ active: activity?.id === item.id }" @click="openActivity(item.id)"><span>{{ activityType(item.type) }}</span><strong>{{ item.title }}</strong><small>{{ item.id }} · {{ item.estimated_minutes }} 分钟</small></button></aside>
          <div class="panel activity-workspace"><template v-if="activity"><div class="activity-title"><div><span>{{ activityType(activity.type) }}</span><h2>{{ activity.title }}</h2><small>{{ activity.id }}</small></div><b>{{ difficulty(activity.difficulty) }}</b></div><p class="prompt">{{ activity.prompt || activity.summary }}</p>
            <section v-if="scenario" class="scenario-card" :data-mode="scenario.mode"><header><div><span>{{ scenario.mode === "tuoling" ? "驼灵授权场景" : "固定合成场景" }}</span><strong>经管背景只服务课程综合实践</strong></div><b>{{ scenario.provider_status === "live" ? "API 在线" : "安全降级" }}</b></header><p>{{ scenario.context }}</p><ul><li v-for="item in scenario.constraints" :key="item">{{ item }}</li></ul><footer><span v-for="source in scenario.source_refs" :key="source">{{ source }}</span><small>{{ scenario.notice }}</small></footer></section>
            <section v-if="activity.type === 'project'" class="project-objectives"><div><b>计算机能力目标</b><span v-for="item in activity.computer_science_objectives" :key="item">{{ item }}</span></div><div v-if="activity.business_context_objectives.length"><b>场景理解目标</b><span v-for="item in activity.business_context_objectives" :key="item">{{ item }}</span></div></section>
            <div v-if="activity.evaluation.options" class="options"><label v-for="option in activity.evaluation.options" :key="option.id" :class="{ selected: answer === option.id }"><input v-model="answer" type="radio" :value="option.id" /><b>{{ option.id }}</b><span>{{ option.text }}</span></label></div>
            <div v-else-if="activity.type === 'code' || activity.type === 'debug'" class="editor"><header><i></i><i></i><i></i><b>{{ activity.evaluation.runtime?.language }} · isolated sandbox</b></header><textarea v-model="code" spellcheck="false"></textarea></div>
            <textarea v-else v-model="answer" class="answer-box" rows="7" placeholder="输入你的回答…"></textarea><button v-if="activity.type !== 'project'" class="primary" @click="submit">提交并验证</button>
            <div v-if="submission" class="verification" :data-pass="submission.verification?.accepted ?? false"><strong>{{ submission.verification?.accepted ? "验证通过" : "反馈已生成" }}</strong><p>{{ submission.feedback }}</p><small v-if="submission.verification">通过 {{ submission.verification.passed_tests }} / {{ submission.verification.total_tests }} 个测试</small></div>
          </template><div v-else class="empty">从左侧选择一道练习，或按照学习路径进入推荐活动。</div></div>
        </section>
      </template>
    </main>
  </div>
</template>
