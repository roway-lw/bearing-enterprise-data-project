<template>
  <div class="enterprise-detail-view">
    <a-page-header
      :title="enterpriseName"
      sub-title="企业详情"
      @back="() => $router.push('/enterprises')"
    >
      <template #extra>
        <a-select
          v-if="batches.length > 1"
          v-model:value="selectedBatch"
          style="width: 200px"
          @change="onBatchChange"
        >
          <a-select-option v-for="b in batches" :key="b.batch_no" :value="b.batch_no">
            {{ b.execute_time }} ({{ b.pipeline_status }})
          </a-select-option>
        </a-select>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <!-- 错误提示 -->
      <a-alert v-if="loadError" type="error" :message="loadError" show-icon style="margin-bottom: 16px" />

      <a-tabs v-model:activeKey="activeTab">
        <!-- 标签画像 -->
        <a-tab-pane key="tags" tab="标签画像">
          <div v-if="detail">
            <!-- 置信度和状态 -->
            <a-descriptions :column="4" size="small" bordered style="margin-bottom: 16px">
              <a-descriptions-item label="置信度">
                <a-progress :percent="Math.round((detail.overall_confidence || 0) * 100)" :size="'small'" style="width: 80px" />
              </a-descriptions-item>
              <a-descriptions-item label="流水线状态">
                <a-tag :color="statusColor(detail.pipeline_status)">{{ detail.pipeline_status || '-' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Token消耗">{{ detail.total_tokens || 0 }}</a-descriptions-item>
              <a-descriptions-item label="耗时">{{ detail.total_time_seconds ? detail.total_time_seconds.toFixed(1) + 's' : '-' }}</a-descriptions-item>
            </a-descriptions>

            <!-- 企业基本信息 -->
            <a-descriptions :column="3" size="small" bordered style="margin-bottom: 16px">
              <a-descriptions-item label="注册资本">{{ detail.registered_capital || '-' }}</a-descriptions-item>
              <a-descriptions-item label="企业简称">{{ detail.enterprise_short_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="员工规模">{{ detail.employee_scale || '-' }}</a-descriptions-item>
            </a-descriptions>

            <!-- 五维标签 -->
            <a-row :gutter="[16, 16]">
              <a-col :span="12" v-for="group in tagGroups" :key="group.title">
                <a-card :title="group.title" size="small">
                  <div v-if="group.items.length">
                    <a-tag v-for="t in group.items" :key="t" style="margin-bottom: 4px">{{ t }}</a-tag>
                  </div>
                  <a-empty v-else :image="simpleImage" description="未明确" />
                </a-card>
              </a-col>
            </a-row>

            <!-- 描述信息 -->
            <a-row :gutter="[16, 16]" style="margin-top: 16px">
              <a-col :span="24" v-if="detail.product_desc">
                <a-card title="产品结构描述" size="small">{{ detail.product_desc }}</a-card>
              </a-col>
              <a-col :span="24" v-if="detail.process_desc">
                <a-card title="工艺能力描述" size="small">{{ detail.process_desc }}</a-card>
              </a-col>
              <a-col :span="24" v-if="detail.application_desc">
                <a-card title="应用领域描述" size="small">{{ detail.application_desc }}</a-card>
              </a-col>
              <a-col :span="24" v-if="detail.supply_chain_desc">
                <a-card title="供应链描述" size="small">{{ detail.supply_chain_desc }}</a-card>
              </a-col>
            </a-row>
          </div>
        </a-tab-pane>

        <!-- 事实关系 -->
        <a-tab-pane key="facts" tab="事实关系">
          <!-- 类型筛选 -->
          <div style="margin-bottom: 12px; display: flex; gap: 8px">
            <a-radio-group v-model:value="factTypeFilter" @change="onFactFilterChange">
              <a-radio-button value="">全部 ({{ factTotal }})</a-radio-button>
              <a-radio-button value="bidding">招投标</a-radio-button>
              <a-radio-button value="customer">客户</a-radio-button>
              <a-radio-button value="supplier">供应商</a-radio-button>
              <a-radio-button value="investment">投资</a-radio-button>
              <a-radio-button value="partnership">合作</a-radio-button>
            </a-radio-group>
          </div>

          <a-table
            :columns="factColumns"
            :data-source="factStore.currentFacts"
            :pagination="{ pageSize: 20 }"
            row-key="id"
            size="small"
            :scroll="{ x: 1200 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'record_type'">
                <a-tag :color="typeColor(record.record_type)">{{ typeName(record.record_type) }}</a-tag>
              </template>
              <template v-if="column.key === 'confidence'">
                <a-progress :percent="Math.round(record.confidence * 100)" :size="'small'" style="width: 60px" />
              </template>
              <template v-if="column.key === 'amount'">
                {{ record.amount ? `${record.amount} ${record.amount_unit || ''}` : '-' }}
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Empty, message } from 'ant-design-vue'
import { getEnterpriseDetail, getEnterpriseBatches } from '@/api/enterprise'
import { useEnterpriseStore } from '@/stores/enterprise'

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const route = useRoute()
const factStore = useEnterpriseStore()

const enterpriseName = computed(() => route.params.name as string)
const detail = ref<any>(null)
const loading = ref(false)
const loadError = ref('')
const batches = ref<any[]>([])
const selectedBatch = ref<string | null>(null)
const activeTab = ref('tags')
const factTypeFilter = ref('')
const factTotal = ref(0)

const tagGroups = computed(() => {
  if (!detail.value) return []
  const d = detail.value
  return [
    { title: '主营产品', items: d.main_products || [] },
    { title: '核心产品', items: d.core_products || [] },
    { title: '高端产品', items: d.high_end_products || [] },
    { title: '产品关键词', items: d.product_keywords || [] },
    { title: '工艺能力', items: d.process_tags || [] },
    { title: '核心工艺', items: d.core_process || [] },
    { title: '制造能力', items: d.manufacturing_tags || [] },
    { title: '特种工艺', items: d.special_process || [] },
    { title: '应用领域', items: d.application_tags || [] },
    { title: '核心应用', items: d.core_application || [] },
    { title: '下游行业', items: d.downstream_industry || [] },
    { title: '供应链角色', items: d.supply_role_tags || [] },
    { title: '客户类型', items: d.customer_type_tags || [] },
    { title: '供应链层级', items: d.supply_level_tags || [] },
    { title: '客户供应链', items: d.supply_chain_tags || [] },
  ].filter(g => g.items && g.items.length > 0)
})

const factColumns = [
  { title: '类型', dataIndex: 'record_type', key: 'record_type', width: 80 },
  { title: '对方企业', dataIndex: 'counterparty', key: 'counterparty', width: 200, ellipsis: true },
  { title: '项目', dataIndex: 'project_name', key: 'project_name', width: 180, ellipsis: true },
  { title: '产品', dataIndex: 'products', key: 'products', width: 150, ellipsis: true },
  { title: '金额', key: 'amount', width: 100 },
  { title: '日期', dataIndex: 'bid_date', key: 'bid_date', width: 100 },
  { title: '来源', dataIndex: 'source_platform', key: 'source_platform', width: 100 },
  { title: '置信度', key: 'confidence', width: 80 },
]

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    detail.value = await getEnterpriseDetail(enterpriseName.value, selectedBatch.value || undefined)
    batches.value = await getEnterpriseBatches(enterpriseName.value)
    if (!selectedBatch.value && batches.value.length) {
      selectedBatch.value = batches.value[0].batch_no
    }
    await loadFacts()
  } catch (e: any) {
    loadError.value = e.message || '加载企业详情失败'
  } finally {
    loading.value = false
  }
}

async function loadFacts() {
  try {
    await factStore.fetchFacts(enterpriseName.value, factTypeFilter.value || undefined)
    factTotal.value = factStore.factTotal
  } catch (e: any) {
    message.warning('加载事实关系失败: ' + (e.message || ''))
  }
}

function onBatchChange() { loadData() }
function onFactFilterChange() { loadFacts() }

function statusColor(s: string) {
  const m: Record<string, string> = { success: 'green', partial: 'orange', failed: 'red' }
  return m[s] || 'default'
}
function typeColor(t: string) {
  const m: Record<string, string> = { bidding: 'blue', customer: 'green', supplier: 'gold', investment: 'red', partnership: 'purple' }
  return m[t] || 'default'
}
function typeName(t: string) {
  const m: Record<string, string> = { bidding: '招投标', customer: '客户', supplier: '供应商', investment: '投资', partnership: '合作' }
  return m[t] || t
}

onMounted(loadData)
watch(enterpriseName, () => loadData())
</script>

<style scoped>
.enterprise-detail-view {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 16px;
}
</style>
