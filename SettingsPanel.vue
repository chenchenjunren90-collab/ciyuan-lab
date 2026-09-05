<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

import type { AccentMode, DeviceMode, LocalLearnerAccount, ThemeMode, UiPreferences } from "../uiPreferences";

const props = defineProps<{
  open: boolean;
  displayName: string;
  preferences: UiPreferences;
  accounts: LocalLearnerAccount[];
  currentStudentId: string;
}>();
const emit = defineEmits<{
  close: [];
  update: [patch: Partial<UiPreferences>];
  "update-name": [value: string];
  "switch-account": [id: string];
  "create-account": [];
  replay: [];
  reset: [];
}>();

const themes: { id: ThemeMode; label: string }[] = [
  { id: "light", label: "日间" },
  { id: "dark", label: "夜间" },
  { id: "system", label: "跟随系统" },
];
const accents: { id: AccentMode; label: string; description: string }[] = [
  { id: "ion", label: "离子青", description: "冷静、清晰的实验台信号" },
  { id: "pulse", label: "脉冲红", description: "延续原方案的高辨识强调" },
  { id: "solar", label: "太阳金", description: "温暖、醒目的任务状态" },
];
const deviceModes: { id: DeviceMode; label: string }[] = [
  { id: "auto", label: "自动" },
  { id: "mobile", label: "手机" },
  { id: "desktop", label: "电脑" },
];

const panel = ref<HTMLElement | null>(null);
let returnFocus: HTMLElement | null = null;

watch(() => props.open, async (open) => {
  if (open) {
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    await nextTick();
    panel.value?.focus();
    return;
  }
  await nextTick();
  if (returnFocus?.isConnected) returnFocus.focus();
  returnFocus = null;
});

function handlePanelKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab" || !panel.value) return;
  const focusable = Array.from(panel.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
  )).filter((element) => element.offsetParent !== null);
  if (!focusable.length) {
    event.preventDefault();
    panel.value.focus();
    return;
  }
  const first = focusable[0]!;
  const last = focusable[focusable.length - 1]!;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

onBeforeUnmount(() => {
  if (returnFocus?.isConnected) returnFocus.focus();
});
</script>

<template>
  <Transition name="settings-fade">
    <div v-if="open" class="settings-backdrop" @click.self="emit('close')">
      <aside ref="panel" class="settings-panel" role="dialog" aria-modal="true" aria-labelledby="settings-title" tabindex="-1" @keydown="handlePanelKeydown">
        <header><div><small>个性化设置</small><h2 id="settings-title">把学习空间调成你喜欢的样子</h2></div><button aria-label="关闭设置" @click="emit('close')">×</button></header>

        <section class="settings-section account-settings">
          <div><b>体验账号</b><span>同一台设备也可为不同同学保留各自的测评、课程、练习与项目进度。</span></div>
          <div class="account-list">
            <button v-for="account in accounts" :key="account.id" :class="{ active: currentStudentId === account.id }" @click="emit('switch-account', account.id)">
              <i>{{ account.displayName.slice(0, 1) || '学' }}</i>
              <span><b>{{ account.displayName }}</b><small>体验编号 · {{ account.id.slice(-6) }}</small></span>
              <em>{{ currentStudentId === account.id ? '当前' : '切换' }}</em>
            </button>
            <button class="add-account" @click="emit('create-account')"><i>＋</i><span><b>新增体验账号</b><small>创建一份完全独立的学习记录</small></span><em>新增</em></button>
          </div>
        </section>

        <section class="settings-section">
          <div><b>当前账号称呼</b><span>用于课堂称呼，并与当前体验账号一起保存在浏览器中。</span></div>
          <input class="settings-name" :value="displayName" maxlength="20" placeholder="新同学" aria-label="当前账号称呼" @input="emit('update-name', ($event.target as HTMLInputElement).value)" />
        </section>

        <section class="settings-section">
          <div><b>明暗模式</b><span>跟随环境选择更舒适的阅读亮度。</span></div>
          <div class="theme-options"><button v-for="item in themes" :key="item.id" :class="{ active: preferences.theme === item.id }" :aria-pressed="preferences.theme === item.id" @click="emit('update', { theme: item.id })"><span>{{ item.label }}</span></button></div>
        </section>

        <section class="settings-section">
          <div><b>颜色风格</b><span>选择后会同步改变导航、内容状态、按钮、进度和课堂强调色。</span></div>
          <div class="accent-options" role="group" aria-label="颜色风格">
            <button v-for="item in accents" :key="item.id" :class="[item.id, { active: preferences.accent === item.id }]" :aria-pressed="preferences.accent === item.id" @click="emit('update', { accent: item.id })">
              <i aria-hidden="true"></i><span><b>{{ item.label }}</b><small>{{ item.description }}</small></span>
            </button>
          </div>
        </section>

        <section class="settings-section">
          <div><b>设备模式</b><span>选择移动端或电脑端布局；自动模式跟随屏幕宽度。</span></div>
          <div class="theme-options"><button v-for="item in deviceModes" :key="item.id" :class="{ active: preferences.deviceMode === item.id }" :aria-pressed="preferences.deviceMode === item.id" @click="emit('update', { deviceMode: item.id })"><span>{{ item.label }}</span></button></div>
        </section>

        <section class="settings-section toggle-list">
          <button role="switch" :aria-checked="preferences.reducedMotion" @click="emit('update', { reducedMotion: !preferences.reducedMotion })"><span><b>减少动态效果</b><small>关闭旋转、漂浮与大幅过渡，降低视觉干扰。</small></span><i :class="{ on: preferences.reducedMotion }"><b></b></i></button>
          <button role="switch" :aria-checked="preferences.highContrast" @click="emit('update', { highContrast: !preferences.highContrast })"><span><b>增强对比度</b><small>让边框、文字和焦点状态更清晰。</small></span><i :class="{ on: preferences.highContrast }"><b></b></i></button>
          <button role="switch" :aria-checked="preferences.welcomeOnLaunch" @click="emit('update', { welcomeOnLaunch: !preferences.welcomeOnLaunch })"><span><b>每次打开显示欢迎页</b><small>适合演示；关闭后只在首次进入时显示。</small></span><i :class="{ on: preferences.welcomeOnLaunch }"><b></b></i></button>
        </section>

        <footer><button class="reset-button" @click="emit('reset')">恢复默认外观</button><button class="replay-button" @click="emit('replay')">重新查看欢迎页</button><button class="done-button" @click="emit('close')">完成</button></footer>
      </aside>
    </div>
  </Transition>
