<script setup lang="ts">
import { ref, watch } from "vue";
import type { DeviceMode } from "../uiPreferences";

const props = defineProps<{ displayName: string; deviceMode: DeviceMode }>();
const emit = defineEmits<{
  start: [displayName: string];
  settings: [];
  "update-device": [mode: DeviceMode];
}>();

const name = ref(props.displayName);
watch(() => props.displayName, (value) => { name.value = value; });

const deviceModes: { id: DeviceMode; label: string; icon: string }[] = [
  { id: "auto", label: "自动", icon: "◐" },
  { id: "mobile", label: "手机", icon: "▯" },
  { id: "desktop", label: "电脑", icon: "▢" },
];

function startLearning(): void {
  emit("start", name.value.trim() || "新同学");
}
</script>

<template>
  <section class="welcome-experience" aria-labelledby="welcome-title">
    <div class="welcome-grid"></div>
    <div class="welcome-glow glow-one"></div>
    <div class="welcome-glow glow-two"></div>
    <header class="welcome-nav">
      <div class="welcome-brand"><i>&lt;/&gt;</i><span><b>词元研究所</b><small>多智能体协同学习平台</small></span></div>
      <button class="welcome-settings" @click="emit('settings')"><span>◐</span> 设置外观</button>
    </header>

    <main class="welcome-main">
      <div class="welcome-copy">
        <div class="welcome-badge"><i></i> 你的课程，将从理解你开始</div>
        <h1 id="welcome-title">不跟固定课表走。<br /><em>沿着你的能力生长。</em></h1>
        <p>先用一次简短测评找到真实起点，再由助教编排课程、老师带领学习、质量监督在后台核验，让每一次练习都推动下一节课发生改变。</p>
        <label class="welcome-name">
          <span>上课时希望怎么称呼你？</span>
          <input v-model="name" maxlength="20" placeholder="新同学" @keyup.enter="startLearning" />
        </label>
        <div class="welcome-device">
          <span>界面适合</span>
          <div>
            <button v-for="item in deviceModes" :key="item.id" :class="{ active: deviceMode === item.id }" :aria-pressed="deviceMode === item.id" @click="emit('update-device', item.id)"><i>{{ item.icon }}</i>{{ item.label }}</button>
          </div>
        </div>
        <div class="welcome-actions">
          <button class="welcome-primary" @click="startLearning">开始能力摸底 <b>→</b></button>
          <button class="welcome-secondary" @click="emit('settings')">先调成喜欢的界面</button>
        </div>
        <div class="welcome-trust"><span>约 8 分钟完成摸底</span><span>课程随能力动态变化</span><span>代码由真实测试验证</span></div>
      </div>

      <div class="welcome-visual" aria-hidden="true">
        <div class="orbit orbit-one"><i>测</i><span></span></div>
        <div class="orbit orbit-two"><i>学</i><span></span></div>
        <div class="orbit orbit-three"><i>练</i><span></span></div>
        <article class="code-console">
          <header><span></span><span></span><span></span><b>今日专属课堂</b></header>
          <div class="console-content">
            <small>助教正在编排</small>
            <h2>从你会的地方继续</h2>
            <p><i>01</i><span>识别知识断层</span><b>完成</b></p>
            <p><i>02</i><span>组合本节内容</span><b>进行中</b></p>
            <p><i>03</i><span>匹配代码练习</span><b>待开始</b></p>
            <pre><code><em>def</em> build_course(profile):
    <span>return</span> next_best_step(profile)</code></pre>
          </div>
        </article>
        <div class="agent-card agent-teacher"><i>林</i><span><b>林老师</b><small>负责讲清楚</small></span></div>
        <div class="agent-card agent-assistant"><i>程</i><span><b>助教小程</b><small>负责规划路线</small></span></div>
        <div class="verified-chip">✓ 质量监督已就绪</div>
      </div>
    </main>

    <footer class="welcome-footer"><span>计算机专业学习是核心</span><i></i><span>讯飞大模型与课程知识库协同</span><i></i><span>财经场景仅用于课后项目实践</span></footer>
  </section>
</template>

