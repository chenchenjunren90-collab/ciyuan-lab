<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { api, type ActivityDetail, type ActivitySummary, type KnowledgePoint, type KnowledgePointDetail, type LearnerProfile, type QaResponse, type SubmissionResult } from "../../services/api";
import { qaFeedbackLabel, serviceFailure, verificationUnavailable } from "../../services/workspaceState";
import SafeMarkdown from "../SafeMarkdown.vue";
import ClassroomCodeTask from "./ClassroomCodeTask.vue";
import AlgorithmLab from "./AlgorithmLab.vue";
import { traceForConcept } from "./algorithmTrace";
import { asCodeTask, chapters, courseNames, lessonScenes, orderKnowledge, readLessonPosition, recommendPoint, type FoundationCourse } from "./courseLearning";

const props = defineProps<{ courseId: FoundationCourse; studentId: string; points: KnowledgePoint[]; profile: LearnerProfile | null }>();
const emit = defineEmits<{ profileUpdated: [profile: LearnerProfile]; openProjects: []; openAssessment: [] }>();
const selected = ref(""), point = ref<KnowledgePointDetail | null>(null), exercises = ref<ActivitySummary[]>([]);
const activity = ref<ActivityDetail | null>(null), view = ref("learn"), sceneIndex = ref(0);
const loading = ref(false), taskLoading = ref(false), busy = ref(false), hintBusy = ref(false), asking = ref(false);
const error = ref(""), taskError = ref(""), qaError = ref(""), search = ref(""), code = ref(""), answer = ref("");
const question = ref(""), qa = ref<QaResponse | null>(null), result = ref<SubmissionResult | null>(null);
const hint = ref(""), hintLevel = ref(0), reflection = ref("");
let scope = 0, taskScope = 0, alive = true;
const name = computed(() => courseNames[props.courseId]);
const coursePoints = computed(() => props.points.filter(item => item.id.startsWith(props.courseId === 'c' ? 'C-' : 'DS-')));
const ordered = computed(() => { try { return orderKnowledge(coursePoints.value); } catch { return coursePoints.value; } });
const recommended = computed(() => { try { return recommendPoint(coursePoints.value, props.profile?.course_id === props.courseId ? props.profile : null); } catch { return ''; } });
const groups = computed(() => {
  const assigned = new Set<string>();
  const result = chapters[props.courseId].map(chapter => ({ title: chapter.title, points: ordered.value.filter(item => {
    const matches = chapter.prefixes.includes(item.id.split("-")[1] ?? "");
    if (matches) assigned.add(item.id);
    return matches;
  }) }));
  const extra = ordered.value.filter(item => !assigned.has(item.id));
  if (extra.length) result.push({ title: "补充知识", points: extra });
  return result.map(group => ({ ...group, points: group.points.filter(item => `${item.id} ${item.title}`.toLowerCase().includes(search.value.trim().toLowerCase())) })).filter(group => group.points.length);
});
const scenes = computed(() => point.value ? lessonScenes(point.value) : []);
const scene = computed(() => scenes.value[sceneIndex.value]);
const worked = computed(() => point.value?.lesson.worked_example);
const traceKind = computed(() => traceForConcept(selected.value));
const task = computed(() => activity.value ? asCodeTask(activity.value) : null);
const mastered = computed(() => new Set(props.profile?.mastery.filter(item => item.evidence_count > 0 && item.score >= .6).map(item => item.knowledge_point_id)));
const prerequisites = computed(() => (point.value?.prerequisites ?? []).map(id => ({ id, title: props.points.find(item => item.id === id)?.title ?? id, mastered: mastered.value.has(id) })));
const positionKey = () => `ciyuan-course-classroom:${props.studentId}:${props.courseId}`;
const taskKey = () => `${positionKey()}:${activity.value?.id}:code`;
function saveValue(key: string, value: string) { try { sessionStorage.setItem(key, value); } catch { /* Storage is optional; live work continues. */ } }
function restoredCode(): string { try { return sessionStorage.getItem(taskKey()) ?? ""; } catch { return ""; } }

