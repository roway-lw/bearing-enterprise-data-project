/** LLM 大模型配置 API */
import client from './client'

export interface LlmConfig {
  enabled: boolean
  base_url: string
  api_key: string
  model: string
  is_configured: boolean
}

/** 获取 LLM 配置 */
export function getLlmConfig() {
  return client.get<any, LlmConfig>('/api/llm/config')
}

/** 更新 LLM 配置 */
export function updateLlmConfig(data: {
  enabled: boolean
  base_url: string
  api_key: string
  model: string
}) {
  return client.put<any, { ok: boolean; config: LlmConfig }>('/api/llm/config', data)
}

/** 测试 LLM 连接 */
export function testLlmConnection(data: {
  base_url: string
  api_key: string
  model: string
}) {
  return client.post<any, { ok: boolean; reply?: string; error?: string }>('/api/llm/test-connection', data)
}
