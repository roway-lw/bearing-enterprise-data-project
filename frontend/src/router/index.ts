/** 路由定义 */
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/pipeline',
    },
    {
      path: '/pipeline',
      name: 'Pipeline',
      component: () => import('@/views/PipelineView.vue'),
      meta: { title: '流水线执行' },
    },
    {
      path: '/result/:taskId?',
      name: 'Result',
      component: () => import('@/views/ResultView.vue'),
      meta: { title: '执行结果' },
    },
    {
      path: '/enterprises',
      name: 'EnterpriseList',
      component: () => import('@/views/EnterpriseListView.vue'),
      meta: { title: '企业查询' },
    },
    {
      path: '/enterprises/:name',
      name: 'EnterpriseDetail',
      component: () => import('@/views/EnterpriseDetailView.vue'),
      meta: { title: '企业详情' },
    },
    {
      path: '/llm-config',
      name: 'LlmConfig',
      component: () => import('@/views/LlmConfigView.vue'),
      meta: { title: '模型配置' },
    },
  ],
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || '轴承企业数据平台'} - 轴承企业数据平台`
})

export default router