async function selectPoint(id: string) {
  if (busy.value || !coursePoints.value.some(item => item.id === id)) return;
  const token = ++scope; ++taskScope;
  selected.value = id; point.value = null; activity.value = null; exercises.value = [];
  error.value = ""; taskError.value = ""; qa.value = null; qaError.value = ""; asking.value = false;
  question.value = ""; reflection.value = ""; result.value = null; hint.value = ""; hintBusy.value = false;
  view.value = "learn"; sceneIndex.value = 0; loading.value = true; taskLoading.value = false;
  try {
    const [detail, items] = await Promise.all([api.knowledgePoint(props.courseId, id), api.activities(props.courseId, { knowledgePointId: id })]);
    if (!alive || token !== scope) return;
    point.value = detail; exercises.value = items.filter(item => item.type !== "project");
    saveValue(positionKey(), id);
    const first = exercises.value.find(item => item.type === "objective") ?? exercises.value[0];
    if (first) void selectTask(first.id);
  } catch (cause) { if (alive && token === scope) error.value = serviceFailure(cause); }
  finally { if (alive && token === scope) loading.value = false; }
}

async function selectTask(id: string) {
  if (busy.value) return;
  const token = ++taskScope, lessonToken = scope;
  taskLoading.value = true; activity.value = null; result.value = null; hint.value = ""; hintLevel.value = 0;
  hintBusy.value = false; answer.value = ""; code.value = ""; taskError.value = "";
  try {
    const detail = await api.activity(props.courseId, id);
    if (!alive || token !== taskScope || lessonToken !== scope) return;
    activity.value = detail; code.value = restoredCode() || asCodeTask(detail).starter_code;
  } catch (cause) { if (alive && token === taskScope) taskError.value = serviceFailure(cause); }
  finally { if (alive && token === taskScope) taskLoading.value = false; }
}
async function submit() {
  const current = activity.value;
  if (!current || busy.value || taskLoading.value) return;
  const isCode = current.type === "code" || current.type === "debug";
  if (!(isCode ? code.value : answer.value).trim()) { taskError.value = "请先填写答案。"; return; }
  const token = taskScope;
  busy.value = true; taskError.value = ""; result.value = null;
  try {
    const response = await api.submit(props.studentId, props.courseId, current.id, isCode
      ? { language: current.evaluation.runtime?.language, source_code: code.value }
      : { response: answer.value });
    if (!alive || token !== taskScope) return;
    result.value = response;
    const mastery = new Map((props.profile?.mastery ?? []).map(item => [item.knowledge_point_id, item]));
    response.mastery_updated.forEach(item => mastery.set(item.knowledge_point_id, item));
    emit("profileUpdated", { student_id: props.studentId, course_id: props.courseId, mastery: [...mastery.values()] });
  } catch (cause) { if (alive && token === taskScope) taskError.value = serviceFailure(cause); }
  finally { if (alive && token === taskScope) busy.value = false; }
}
async function requestHint() {
  if (!activity.value || hintBusy.value || hintLevel.value >= 3) return;
  const token = taskScope;
  hintBusy.value = true;
  try {
    const response = await api.hint(props.studentId, props.courseId, activity.value.id, (hintLevel.value + 1) as 1 | 2 | 3, { sourceCode: code.value, diagnostics: result.value?.verification?.diagnostics });
    if (alive && token === taskScope) { hint.value = response.hint; hintLevel.value = response.level; }
  } catch (cause) { if (alive && token === taskScope) taskError.value = serviceFailure(cause); }
  finally { if (alive && token === taskScope) hintBusy.value = false; }
}
async function ask() {
  if (!question.value.trim() || asking.value) return;
  const token = scope;
  asking.value = true; qa.value = null; qaError.value = "";
  try {
    // Preserve the student's literal question; server applies course isolation and evidence gates.
    const response = await api.ask(props.studentId, props.courseId, question.value.trim());
    if (alive && token === scope) qa.value = response;
  } catch (cause) { if (alive && token === scope) qaError.value = serviceFailure(cause); }
  finally { if (alive && token === scope) asking.value = false; }
}
watch(code, value => { if (activity.value) saveValue(taskKey(), value); });
watch(() => [props.courseId, props.studentId, props.points.map(item => item.id).join(",")], () => {
  if (!coursePoints.value.length) return;
  let saved = ""; try { saved = readLessonPosition(sessionStorage, positionKey()); } catch { /* SSR / unavailable storage */ }
  void selectPoint(coursePoints.value.some(item => item.id === saved) ? saved : recommended.value);
}, { immediate: true });
onBeforeUnmount(() => { alive = false; ++scope; ++taskScope; });
</script>

