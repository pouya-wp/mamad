<script setup lang="ts">
// Boolean props default to false in Vue when omitted, so padding must default explicitly.
withDefaults(defineProps<{ title?: string; subtitle?: string; padded?: boolean }>(), { padded: true })
</script>

<template>
  <section data-reveal class="card spotlight flex flex-col transition-colors duration-500 hover:border-white/10">
    <header v-if="title || $slots.actions" class="flex items-center gap-3 px-6 pt-6 sm:px-7 sm:pt-7">
      <div class="min-w-0 flex-1">
        <h2 class="font-bold text-bone">{{ title }}</h2>
        <p v-if="subtitle" class="mt-1 text-xs text-ink-400">{{ subtitle }}</p>
      </div>
      <slot name="actions" />
    </header>
    <div class="flex-1" :class="padded === false ? '' : 'p-6 sm:p-7'">
      <slot />
    </div>
  </section>
</template>
