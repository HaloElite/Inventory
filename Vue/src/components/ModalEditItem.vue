<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue';
import { CATEGORY_OPTIONS } from '@/helper/constants';
import { useInventory } from '@/composables/useInventory';
import type { inventoryItem, Category } from '@/types/inventoryTypes';
import Modal from './Modal.vue';
import ComboBox from './ComboBox.vue';
import InputCustom from '@/components/InputCustom.vue';
import ButtonCustom from '@/components/ButtonCustom.vue';

const props = defineProps<{
  item: inventoryItem | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { updateItemMutation, deleteItemMutation } = useInventory();

const editTitle = ref<string>(''),
  editCount = ref<number | string>(0),
  category = ref<Category>('general');

watch(
  () => props.item,
  (newItem) => {
    if (newItem !== null) {
      editTitle.value = newItem.title;
      editCount.value = newItem.count;
      category.value = newItem.category;
    }
  },
);

const onUpdate = async () => {
  if (!props.item) return;
  await updateItemMutation.mutateAsync({
    title: editTitle.value,
    count: Number(editCount.value),
    id: props.item.id,
    category: category.value,
  });
  emit('close');
};

const onDelete = async () => {
  if (!props.item) return;
  await deleteItemMutation.mutateAsync(props.item.id);
  emit('close');
};
</script>

<template>
  <Modal :open="item !== null" @close="emit('close')">
    <template #default="{ dialogRef }">
      <h2 class="edit-modal__title">Item bearbeiten</h2>
      <div class="edit-modal__fields" ref="target">
        <InputCustom name="Gegenstand" v-model="editTitle" />
        <InputCustom name="Anzahl" type="number" v-model="editCount" />
        <ComboBox
          name="Kategorie"
          dropdown-label-name="Kategorie"
          v-model="category"
          :teleport-target="dialogRef"
          :options="CATEGORY_OPTIONS"
        />
      </div>
      <div class="edit-modal__actions">
        <ButtonCustom @click="onUpdate">Aktualisieren</ButtonCustom>
        <ButtonCustom mode="delete" @click="onDelete">Löschen</ButtonCustom>
      </div>
    </template>
  </Modal>
</template>

<style scoped>
.edit-modal__title {
  margin: 0;
  font-size: var(--font-size-label);
}

.edit-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-component);
}

.edit-modal__actions {
  display: flex;
  gap: var(--spacing-component);
}
</style>
