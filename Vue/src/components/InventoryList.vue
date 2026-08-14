<script setup lang="ts">
import { CATEGORY_OPTIONS } from '@/helper/constants';

import type { Category, inventoryItem } from '@/types/inventoryTypes';
import { useBreakpoint } from '@/composables/useBreakpoints';

import { computed, ref } from 'vue';

import { useInventory } from '@/composables/useInventory';
import { formatDate } from '@/helper/dateFormatter';

import ModalEditItem from './ModalEditItem.vue';
import StatusBadge from './StatusBadge.vue';
import ButtonCustom from './ButtonCustom.vue';
import SvgRenderer from './SvgRenderer.vue';

const { items, deleteItemMutation } = useInventory();
const selectedItem = ref<inventoryItem | null>(null);

const setSelectedItem = (item: inventoryItem) => {
  selectedItem.value = { ...item };
};

const { isMobile } = useBreakpoint();

const deleteConfirmationStack = ref<number[]>([]);

const showDeleteConfirmation = (itemId: number) => {
  const itemToDelete = items.value.find((item: inventoryItem) => item.id === itemId);
  if (itemToDelete) {
    deleteConfirmationStack.value.push(itemId);
  }
};

const deleteItem = (itemId: number) => {
  deleteItemMutation.mutate(itemId);
  deleteConfirmationStack.value = deleteConfirmationStack.value.filter((id) => id !== itemId);
};

const mapCategoryNames = (val: Category) => {
  return CATEGORY_OPTIONS.find((el) => el.value === val)?.title || 'val';
};
</script>
<template>
  <section class="inventory-list" aria-labelledby="inventory-list-heading">
    <h2 id="inventory-list-heading">Inventar</h2>

    <p v-if="!items || items.length === 0">Keine Gegenstände im Inventar.</p>

    <template v-else>
      <!-- Desktop: genuine data table -->
      <table v-if="!isMobile">
        <caption class="sr-only">
          Liste der Gegenstände im Inventar
        </caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Bild</th>
            <th scope="col">Name</th>
            <th scope="col">Menge</th>
            <th scope="col">Zustand</th>
            <th scope="col">Kategorie</th>
            <th scope="col">Erstellt am</th>
            <th scope="col"><span>Aktion</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in items"
            :key="item.id"
            class="inventory-list__row"
            @click="setSelectedItem(item)"
            @keydown.space="setSelectedItem(item)"
            @keydown.enter="setSelectedItem(item)"
            tabindex="0"
          >
            <td>{{ item.id }}</td>
            <td>
              <img v-if="item.image" :src="item.image" alt="" class="inventory-list__item-image" />
            </td>
            <td>
              {{ item.title }}
            </td>
            <td>
              <span class="inventory-list__item-count">{{ item.count }}</span>
            </td>
            <td>
              <StatusBadge :status="item.condition" />
            </td>
            <td>
              {{ mapCategoryNames(item.category) }}
            </td>
            <td>
              <time class="inventory-list__item-timestamp" :datetime="item.created_at">{{ formatDate(item.created_at) }}</time>
            </td>
            <td class="inventory-list__row-actions">
              <ButtonCustom
                v-show="!deleteConfirmationStack.includes(item.id)"
                mode="delete"
                :aria-label="`${item.title} löschen`"
                @click.stop="showDeleteConfirmation(item.id)"
              >
                <span class="inventory-list__delete-button-content">
                  <SvgRenderer
                    class="inventory-list__delete-button-icon"
                    name="trashcan"
                    aria-hidden="true"
                    width="16"
                    height="16"
                  />
                  <span aria-hidden="true">DEL</span>
                </span>
              </ButtonCustom>

              <span v-show="deleteConfirmationStack.includes(item.id)" class="sr-only"> Löschen bestätigen </span>

              <ButtonCustom
                v-show="deleteConfirmationStack.includes(item.id)"
                mode="delete"
                :aria-label="`Löschen von ${item.title} bestätigen`"
                @click.stop="deleteItem(item.id)"
              >
                <span class="inventory-list__delete-button-content">
                  <SvgRenderer
                    class="inventory-list__delete-button-icon"
                    name="trashcan"
                    aria-hidden="true"
                    width="16"
                    height="16"
                  />
                  <span aria-hidden="true">JA</span>
                </span>
              </ButtonCustom>

              <ButtonCustom
                v-show="deleteConfirmationStack.includes(item.id)"
                mode="default"
                :aria-label="`Löschen von ${item.title} abbrechen`"
                @click.stop="deleteConfirmationStack = deleteConfirmationStack.filter((id) => id !== item.id)"
              >
                <span class="inventory-list__delete-button-content">
                  <span aria-hidden="true">NEIN</span>
                </span>
              </ButtonCustom>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Mobile: card list — no longer forced into <table> markup -->
      <ul v-else class="inventory-list__mobile-list">
        <li
          v-for="item in items"
          :key="item.id"
          class="inventory-list__mobile-row"
          @click="setSelectedItem(item)"
          @keydown.space="setSelectedItem(item)"
          @keydown.enter="setSelectedItem(item)"
          tabindex="0"
        >
          <span class="inventory-list__mobile-item-header">
            <img v-if="item.image" :src="item.image" alt="" class="inventory-list__mobile-item-image" />
            <span class="inventory-list__item-title inventory-list__mobile-item-title">{{ item.title }}</span>
          </span>

          <span class="inventory-list__mobile-description">
            <StatusBadge :status="item.condition" />
            <span>{{ item.category }}</span>
          </span>

          <span class="inventory-list__mobile-footer">
            <span class="inventory-list__item-count">{{ item.count }}x</span>
            <time :datetime="item.created_at">{{ formatDate(item.created_at) }}</time>
          </span>

          <ButtonCustom
            v-show="!deleteConfirmationStack.includes(item.id)"
            mode="delete"
            :aria-label="`${item.title} löschen`"
            class="inventory-list__mobile-delete"
            @click.stop="showDeleteConfirmation(item.id)"
          >
            <span class="inventory-list__delete-button-content">
              <SvgRenderer name="trashcan" aria-hidden="true" width="16" height="16" />
              <span aria-hidden="true">DEL</span>
            </span>
          </ButtonCustom>

          <span v-show="deleteConfirmationStack.includes(item.id)" class="sr-only">Löschen bestätigen</span>
          <ButtonCustom
            v-show="deleteConfirmationStack.includes(item.id)"
            mode="delete"
            :aria-label="`Löschen von ${item.title} bestätigen`"
            @click.stop="deleteItem(item.id)"
          >
            <span class="inventory-list__delete-button-content">
              <SvgRenderer class="inventory-list__delete-button-icon" name="trashcan" aria-hidden="true" width="16" height="16" />
              <span aria-hidden="true">JA</span>
            </span>
          </ButtonCustom>
          <ButtonCustom
            v-show="deleteConfirmationStack.includes(item.id)"
            mode="default"
            :aria-label="`Löschen von ${item.title} abbrechen`"
            @click.stop="deleteConfirmationStack = deleteConfirmationStack.filter((id) => id !== item.id)"
          >
            <span class="inventory-list__delete-button-content">
              <span aria-hidden="true">NEIN</span>
            </span>
          </ButtonCustom>
        </li>
      </ul>
    </template>
  </section>

  <ModalEditItem :item="selectedItem" @close="selectedItem = null" />
