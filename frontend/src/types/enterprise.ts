/** 企业数据 TypeScript 类型定义 */

export interface EnterpriseListItem {
  id: number
  enterprise_name: string
  batch_no: string
  overall_confidence: number | null
  pipeline_status: string | null
  execute_time: string | null
  total_tokens: number | null
  total_time_seconds: number | null
  main_products: string[] | null
  application_tags: string[] | null
  flat_tags: Record<string, string[]> | null
  product_detail_tags: Record<string, any> | null
  service_detail_tags: Record<string, any> | null
  capability_detail_tags: Record<string, any> | null
  [key: string]: any
}

export interface EnterpriseListResponse {
  enterprises: EnterpriseListItem[]
  total: number
  page: number
  page_size: number
}

export interface FactRecord {
  id: number
  enterprise_name: string
  batch_no: string
  record_id: string
  record_type: string
  counterparty: string | null
  counterparty_short: string | null
  counterparty_industry: string | null
  project_name: string | null
  bid_type: string | null
  bid_role: string | null
  bid_date: string | null
  region: string | null
  amount: string | null
  amount_unit: string | null
  products: string | null
  product_detail: string | null
  rel_type: string | null
  rel_desc: string | null
  evidence_type: string | null
  evidence_text: string | null
  source_platform: string | null
  source_url: string | null
  confidence: number
  is_current: boolean | null
  [key: string]: any
}

export interface FactResponse {
  facts: FactRecord[]
  summary: Record<string, number>
  total: number
  page: number
  page_size: number
}

export interface DbConfig {
  configured: boolean
  host: string
  port: number
  database: string
}
