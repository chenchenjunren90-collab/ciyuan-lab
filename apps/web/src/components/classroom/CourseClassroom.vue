<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { api, type ActivityDetail, type ActivitySummary, type KnowledgePoint, type KnowledgePointDetail, type LearnerProfile } from "../../services/api";
import { serviceFailure, verificationUnavailable } from "../../services/workspaceState";
import SafeMarkdown from "../SafeMarkdown.vue";
import ClassroomCodeTask from "./ClassroomCodeTask.vue";
import { currentVerification, type ReviewedSubmission } from "../../services/submittedCode";
import CourseQuestionPanel from "./CourseQuestionPanel.vue";
import AlgorithmLab from "./AlgorithmLab.vue";
import { traceForConcept } from "./algorithmTrace";
import { asCodeTask, chapters, courseNames, lessonScenes, orderKnowledge, readLessonPosition, recommendPoint, type FoundationCourse } from "./courseLearning";

const props = defineProps<{ courseId: FoundationCourse; studentId: string; points: KnowledgePoint[]; profile: LearnerProfile | null }>();
const emit = defineEmits<{ profileUpdated: [profile: LearnerProfile]; openProjects: []; openAssessment: [] }>();
const selected = ref(""), point = ref<KnowledgePointDetail | null>(null), exercises = ref<ActivitySummary[]>([]);
const activity = ref<ActivityDetail | null>(null), view = ref("learn"), sceneIndex = ref(0);
const loading = ref(false), taskLoading = ref(false), busy = ref(false), hintBusy = ref(false);
const error = ref(""), taskError = ref(""), search = ref(""), code = ref(""), answer = ref("");
const result = ref<ReviewedSubmission | null>(null);
const hint = ref(""), hintLevel = ref(0), reflection = ref("");
const syllabusExpanded = ref(false);
const syllabusToggle = ref<HTMLButtonElement>();
const directoryBody = ref<HTMLElement>();
watch([selected, syllabusExpanded], async () => {
  await nextTick();
  const directory = directoryBody.value;
  const current = directory?.querySelector<HTMLElement>('[aria-current="step"]');
  if (!directory?.clientHeight || !current) return;
  const bounds = directory.getBoundingClientRect();
  const row = current.getBoundingClientRect();
  const searchHeight = directory.querySelector('label')?.clientHeight ?? 0;
  if (row.top < bounds.top + searchHeight || row.bottom > bounds.bottom) {
    directory.scrollTop += row.top - bounds.top - (directory.clientHeight - row.height) / 2;
  }
});
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
const prerequisites = computed(() => (point.value?.prerequisites ?? []).map(id => ({ id, title: props.points.find(item => item.id === id)?.title ?? "前置知识", mastered: mastered.value.has(id) })));
const positionKey = () => `ciyuan-course-classroom:${props.studentId}:${props.courseId}`;
const taskKey = () => `${positionKey()}:${activity.value?.id}:code`;
function saveValue(key: string, value: string) { try { sessionStorage.setItem(key, value); } catch { /* Storage is optional; live work continues. */ } }
function restoredCode(): string { try { return sessionStorage.getItem(taskKey()) ?? ""; } catch { return ""; } }