</template>
<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.inventory-list {
  padding: var(--spacing-page);
  color: var(--color-text-default);
  border: var(--border-width-standard) solid var(--color-border-default);
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

th,
td {
  padding: var(--spacing-component);
  text-align: left;
}

th:nth-child(1),
th:nth-child(2) {
  width: calc(var(--dimension-icon) + 2 * var(--spacing-component));
}

th:nth-child(4) {
  width: calc(var(--dimension-badge) + 2 * var(--spacing-component));
}

th:nth-child(8) {
  width: calc(var(--dimension-table-cell) + 2 * var(--spacing-component));
}

th {
  padding-bottom: var(--spacing-table-header);
  background-color: var(--color-bg-table-row-hover);
  color: var(--color-text-default);
}

/* Row is the visual hover/click target again, via the stretched-button trick */
.inventory-list__row {
  position: relative;
  transition: background-color 0.3s ease;
  cursor: pointer;
}

.inventory-list__row:hover,
.inventory-list__row:focus-within {
  background-color: var(--color-bg-table-row-hover);
  color: var(--color-text-default);
}

.inventory-list__row-trigger::after {
  content: '';
  position: absolute;
  inset: 0;
}

.inventory-list__item-image {
  width: var(--dimension-icon);
  height: var(--dimension-icon);
  object-fit: cover;
  image-rendering: smooth;
}

.inventory-list__item-count {
  border: var(--border-width-badge) solid;
  background-color: var(--color-bg-accent-1-dark);
  padding: var(--spacing-list-minimal) var(--padding-element-large);
}

.inventory-list__item-timestamp {
  color: var(--color-text-info);
  white-space: wrap;
  word-break: break-word;
}

.inventory-list__row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-list-big);
}

.inventory-list__delete-button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: var(--line-height-button);

  gap: var(--spacing-list-minimal);

  .inventory-list__delete-button-icon {
    height: 16px;
    width: 16px;
  }
}

/* Delete button must sit above the stretched row-trigger to stay clickable */
td > :is(.inventory-list__row-trigger + *, [class*='delete']) {
  position: relative;
  z-index: 1;
}

/* Mobile */
.inventory-list__mobile-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-list-big);
}

.inventory-list__mobile-row {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-list-big);
  transition: background-color 0.3s ease;
  padding-left: var(--spacing-list-medium);
  border-left: var(--border-width-badge) solid var(--color-border-default);
}

.inventory-list__mobile-row:hover,
.inventory-list__mobile-row:focus-within {
  background-color: var(--color-bg-table-row-hover);
  color: var(--color-text-default);
}

.inventory-list__mobile-row__start {
  all: unset;
  cursor: pointer;
  color: inherit;
  font: inherit;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-list-medium);
}

.inventory-list__mobile-row__start::after {
  content: '';
  position: absolute;
  inset: 0;
}

.inventory-list__mobile-delete {
  position: relative;
  z-index: 1;
}

.inventory-list__mobile-item-title {
  font-size: var(--font-size-mobile);
  line-height: var(--line-height-item-small);
}

.inventory-list__mobile-item-header,
.inventory-list__mobile-footer {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--spacing-list-medium);
}

.inventory-list__mobile-description {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  gap: var(--spacing-list-big);
  width: 100%;
}

.inventory-list__item-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-list-medium);
}

.inventory-list__mobile-item-image {
  width: var(--dimension-icon-mobile);
  height: var(--dimension-icon-mobile);
  object-fit: cover;
  image-rendering: smooth;
}
</style>
