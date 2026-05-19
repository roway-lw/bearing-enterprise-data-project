<template>
  <div class="pipeline-view">
    <!-- 输入与配置区 -->
    <a-card title="流水线执行" style="margin-bottom: 16px">
      <!-- 输入模式切换 -->
      <a-tabs v-model:activeKey="inputMode">
        <a-tab-pane key="manual" tab="手动输入">
          <a-textarea
            v-model:value="nameText"
            placeholder="输入企业名称，每行一个&#10;例如：&#10;河北宝鑫轴承制造有限责任公司&#10;河北鑫泰轴承锻造有限公司"
            :rows="4"
            :disabled="store.isRunning"
          />
        </a-tab-pane>
        <a-tab-pane key="database" tab="数据库导入">
          <DbImport :disabled="store.isRunning" @selected="onDbNamesSelected" />
        </a-tab-pane>
      </a-tabs>

      <!-- 输出配置 -->
      <a-divider style="margin: 12px 0" />
      <div style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap">
        <a-checkbox v-model:checked="fileOutput">文件输出 (JSON + Excel)</a-checkbox>
        <a-checkbox v-model:checked="dbOutput">数据库输出</a-checkbox>
        <template v-if="dbOutput">
          <a-input v-model:value="tagTable" addon-before="标签表" style="width: 260px" />
          <a-input v-model:value="factTable" addon-before="事实表" style="width: 260px" />
        </template>
      </div>

      <!-- 操作按钮 -->
      <div style="margin-top: 16px; display: flex; gap: 12px">
        <a-button
          type="primary"
          size="large"
          :loading="store.isRunning"
          :disabled="!canStart"
          @click="onStart"
        >
          {{ store.isRunning ? '执行中...' : store.taskStatus === 'completed' ? '再次执行' : '开始执行' }}
        </a-button>
        <a-button v-if="store.isRunning" @click="onCancel">取消</a-button>
        <a-button v-if="store.taskId && !store.isRunning" @click="onReset">清空结果</a-button>
        <span v-if="nameCount > 0" style="line-height: 40px; color: #666">
          共 {{ nameCount }} 家企业
        </span>
      </div>
      <a-alert
        v-if="store.error"
        type="error"
        show-icon
        :message="store.error"
        style="margin-top: 12px"
      />
    </a-card>

    <!-- 实时进度面板 -->
    <a-card v-if="store.taskId" title="执行进度" style="margin-bottom: 16px">
      <!-- 批量进度 -->
      <a-progress
        v-if="store.batchTotal > 1"
        :percent="store.batchPercent"
        :format="() => `${store.batchCompleted}/${store.batchTotal}`"
        style="margin-bottom: 12px"
      />

      <!-- 5节点流程时间线 -->
      <a-steps :current="store.currentStageIndex" size="small" style="margin-bottom: 16px">
        <a-step title="采集" :description="getStageDesc(0)" />
        <a-step title="清洗" :description="getStageDesc(1)" />
        <a-step title="打标" :description="getStageDesc(2)" />
        <a-step title="事实提取" :description="getStageDesc(3)" />
        <a-step title="归档" :description="getStageDesc(4)" />
      </a-steps>

      <!-- 当前企业 + 步骤详情 -->
      <a-descriptions :column="2" size="small" bordered>
        <a-descriptions-item label="当前企业">{{ store.currentEnterprise || '-' }}</a-descriptions-item>
        <a-descriptions-item label="当前步骤">{{ store.currentStep || '-' }}</a-descriptions-item>
        <a-descriptions-item label="详细信息" :span="2">{{ store.currentDetail || '-' }}</a-descriptions-item>
      </a-descriptions>

      <!-- 数据源列表 -->
      <div v-if="store.dataSources.length > 0" style="margin-top: 12px">
        <div style="margin-bottom: 6px; font-weight: 500">数据源</div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px">
          <a-tag
            v-for="ds in store.dataSources"
            :key="ds.platform"
            :color="dsColor(ds.status)"
          >
            {{ ds.platform }}
            <span v-if="ds.pages">({{ ds.pages }}页)</span>
          </a-tag>
        </div>
      </div>

      <!-- Token 消耗 + 耗时 -->
      <a-row :gutter="16" style="margin-top: 12px">
        <a-col :span="12">
          <a-statistic title="Token 消耗" :value="store.tokenUsage.total" />
        </a-col>
        <a-col :span="12">
          <a-statistic title="已耗时" :value="formatTime(store.elapsedSeconds)" />
        </a-col>
      </a-row>
    </a-card>

    <!-- 执行结果卡片（单条或批量） -->
    <a-card v-if="store.results.length > 0" title="执行结果">
      <ResultCard
        v-for="r in store.results"
        :key="r.enterprise_name"
        :result="r"
      />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useWebSocket } from '@/composables/useWebSocket'