<style scoped>
.welcome-experience{position:fixed;z-index:500;inset:0;min-width:0;min-height:620px;overflow-x:hidden;overflow-y:auto;color:#f7f8fb;background:radial-gradient(circle at 72% 42%,color-mix(in srgb,var(--accent) 24%,transparent),transparent 26%),linear-gradient(135deg,#090b11 0%,#111621 48%,#090a0f 100%)}
.welcome-grid{position:absolute;inset:0;opacity:.16;background-image:linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px);background-size:46px 46px;mask-image:linear-gradient(90deg,transparent 0,#000 45%,#000 100%)}
.welcome-glow{position:absolute;width:420px;height:420px;border-radius:50%;filter:blur(90px);opacity:.18;pointer-events:none}.glow-one{top:-220px;left:-120px;background:var(--accent)}.glow-two{right:-180px;bottom:-260px;background:#456ff2}
.welcome-nav,.welcome-main,.welcome-footer{position:relative;z-index:2;width:min(1380px,calc(100% - 72px));margin-inline:auto}.welcome-nav{height:92px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff14}.welcome-brand{display:flex;align-items:center;gap:13px}.welcome-brand>i{width:44px;height:44px;display:grid;place-items:center;border-radius:13px;color:#fff;background:linear-gradient(145deg,var(--accent),var(--accent-dark));box-shadow:0 12px 32px color-mix(in srgb,var(--accent) 42%,transparent);font:900 12px Consolas,monospace}.welcome-brand span,.welcome-brand b,.welcome-brand small{display:block}.welcome-brand b{font-size:16px}.welcome-brand small{margin-top:4px;color:#8f98aa;font-size:10px;letter-spacing:.08em}.welcome-settings{display:flex;align-items:center;gap:8px;padding:10px 14px;border:1px solid #ffffff1c;border-radius:999px;color:#d9deea;background:#ffffff0a;font-size:12px}.welcome-settings:hover{border-color:color-mix(in srgb,var(--accent) 65%,#fff);background:#ffffff12}.welcome-settings span{color:var(--accent-bright);font-size:16px}
.welcome-main{min-height:calc(100vh - 162px);display:grid;grid-template-columns:minmax(0,1fr) minmax(480px,.88fr);align-items:center;gap:clamp(42px,7vw,100px);padding:60px 0 76px}.welcome-copy{max-width:720px}.welcome-badge{width:max-content;display:flex;align-items:center;gap:9px;padding:8px 12px;border:1px solid color-mix(in srgb,var(--accent) 42%,transparent);border-radius:999px;color:#cdd3df;background:color-mix(in srgb,var(--accent) 10%,transparent);font-size:11px}.welcome-badge i{width:7px;height:7px;border-radius:50%;background:var(--accent-bright);box-shadow:0 0 0 5px color-mix(in srgb,var(--accent) 16%,transparent),0 0 18px var(--accent)}.welcome-copy h1{margin:23px 0 22px;font-size:clamp(44px,5.3vw,78px);line-height:1.05;letter-spacing:-.065em}.welcome-copy h1 em{color:transparent;background:linear-gradient(100deg,#fff 0%,var(--accent-bright) 46%,#fff 100%);background-clip:text;font-style:normal}.welcome-copy>p{max-width:650px;color:#a9b1c1;font-size:15px;line-height:1.9}.welcome-name{width:min(430px,100%);display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:13px;margin-top:28px;padding:7px 8px 7px 16px;border:1px solid #ffffff1a;border-radius:14px;background:#ffffff0a}.welcome-name span{color:#9da6b6;font-size:11px;white-space:nowrap}.welcome-name input{min-width:0;padding:10px;border:0;border-radius:9px;color:#fff;background:#ffffff0b;outline:none}.welcome-name:focus-within{border-color:var(--accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 14%,transparent)}.welcome-device{width:min(430px,100%);display:grid;grid-template-columns:auto 1fr;align-items:center;gap:13px;margin-top:14px}.welcome-device>span{color:#9da6b6;font-size:11px;white-space:nowrap}.welcome-device>div{display:flex;gap:8px}.welcome-device button{display:flex;align-items:center;gap:6px;padding:9px 13px;border:1px solid #ffffff1c;border-radius:999px;color:#c3cad7;background:#ffffff0a;font-size:11px}.welcome-device button i{color:var(--accent-bright);font-style:normal}.welcome-device button.active{border-color:color-mix(in srgb,var(--accent) 70%,#fff);color:#fff;background:color-mix(in srgb,var(--accent) 22%,transparent)}.welcome-actions{display:flex;align-items:center;gap:11px;margin-top:18px}.welcome-actions button{padding:13px 19px;border-radius:11px;font-size:12px;font-weight:800}.welcome-primary{border:0;color:#fff;background:linear-gradient(135deg,var(--accent-bright),var(--accent-dark));box-shadow:0 13px 30px color-mix(in srgb,var(--accent) 34%,transparent)}.welcome-primary:hover{transform:translateY(-2px);box-shadow:0 17px 38px color-mix(in srgb,var(--accent) 42%,transparent)}.welcome-primary b{margin-left:10px}.welcome-secondary{border:1px solid #ffffff1a;color:#ccd2df;background:#ffffff08}.welcome-trust{display:flex;flex-wrap:wrap;gap:10px 20px;margin-top:25px;color:#7f899c;font-size:10px}.welcome-trust span::before{content:"✓";margin-right:7px;color:#51d29a}
.welcome-visual{position:relative;min-height:560px;display:grid;place-items:center}.code-console{position:relative;z-index:3;width:min(500px,88%);overflow:hidden;border:1px solid #ffffff1c;border-radius:23px;background:#111620e8;box-shadow:0 35px 100px #0008,0 0 0 1px color-mix(in srgb,var(--accent) 12%,transparent);backdrop-filter:blur(16px);transform:perspective(1200px) rotateY(-7deg) rotateX(2deg)}.code-console>header{display:flex;align-items:center;gap:6px;padding:13px 16px;border-bottom:1px solid #ffffff10;background:#ffffff06}.code-console>header span{width:7px;height:7px;border-radius:50%;background:#485064}.code-console>header span:first-child{background:#ff657a}.code-console>header span:nth-child(2){background:#ffc76a}.code-console>header span:nth-child(3){background:#59d59e}.code-console>header b{margin-left:auto;color:#737e91;font-size:9px}.console-content{padding:28px}.console-content>small{color:var(--accent-bright);font-size:9px;font-weight:800;letter-spacing:.12em}.console-content h2{margin:8px 0 23px;font-size:27px}.console-content p{display:grid;grid-template-columns:32px 1fr auto;align-items:center;gap:9px;margin:8px 0;padding:10px 12px;border:1px solid #ffffff0b;border-radius:10px;color:#c3cad7;background:#ffffff05;font-size:10px}.console-content p i{color:#697487;font:normal 9px Consolas}.console-content p b{color:#6bd5aa;font-size:8px}.console-content p:nth-of-type(2) b{color:var(--accent-bright)}.console-content p:nth-of-type(3) b{color:#707b8e}.console-content pre{margin:22px 0 0;padding:17px;overflow:hidden;border-radius:12px;color:#c8d0df;background:#080b11;font:11px/1.75 Consolas,monospace}.console-content code em{color:#ff7790;font-style:normal}.console-content code span{color:#6ba8ff}.orbit{position:absolute;z-index:1;border:1px solid color-mix(in srgb,var(--accent) 25%,transparent);border-radius:50%;animation:welcome-spin 18s linear infinite}.orbit i{position:absolute;display:grid;place-items:center;border:1px solid #ffffff21;border-radius:50%;color:#fff;background:#171d29;box-shadow:0 0 28px color-mix(in srgb,var(--accent) 32%,transparent);font:normal 800 11px serif}.orbit-one{width:520px;height:520px}.orbit-one i{top:42px;right:48px;width:42px;height:42px}.orbit-two{width:410px;height:410px;animation-direction:reverse;animation-duration:14s}.orbit-two i{bottom:30px;left:55px;width:36px;height:36px}.orbit-three{width:610px;height:610px;border-style:dashed;animation-duration:28s}.orbit-three i{top:50%;right:-18px;width:38px;height:38px}.agent-card{position:absolute;z-index:5;display:flex;align-items:center;gap:9px;padding:10px 13px;border:1px solid #ffffff16;border-radius:13px;background:#161c27e8;box-shadow:0 14px 35px #0005;backdrop-filter:blur(12px)}.agent-card>i{width:33px;height:33px;display:grid;place-items:center;border-radius:10px;color:#fff;background:linear-gradient(145deg,var(--accent),var(--accent-dark));font:normal 800 11px serif}.agent-card span,.agent-card b,.agent-card small{display:block}.agent-card b{font-size:10px}.agent-card small{margin-top:3px;color:#7f899a;font-size:8px}.agent-teacher{top:63px;left:-6px}.agent-assistant{right:-8px;bottom:75px}.agent-assistant>i{background:linear-gradient(145deg,#238f72,#125a4a)}.verified-chip{position:absolute;z-index:5;right:18px;top:100px;padding:9px 12px;border:1px solid #4e9073;border-radius:999px;color:#8de2bd;background:#10251eeb;font-size:9px;box-shadow:0 12px 28px #0004}
.welcome-footer{min-height:70px;display:flex;align-items:center;justify-content:center;gap:16px;border-top:1px solid #ffffff12;color:#6f798c;font-size:9px}.welcome-footer i{width:3px;height:3px;border-radius:50%;background:#4f5869}
@keyframes welcome-spin{to{transform:rotate(360deg)}}
@media(max-width:980px){.welcome-main{grid-template-columns:1fr;padding-top:45px}.welcome-visual{min-height:500px}.welcome-copy{margin-inline:auto;text-align:center}.welcome-badge,.welcome-name{margin-inline:auto}.welcome-actions,.welcome-trust{justify-content:center}.welcome-copy>p{margin-inline:auto}.agent-teacher{left:4%}.agent-assistant{right:4%}}
@media(max-width:620px){.welcome-experience{min-height:100vh}.welcome-nav,.welcome-main,.welcome-footer{width:min(100% - 32px,1380px)}.welcome-nav{height:76px}.welcome-brand small{display:none}.welcome-settings{padding:9px}.welcome-settings>span+span{display:none}.welcome-main{min-height:auto;padding:45px 0}.welcome-copy h1{font-size:39px}.welcome-copy>p{font-size:13px}.welcome-name{grid-template-columns:1fr;gap:5px;text-align:left}.welcome-actions{align-items:stretch;flex-direction:column}.welcome-visual{min-height:400px}.orbit-one{width:380px;height:380px}.orbit-two{width:300px;height:300px}.orbit-three{display:none}.code-console{width:94%;transform:none}.console-content{padding:21px}.agent-card{display:none}.verified-chip{top:34px;right:0}.welcome-footer{flex-wrap:wrap;padding:18px 0;text-align:center}}
</style>
