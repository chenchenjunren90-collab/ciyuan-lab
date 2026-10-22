<script setup lang="ts">
import { computed } from "vue";
import { motionDirective as vMotion } from "../directives/motion";
import BeginnerShortcut from "./BeginnerShortcut.vue";
import type { DiagnosticQuiz, DiagnosticSubmissionResult } from "../services/api";

const props = defineProps<{
  quiz: DiagnosticQuiz;
  answers: Record<string, string>;
  questionIndex: number;
  busy: boolean;
  result: DiagnosticSubmissionResult | null;
}>();
const emit = defineEmits<{
  answer: [exerciseId: string, optionId: string];
  "update:questionIndex": [index: number];
  submit: [];
  skip: [];
  retake: [];
  path: [];
}>();
const item = computed(() => props.quiz.items[props.questionIndex]);
const answeredCount = computed(() => props.quiz.items.filter(question => props.answers[question.exercise_id]).length);
const complete = computed(() => answeredCount.value === props.quiz.items.length && props.quiz.items.length > 0);
function firstUnanswered() {
  const index = props.quiz.items.findIndex(question => !props.answers[question.exercise_id]);
  if (index >= 0) emit("update:questionIndex", index);
}
</script>

<template>
  <section class="panel assessment assessment-page" aria-labelledby="diagnostic-heading">
    <header><div><h2 id="diagnostic-heading">{{ quiz.title }}</h2></div><p>{{ quiz.instructions }}</p></header>
    <template v-if="!result">
      <div class="assessment-progress-summary" role="status" aria-live="polite"><span>{{ answeredCount }} / {{ quiz.items.length }} 已作答</span><span>不确定时可以选择“我不知道”</span></div>
      <progress :value="answeredCount" :max="quiz.items.length" aria-label="摸底作答进度"></progress>
      <BeginnerShortcut v-if="quiz.phase === 'initial'" :busy="busy" @skip="emit('skip')" />
      <div v-if="item" class="diagnostic-list">
        <article :key="item.exercise_id" v-motion="item.exercise_id" :aria-label="`第 ${questionIndex + 1} 题`">
          <header aria-live="polite" aria-atomic="true"><em>{{ questionIndex + 1 }} / {{ quiz.items.length }}</em><div><strong>{{ item.prompt }}</strong></div></header>
          <div><button v-for="option in item.options" :key="option.id" :class="{ active: answers[item.exercise_id] === option.id, unknown: option.id === 'UNKNOWN' }" :aria-pressed="answers[item.exercise_id] === option.id" :disabled="busy" @click="emit('answer', item.exercise_id, option.id)"><b>{{ option.id === 'UNKNOWN' ? '?' : option.id }}</b>{{ option.text }}</button></div>
        </article>
      </div>
      <p v-else role="status">当前课程暂时没有可用的摸底题目。</p>
      <nav class="assessment-question-nav" aria-label="摸底题目导航">
        <button class="secondary" :disabled="busy || questionIndex === 0" @click="emit('update:questionIndex', questionIndex - 1)">上一题</button>
        <button v-if="questionIndex < quiz.items.length - 1" class="primary" :disabled="busy" @click="emit('update:questionIndex', questionIndex + 1)">下一题</button>
        <button v-else-if="!complete" class="secondary" :disabled="busy" @click="firstUnanswered">返回未答题</button>
      </nav>
      <footer class="diagnostic-actions"><span>{{ complete ? '已完成全部题目，可以提交。' : '答案会在页面间往返时保留，提交前可随时修改。' }}</span><button class="primary" :disabled="!complete || busy" @click="emit('submit')">{{ busy ? '正在生成个性化路径…' : quiz.phase === 'initial' ? '提交诊断并生成路径' : '提交重测并更新画像' }}</button></footer>
    </template>
    <div v-else class="assessment-complete" role="status">
      <h3>本轮 {{ result.correct_count }} / {{ result.total_count }}</h3>
      <p>结果已转化为学习证据；{{ result.unknown_count ? `“我不知道” ${result.unknown_count} 题已安排回补。` : '画像和后续路径已经刷新。' }}</p>
      <div><button class="primary" @click="emit('path')">查看个性化路径</button><button class="secondary" :disabled="busy" @click="emit('retake')">准备阶段重测</button></div>
    </div>
  </section>
</template>
