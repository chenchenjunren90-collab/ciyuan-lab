<script setup lang="ts">
import { ref, watch } from "vue";

import { verificationUnavailable } from "../../services/workspaceState";
import type { ClassroomCodeTask, SubmissionResult } from "../../services/api";

const props = defineProps<{
  task: ClassroomCodeTask;
  modelValue: string;
  result: SubmissionResult | null;
  loading: boolean;
  hint: string;
  hintLoading: boolean;
  label: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  submit: [];
  hint: [];
}>();

function updateCode(event: Event): void {
  const value = (event.target as HTMLTextAreaElement).value;
  emit("update:modelValue", value);
}

const codeNotice = ref("");
const codeEditor = ref<HTMLTextAreaElement | null>(null);

watch(() => props.modelValue, (value) => {
  if (value.trim()) codeNotice.value = "";
});

watch(() => props.result, (result) => {
  if (result) codeNotice.value = "";
});

watch(() => props.loading, (loading) => {
  if (!loading) codeNotice.value = "";
});

function submitCode(): void {
  if (props.loading) {
    codeNotice.value = "代码正在运行，请稍候查看结果。";
    return;
  }
  const sourceCode = codeEditor.value?.value ?? props.modelValue;
  if (!sourceCode.trim()) {
    codeNotice.value = "请先在代码区输入或补全代码，再运行提交。";
    return;
  }
  codeNotice.value = "代码已提交，正在隔离环境中运行公开样例和隐藏测试…";
  emit("submit");
}
</script>

<template>
  <div class="code-task">
    <header><div><p>{{ label }}</p><h3>{{ task.title }}</h3><small>{{ task.exercise_id }} · {{ { beginner: "入门", intermediate: "进阶", advanced: "挑战" }[task.difficulty] ?? task.difficulty }} · 约 {{ task.estimated_minutes }} 分钟</small></div><span>真实运行 + 隐藏测试</span></header>
    <section class="problem-statement">
      <h4>题目说明</h4><p>{{ task.prompt }}</p>
      <div class="io-format"><article><b>输入格式</b><span>{{ task.input_format }}</span></article><article><b>输出格式</b><span>{{ task.output_format }}</span></article></div>
      <div class="task-constraints"><b>约束与边界</b><ul><li v-for="item in task.constraints" :key="item">{{ item }}</li></ul></div>
    </section>
    <div class="code-workspace">
      <section class="code-editor">
        <header><i></i><i></i><i></i><b>main.py</b><span>Python 3.11</span></header>
        <textarea ref="codeEditor" :value="modelValue" :disabled="loading" spellcheck="false" aria-label="课堂练习代码" @input="updateCode"></textarea>
      </section>
      <aside><b>公开样例</b><article v-for="(sample, index) in task.public_examples" :key="index"><small>样例 {{ index + 1 }}</small><div><span>输入</span><code>{{ sample.input.trim() || "（空）" }}</code></div><div><span>输出</span><code>{{ sample.expected_output.trim() || "（空行）" }}</code></div><p>{{ sample.explanation }}</p></article><button :disabled="hintLoading" @click="emit('hint')">{{ hintLoading ? "助教正在分析…" : "向助教要一个提示" }}</button><article v-if="hint" class="hint-card" role="status" aria-live="polite"><small>助教提示</small><p>{{ hint }}</p></article></aside>
    </div>
    <footer><div v-if="result" class="task-result" :data-pass="result.verification?.accepted"><b>{{ verificationUnavailable(result) ? "验证服务暂不可用" : result.verification?.accepted ? "全部测试通过" : "请根据反馈继续调试" }}</b><span>{{ result.feedback }}</span><small v-if="result.verification && !verificationUnavailable(result)">{{ result.verification.passed_tests }} / {{ result.verification.total_tests }} 项测试通过</small></div><div v-if="codeNotice" class="task-notice" role="status" aria-live="polite">{{ codeNotice }}</div><button class="primary" :aria-busy="loading" @click="submitCode">{{ loading ? "正在隔离环境中验证…" : "运行并提交" }}</button></footer>
  </div>
</template>

