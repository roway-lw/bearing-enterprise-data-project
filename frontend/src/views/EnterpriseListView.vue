<template>
  <div class="enterprise-list-view">
    <a-card title="企业查询">
      <!-- 搜索栏 -->
      <div style="display: flex; gap: 12px; margin-bottom: 16px">
        <a-input-search
          v-model:value="store.keyword"
          placeholder="搜索企业名称"
          enter-button="搜索"
          style="max-width: 400px"
          @search="onSearch"
        />
        <a-select v-model:value="store.sortBy" style="width: 140px" @change="onSearch">
          <a-select-option value="execute_time">执行时间</a-select-option>
          <a-select-option value="overall_confidence">置信度</a-select-option>
          <a-select-option value="enterprise_name">企业名称</a-select-option>
        </a-select>
        <a-select v-model:value="store.sortOrder" style="width: 100px" @change="onSearch">
          <a-select-option value="desc">降序</a-select-option>
          <a-select-option value="asc">升序</a-select-option>
        </a-select>
      </div>

      <!-- 表格 -->
      <a-table
        :columns="columns"
        :data-source="store.enterprises"
        :loading="store.loading"
        :pagination="pagination"
        row-key="enterprise_name"
        @change="onTableChange"
        :scroll="{ x: 1400 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'enterprise_name'">
            <router-link :to="`/enterprises/${encodeURIComponent(record.enterprise_name)}`">
              {{ record.enterprise_name }}
            </router-link>
          </template>
          <template v-if="column.key === 'pipeline_status'">
            <a-tag :color="statusColor(record.pipeline_status)">{{ record.pipeline_status || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'overall_confidence'">
            <a-progress :percent="Math.round((record.overall_confidence || 0) * 100)" :size="'small'" style="width: 80px" />
          </template>
          <template v-if="column.key === 'tags'">
            <div class="tag-cell">
              <a-tag v-for="t in getTagList(record).slice(0, 8)" :key="t" size="small" color="blue">{{ t }}</a-tag>
              <span v-if="getTagList(record).length > 8" style="color: #999; font-size: 12px">+{{ getTagList(record).length - 8 }}</span>
            </div>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useEnterpriseStore } from '@/stores/enterprise'

const store = useEnterpriseStore()

const columns = [
  { title: '企业名称', dataIndex: 'enterprise_name', key: 'enterprise_name', width: 280, fixed: 'left' as const },
  { title: '状态', dataIndex: 'pipeline_status', key: 'pipeline_status', width: 80 },
  { title: '置信度', dataIndex: 'overall_confidence', key: 'overall_confidence', width: 100 },
  { title: '标签', key: 'tags', width: 400 },
  { title: '执行时间', dataIndex: 'execute_time', key: 'execute_time', width: 160 },
]

const pagination = computed(() => ({
  current: store.page,
  pageSize: store.pageSize,
  total: store.total,
  showTotal: (t: number) => `共 ${t} 家企业`,
}))

function getTagList(record: any): string[] {
  const tags: string[] = []
  const fields = [
    'main_products', 'core_products', 'high_end_products',
    'process_tags', 'core_process', 'manufacturing_tags', 'special_process',
    'application_tags', 'core_application', 'downstream_industry',
    'supply_chain_tags', 'customer_type_tags', 'supply_role_tags', 'supply_level_tags',
  ]
  for (const f of fields) {
    const v = record[f]
    if (Array.isArray(v)) {
      tags.push(...v)
    }
  }
  // 去重
  return [...new Set(tags)]
}

function onSearch() {
  store.page = 1
  store.fetchList()
}

function onTableChange(pag: any) {
  store.page = pag.current
  store.pageSize = pag.pageSize
  store.fetchList()
}

function statusColor(s: string) {
  const m: Record<string, string> = { success: 'green', partial: 'orange', failed: 'red' }
  return m[s] || 'default'
}

onMounted(() => store.fetchList())
</script>

<style scoped>
.enterprise-list-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px;
}
.tag-cell {
  max-height: 80px;
  overflow-y: auto;
}
</style>
