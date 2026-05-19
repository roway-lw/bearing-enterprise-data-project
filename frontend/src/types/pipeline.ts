/** 流水线相关 TypeScript 类型定义 */

export interface OutputConfig {
  file_output: boolean
  db_output: boolean
  tag_table?: string
  fact_table?: string
}

export interface PipelineRunRequest {
  enterprise_names: string[]
  output_config: OutputConfig
}

export interface PipelineRunResponse {
  task_id: string
  enterprise_count: number
  status: string
}

export interface DataSourceStatus {
  platform: string
  status: 'success' | 'failed' | 'skipped' | 'running'
  pages: number
  text_length?: number
}

export interface TokenUsageStage {
  input_tokens: number
  output_tokens: number
  total_tokens: number
}

export interface TokenUsage {
  total: number
  stages: Record<string, TokenUsageStage>
}

export interface ProgressMessage {
  type: 'progress' | 'enterprise_complete' | 'batch_complete' | 'pong'
  task_id?: string
  enterprise_name?: string
  progress?: number
  stage?: string
  step?: string
  detail?: string
  elapsed_seconds?: number
  data_sources?: DataSourceStatus[]
  token_usage?: TokenUsage
  status?: string
  confidence?: number
  tag_summary?: string[]
  fact_count?: number
  token_total?: number
  error?: string
  batch_progress?: { completed: number; total: number }
  results?: EnterpriseResultSummary[]
}

export interface EnterpriseResultSummary {
  enterprise_name: string
  status: string
  confidence: number
  elapsed_seconds?: number
  token_total?: number
  tag_summary?: string[]
  fact_count?: number
}

export interface TaskInfo {
  task_id: string
  enterprise_count: number
  status: string
  completed_count: number
  failed_count: number
  created_at: string
}
