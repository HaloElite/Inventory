<script lang="ts" setup>
import { icons } from '@/assets/icons';
import { onMounted, onBeforeUnmount, ref } from 'vue';
import SvgRenderer from './SvgRenderer.vue';
import ButtonCustom from './ButtonCustom.vue';

const NAV_ELEMENTS = [
  {
    id: 'n-1',
    route: '',
    alt: 'Dashboard',
    label: 'Dashboard',
    icon: 'home',
  },
  {
    id: 'n-2',
    route: 'Visualizer',
    alt: 'Visualizer',
    label: 'Visualizer',
    icon: 'items',
  },
];

const isOpen = ref<boolean>(false),
  buttoncustom = ref<InstanceType<typeof ButtonCustom> | null>(null);

const controller = new AbortController();

const closeMenu = () => {
  isOpen.value = false;
  buttoncustom.value?.buttoncustom?.focus();
};

onMounted(() => {
  window.addEventListener(
    'keydown',
    (e) => {
      if (e.key === 'Escape' && isOpen.value) {
        closeMenu();
      }
    },
    { signal: controller.signal },
  );
});

onBeforeUnmount(() => {
  controller.abort();
});
</script>

<template>
  <ButtonCustom
    ref="buttoncustom"
    class="nav-list-handle"
    :class="{ open: isOpen }"
    @click="isOpen = !isOpen"
    :aria-label="isOpen ? 'Close navigation' : 'Open navigation'"
  >
    <span></span>
    <span></span>
    <span></span>
  </ButtonCustom>

  <div class="nav-list-container-backdrop" :class="{ open: isOpen }" @click.self="closeMenu">
    <nav class="nav-list-container" :class="{ open: isOpen }" :inert="!isOpen">
      <ButtonCustom class="nav-list-container__close-btn" @click="closeMenu" aria-label="Close navigation"> x </ButtonCustom>

      <ol class="nav-list-ordered">
        <li v-for="el in NAV_ELEMENTS" :key="el.id" class="nav-list-ordered__item">
          <SvgRenderer :name="el.icon as keyof typeof icons" :alt="el.alt" class="nav-list-ordered__icon" />
          <RouterLink :to="`/${el.route.toLowerCase()}`">{{ el.label }}</RouterLink>
        </li>
      </ol>
    </nav>
  </div>
</template>

<style lang="css" scoped>
.nav-list-handle {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  height: 2.5rem;
  width: 2.5rem;
  background-color: var(--color-bg-main);
  border: var(--border-width-standard) solid var(--color-border-default);
  cursor: pointer;

  span {
    display: block;
    width: 1.1rem;
    height: 2px;
    background-color: var(--color-text-default);
    border-radius: 2px;
    transition: opacity 150ms;
  }

  &:hover span {
    background-color: var(--color-bg-accent-1);
  }
}

.nav-list-container {
  position: fixed;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
  gap: var(--spacing-component);
  left: 0;
  top: 0;
  width: auto;
  height: 100%;
  overflow: hidden;
  visibility: hidden;
  padding: var(--padding-element-large) var(--padding-element);
  border: var(--border-width-standard) solid var(--color-border-default);
  background-color: var(--color-bg-main);
  clip-path: circle(0% at 0 0);
  transition:
    clip-path 400ms ease-in-out,
    visibility 0s 400ms;

  &.open {
    visibility: visible;
    clip-path: circle(150% at 0 0);
    transition:
      clip-path 400ms ease-in-out,
      visibility 0s;
  }
}

.nav-list-container__close-btn {
  align-self: flex-end;
}

.nav-list-ordered {
  margin-block-start: var(--spacing-nav-list);
  margin-block-end: var(--spacing-nav-list);
  padding-inline-start: var(--spacing-nav-list);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-component);
  list-style: none;
  margin: var(--spacing-nav-list);
  height: 100%;

  a {
    flex-grow: 1;
    text-decoration: none;
    font-size: var(--text-base);
    font-weight: var(--weight-base);
    color: var(--color-text-default);
    transition: color 150ms;
  }
}

.nav-list-ordered__item {
  position: relative;
  padding: var(--padding-element-thin) var(--padding-element) var(--padding-element-thin) var(--padding-element);
  border-top-right-radius: var(--border-radius-single-edges);
  border-bottom-right-radius: var(--border-radius-single-edges);
  display: flex;
  align-items: center;
  gap: var(--spacing-component);

  &::before {
    content: '';
    position: absolute;
    left: 0;
    height: 100%;
    width: 0.25rem;
    background-color: var(--color-bg-accent-1);
    opacity: 0;
    transition: opacity 150ms;
  }

  &:has(.router-link-active),
  &:has(.router-link-exact-active),
  &:has(a:hover),
  &:has(a:focus) {
    &::before {
      opacity: 1;
    }
    a {
      color: var(--color-bg-accent-1);
    }
    background-color: var(--color-bg-accent-1-dark);
  }
}

.nav-list-container-backdrop {
  position: fixed;
  inset: 0;
  background-color: transparent;
  pointer-events: none;
  z-index: 100;
  transition: background-color 200ms ease-in-out;

  &.open {
    background-color: rgba(0, 0, 0, 0.4);
    pointer-events: auto;
  }
}
</style>