async function selectPoint(id: string) {
  if (busy.value || !coursePoints.value.some(item => item.id === id)) return;
  if (syllabusExpanded.value) {
    syllabusExpanded.value = false;
    syllabusToggle.value?.focus();
  }
  const token = ++scope; ++taskScope;
  selected.value = id; point.value = null; activity.value = null; exercises.value = [];
  error.value = ""; taskError.value = "";
  reflection.value = ""; result.value = null; hint.value = ""; hintBusy.value = false;
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
  const submittedSource = code.value;
  busy.value = true; taskError.value = ""; result.value = null;
  try {
    const response = await api.submit(props.studentId, props.courseId, current.id, isCode
      ? { language: current.evaluation.runtime?.language, source_code: submittedSource }
      : { response: answer.value });
    if (!alive || token !== taskScope) return;
    result.value = isCode ? { ...response, submittedSource } : response;
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
  const draft = code.value;
  const verification = currentVerification(result.value, draft);
  try {
    const response = await api.hint(props.studentId, props.courseId, activity.value.id, (hintLevel.value + 1) as 1 | 2 | 3, {
      sourceCode: draft, diagnostics: verification?.diagnostics,
      passedTests: verification?.passed_tests, totalTests: verification?.total_tests,
    });
    if (alive && token === taskScope && code.value === draft) { hint.value = response.hint; hintLevel.value = response.level; }
  } catch (cause) { if (alive && token === taskScope) taskError.value = serviceFailure(cause); }
  finally { if (alive && token === taskScope) hintBusy.value = false; }
}
watch(code, value => {
  hint.value = "";
  hintLevel.value = 0;
  if (activity.value) saveValue(taskKey(), value);
});
watch(() => [props.courseId, props.studentId, props.points.map(item => item.id).join(",")], () => {
  if (!coursePoints.value.length) return;
  let saved = ""; try { saved = readLessonPosition(sessionStorage, positionKey()); } catch { /* SSR / unavailable storage */ }
  void selectPoint(coursePoints.value.some(item => item.id === saved) ? saved : recommended.value);
}, { immediate: true });
onBeforeUnmount(() => { alive = false; ++scope; ++taskScope; });
</script>

<template>
  <section class="foundation-classroom">
    <div class="course-layout">
      <aside class="syllabus" aria-label="课程目录">
        <h2 class="directory-title">课程目录</h2>
        <button ref="syllabusToggle" class="directory-toggle" aria-controls="course-directory" :aria-expanded="syllabusExpanded" @click="syllabusExpanded = !syllabusExpanded">
          <strong>课程目录</strong><span>{{ syllabusExpanded ? '收起 −' : '展开 ＋' }}</span>
        </button>
        <div id="course-directory" ref="directoryBody" class="directory-body" :class="{ expanded: syllabusExpanded }">
          <label><span class="search-label">查找知识点</span><input v-model="search" type="search" placeholder="搜索知识点名称" /></label>
          <button class="recommend" :disabled="busy || !recommended" @click="selectPoint(recommended)">从推荐起点继续 →</button>
          <p class="small">{{ profile?.mastery.some(item => item.evidence_count > 0) ? '依据已有测评与前置关系推荐' : '暂无测评，按前置顺序推荐' }}</p>
          <section v-for="group in groups" :key="group.title"><h3>{{ group.title }}</h3>
            <button v-for="item in group.points" :key="item.id" :disabled="busy" :class="{ selected: selected === item.id }" :aria-current="selected === item.id ? 'step' : undefined" @click="selectPoint(item.id)">
              <span>{{ item.title }}</span><small v-if="mastered.has(item.id)">已掌握</small>
            </button>
          </section>
          <p v-if="!groups.length">没有匹配的知识点。</p>
        </div>
      </aside>
      <section class="lesson" aria-label="当前知识点课堂">
        <p v-if="loading" role="status">正在读取课程讲解与练习…</p><div v-else-if="error" role="alert"><p>{{ error }}</p><button @click="selectPoint(selected)">重新加载</button></div>
        <template v-else-if="point">
          <header class="lesson-heading">
            <div class="course-links"><span>{{ name }}</span><div><button @click="emit('openAssessment')">能力摸底</button><button @click="emit('openProjects')">项目实践 ↗</button></div></div>
            <h2>{{ point.title }}</h2>
            <small>约 {{ point.estimated_minutes }} 分钟 · {{ point.status === 'reviewed' ? '已审核' : '教学草稿，待教师审核' }}</small>
            <details class="lesson-goals" :open="view === 'learn'"><summary>学习目标与前置知识</summary>
              <ul><li v-for="objective in point.learning_objectives" :key="objective">{{ objective }}</li></ul>
              <div v-if="prerequisites.length" class="prerequisites"><span>前置知识</span><button v-for="item in prerequisites" :key="item.id" :disabled="busy" @click="selectPoint(item.id)">{{ item.title }} {{ item.mastered ? '✓' : '↗' }}</button></div>
            </details>
          </header>
          <nav class="views segment-rail" aria-label="课堂学习环节"><button v-for="[id, title] in [['learn','分段讲解'],['lab','交互实验'],['practice','随堂练习'],['ask','课程答疑']]" :key="id" :aria-pressed="view === id" @click="view = id">{{ title }}</button></nav>
          <section v-if="view === 'learn'" class="reading">
            <div v-if="scene" class="scene"><small>讲解 {{ sceneIndex + 1 }} / {{ scenes.length }}</small><h3>{{ scene.title }}</h3><SafeMarkdown :source="scene.content" /><div class="controls"><button :disabled="sceneIndex === 0" @click="sceneIndex--">上一段</button><button :disabled="sceneIndex === scenes.length - 1" @click="sceneIndex++">下一段 →</button></div></div>
            <article v-if="worked" class="worked"><h3>跟着例题推演</h3><p>{{ worked.problem }}</p><pre><code>{{ worked.code }}</code></pre><ol><li v-for="step in worked.steps" :key="step">{{ step }}</li></ol><p>{{ worked.reflection }}</p></article>
            <article v-else><h3>例子与解释</h3><SafeMarkdown v-for="example in point.lesson.examples" :key="example" :source="example" /></article>
            <article class="mistakes"><h3>容易出错的地方</h3><ul><li v-for="mistake in point.lesson.common_mistakes" :key="mistake">{{ mistake }}</li></ul></article>
            <label v-if="point.lesson.checkpoint" class="reflection">先说说你的理解：{{ point.lesson.checkpoint.prompt }}<textarea v-model="reflection" rows="3" placeholder="写下预测，再去实验或练习区验证。此处不计分。" /><small>{{ point.lesson.checkpoint.guidance }}</small></label>
            <footer class="reading-footer"><details v-if="point.source_refs.length"><summary>查看讲解来源（{{ point.source_refs.length }}）</summary><ul><li v-for="source in point.source_refs" :key="source">{{ source }}</li></ul></details><button @click="view = 'practice'">用练习检验理解 →</button></footer>
          </section>
          <section v-else-if="view === 'lab'"><p v-if="!traceKind" class="small">当前知识点暂无专属演示。你可以探索本课程的实验主题，再回到本节练习。</p><AlgorithmLab :key="selected" :student-id="studentId" :course-id="courseId" :initial-kind="traceKind ?? (courseId === 'c' ? 'array' : 'stack')" /></section>
          <section v-else-if="view === 'practice'" class="practice">
            <nav class="task-picker" aria-label="本节练习"><button v-for="item in exercises" :key="item.id" :disabled="busy" :aria-pressed="activity?.id === item.id" @click="selectTask(item.id)">{{ item.title }}</button></nav>
            <p v-if="taskLoading" role="status">正在读取题目…</p><p v-if="taskError" role="alert">{{ taskError }}</p>
            <template v-if="activity && !taskLoading"><ClassroomCodeTask v-if="task && ['code','debug'].includes(activity.type)" v-model="code" :task="task" :language="activity.evaluation.runtime?.language" :result="result" :loading="busy" :hint="hint" :hint-loading="hintBusy" :hint-exhausted="hintLevel >= 3" label="本节编程任务" @submit="submit" @hint="requestHint" />
              <form v-else @submit.prevent="submit"><h3>{{ activity.title }}</h3><SafeMarkdown :source="activity.prompt ?? ''" /><fieldset v-if="activity.evaluation.options" :disabled="busy"><legend>选择答案</legend><label v-for="option in activity.evaluation.options" :key="option.id"><input v-model="answer" type="radio" :value="option.id" :name="activity.id" />{{ option.id }}. {{ option.text }}</label></fieldset><textarea v-else v-model="answer" :disabled="busy" rows="5" aria-label="练习答案" /><button :disabled="busy" type="submit">{{ busy ? '正在验证…' : '提交并验证' }}</button><div v-if="result" role="status"><b>{{ verificationUnavailable(result) ? '验证服务暂不可用' : !result.verification ? '评分反馈' : result.verification.accepted ? '验证通过' : '查看反馈后再试' }}</b><p>{{ result.feedback }}</p></div></form>
              <p v-if="result && activity.reflection_prompt">复盘：{{ activity.reflection_prompt }}</p><button v-if="result && !verificationUnavailable(result)" :disabled="busy || !recommended" @click="selectPoint(recommended)">继续推荐知识点 →</button>
            </template><p v-else-if="!taskLoading && !exercises.length">本知识点暂无可用练习。</p>
          </section>
          <CourseQuestionPanel v-show="view === 'ask'" :key="selected" :student-id="studentId" :course-id="courseId" />
        </template><p v-else>课程目录载入后即可选择知识点开始学习。</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.foundation-classroom { color:var(--ink); font-size:16px; }
.course-layout { display:grid; grid-template-columns:clamp(168px,14vw,210px) minmax(0,1fr); gap:clamp(12px,1.4vw,24px); align-items:start; margin-top:20px; }
button,input,textarea { font:inherit; color:var(--ink); border:1px solid var(--line); border-radius:8px; background:var(--surface-raised); }
button { min-height:44px; padding:8px 12px; cursor:pointer; }
button:disabled { opacity:.5; cursor:default; }
input,textarea { max-width:100%; padding:10px; } textarea { width:100%; resize:vertical; line-height:1.7; }
.syllabus { min-width:0; position:sticky; top:16px; padding:4px 12px 0 0; border-inline-end:1px solid var(--line); }
.directory-body { max-height:calc(100vh - 78px); overflow-y:auto; overscroll-behavior-y:contain; scrollbar-width:thin; }
.directory-title { margin:0 0 12px; font-size:16px; }
.syllabus .directory-toggle { display:none; }
.directory-body label { display:grid; position:sticky; top:0; z-index:1; background:var(--surface); }
.search-label { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
.syllabus input { width:100%; min-height:42px; font-size:14px; }
.directory-body section { margin-top:18px; }
.directory-body h3 { font-size:13px; margin:0 0 5px; color:var(--muted); }
.directory-body button { display:grid; width:100%; gap:1px; text-align:left; border:0; background:transparent; font-size:14px; padding:7px 10px; line-height:1.45; }
.directory-body button:hover { background:var(--surface-muted); }
.directory-body button.selected { color:var(--accent-ink); background:var(--accent-pale); box-shadow:inset 3px 0 var(--accent); font-weight:700; }
.directory-body button small,.small { font-size:12px; color:var(--muted); }
.directory-body .recommend { margin-top:6px; color:var(--accent-ink); padding-inline:0; font-weight:650; }
.directory-body .small { margin:0; line-height:1.5; }
.lesson { min-width:0; }.lesson-heading h2 { margin:3px 0; font-size:clamp(24px,2.4vw,34px); }.lesson-heading small { color:var(--muted); }
.course-links { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:4px 12px; }
.course-links span { color:var(--accent-ink); font-size:13px; font-weight:650; }
.course-links div { display:flex; gap:6px; }
.course-links button { padding:4px 8px; min-height:40px; color:var(--muted); background:transparent; border:0; font-size:13px; }
.course-links button:hover { background:var(--surface-muted); color:var(--ink); }
.lesson-goals { margin-top:10px; font-size:14px; }
.lesson-goals summary { cursor:pointer; padding-block:8px; font-weight:600; }
.lesson-goals ul { margin:6px 0; padding-inline-start:20px; line-height:1.7; }
.prerequisites,.views,.task-picker,.controls,.reading-footer { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.prerequisites { font-size:13px; } .prerequisites button { min-height:36px; }
.views { margin:12px 0 18px; border-bottom:1px solid var(--line); gap:0; }
.views button { border:0; border-radius:0; padding-inline:clamp(8px,1.3vw,19px); color:var(--muted); background:transparent; }
.views [aria-pressed=true] { color:var(--accent-ink); font-weight:700; box-shadow:inset 0 -3px var(--accent); }
.reading>article,.scene,.reflection,.practice>form { display:block; margin-bottom:16px; padding:clamp(16px,2vw,26px); border:1px solid var(--line); border-radius:14px; background:var(--surface-raised); line-height:1.85; }
.reading h3 { margin:0 0 12px; } .reading li { margin:8px 0; }
.controls,.reading-footer { justify-content:space-between; margin-top:18px; }
.reading-footer { font-size:12px; overflow-wrap:anywhere; }
pre { white-space:pre; overflow:auto; padding:16px; background:var(--code); color:var(--code-ink); border-radius:8px; font:14px/1.7 Consolas,monospace; }
.reflection textarea { display:block; margin:12px 0; }
.task-picker { margin-bottom:16px; }.task-picker [aria-pressed=true] { color:var(--accent-ink); background:var(--accent-pale); }
fieldset { border:0; padding:0; margin:16px 0; } fieldset label { display:flex; align-items:center; gap:10px; min-height:48px; }
form>button { margin-top:12px; } :is(button,input,textarea,summary):focus-visible { outline:2px solid var(--accent-ink); outline-offset:2px; }
@media(max-width:1050px) {
  .course-layout { grid-template-columns:minmax(0,1fr); }
  .syllabus { position:static; max-height:none; padding:0; border:1px solid var(--line); border-radius:10px; background:var(--surface-raised); overflow:visible; }
  .directory-title { display:none; } .syllabus .directory-toggle { display:flex; width:100%; align-items:center; justify-content:space-between; padding:10px 14px; border:0; }
  .directory-toggle span { color:var(--muted); font-size:13px; }
  .directory-body { display:none; } .directory-body.expanded { display:block; max-height:45vh; padding:12px; overflow:auto; border-top:1px solid var(--line); }
}
@media(max-width:600px) {
  .course-layout { margin-top:12px; }.views { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); }.views button { font-size:14px; padding-inline:2px; }
  input,textarea,.syllabus input { font-size:16px; }
}
</style>
