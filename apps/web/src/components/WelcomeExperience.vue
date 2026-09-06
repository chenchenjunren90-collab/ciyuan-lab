<script setup lang="ts">
import { ref, watch } from "vue";
import ThemeToggle from "./ThemeToggle.vue";
import type { DeviceMode } from "../uiPreferences";

const props = defineProps<{ displayName: string; deviceMode: DeviceMode; darkTheme: boolean }>();
const emit = defineEmits<{
  start: [displayName: string];
  settings: [];
  "update-device": [mode: DeviceMode];
  "toggle-theme": [];
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
      <div class="welcome-brand"><i>&lt;/&gt;</i><span><b>词元研究所</b><small>计算机专业学习平台</small></span></div>
      <div class="welcome-appearance"><ThemeToggle :dark="darkTheme" @toggle="emit('toggle-theme')" /><button class="welcome-settings" @click="emit('settings')" aria-label="打开外观设置"><span aria-hidden="true">Aa</span> 设置外观</button></div>
    </header>

    <main class="welcome-main">
      <form class="welcome-copy" @submit.prevent="startLearning">
        <h1 id="welcome-title">从你会的地方，<br />开始下一课。</h1>
        <p>先完成一次简短摸底。课程会根据你的回答、练习证据和验证结果持续调整。</p>
        <label class="welcome-name">
          <span>上课时希望怎么称呼你？</span>
          <input v-model="name" maxlength="20" autocomplete="nickname" placeholder="新同学" />
        </label>
        <div class="welcome-device">
          <span>界面适合</span>
          <div>
            <button v-for="item in deviceModes" :key="item.id" type="button" :class="{ active: deviceMode === item.id }" :aria-pressed="deviceMode === item.id" @click="emit('update-device', item.id)"><i>{{ item.icon }}</i>{{ item.label }}</button>
          </div>
        </div>
        <div class="welcome-actions">
          <button type="submit" class="welcome-primary">开始能力摸底 <b aria-hidden="true">→</b></button>
          <button type="button" class="welcome-secondary" @click="emit('settings')">先调成喜欢的界面</button>
        </div>
      </form>

      <aside class="welcome-route" aria-label="个性化学习流程">
        <header><span>你的学习闭环</span><strong>每一步都有依据</strong></header>
        <ol>
          <li style="--step: 0"><i>测</i><div><b>确认真实起点</b><span>约 8 分钟完成能力摸底</span></div><em>现在</em></li>
          <li style="--step: 1"><i>排</i><div><b>生成学习路线</b><span>助教根据画像编排下一课</span></div></li>
          <li style="--step: 2"><i>学</i><div><b>进入专属课堂</b><span>老师讲解，练习紧跟知识点</span></div></li>
          <li style="--step: 3"><i>验</i><div><b>用结果更新画像</b><span>代码由真实测试与规则验证</span></div></li>
        </ol>
        <footer><span>学情规划</span><span>课程辅导</span><span>质量监督</span></footer>
      </aside>
    </main>

    <footer class="welcome-footer"><span>计算机专业学习是核心</span><span>课程知识库提供可核验来源</span><span>财经场景仅用于课后项目实践</span></footer>
  </section>
</template>

<style scoped>
.welcome-experience{--welcome-bg:#0d0f12;--welcome-panel:#f2f0eb;--welcome-ink:#171719;--welcome-muted:#696561;position:fixed;z-index:500;inset:0;min-width:0;min-height:620px;overflow-x:hidden;overflow-y:auto;color:#f5f3ee;background:var(--welcome-bg)}
.welcome-experience::before{content:"";position:absolute;inset:0 auto 0 51%;width:1px;background:#ffffff12;pointer-events:none}
.welcome-nav,.welcome-main,.welcome-footer{position:relative;width:min(1400px,calc(100% - 72px));margin-inline:auto}.welcome-nav{height:72px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff17}.welcome-brand{display:flex;align-items:center;gap:12px}.welcome-brand>i{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;color:#fff;background:var(--accent);font:900 12px Consolas,monospace;font-style:normal}.welcome-brand span,.welcome-brand b,.welcome-brand small{display:block}.welcome-brand b{font-size:15px;letter-spacing:.01em}.welcome-brand small{margin-top:3px;color:#858790;font-size:12px}.welcome-settings{display:flex;align-items:center;gap:9px;padding:9px 13px;border:1px solid #36383e;border-radius:999px;color:#d7d6d2;background:transparent;font-size:12px}.welcome-settings:hover{border-color:#73757c;background:#ffffff0a}.welcome-settings span{color:var(--accent-bright);font:800 12px Consolas,monospace}
.welcome-main{min-height:calc(100dvh - 136px);display:grid;grid-template-columns:minmax(0,1fr) minmax(420px,.82fr);align-items:center;gap:clamp(48px,8vw,128px);padding:clamp(34px,6vh,68px) 0}.welcome-copy{max-width:680px}.welcome-copy h1{margin:0 0 20px;font-size:clamp(44px,5vw,72px);font-weight:850;line-height:1.08;letter-spacing:-.04em;text-wrap:balance}.welcome-copy h1::after{content:"";display:block;width:72px;height:6px;margin-top:24px;border-radius:999px;background:var(--accent)}.welcome-copy>p{max-width:33em;margin-bottom:0;color:#aaa9a5;font-size:15px;line-height:1.75}.welcome-name{width:min(440px,100%);display:grid;gap:8px;margin-top:27px}.welcome-name span,.welcome-device>span{color:#b9b8b4;font-size:12px;font-weight:700}.welcome-name input{width:100%;padding:13px 14px;border:1px solid #3b3d43;border-radius:12px;color:#fff;background:#17191e;outline:none}.welcome-name input::placeholder{color:#85878f}.welcome-name input:focus{border-color:var(--accent-bright);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 24%,transparent)}.welcome-device{width:min(440px,100%);display:grid;grid-template-columns:auto 1fr;align-items:center;gap:14px;margin-top:14px}.welcome-device>div{display:flex;gap:7px}.welcome-device button{display:flex;align-items:center;gap:7px;padding:8px 12px;border:1px solid #383a40;border-radius:999px;color:#b9b9b7;background:transparent;font-size:12px}.welcome-device button i{min-width:16px;color:#898b92;font:800 12px Consolas,monospace;font-style:normal}.welcome-device button:hover{border-color:#71737a;color:#fff}.welcome-device button.active{border-color:var(--accent);color:#fff;background:color-mix(in srgb,var(--accent) 22%,transparent)}.welcome-device button.active i{color:#fff}.welcome-actions{display:flex;align-items:center;gap:10px;margin-top:19px}.welcome-actions button{min-height:44px;padding:11px 18px;border-radius:12px;font-size:12px;font-weight:800;white-space:nowrap}.welcome-primary{border:1px solid var(--accent);color:#fff;background:var(--accent);box-shadow:0 13px 30px color-mix(in srgb,var(--accent-dark) 24%,transparent)}.welcome-primary:hover{background:var(--accent-bright);transform:translateY(-1px)}.welcome-primary b{margin-left:10px}.welcome-secondary{border:1px solid #393b41;color:#cbc9c5;background:transparent}.welcome-secondary:hover{border-color:#73757c;color:#fff;background:#ffffff08}
.welcome-route{overflow:hidden;border-radius:16px;color:var(--welcome-ink);background:var(--welcome-panel);box-shadow:0 32px 80px #0006}.welcome-route>header{display:flex;align-items:flex-end;justify-content:space-between;padding:22px 24px 18px;border-bottom:1px solid #d8d4cd}.welcome-route>header span{font-size:18px;font-weight:850}.welcome-route>header strong{color:var(--welcome-muted);font-size:12px}.welcome-route ol{position:relative;margin:0;padding:12px 24px 10px;list-style:none}.welcome-route ol::before{content:"";position:absolute;top:34px;bottom:33px;left:44px;width:1px;background:#d2cec7}.welcome-route li{position:relative;display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:12px;padding:12px 0;animation:route-enter .55s cubic-bezier(.16,1,.3,1) both;animation-delay:calc(var(--step) * 80ms)}.welcome-route li i{z-index:1;width:40px;height:40px;display:grid;place-items:center;border:1px solid #cac5bd;border-radius:12px;color:#77726d;background:var(--welcome-panel);font-style:normal;font-size:12px;font-weight:850}.welcome-route li:first-child i{border-color:var(--accent);color:#fff;background:var(--accent)}.welcome-route li div,.welcome-route li b,.welcome-route li span{display:block}.welcome-route li b{font-size:13px}.welcome-route li span{margin-top:4px;color:var(--welcome-muted);font-size:12px;line-height:1.45}.welcome-route li em{padding:5px 8px;border-radius:999px;color:var(--accent-dark);background:color-mix(in srgb,var(--accent) 10%,#fff);font-size:12px;font-style:normal;font-weight:850}.welcome-route>footer{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #d8d4cd;background:#e8e5df}.welcome-route>footer span{padding:12px 8px;color:#66625f;font-size:12px;font-weight:800;text-align:center}.welcome-route>footer span+span{border-left:1px solid #d0ccc5}
.welcome-footer{min-height:64px;display:flex;align-items:center;justify-content:space-between;gap:24px;border-top:1px solid #ffffff17;color:#898b92;font-size:12px}.welcome-footer span:nth-child(2){color:#a5a6aa}
.welcome-route>header strong,.welcome-route li em,.welcome-route>footer span{font-size:12px}.welcome-route li i{color:#696561}.welcome-route>footer span{color:#5f5b57}
@keyframes route-enter{from{opacity:0;transform:translateY(12px)}}
@media(max-width:980px){.welcome-experience::before{display:none}.welcome-main{grid-template-columns:1fr;gap:34px;padding:42px 0}.welcome-copy{max-width:720px}.welcome-route{width:min(640px,100%)}.welcome-footer{padding:20px 0;flex-wrap:wrap}.welcome-main{min-height:auto}}
@media(max-width:620px){.welcome-experience{min-height:100dvh}.welcome-nav,.welcome-main,.welcome-footer{width:min(calc(100% - 32px),1400px)}.welcome-nav{height:64px}.welcome-brand small{display:none}.welcome-settings{padding:8px 10px}.welcome-settings span{display:none}.welcome-main{gap:28px;padding:34px 0}.welcome-copy h1{font-size:39px}.welcome-copy h1::after{height:5px;margin-top:18px}.welcome-copy>p{font-size:13px}.welcome-device{grid-template-columns:1fr;gap:8px}.welcome-device button{min-height:44px}.welcome-actions{align-items:stretch;flex-direction:column}.welcome-actions button{width:100%}.welcome-route>header{padding:18px}.welcome-route ol{padding-inline:18px}.welcome-route ol::before{left:38px}.welcome-route li{grid-template-columns:40px minmax(0,1fr)}.welcome-route li em{display:none}.welcome-route>footer{display:none}.welcome-footer{align-items:flex-start;flex-direction:column;gap:8px;padding:18px 0 24px}}
@media(prefers-reduced-motion:reduce){.welcome-route li{animation:none}}

/* The welcome screen uses the same selectable signal system as the workspace. */
.welcome-experience{--welcome-bg:var(--surface);--welcome-panel:var(--surface-raised);--welcome-ink:var(--ink);--welcome-muted:var(--muted);color:var(--ink);background:var(--surface)}
.welcome-experience::before{background:var(--line)}
.welcome-nav,.welcome-footer{border-color:var(--line)}
.welcome-brand>i{border:1px solid var(--accent);border-radius:8px;color:var(--accent-ink);background:transparent}
.welcome-settings{border-color:var(--line);border-radius:7px;color:var(--muted)}
.welcome-settings:hover{border-color:var(--accent);color:var(--ink);background:var(--accent-pale)}
.welcome-copy h1{max-width:12ch;font-family:var(--font-display);font-size:clamp(42px,4.6vw,66px);font-weight:400;letter-spacing:-.025em}
.welcome-copy h1::after{width:58px;height:2px;border-radius:0}
.welcome-copy>p,.welcome-name span,.welcome-device>span{color:var(--muted)}
.welcome-name input{border-color:var(--line);border-radius:8px;color:var(--ink);background:var(--surface-raised)}
.welcome-device button{border-color:var(--line);border-radius:6px;color:var(--muted)}
.welcome-device button.active{color:var(--accent-ink);background:var(--accent-pale)}
.welcome-actions button{border-radius:7px}.welcome-primary{color:var(--accent-contrast);box-shadow:0 10px 24px #0004}.welcome-primary:hover{background:var(--accent)}
.welcome-secondary{border-color:var(--line);color:var(--muted)}
.welcome-route{border:1px solid var(--line);border-radius:12px;color:var(--ink);background:var(--surface-raised);box-shadow:none}
.welcome-route>header,.welcome-route>footer{border-color:var(--line)}
.welcome-route ol::before{background:var(--line)}
.welcome-route li i{border-color:var(--line);border-radius:7px;color:var(--muted);background:var(--surface-raised)}
.welcome-route li:first-child i{color:var(--accent-contrast);background:var(--accent)}
.welcome-route li em{border-radius:5px;color:var(--accent-ink);background:var(--accent-pale)}
.welcome-route>footer{background:var(--surface-muted)}
.welcome-route>footer span,.welcome-route li span,.welcome-route>header strong{color:var(--muted)}
.welcome-route>footer span+span{border-color:var(--line)}
.welcome-footer{color:var(--muted)}
.welcome-appearance { display:flex; align-items:center; gap:8px; }
.welcome-brand small,.welcome-footer span:nth-child(2) { color:var(--muted); }
.welcome-settings span { color:var(--accent-ink); }
.welcome-device button i { color:var(--muted); }
.welcome-device button.active i { color:var(--accent-ink); }
.welcome-secondary:hover,.welcome-device button:hover { color:var(--accent-ink); background:var(--accent-pale); border-color:var(--accent); }
</style>
