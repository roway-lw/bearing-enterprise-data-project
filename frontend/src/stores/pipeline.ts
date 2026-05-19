/** 流水线状态管理 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  OutputConfig, ProgressMessage, EnterpriseResultSummary,
  DataSourceStatus, TokenUsage
} from '@/types/pipeline'
import { runPipeline } from '@/api/pipeline'

export const usePipelineStore = defineStore('pipeline', () => {
  // 当前任务
  const taskId = ref<string | null>(null)
  const taskStatus = ref<'idle' | 'queued' | 'running' | 'completed' | 'failed'>('idle')
  const enterpriseNames = ref<string[]>([])
  const outputConfig = ref<OutputConfig>({ file_output: true, db_output: false })

  // 实时进度
  const currentProgress = ref(0)
  const currentStage = ref('')
  const currentStep = ref('')
  const currentDetail = ref('')
  const currentEnterprise = ref('')
  const elapsedSeconds = ref(0)
  const dataSources = ref<DataSourceStatus[]>([])
  const tokenUsage = ref<TokenUsage>({ total: 0, stages: {} })

  // 批量进度
  const batchCompleted = ref(0)
  const batchTotal = ref(0)

  // 结果
  const results = ref<EnterpriseResultSummary[]>([])
  const error = ref<string | null>(null)

  // 计算属性
  const isRunning = computed(() => taskStatus.value === 'running' || taskStatus.value === 'queued')
  const progressPercent = computed(() => Math.min(currentProgress.value, 100))
  const batchPercent = computed(() =>
    batchTotal.value > 0 ? Math.round((batchCompleted.value / batchTotal.value) * 100) : 0
  )

  // 当前处理阶段对应的步骤索引 (0-4)
  const currentStageIndex = computed(() => {
    const p = currentProgress.value
    if (p <= 60) return 0  // 采集
    if (p <= 80) return 1  // 清洗
    if (p <= 95) return 2  // 打标
    if (p <= 97) return 3  // 事实提取
    return 4               // 归档
  })

  function resetProgressState(keepResults = false) {
    taskId.value = null
    currentProgress.value = 0
    currentStage.value = ''
    currentStep.value = ''
    currentDetail.value = ''
    currentEnterprise.value = ''
    elapsedSeconds.value = 0
    dataSources.value = []
    tokenUsage.value = { total: 0, stages: {} }
    batchCompleted.value = 0
    batchTotal.value = 0
    error.value = null
    if (!keepResults) results.value = []
  }

  async function start(names: string[], config: OutputConfig) {
    resetProgressState(false)
    enterpriseNames.value = names
    outputConfig.value = config
    batchTotal.value = names.length
    taskStatus.value = 'queued'

    try {
      const res = await runPipeline({
        enterprise_names: names,
        output_config: config,
      })
      taskId.value = res.task_id
      taskStatus.value = 'running'
      currentProgress.value = 0
      currentStage.value = '调度'
      currentStep.value = '任务已创建'
      currentDetail.value = `等待后端开始执行，共 ${names.length} 家企业`
    } catch (e: any) {
      finishAsFailed(e.message)
    }
  }

  function updateProgress(msg: ProgressMessage) {
    if (msg.progress !== undefined) currentProgress.value = msg.progress
    if (msg.stage) currentStage.value = msg.stage
    if (msg.step) currentStep.value = msg.step
    if (msg.detail) currentDetail.value = msg.detail
    if (msg.elapsed_seconds !== undefined) elapsedSeconds.value = msg.elapsed_seconds
    if (msg.enterprise_name) currentEnterprise.value = msg.enterprise_name
    if (msg.data_sources) dataSources.value = msg.data_sources
    if (msg.token_usage) {
      const usage: any = msg.token_usage
      tokenUsage.value = {
        ...usage,
        total: usage.total ?? usage.total_tokens ?? 0,
      }
    }
    if (msg.type === 'progress') taskStatus.value = 'running'
  }

  function addResult(msg: ProgressMessage) {
    results.value.push({
      enterprise_name: msg.enterprise_name || '',
      status: msg.status || 'unknown',
      confidence: msg.confidence || 0,
      elapsed_seconds: msg.elapsed_seconds,
      token_total: msg.token_total,
      tag_summary: msg.tag_summary,
      fact_count: msg.fact_count,
    })
    if (msg.batch_progress) {
      batchCompleted.value = msg.batch_progress.completed
      batchTotal.value = msg.batch_progress.total
    }
  }

  function setCompleted() {
    taskStatus.value = 'completed'
    currentProgress.value = 100
    currentStep.value = '执行完成'
    currentDetail.value = '可以再次点击开始执行'
  }

  function finishAsFailed(message: string) {
    taskStatus.value = 'failed'
    error.value = message
    currentStep.value = '执行失败'
    currentDetail.value = message
  }

  function reset() {
    taskStatus.value = 'idle'
    enterpriseNames.value = []
    resetProgressState(false)
  }

  return {
    taskId, taskStatus, enterpriseNames, outputConfig,
    currentProgress, currentStage, currentStep, currentDetail,
    currentEnterprise, elapsedSeconds, dataSources, tokenUsage,
    batchCompleted, batchTotal, results, error,
    isRunning, progressPercent, batchPercent, currentStageIndex,
    start, updateProgress, addResult, setCompleted, finishAsFailed, reset,
  }
})