<style scoped>
.code-task > header { display: flex; align-items: start; justify-content: space-between; gap: 20px; }
.code-task header p { margin: 0 0 5px; color: #b4233b; font-size: 12px; font-weight: 800; }.code-task header h3 { margin: 0; font-size: 22px; }.code-task header div > small { display: block; margin-top: 6px; color: #8e8185; font-size: 12px; }.code-task header > span { padding: 6px 9px; border-radius: 99px; color: #7c666c; background: #f7f1f1; font-size: 12px; }
.problem-statement { margin: 16px 0; padding: 18px; border: 1px solid #e9dfe0; border-radius: 14px; background: #fffdfc; }.problem-statement h4 { margin: 0 0 8px; font-size: 14px; }.problem-statement > p { margin: 0; color: #51474b; font-size: 12px; line-height: 1.8; }.io-format { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }.io-format article { padding: 12px; border-radius: 10px; background: #f8f4f3; }.io-format b, .io-format span { display: block; }.io-format b { color: #9f263a; font-size: 12px; }.io-format span { margin-top: 5px; color: #62575b; font-size: 12px; line-height: 1.65; }.task-constraints { margin-top: 13px; }.task-constraints > b { font-size: 12px; }.task-constraints ul { display: flex; flex-wrap: wrap; gap: 7px; margin: 8px 0 0; padding: 0; list-style: none; }.task-constraints li { padding: 6px 9px; border: 1px solid #eadcdd; border-radius: 99px; color: #75676c; background: #fff; font-size: 12px; }
.code-workspace { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 12px; }.code-editor { overflow: hidden; border-radius: 12px; background: #11141b; box-shadow: 0 14px 30px #080a1028; }.code-editor header { height: 37px; display: flex; align-items: center; gap: 5px; padding: 0 12px; border-bottom: 1px solid #292d36; }.code-editor header i { width: 8px; height: 8px; border-radius: 50%; background: #f36c6c; }.code-editor header i:nth-child(2) { background: #eebd52; }.code-editor header i:nth-child(3) { background: #63bc75; }.code-editor header b { margin-left: 7px; color: #cfd5df; font: 12px Consolas; }.code-editor header span { margin-left: auto; color: #767f91; font: 12px Consolas; }.code-editor textarea { width: 100%; min-height: 310px; padding: 17px; resize: vertical; border: 0; outline: 0; color: #f4e9d0; background: transparent; font: 12px/1.75 Consolas, monospace; tab-size: 4; }.code-workspace > aside { padding: 14px; border: 1px solid #e6dddd; border-radius: 12px; background: #fffbf8; }.code-workspace > aside > b { font-size: 12px; }.code-workspace > aside article { margin-top: 10px; padding: 11px; border-radius: 9px; background: #f4efec; }.code-workspace aside small { display: block; margin-bottom: 7px; color: #9a858b; font-size: 12px; font-weight: 800; }.code-workspace aside article > div { display: grid; grid-template-columns: 36px 1fr; gap: 7px; margin-top: 5px; }.code-workspace aside article > div span { color: #9a858b; font-size: 12px; }.code-workspace aside code { overflow: auto; padding: 5px 7px; border-radius: 5px; color: #3f3639; background: #fff; font: 12px/1.55 Consolas; white-space: pre-wrap; }.code-workspace aside article p { margin: 8px 0 0; color: #6e6266; font-size: 12px; line-height: 1.6; }.code-workspace > aside button { width: 100%; margin-top: 11px; padding: 9px; border: 1px solid #dec7c9; border-radius: 8px; color: #9f263a; background: #fff; font-size: 12px; }.code-task > footer { display: flex; align-items: center; justify-content: flex-end; gap: 15px; margin-top: 14px; }.task-result { flex: 1; padding: 10px 12px; border-radius: 9px; color: #9f293b; background: #fff0f1; }.task-result[data-pass="true"] { color: #2a7650; background: #edf8f1; }.task-result b, .task-result span, .task-result small { display: block; }.task-result b { font-size: 12px; }.task-result span { margin-top: 4px; font-size: 12px; }.task-result small { margin-top: 4px; opacity: .75; font-size: 12px; }
.primary { padding: 10px 17px; border: 0; border-radius: 9px; color: #fff; background: linear-gradient(135deg, #cc1936, #a70f27); box-shadow: 0 8px 18px #b5163030; font-size: 12px; font-weight: 700; }.primary:disabled { opacity: .5; box-shadow: none; }
.code-workspace > aside button:disabled { opacity: .62; cursor: wait; }
.code-workspace > aside .hint-card { border: 1px solid #e5c8ad; color: #654f3c; background: #fff8e8; }
.code-workspace > aside .hint-card small { color: #9a5a2e; }
.code-workspace > aside .hint-card p { margin: 0; font-size: 12px; line-height: 1.7; }
.task-notice { flex: 1; padding: 10px 12px; border-radius: 9px; color: #785c35; background: #fff7e7; font-size: 12px; line-height: 1.6; }
@media (max-width: 760px) { .io-format, .code-workspace { grid-template-columns: 1fr; }.code-editor textarea { min-height: 240px; } }

/* Match the imported workspace appearance, including the embedded code task. */
.code-task { color: var(--ink); }
.problem-statement, .code-workspace > aside { color: var(--ink); border-color: var(--line); background: var(--surface-raised); }
.io-format article, .code-workspace > aside article { color: var(--ink); background: var(--surface-muted); }
.problem-statement > p, .io-format span, .code-workspace aside article p { color: var(--ink); }
.code-task header p, .io-format b { color: var(--accent-ink); }
.code-task header div > small, .code-workspace aside small, .code-workspace aside article > div span { color: var(--muted); }
.code-task header > span, .task-constraints li, .code-workspace aside code { color: var(--ink); border-color: var(--line); background: var(--surface-muted); }
.code-workspace > aside button { color: var(--accent-ink); border-color: var(--line); background: var(--surface-raised); }
.primary { color: var(--accent-contrast); background: var(--accent); box-shadow: none; }
.primary:focus-visible, .code-editor textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.code-task button { min-height: 44px; }
</style>
