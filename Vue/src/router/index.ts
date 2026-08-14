import VisualizerView from '@/views/VisualizerView.vue';
import HomePage from '@/views/HomePage.vue';
import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', component: HomePage },
  { path: '/visualizer', component: VisualizerView },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router;
