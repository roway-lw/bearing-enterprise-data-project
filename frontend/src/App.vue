<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header style="background: #fff; padding: 0 24px; display: flex; align-items: center; border-bottom: 1px solid #f0f0f0">
      <div style="font-size: 18px; font-weight: 600; color: #1890ff; margin-right: 32px">
        轴承企业数据平台
      </div>
      <a-menu mode="horizontal" :selected-keys="[currentRoute]" @click="onMenuClick">
        <a-menu-item key="/pipeline">流水线执行</a-menu-item>
        <a-menu-item key="/enterprises">企业查询</a-menu-item>
        <a-menu-item key="/llm-config">模型配置</a-menu-item>
      </a-menu>
    </a-layout-header>
    <a-layout-content style="background: #f5f5f5; padding: 16px 0">
      <router-view />
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => {
  const path = route.path
  if (path.startsWith('/enterprises')) return '/enterprises'
  if (path.startsWith('/result')) return '/pipeline'
  if (path.startsWith('/llm')) return '/llm-config'
  return path
})

function onMenuClick({ key }: { key: string }) {
  router.push(key)
}
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>
