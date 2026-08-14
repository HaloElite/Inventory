<script lang="ts" setup>
import TopNavigation from './components/TopNavigation.vue';
</script>

<template>
  <div class="main-page">
    <TopNavigation />

    <main class="main-page__content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.main-page {
  padding: var(--spacing-page);
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100dvh;
  width: 100%;
  font-size: var(--font-size-default);
  background-color: var(--color-bg-main);
}

.main-page__content {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
</style>
