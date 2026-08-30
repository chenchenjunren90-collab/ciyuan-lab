<script setup lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed } from "vue";

const props = defineProps<{ source: string }>();

const html = computed(() => {
  const rendered = marked.parse(props.source || "", {
    async: false,
    breaks: true,
    gfm: true,
  }) as string;
  return DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style", "iframe", "form"],
    FORBID_ATTR: ["style", "onerror", "onclick"],
  });
});
</script>

<template>
  <div class="safe-markdown" v-html="html"></div>
</template>

<style scoped>
.safe-markdown { color: inherit; font: inherit; line-height: 1.72; overflow-wrap: anywhere; }
.safe-markdown :deep(p) { margin: 0 0 .65em; }
.safe-markdown :deep(p:last-child) { margin-bottom: 0; }
.safe-markdown :deep(ul), .safe-markdown :deep(ol) { margin: .45em 0 .7em; padding-left: 1.45em; }
.safe-markdown :deep(li + li) { margin-top: .25em; }
.safe-markdown :deep(strong) { color: #342a2e; font-weight: 800; }
.safe-markdown :deep(code) { padding: .12em .38em; border-radius: 4px; color: #9f1730; background: #fff0f2; font: .92em Consolas, monospace; }
.safe-markdown :deep(pre) { margin: .7em 0; padding: 11px 12px; overflow: auto; border-radius: 8px; color: #eef1f7; background: #15171d; }
.safe-markdown :deep(pre code) { padding: 0; color: inherit; background: transparent; }
.safe-markdown :deep(blockquote) { margin: .7em 0; padding-left: 10px; border-left: 3px solid #d78a96; color: #75666b; }
</style>
