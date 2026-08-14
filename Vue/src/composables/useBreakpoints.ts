import { ref, onMounted, onUnmounted } from 'vue';

export const useBreakpoint = (breakpoint = 1024) => {
  const isMobile = ref(window.innerWidth <= breakpoint);
  const handler = () => (isMobile.value = window.innerWidth <= breakpoint);

  onMounted(() => window.addEventListener('resize', handler));
  onUnmounted(() => window.removeEventListener('resize', handler));

  return { isMobile };
};
