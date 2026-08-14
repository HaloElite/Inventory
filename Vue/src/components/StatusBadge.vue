<script lang="ts" setup>
import SvgRenderer from '@/components/SvgRenderer.vue';

defineProps<{
  status: 'new' | 'used' | 'damaged';
}>();

const statusTextMap = {
  new: 'Neu',
  used: 'Gebraucht',
  damaged: 'Beschädigt',
};
</script>

<template>
  <div class="status-badge" :class="status" aria-label="Zustand des Gegenstands" :data-status="status">
    <SvgRenderer v-if="status === 'new'" name="star" alt="Neuer Gegenstand" width="12" height="12" class="status-badge__icon" />
    <span>{{ statusTextMap[status] }}</span>
  </div>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-list-minimal);
  font-size: var(--text-base);
  line-height: var(--line-height-base);
}

@media screen and (max-width: 1024px) {
  .status-badge {
    font-size: var(--font-size-default);
    line-height: var(--line-height-button);
  }
}

.status-badge[data-status='new'] {
  color: var(--color-text-default);
}

.status-badge[data-status='used'] {
  color: var(--color-text-info);
}

.status-badge[data-status='damaged'] {
  color: var(--color-text-accent-2);
}
</style>
