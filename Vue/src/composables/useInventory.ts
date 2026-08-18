import type { inventoryItem } from '@/types/inventoryTypes';
import { useQueryClient, useQuery, useMutation } from '@tanstack/vue-query';

import { ref } from 'vue';

const shouldLoad = ref<boolean>(false),
  item = ref<string>(''),
  count = ref<number>(1),
  storage = ref<string>(''),
  itemError = ref<boolean>(false),
  category = ref<string>('general');

export const useInventory = () => {
  const queryClient = useQueryClient();

  // --------------------------------------------------------------------------
  //   INVENTAR LADEN
  // --------------------------------------------------------------------------
  const inventoryQuery = useQuery({
    queryKey: ['inventory'],
    queryFn: async (): Promise<inventoryItem[]> => {
      const response = await fetch('/api/get-inventory');

      if (!response.ok) {
        throw new Error('Failed to fetch inventory');
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        console.warn('Expected inventory array but received:', data);
        return [];
      }

      return data.map((item: inventoryItem) => ({
        ...item,
        image: item.image ? `/${item.image}` : undefined,
      }));
    },
    enabled: () => shouldLoad.value,
    initialData: [],
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    retry: false,
  });

  // --------------------------------------------------------------------------
  //   ITEM HINZUFÜGEN
  // --------------------------------------------------------------------------
  const addItemMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/add-inventory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          item: item.value,
          count: count.value,
          condition: 'new',
          category: category.value,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to add item');
      }

      item.value = '';
      itemError.value = false;
    },

    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },

    onError: () => {
      itemError.value = true;
    },
  });

  // --------------------------------------------------------------------------
  //   ITEM AKTUALISIEREN
  // --------------------------------------------------------------------------
  const updateItemMutation = useMutation({
    mutationFn: async (properties: { title: string; count: number; id: number; category: string }) => {
      await fetch(`/api/update-item/${properties.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: properties.title,
          count: properties.count,
          category: properties.category,
        }),
      });
    },

    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
    onError(error) {
      console.error('ERROR', error);
    },
  });

  // --------------------------------------------------------------------------
  //   ITEM LÖSCHEN
  // --------------------------------------------------------------------------
  const deleteItemMutation = useMutation({
    mutationFn: async (id: number) => {
      await fetch(`/api/delete-item/${id}`, {
        method: 'DELETE',
      });
    },

    async onSuccess() {
      await queryClient.invalidateQueries({
        queryKey: ['inventory'],
      });
    },
    onError(error) {
      console.error('ERROR', error);
    },
  });

  // --------------------------------------------------------------------------
  //   INVENTAR LÖSCHEN
  // --------------------------------------------------------------------------
  const clearInventoryMutation = useMutation({
    mutationFn: async () => {
      await fetch('/api/clear-inventory', {
        method: 'DELETE',
      });
    },

    async onSuccess() {
      await queryClient.invalidateQueries({
        queryKey: ['inventory'],
      });
    },
    onError(error) {
      console.error('ERROR', error);
    },
  });

  return {
    // State
    shouldLoad,

    // Actions
    items: inventoryQuery.data,
    addItemMutation,
    updateItemMutation,
    deleteItemMutation,
    clearInventoryMutation,

    // Form
    item,
    count,
    category,
    storage,
    itemError,

    // Additional information
    isLoading: inventoryQuery.isLoading,
    isFetching: inventoryQuery.isFetching,
    isError: inventoryQuery.isError,
  };
};
