<script setup lang="ts">
import { ref, watch } from 'vue';

const { open = false } = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const dialogEl = ref<HTMLDialogElement | null>(null);

watch(
  () => open,
  (isOpen) => {
    if (isOpen) {
      dialogEl.value?.showModal();
    } else {
      dialogEl.value?.close();
    }
  },
  {
    immediate: true,
  },
);

const onBackdropClick = (event: MouseEvent) => {
  if (event.target === dialogEl.value) {
    emit('close');
  }
};
</script>

<template>
  <dialog ref="dialogEl" class="modal" @click="onBackdropClick" @cancel="emit('close')">
    <div class="modal__panel" @click.stop>
      <button class="modal__close" type="button" aria-label="Schließen" @click="emit('close')">×</button>
      <!-- Emittiert das ref als slot prop -> #default= / v-slot= -->
      <slot :dialog-ref="dialogEl" />
    </div>
  </dialog>
</template>

<style scoped>
.modal {
  overflow: visible;
  border: var(--border-width-standard) solid var(--color-border-default);
  border-radius: var(--border-radius-single-edges);
  background-color: var(--color-bg-main);
  color: var(--color-text-default);
  padding: 0;
  min-width: 320px;
}

.modal::backdrop {
  background-color: rgba(0, 0, 0, 0.6);
}

.modal__panel {
  padding: var(--spacing-page);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-component);
}

.modal__close {
  align-self: flex-end;
  border: none;
  background: none;
  color: var(--color-text-default);
  cursor: pointer;
  font-size: var(--font-size-icon);
  line-height: var(--line-height-button);
  padding: 0;

  &:hover {
    color: var(--color-text-accent-3);
  }
}

dialog {
  --duration: 0.25s;

  transition:
    opacity var(--duration) ease-in-out,
    display var(--duration) ease-in-out allow-discrete,
    overlay var(--duration) ease-in-out allow-discrete; /* allow-discrete enables the animation of discrete animation type properties, such as display -> display is used for dialog internally */

  /* Post-Entry State */
  &[open] {
    opacity: 1;
  }

  /* Closing State */
  &:not([open]) {
    opacity: 0;
  }

  /* The style when closed -> iitial styles when added to the DOM -> useful for dialog display: none  */
  @starting-style {
    &[open] {
      opacity: 0;
    }
  }
}
</style>
