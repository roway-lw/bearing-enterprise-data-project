/** 流水线 API */
import client from './client'
import type { PipelineRunRequest, PipelineRunResponse, TaskInfo } from '@/types/pipeline'

export function runPipeline(data: PipelineRunRequest): Promise<PipelineRunResponse> {
  return client.post('/api/pipeline/run', data)
}

export function getTasks(): Promise<TaskInfo[]> {
  return client.get('/api/pipeline/tasks')
}

export function getTask(taskId: string): Promise<any> {
  return client.get(`/api/pipeline/tasks/${taskId}`)
}

export function cancelTask(taskId: string): Promise<any> {
  return client.post(`/api/pipeline/tasks/${taskId}/cancel`)
}
