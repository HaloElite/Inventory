<script setup lang="ts">
import { ref } from 'vue';
defineEmits<{
  click: [ev: MouseEvent];
}>();

const {
  arLabelName = 'label-custom',
  mode = 'default',
  active = false,
} = defineProps<{
  arLabelName?: string;
  mode?: 'default' | 'delete';
  active?: boolean;
}>();

const buttoncustom = ref<HTMLButtonElement | null>(null);

defineExpose({
  buttoncustom,
});
</script>

<template>
  <button
    ref="buttoncustom"
    class="button-custom"
    :class="{ 'mode-delete': mode === 'delete', active: active }"
    type="button"
    @click.stop="$emit('click', $event)"
    @keydown.stop
    :aria-label="arLabelName"
  >
    <slot />
  </button>
</template>

<style scoped>
.button-custom {
  background-color: var(--color-bg-main);
  color: var(--color-text-default);
  border: var(--border-width-standard) solid var(--color-border-default);
  padding: var(--spacing-button);
  cursor: pointer;
  font-size: var(--font-size-button);
  line-height: var(--line-height-button);
  display: inline-flex;
  width: var(--dimension-button-full);
  align-items: center;
  justify-content: center;
  transition: border-color 0.3s ease;
  &.active {
    border-color: var(--color-border-accent-1);
  }
  &:hover {
    border-color: var(--color-border-hover-1);
  }
  &:focus-visible {
    outline: none;
    border-color: transparent;
    box-shadow: 2px 2px 0 3px var(--color-border-accent-1);
  }
}

.mode-delete {
  border-color: var(--color-border-accent-2);
  color: var(--color-text-accent-2);
  &:hover {
    border-color: var(--color-border-hover-2);
  }
}

@media screen and (max-width: 1024px) {
  .button-custom {
    font-size: var(--font-size-mobile);
    line-height: var(--line-height-button-small);
  }
}
</style>