import { cancelTask } from '@/api/pipeline'
import DbImport from '@/components/pipeline/DbImport.vue'
import ResultCard from '@/components/result/ResultCard.vue'

const store = usePipelineStore()

// WebSocket 自动跟随 taskId
useWebSocket(computed(() => store.taskId))

const inputMode = ref('manual')
const nameText = ref('')
const fileOutput = ref(true)
const dbOutput = ref(false)
const tagTable = ref('enterprise_tag')
const factTable = ref('enterprise_fact')

// 保存/恢复输出配置
const OUTPUT_STORAGE_KEY = 'bearing_output_config'

function saveOutputConfig() {
  try {
    localStorage.setItem(OUTPUT_STORAGE_KEY, JSON.stringify({
      fileOutput: fileOutput.value,
      dbOutput: dbOutput.value,
      tagTable: tagTable.value,
      factTable: factTable.value,
    }))
  } catch { /* ignore */ }
}

function loadOutputConfig() {
  try {
    const saved = localStorage.getItem(OUTPUT_STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (parsed.fileOutput !== undefined) fileOutput.value = parsed.fileOutput
      if (parsed.dbOutput !== undefined) dbOutput.value = parsed.dbOutput
      if (parsed.tagTable) tagTable.value = parsed.tagTable
      if (parsed.factTable) factTable.value = parsed.factTable
    }
  } catch { /* ignore */ }
}

watch([fileOutput, dbOutput, tagTable, factTable], saveOutputConfig)
onMounted(loadOutputConfig)

const parsedNames = computed(() =>
  nameText.value.split('\n').map(s => s.trim()).filter(Boolean)
)
const nameCount = computed(() => parsedNames.value.length)
const canStart = computed(() => {
  if (store.isRunning) return false
  return parsedNames.value.length > 0
})

function onDbNamesSelected(names: string[]) {
  nameText.value = names.join('\n')
  inputMode.value = 'manual'
  message.success(`已加载 ${names.length} 个企业名称`)
}

async function onStart() {
  const names = parsedNames.value
  if (!names.length) return
  await store.start(names, {
    file_output: fileOutput.value,
    db_output: dbOutput.value,
    tag_table: tagTable.value.trim() || 'enterprise_tag',
    fact_table: factTable.value.trim() || 'enterprise_fact',
  })
}

async function onCancel() {
  if (store.taskId) {
    await cancelTask(store.taskId)
    store.reset()
    message.info('任务已取消')
  }
}

function onReset() {
  store.reset()
}

function getStageDesc(idx: number) {
  if (store.currentStageIndex > idx) return '已完成'
  if (store.currentStageIndex === idx) return store.currentStep || '进行中...'
  return ''
}

function dsColor(status: string) {
  const m: Record<string, string> = { success: 'green', failed: 'red', running: 'blue', skipped: 'default' }
  return m[status] || 'default'
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}秒`
  return `${Math.floor(seconds / 60)}分${(seconds % 60).toFixed(0)}秒`
}
</script>

<style scoped>
.pipeline-view {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
}
</style>
