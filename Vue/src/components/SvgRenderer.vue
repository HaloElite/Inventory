<script lang="ts" setup>
import { icons } from '@/assets/icons';
defineProps<{ name: keyof typeof icons }>();
</script>

<template>
  <img :src="icons[name]" />
</template>
