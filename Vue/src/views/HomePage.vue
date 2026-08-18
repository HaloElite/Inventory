<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useInventory } from '@/composables/useInventory';
import { CATEGORY_OPTIONS } from '@/helper/constants';

import Modal from '@/components/Modal.vue';
import ComboBox from '@/components/ComboBox.vue';
import InputCustom from '@/components/InputCustom.vue';
import ButtonCustom from '@/components/ButtonCustom.vue';
import InventoryList from '@/components/InventoryList.vue';

const { shouldLoad, items, item, count, category, storage, itemError, addItemMutation, clearInventoryMutation } = useInventory();

const clearErrorOnFocus = () => {
  itemError.value = false;
};

const openConfirm = ref<boolean>(false);

const confirmClear = () => {
  clearInventoryMutation.mutate();
  openConfirm.value = false;
};

const openConfirmClear = () => {
  if (items.value.length) openConfirm.value = true;
};

onMounted(() => (shouldLoad.value = true));
</script>

<template>
  <div class="overview-page">
    <fieldset class="overview-page__elements">
      <legend>Aktionen</legend>

      <div class="overview-page__elements-inputs">
        <InputCustom
          @focus="clearErrorOnFocus()"
          :error="itemError"
          name="Gegenstand"
          ar-label-name="Gegenstand"
          placeholder="Spaten"
          v-model="item"
        />
        <InputCustom
          @focus="clearErrorOnFocus()"
          name="Gegenstand"
          ar-label-name="Gegenstand"
          placeholder="Lagerort"
          v-model="storage"
        />
        <InputCustom name="Anzahl" ar-label-name="Anzahl" type="number" placeholder="Anzahl" v-model="count" />
        <ComboBox
          name="Kategorie"
          dropdown-label-name="Kategorie"
          v-model="category"
          teleport-target="body"
          :options="CATEGORY_OPTIONS"
        />
      </div>

      <div class="overview-page__elements-actions">
        <ButtonCustom ar-label-name="Gegenstand hinzufügen" @click="addItemMutation.mutateAsync()">Hinzufügen</ButtonCustom>
        <ButtonCustom :disabled="!items.length" ar-label-name="Gegenstände löschen" @click="openConfirmClear"
          >Liste leeren</ButtonCustom
        >
      </div>
    </fieldset>

    <InventoryList />

    <Modal :open="openConfirm" @close="openConfirm = false">
      <p>Wirklich löschen?</p>
      <ButtonCustom @click="confirmClear">Ja</ButtonCustom>
      <ButtonCustom @click="openConfirm = false">Nein</ButtonCustom>
    </Modal>
  </div>
</template>

<style scoped>
.overview-page {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-section);
  padding-top: var(--spacing-section);
}

.overview-page__elements {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-component);
  color: var(--color-text-inverted);
  border: var(--border-width-standard) solid var(--color-border-default);
  margin: 0;

  legend {
    font-size: var(--font-size-label);
    padding: 0 var(--spacing-section);
  }

  .overview-page__elements-inputs {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: var(--spacing-component);
  }

  .overview-page__elements-actions {
    display: flex;
    flex-direction: column;
    justify-content: start;
    gap: var(--spacing-component);
  }
}

@media screen and (max-width: 1024px) {
  .overview-page__elements-inputs,
  .overview-page__elements-actions {
    word-break: break-word;
    min-width: var(--dimension-control-s);
    flex: 1;
  }
  .overview-page__elements {
    flex-wrap: wrap;
    justify-content: space-between;
  }
}

.item_list-items {
  list-style: none;
  color: var(--color-text-inverted);
}
</style>
