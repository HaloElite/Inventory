import { onUnmounted, type Ref } from 'vue';

const useClickOutside = (target: Ref<HTMLElement | null>, ignore: Array<Ref<HTMLElement | null>>, toggleRef: Ref<boolean>) => {
  const controller = new AbortController();

  const handleClickOutside = (event: PointerEvent) => {
    if (!target.value) return;

    const clickTarget: EventTarget | undefined = event.composedPath()[0];

    if (!(clickTarget instanceof Node)) return;

    if (!target.value.contains(clickTarget) && ignore.every((el) => !el.value?.contains(clickTarget))) {
      toggleRef.value = false;
    }
  };

  window.addEventListener('pointerdown', handleClickOutside, { signal: controller.signal, passive: true });

  onUnmounted(() => {
    controller.abort();
  });
};

export { useClickOutside };
