<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { api, type CourseId, type QaResponse } from "../../services/api";
import { qaFeedbackLabel, serviceFailure } from "../../services/workspaceState";
import SafeMarkdown from "../SafeMarkdown.vue";

const props = defineProps<{ studentId: string; courseId: CourseId; reference?: { label: string; question: string; pointId: string } }>();
const draft = ref(""), sent = ref(""), error = ref(""), busy = ref(false);
const reply = ref<QaResponse | null>(null);
const editor = ref<HTMLTextAreaElement>();
let requestId = 0;
watch(() => props.reference, async reference => {
  if (!reference) return;
  ++requestId;
  busy.value = false;
  reply.value = null;
  sent.value = error.value = "";
  draft.value = reference.question;
  await nextTick();
  editor.value?.focus();
});
onBeforeUnmount(() => ++requestId);

async function ask() {
  const question = draft.value.trim();
  if (question.length < 2 || busy.value) return;
  const id = ++requestId;
  busy.value = true;
  sent.value = question;
  reply.value = null;
  error.value = "";
  try {
    const response = await api.ask(props.studentId, props.courseId, question, props.reference?.pointId);
    if (id === requestId) reply.value = response;
  } catch (cause) {
    if (id === requestId) error.value = serviceFailure(cause);
  } finally {
    if (id === requestId) busy.value = false;
  }
}
</script>

<template>
  <aside class="study-tutor" aria-label="课程答疑">
    <header><span class="tutor-symbol" aria-hidden="true">?</span><h3>课程辅导</h3></header>
    <form @submit.prevent="ask">
      <p v-if="reference" class="frame-reference">引用步骤<strong>{{ reference.label }}</strong></p>
      <label>你的问题<textarea ref="editor" v-model="draft" rows="5" minlength="2" maxlength="1000"
        :disabled="busy" placeholder="描述你想弄清楚的步骤或变量…" @keydown.ctrl.enter.prevent="ask" /></label>
      <button class="ask-button" :disabled="busy || draft.trim().length < 2">{{ busy ? '正在检索与复核…' : error ? '重试发送' : '发送问题' }}</button>
    </form>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-if="reply" aria-live="polite">
      <h4>{{ qaFeedbackLabel(reply) }}</h4>
      <SafeMarkdown :source="reply.answer || '当前课程资料依据不足。'" />
      <details v-if="reply.citations.length"><summary>查看依据（{{ reply.citations.length }}）</summary>
        <ul><li v-for="item in reply.citations" :key="item.chunk_id">{{ item.source_title || item.source_id }}<br>{{ item.source_id }} · {{ item.chunk_id }}</li></ul>
      </details>
      <details><summary>已发送的问题</summary><p class="sent">{{ sent }}</p></details>
      <details><summary>检索与复核过程</summary><p v-for="step in reply.trace" :key="step.component + step.detail">{{ step.detail }}</p></details>
    </section>
  </aside>
</template>

<style scoped>
.study-tutor { min-width:0; overflow-wrap:anywhere; padding:clamp(16px,1.5vw,22px); border:1px solid var(--line); border-radius:16px; background:var(--surface-raised); color:var(--ink); }
header { display:flex; align-items:center; gap:10px; }
h3,h4 { margin:0; } h3 { font-size:18px; }
.tutor-symbol { display:grid; place-items:center; width:30px; height:30px; border-radius:9px 9px 9px 1px; color:var(--accent-contrast); background:var(--accent); font:bold 18px/1 Consolas,monospace; }
form,label { display:grid; gap:9px; } form { margin-top:18px; } label { font-size:14px; font-weight:600; }
.frame-reference { margin:0 0 3px; padding:8px 11px; border-inline-start:3px solid var(--accent); color:var(--muted); background:var(--accent-pale); font-size:12px; }
.frame-reference strong { display:block; margin-top:2px; color:var(--ink); font-size:14px; }
textarea { width:100%; box-sizing:border-box; resize:vertical; min-height:84px; padding:10px 12px; border:1px solid var(--line); border-radius:8px; background:var(--surface-raised); color:var(--ink); font:400 16px/1.55 var(--font-body); }
.ask-button { justify-self:end; min-height:44px; padding:8px 18px; border:0; border-radius:8px; color:var(--accent-contrast); background:var(--accent); cursor:pointer; font:inherit; }
button:disabled { opacity:.5; cursor:default; }
section { margin-top:18px; border-top:1px solid var(--line); padding-top:16px; } h4 { color:var(--ink); font-size:15px; }
summary { padding:9px 0; color:var(--muted); cursor:pointer; font-size:14px; }
.sent { white-space:pre-wrap; } ul { padding-inline-start:18px; }
:is(button,textarea,summary):focus-visible { outline:2px solid var(--accent-ink); outline-offset:2px; }
</style>
