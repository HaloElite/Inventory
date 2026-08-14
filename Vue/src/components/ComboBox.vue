<script setup lang="ts">
import { useFloating, flip, shift, offset, size } from '@floating-ui/vue';
import { ref, useTemplateRef, nextTick, onMounted, useId } from 'vue';
import { useClickOutside } from '@/composables/clickOutside';

const {
  name = 'select-custom',
  arLabelName = 'label-custom',
  dropdownLabelName = 'dropdown-custom',
  placeholder = 'Auswählen',
  error = false,
  options = [],
  teleportTarget = null,
} = defineProps<{
  name?: string;
  arLabelName?: string;
  dropdownLabelName?: string;
  placeholder?: string;
  error?: boolean;
  options?: { title: string; value: string }[];
  teleportTarget?: string | HTMLElement | null;
}>();

defineEmits<{
  focus: [];
}>();

const currentValue = defineModel<string | number | null>(),
  openDropdown = ref<boolean>(false),
  inputElement = ref<HTMLInputElement | null>(null),
  dropdownOption = useTemplateRef<HTMLElement[] | null>('dropdownOption'),
  floating = ref<HTMLElement | null>(null),
  dropdownId = useId();

const { floatingStyles } = useFloating(inputElement, floating, {
  placement: 'bottom-start',
  middleware: [
    flip(),
    shift(),
    offset(5),
    size({
      apply({ availableWidth, availableHeight, elements }) {
        Object.assign(elements.floating.style, {
          maxWidth: `${Math.max(0, availableWidth)}px`,
          maxHeight: `${Math.min(400, availableHeight)}px`,
        });
      },
    }),
  ],
});

const selectOption = (selectedValue: string) => {
  currentValue.value = selectedValue;
  openDropdown.value = false;
  inputElement.value?.focus();
};

const showDropdown = () => {
  if (!openDropdown.value) openDropdown.value = true;
};

const toggleDropdown = () => {
  openDropdown.value = !openDropdown.value;
  focusFirstOption();
};

const focusFirstOption = async () => {
  await nextTick(() => dropdownOption.value?.[0]?.focus());
};

const keyboardNavigation = (event: KeyboardEvent) => {
  if (event.code === 'ArrowDown' || event.code === 'ArrowUp' || event.code === 'Enter' || event.code === 'Space') {
    event.preventDefault();
    showDropdown();
    focusFirstOption();
  }
  if (event.code === 'Escape') {
    openDropdown.value = false;
  }
};

const focusNextOption = (event: KeyboardEvent, index: number) => {
  const nextIndex = (index + 1) % options.length;
  focusOption(nextIndex);
};

const focusPreviousOption = (event: KeyboardEvent, index: number) => {
  const previousIndex = index === 0 ? options.length - 1 : index - 1;
  focusOption(previousIndex);
};

const focusOption = (index: number) => {
  nextTick(() => {
    dropdownOption.value?.[index]?.focus();
  });
};

onMounted(() => {
  useClickOutside(inputElement, [floating], openDropdown);
});
</script>

<template>
  <button
    ref="inputElement"
    :name="name"
    type="button"
    :aria-label="arLabelName"
    :placeholder="placeholder"
    class="select-custom"
    role="combobox"
    aria-haspopup="listbox"
    :aria-expanded="openDropdown"
    :aria-controls="dropdownId"
    @click="toggleDropdown"
    @keydown="keyboardNavigation($event)"
    @keydown.tab="openDropdown = false"
    @focusin="$emit('focus')"
    :class="{ 'select-custom__error': error }"
  >
    {{ currentValue ? options.find((option) => option.value === currentValue)?.title : placeholder }}
  </button>

  <template v-if="teleportTarget">
    <Teleport :to="teleportTarget">
      <Transition name="fade" mode="out-in">
        <div ref="floating" :style="floatingStyles" v-if="openDropdown" class="select-custom__dropdown" @click.stop>
          <ul :id="dropdownId" role="listbox" :aria-label="dropdownLabelName" @keydown.escape="openDropdown = false">
            <li
              ref="dropdownOption"
              role="option"
              :aria-label="option.title"
              v-for="(option, index) in options"
              tabindex="0"
              :key="option.value"
              @click="selectOption(option.value)"
              @keydown.enter.prevent.stop="selectOption(option.value)"
              @keydown.space.prevent.stop="selectOption(option.value)"
              @keydown.down.prevent="focusNextOption($event, index)"
              @keydown.up.prevent="focusPreviousOption($event, index)"
            >
              {{ option.title }}
            </li>
          </ul>
        </div>
      </Transition>
    </Teleport>
  </template>
</template>

<style scoped>
.select-custom {
  position: relative;
  padding: var(--spacing-inputs);
  border: var(--border-width-standard) solid var(--color-border-default);
  background-color: var(--color-bg-main);
  color: var(--color-text-default);
  font-size: var(--font-size-default);
  width: var(--dimension-input);
  box-sizing: border-box;
}

.select-custom__error {
  border-color: var(--color-border-accent-2);
}

.select-custom:focus {
  outline: none;
  border-color: transparent;
  box-shadow: 2px 2px 0 3px var(--color-border-accent-1);
}

.select-custom__dropdown {
  background-color: var(--color-bg-main);
  border: var(--border-width-standard) solid var(--color-border-default);
  border-radius: var(--border-radius-single-edges);
  box-shadow: var(--box-shadow-dropdown);
  z-index: 1000;
  padding: var(--spacing-component);
  max-height: var(--dimension-dropdown);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-default) var(--color-bg-main);

  ul {
    margin: 0;
    padding: 0;
  }

  li {
    list-style: none;
    padding: var(--spacing-button) 0;
    cursor: pointer;
  }

  li:hover {
    color: var(--color-text-inverted);
  }

  li:focus {
    outline: none;
    background-color: var(--color-bg-accent-1-hover);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media screen and (max-width: 1024px) {
  .select-custom {
    width: var(--dimension-input-full);
    font-size: var(--font-size-mobile);
  }
}
</style>
