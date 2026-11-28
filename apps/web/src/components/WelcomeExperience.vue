<script setup lang="ts">
import { ref, watch } from "vue";
import SearchTracePreview from "./SearchTracePreview.vue";
import ThemeToggle from "./ThemeToggle.vue";
import type { DeviceMode, PaletteId } from "../uiPreferences";

const props = defineProps<{ displayName: string; deviceMode: DeviceMode; theme: PaletteId }>();
const emit = defineEmits<{
  start: [displayName: string];
  settings: [];
  "update-device": [mode: DeviceMode];
  "toggle-theme": [theme: PaletteId];
}>();

const name = ref(props.displayName);
watch(() => props.displayName, (value) => { name.value = value; });

const deviceModes: { id: DeviceMode; label: string; icon: string }[] = [
  { id: "auto", label: "自动", icon: "A" },
  { id: "mobile", label: "手机", icon: "M" },
  { id: "desktop", label: "电脑", icon: "D" },
];

function startLearning(): void {
  emit("start", name.value.trim() || "新同学");
}
</script>

<template>
  <section class="welcome-experience" aria-labelledby="welcome-title">
    <header class="welcome-nav">
      <div class="welcome-brand"><i class="brand-mark" aria-hidden="true"></i><b>词元研究所</b></div>
      <div class="welcome-appearance"><ThemeToggle :theme="theme" @select="emit('toggle-theme', $event)" />
        <button class="welcome-settings" @click="emit('settings')">界面设置</button>
      </div>
    </header>
    <main class="welcome-main">
      <form class="welcome-copy" @submit.prevent="startLearning">
        <h1 id="welcome-title">追踪代码，<br>看懂每一步。</h1>
        <p class="lead"><span aria-hidden="true">›_</span>从 C 语言、Python 到数据结构，跟着变量走一遍，用代码和测试验证你的理解。</p>
        <label class="welcome-name">上课时希望怎么称呼你？
          <input v-model="name" maxlength="20" autocomplete="nickname" placeholder="新同学" />
        </label>
        <button type="submit" class="welcome-primary">开始能力摸底 <span aria-hidden="true">→</span></button>
      </form>
      <SearchTracePreview />
    </main>
    <section class="welcome-route" aria-label="个性化学习流程">
      <h2>你的学习路线</h2>
      <ol><li><b>能力摸底</b><span>约 8 分钟确认起点</span></li>
        <li><b>课程规划</b><span>按已有证据推荐下一课</span></li>
        <li><b>课堂练习</b><span>推演算法，提交代码</span></li>
        <li><b>验证与复盘</b><span>根据测试结果更新掌握度</span></li></ol>
    </section>
    <footer class="welcome-footer">
      <span>界面布局</span><div class="segment-rail" role="group" aria-label="界面布局"><button v-for="item in deviceModes" :key="item.id" type="button" :aria-pressed="deviceMode === item.id" @click="emit('update-device', item.id)">{{ item.label }}</button></div>
    </footer>
  </section>
</template>

<style scoped>
.welcome-experience { position:fixed; inset:0; overflow:auto; z-index:500; background:var(--surface); color:var(--ink); }
.welcome-nav { padding:10px max(5vw,calc((100vw - 1250px)/2)); display:flex; align-items:center; justify-content:space-between; gap:12px; border-bottom:1px solid var(--line); background:var(--surface); color:var(--ink); }
.welcome-brand,.welcome-appearance,.welcome-footer { display:flex; align-items:center; gap:12px; }
.welcome-brand { white-space:nowrap; }
.welcome-settings { color:inherit; background:transparent; border:1px solid var(--line); border-radius:999px; min-height:44px; padding:6px 12px; cursor:pointer; }
.welcome-main,.welcome-route,.welcome-footer { width:min(90%,1250px); margin-inline:auto; }
.welcome-main { display:grid; grid-template-columns:minmax(0,.85fr) minmax(0,1.15fr); align-items:center; gap:clamp(26px,7vw,100px); padding:clamp(40px,6vw,88px) 0; }
html[data-theme] .welcome-experience .welcome-copy h1 { font-family:var(--font-display); font-size:clamp(39px,4.4vw,68px); font-weight:var(--title-weight); letter-spacing:-.025em; line-height:1.24; margin:0; }
.welcome-copy p { margin:22px 0; max-width:32em; line-height:1.75; color:var(--muted); }
.lead { display:flex; align-items:baseline; gap:14px; font-size:clamp(16px,1.5vw,20px); }.lead > span { color:var(--accent-ink); font-family:monospace; flex:none; }
.welcome-name { display:grid; gap:6px; font-size:13px; color:var(--muted); }
.welcome-name input { width:min(100%,310px); min-height:44px; color:var(--ink); background:var(--surface); border:1px solid var(--line); border-radius:2px; padding:8px 12px; font:inherit; font-size:16px; }
.welcome-primary { display:inline-flex; gap:25px; align-items:center; margin-top:14px; padding:12px 18px; min-height:44px; border:0; border-radius:2px; font:inherit; font-weight:600; cursor:pointer; }
.welcome-route { border-top:1px solid var(--line); padding-block:25px; }
.welcome-route h2 { margin:0 0 16px; font-size:25px; }
.welcome-route ol { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; padding:0; list-style:none; margin:0; }
.welcome-route li { display:grid; gap:5px; padding-block:10px; border-top:1px solid var(--line); }
.welcome-route li span,.welcome-footer { font-size:13px; color:var(--muted); }
.welcome-footer { flex-wrap:wrap; padding:10px 0 20px; }
.welcome-footer button { min-height:44px; background:none; border:0; border-bottom:2px solid transparent; color:var(--muted); font:inherit; cursor:pointer; }
.welcome-footer button[aria-pressed=true] { color:var(--ink); }
:is(input,button):focus-visible { outline:2px solid currentColor; outline-offset:2px; }
@media(max-width:760px) {
  .welcome-main { grid-template-columns:1fr; gap:28px; padding-block:28px; }
  .welcome-route ol { grid-template-columns:1fr 1fr; }
}
@media(max-width:370px) { .welcome-nav { padding-inline:10px; }.welcome-appearance { gap:4px; } }
</style>
