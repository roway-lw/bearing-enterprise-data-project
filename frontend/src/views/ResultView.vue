<template>
  <div class="result-view">
    <a-card title="执行结果">
      <a-empty v-if="store.results.length === 0" description="暂无执行结果" />
      <ResultCard
        v-for="r in store.results"
        :key="r.enterprise_name"
        :result="r"
        @detail="goDetail(r.enterprise_name)"
      />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { usePipelineStore } from '@/stores/pipeline'
import ResultCard from '@/components/result/ResultCard.vue'
import { useRouter } from 'vue-router'

const store = usePipelineStore()
const router = useRouter()

function goDetail(name: string) {
  router.push(`/enterprises/${encodeURIComponent(name)}`)
}
</script>

<style scoped>
.result-view {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
}
</style>
