<template>
  <a-card size="small" style="margin-bottom: 8px" :class="{ 'result-failed': result.status === 'failed' }">
    <div style="display: flex; justify-content: space-between; align-items: center">
      <div>
        <span style="font-weight: 500; margin-right: 12px">{{ result.enterprise_name }}</span>
        <a-tag :color="statusColor">{{ result.status }}</a-tag>
        <span style="color: #666; margin-left: 12px">
          置信度 {{ (result.confidence * 100).toFixed(0) }}%
        </span>
      </div>
      <a-button type="link" size="small" @click="$emit('detail')">查看详情</a-button>
    </div>

    <!-- 标签摘要 -->
    <div v-if="result.tag_summary?.length" style="margin-top: 8px">
      <a-tag v-for="t in result.tag_summary" :key="t" color="blue" size="small">{{ t }}</a-tag>
    </div>

    <!-- 统计信息 -->
    <div style="margin-top: 6px; color: #999; font-size: 12px">
      <span v-if="result.fact_count">事实关系: {{ result.fact_count }}条</span>
      <span v-if="result.token_total" style="margin-left: 12px">Token: {{ result.token_total }}</span>
      <span v-if="result.elapsed_seconds" style="margin-left: 12px">耗时: {{ result.elapsed_seconds.toFixed(0) }}s</span>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EnterpriseResultSummary } from '@/types/pipeline'

const props = defineProps<{ result: EnterpriseResultSummary }>()
defineEmits<{ detail: [] }>()

const statusColor = computed(() => {
  const m: Record<string, string> = { success: 'green', partial: 'orange', failed: 'red' }
  return m[props.result.status] || 'default'
})
</script>

<style scoped>
.result-failed {
  background: #fff2f0;
}
</style>
