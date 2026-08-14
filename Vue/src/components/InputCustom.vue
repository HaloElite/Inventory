<script setup lang="ts">
import { ref } from 'vue';

const {
  type = 'text',
  name = 'input-custom',
  arLabelName = 'label-custom',
  placeholder = 'Eingabe',
  error = false,
} = defineProps<{
  type?: string;
  name?: string;
  arLabelName?: string;
  placeholder?: string;
  error?: boolean;
}>();

defineEmits<{
  focus: [];
}>();

const currentValue = defineModel<string | number | null>(),
  inputElement = ref<HTMLInputElement | null>(null);
</script>

<template>
  <input
    ref="inputElement"
    :name="name"
    :type="type"
    :aria-label="arLabelName"
    v-model="currentValue"
    :placeholder="placeholder"
    autocomplete="off"
    class="input-custom"
    @focusin="$emit('focus')"
    :class="{ 'input-custom__error': error }"
  />
</template>

<style scoped>
.input-custom {
  position: relative;
  padding: var(--spacing-inputs);
  border: var(--border-width-standard) solid var(--color-border-default);
  background-color: var(--color-bg-main);
  color: var(--color-text-default);
  font-size: var(--font-size-default);
  width: var(--dimension-input);
  box-sizing: border-box;
  &:hover {
    border-color: var(--color-border-hover-1);
  }
}

.input-custom__error {
  border-color: var(--color-border-accent-2);
}

.input-custom:focus {
  outline: none;
  border-color: transparent;
  box-shadow: 2px 2px 0 3px var(--color-border-accent-1);
}

@media screen and (max-width: 1024px) {
  .input-custom {
    width: var(--dimension-input-full);
    font-size: var(--font-size-mobile);
  }
}
</style>