</template>

<style scoped>
.settings-backdrop{position:fixed;z-index:620;inset:0;display:flex;justify-content:flex-end;background:#07091099;backdrop-filter:blur(8px)}.settings-panel{width:min(470px,100%);height:100%;overflow:auto;padding:30px;color:var(--ink);background:var(--surface,#fff);box-shadow:-28px 0 80px #0004}.settings-panel>header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding-bottom:24px;border-bottom:1px solid var(--line)}.settings-panel>header small{color:var(--accent);font-size:9px;font-weight:900;letter-spacing:.14em}.settings-panel h2{margin:7px 0 0;font-size:25px;line-height:1.25;letter-spacing:-.04em}.settings-panel>header button{width:34px;height:34px;border:1px solid var(--line);border-radius:50%;color:var(--muted);background:var(--surface-raised,#fff);font-size:20px}.settings-section{display:grid;gap:14px;padding:22px 0;border-bottom:1px solid var(--line)}.settings-section>div:first-child b,.settings-section>div:first-child span{display:block}.settings-section>div:first-child b{font-size:13px}.settings-section>div:first-child span{margin-top:5px;color:var(--muted);font-size:10px;line-height:1.55}.settings-name{width:100%;padding:12px 13px;border:1px solid var(--line);border-radius:10px;color:var(--ink);background:var(--surface-raised,#fff);outline:none}.settings-name:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 14%,transparent)}.theme-options{display:grid!important;grid-template-columns:repeat(3,1fr);gap:8px}.theme-options button{display:grid;place-items:center;gap:7px;padding:13px 8px;border:1px solid var(--line);border-radius:11px;color:var(--muted);background:var(--surface-raised,#fff);font-size:10px}.theme-options button i{font:normal 17px serif}.theme-options button.active{border-color:var(--accent);color:var(--accent-dark);background:var(--accent-soft);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 18%,transparent)}.accent-options{display:grid!important;grid-template-columns:repeat(4,1fr);gap:8px}.accent-options button{display:grid;place-items:center;gap:7px;padding:11px 5px;border:1px solid transparent;border-radius:10px;color:var(--muted);background:transparent;font-size:9px}.accent-options button>i{width:27px;height:27px;border-radius:50%;background:#d6001c;box-shadow:inset 0 0 0 4px #fff,0 0 0 1px #ccd0d7}.accent-options .blue>i{background:#2563eb}.accent-options .teal>i{background:#0f8f78}.accent-options .violet>i{background:#7950d8}.accent-options button.active{border-color:var(--line);color:var(--ink);background:var(--surface-muted,#f5f6f8)}.accent-options button.active>i{box-shadow:inset 0 0 0 4px var(--surface-raised,#fff),0 0 0 2px currentColor}.toggle-list{gap:0}.toggle-list>button{width:100%;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:13px 0;border:0;color:var(--ink);background:transparent;text-align:left}.toggle-list>button span{display:grid;gap:4px}.toggle-list>button span>b{font-size:11px}.toggle-list>button span>small{color:var(--muted);font-size:9px;line-height:1.5}.toggle-list>button>i{width:40px;height:22px;flex:0 0 auto;padding:3px;border-radius:999px;background:#b9bec8;transition:.2s}.toggle-list>button>i b{display:block;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 2px 5px #0003;transition:.2s}.toggle-list>button>i.on{background:var(--accent)}.toggle-list>button>i.on b{transform:translateX(18px)}.settings-panel>footer{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;padding-top:24px}.settings-panel>footer button{padding:10px 12px;border-radius:9px;font-size:9px;font-weight:800}.reset-button{margin-right:auto;border:0;color:var(--muted);background:transparent}.replay-button{border:1px solid var(--line);color:var(--ink);background:var(--surface-raised,#fff)}.done-button{border:0;color:#fff;background:linear-gradient(135deg,var(--accent-bright),var(--accent-dark));box-shadow:0 8px 18px color-mix(in srgb,var(--accent) 24%,transparent)}.settings-fade-enter-active,.settings-fade-leave-active{transition:opacity .2s}.settings-fade-enter-active .settings-panel,.settings-fade-leave-active .settings-panel{transition:transform .25s ease}.settings-fade-enter-from,.settings-fade-leave-to{opacity:0}.settings-fade-enter-from .settings-panel,.settings-fade-leave-to .settings-panel{transform:translateX(30px)}
.account-list{display:grid!important;gap:8px}.account-list>button{display:grid;grid-template-columns:36px minmax(0,1fr) auto;align-items:center;gap:10px;width:100%;padding:10px;border:1px solid var(--line);border-radius:11px;color:var(--ink);background:var(--surface-raised,#fff);text-align:left}.account-list>button>i{display:grid;place-items:center;width:32px;height:32px;border-radius:9px;color:var(--accent-dark);background:var(--accent-soft);font-style:normal;font-weight:900}.account-list>button>span{display:grid;gap:3px;min-width:0}.account-list>button>span b{overflow:hidden;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.account-list>button>span small{color:var(--muted);font-size:8px}.account-list>button>em{color:var(--muted);font-size:8px;font-style:normal;font-weight:800}.account-list>button.active{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 10%,transparent)}.account-list>button.active>em{color:var(--accent)}.account-list>button.add-account{border-style:dashed}.account-list>button.add-account>i{color:var(--muted);background:var(--surface-muted,#f5f6f8)}
@media(max-width:520px){.settings-panel{padding:24px 18px}.theme-options{grid-template-columns:1fr!important}.theme-options button{display:flex}.settings-panel>footer{align-items:stretch;flex-direction:column}.reset-button{margin:0}}

/* Mainframe appearance settings: one active signal color, no decorative card chrome. */
.settings-backdrop{background:#05080dcc;backdrop-filter:none}
.settings-panel{width:min(520px,100%);padding:28px;border-left:1px solid var(--line);background:var(--surface);box-shadow:-24px 0 64px #0008}
.settings-panel>header{border-color:var(--line)}
.settings-panel>header small{font-family:var(--font-data);letter-spacing:.16em;text-transform:uppercase}
.settings-panel h2{font-size:24px;letter-spacing:-.025em}
.settings-panel>header button{border-radius:8px;background:var(--surface-muted)}
.settings-section{padding:20px 0}
.settings-name,.theme-options button,.account-list>button{border-radius:8px;background:var(--surface-raised);box-shadow:none}
.theme-options{gap:6px}
.theme-options button{min-height:42px;padding:10px}
.theme-options button.active{color:var(--accent-ink);background:var(--accent-soft);box-shadow:inset 0 0 0 1px var(--accent)}
.accent-options{display:grid!important;grid-template-columns:1fr;gap:6px}
.accent-options button{width:100%;display:grid;grid-template-columns:22px minmax(0,1fr);align-items:center;gap:11px;padding:10px 11px;border:1px solid var(--line);border-radius:8px;color:var(--ink);background:var(--surface-raised);text-align:left}
.accent-options button>i{width:18px;height:18px;border:0;border-radius:3px;background:#34beca;box-shadow:inset 0 0 0 1px #ffffff52}
.accent-options button.pulse>i{background:#e24b5f}
.accent-options button.solar>i{background:#e9a83c}
.accent-options button>span,.accent-options button b,.accent-options button small{display:block}
.accent-options button b{font-size:10px}
.accent-options button small{margin-top:3px;color:var(--muted);font-size:8px;line-height:1.4}
.accent-options button.active{border-color:var(--accent);color:var(--accent-ink);background:var(--accent-soft)}
.accent-options button.active>i{box-shadow:0 0 0 2px var(--surface-raised),0 0 0 3px var(--accent)}
.account-list>button>i{border-radius:6px}
.toggle-list>button>i{border-radius:999px}
.done-button{color:var(--accent-contrast);background:var(--accent);box-shadow:0 8px 18px #0003}
.replay-button{background:var(--surface-raised)}
</style>