<template>
  <section class="foundation-classroom">
    <header class="masthead"><div><small>{{ name }} · 分段学习与验证</small><h1>把每一步，想明白。</h1><p>{{ courseId === 'c' ? '从变量走到指针与内存，观察对象怎样被程序改变。' : '从结构走到算法，跟踪每一次入队、移动和边界收缩。' }}</p></div><div class="entry-actions"><button @click="emit('openAssessment')">能力摸底</button><button @click="emit('openProjects')">进入项目实践 →</button></div></header>
    <div class="workspace">
      <aside class="syllabus" aria-label="课程目录"><label>查找知识点<input v-model="search" placeholder="名称或知识点编号" /></label><button class="recommend" :disabled="busy || !recommended" @click="selectPoint(recommended)">从推荐起点继续 →</button><p class="small">{{ profile?.mastery.some(item => item.evidence_count > 0) ? '推荐依据：已有测评与前置关系' : '尚无测评证据，按前置顺序学习' }}</p><section v-for="group in groups" :key="group.title"><h2>{{ group.title }}</h2><button v-for="item in group.points" :key="item.id" :disabled="busy" :class="{ selected: selected === item.id }" :aria-current="selected === item.id ? 'step' : undefined" @click="selectPoint(item.id)"><span>{{ item.title }}</span><small>{{ mastered.has(item.id) ? '已掌握' : item.id }}</small></button></section><p v-if="!groups.length">没有匹配的知识点。</p></aside>
      <section class="lesson" aria-label="当前知识点课堂">
        <p v-if="loading" role="status">正在读取课程讲解与练习…</p><div v-else-if="error" role="alert"><p>{{ error }}</p><button @click="selectPoint(selected)">重新加载</button></div>
        <template v-else-if="point">
          <header class="lesson-heading"><small>{{ point.id }} · 约 {{ point.estimated_minutes }} 分钟 · {{ point.status === 'reviewed' ? '已审核' : '教学草稿，待教师审核' }}</small><h2>{{ point.title }}</h2><p v-for="objective in point.learning_objectives" :key="objective">{{ objective }}</p><div v-if="prerequisites.length" class="prerequisites"><span>前置知识</span><button v-for="item in prerequisites" :key="item.id" :disabled="busy" @click="selectPoint(item.id)">{{ item.title }} {{ item.mastered ? '✓' : '↗' }}</button></div></header>
          <nav class="views" aria-label="课堂学习环节"><button v-for="[id, title] in [['learn','分段讲解'],['lab','交互实验'],['practice','随堂练习'],['ask','课程答疑']]" :key="id" :aria-pressed="view === id" @click="view = id">{{ title }}</button></nav>
          <section v-if="view === 'learn'" class="reading">
            <div v-if="scene" class="scene"><small>讲解 {{ sceneIndex + 1 }} / {{ scenes.length }}</small><h3>{{ scene.title }}</h3><SafeMarkdown :source="scene.content" /><div class="controls"><button :disabled="sceneIndex === 0" @click="sceneIndex--">上一段</button><button :disabled="sceneIndex === scenes.length - 1" @click="sceneIndex++">下一段 →</button></div></div>
            <article v-if="worked" class="worked"><h3>跟着例题推演</h3><p>{{ worked.problem }}</p><pre><code>{{ worked.code }}</code></pre><ol><li v-for="step in worked.steps" :key="step">{{ step }}</li></ol><p>{{ worked.reflection }}</p></article>
            <article v-else><h3>例子与解释</h3><SafeMarkdown v-for="example in point.lesson.examples" :key="example" :source="example" /></article>
            <article class="mistakes"><h3>容易出错的地方</h3><ul><li v-for="mistake in point.lesson.common_mistakes" :key="mistake">{{ mistake }}</li></ul></article>
            <label v-if="point.lesson.checkpoint" class="reflection">先说说你的理解：{{ point.lesson.checkpoint.prompt }}<textarea v-model="reflection" rows="3" placeholder="写下预测，再去实验或练习区验证。此处不计分。" /><small>{{ point.lesson.checkpoint.guidance }}</small></label>
            <footer class="reading-footer"><span>讲解来源：{{ point.source_refs.join('、') }}</span><button @click="view = 'practice'">用练习检验理解 →</button></footer>
          </section>
          <section v-else-if="view === 'lab'"><p v-if="!traceKind" class="small">当前知识点暂无专属演示。你可以探索本课程的实验主题，再回到本节练习。</p><AlgorithmLab :key="selected" :course-id="courseId" :initial-kind="traceKind ?? (courseId === 'c' ? 'array' : 'stack')" /></section>
          <section v-else-if="view === 'practice'" class="practice">
            <nav class="task-picker" aria-label="本节练习"><button v-for="item in exercises" :key="item.id" :disabled="busy" :aria-pressed="activity?.id === item.id" @click="selectTask(item.id)">{{ item.title }}</button></nav>
            <p v-if="taskLoading" role="status">正在读取题目…</p><p v-if="taskError" role="alert">{{ taskError }}</p>
            <template v-if="activity && !taskLoading"><ClassroomCodeTask v-if="task && ['code','debug'].includes(activity.type)" v-model="code" :task="task" :language="activity.evaluation.runtime?.language" :result="result" :loading="busy" :hint="hint" :hint-loading="hintBusy" :hint-exhausted="hintLevel >= 3" label="本节编程任务" @submit="submit" @hint="requestHint" />
              <form v-else @submit.prevent="submit"><h3>{{ activity.title }}</h3><SafeMarkdown :source="activity.prompt ?? ''" /><fieldset v-if="activity.evaluation.options" :disabled="busy"><legend>选择答案</legend><label v-for="option in activity.evaluation.options" :key="option.id"><input v-model="answer" type="radio" :value="option.id" :name="activity.id" />{{ option.id }}. {{ option.text }}</label></fieldset><textarea v-else v-model="answer" :disabled="busy" rows="5" aria-label="练习答案" /><button :disabled="busy" type="submit">{{ busy ? '正在验证…' : '提交并验证' }}</button><div v-if="result" role="status"><b>{{ verificationUnavailable(result) ? '验证服务暂不可用' : !result.verification ? '评分反馈' : result.verification.accepted ? '验证通过' : '查看反馈后再试' }}</b><p>{{ result.feedback }}</p></div></form>
              <p v-if="result && activity.reflection_prompt">复盘：{{ activity.reflection_prompt }}</p><button v-if="result && !verificationUnavailable(result)" :disabled="busy || !recommended" @click="selectPoint(recommended)">继续推荐知识点 →</button>
            </template><p v-else-if="!taskLoading && !exercises.length">本知识点暂无可用练习。</p>
          </section>
          <section v-else class="tutor"><p>提问当前课程的概念、代码或算法边界。回答依据已审核课程资料，证据不足时会明确提示。</p><form @submit.prevent="ask"><label>你的问题<textarea v-model="question" rows="4" maxlength="2000" :placeholder="courseId === 'c' ? '例如：为什么修改指针指向的值会改变原变量？' : '例如：为什么二分查找命中后还要继续缩小右边界？'" /></label><button :disabled="asking || !question.trim()">{{ asking ? '正在检索与复核…' : '发送问题' }}</button></form><p v-if="qaError" role="alert">{{ qaError }}</p><article v-if="qa"><h3>{{ qaFeedbackLabel(qa) }}</h3><SafeMarkdown :source="qa.answer || '当前没有足够的课程证据。'" /><ul><li v-for="citation in qa.citations" :key="citation.chunk_id">{{ citation.source_title ?? citation.source_id }} · {{ citation.chunk_id }}</li></ul><details><summary>检索与复核过程</summary><p v-for="(step, i) in qa.trace" :key="i">{{ step.detail }}</p></details></article></section>
        </template><p v-else>课程目录载入后即可选择知识点开始学习。</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.foundation-classroom{color:var(--ink);font-size:16px;}.masthead{display:flex;justify-content:space-between;gap:24px;align-items:center;margin:12px 0 28px;}.masthead h1{font-size:clamp(25px,3vw,36px);margin:10px 0;}.masthead p,.small,small{color:var(--muted);line-height:1.7;}.entry-actions{display:flex;gap:8px;flex-wrap:wrap;}button,input,textarea{font:inherit;color:var(--ink);border:1px solid var(--line);background:var(--surface-raised);border-radius:8px;}button{min-height:44px;padding:10px 14px;cursor:pointer;}button:disabled{opacity:.45;cursor:default;}input,textarea{padding:10px;max-width:100%;}textarea{width:100%;resize:vertical;line-height:1.7;}.workspace{display:grid;grid-template-columns:245px minmax(0,1fr);gap:24px;}.syllabus{max-height:calc(100vh - 160px);overflow:auto;position:sticky;top:20px;padding:16px;background:var(--surface-raised);border:1px solid var(--line);border-radius:12px;align-self:start;}.syllabus label{display:grid;gap:8px;font-size:13px;}.syllabus input{width:100%;}.syllabus h2{font-size:13px;margin:24px 0 10px;color:var(--muted);}.syllabus button{display:grid;width:100%;text-align:left;gap:5px;margin:4px 0;border-color:transparent;background:transparent;font-size:13px;}.syllabus .selected{border-color:var(--accent);background:var(--accent-pale);color:var(--accent-ink);}.syllabus .recommend{margin-top:12px;color:var(--accent-ink);border-color:var(--line);}.lesson{min-width:0;}.lesson-heading{border-bottom:1px solid var(--line);padding-bottom:20px;}.lesson-heading h2{margin:10px 0;font-size:25px;}.lesson-heading p{font-size:14px;line-height:1.7;margin:6px 0;}.prerequisites{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;margin-top:15px;}.views{display:flex;gap:8px;margin:20px 0;flex-wrap:wrap;}.views [aria-pressed=true],.task-picker [aria-pressed=true]{background:var(--accent-pale);color:var(--accent-ink);border-color:var(--accent);}.reading>article,.scene,.reflection,.tutor>article,.practice>form{display:block;margin-bottom:20px;padding:24px;background:var(--surface-raised);border:1px solid var(--line);border-radius:12px;line-height:1.85;}.reading h3{margin:0 0 14px;}.scene h3{margin-top:8px;}.controls{display:flex;justify-content:space-between;margin-top:20px;}pre{white-space:pre;overflow:auto;padding:18px;background:var(--code);color:var(--code-ink);border-radius:8px;font:13px/1.8 Consolas,monospace;}.reading li{margin:8px 0;}.reflection textarea{display:block;margin:12px 0;}.reading-footer{display:flex;justify-content:space-between;gap:20px;align-items:center;flex-wrap:wrap;font-size:12px;overflow-wrap:anywhere;}.task-picker{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;}fieldset{border:0;padding:0;margin:20px 0;}fieldset label{display:flex;gap:10px;align-items:center;min-height:48px;line-height:1.7;}form>label{display:grid;gap:8px;}form>button{margin-top:12px;}.tutor li{overflow-wrap:anywhere;}button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--accent);outline-offset:3px;}@media(max-width:1000px){.workspace{grid-template-columns:200px minmax(0,1fr);gap:14px;}}@media(max-width:760px){input,textarea{font-size:16px;}.workspace{grid-template-columns:1fr;}.syllabus{position:static;max-height:240px;}.masthead{display:block;}.entry-actions{margin-top:14px;}.reading>article,.scene,.reflection{padding:16px;}}
</style>
