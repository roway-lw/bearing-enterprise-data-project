/** 企业查询 API */
import client from './client'
import type { EnterpriseListResponse, FactResponse } from '@/types/enterprise'

export function getEnterprises(params: {
  keyword?: string
  sort_by?: string
  sort_order?: string
  page?: number
  page_size?: number
}): Promise<EnterpriseListResponse> {
  return client.get('/api/enterprises', { params })
}

export function getEnterpriseDetail(name: string, batchNo?: string): Promise<any> {
  const params: any = {}
  if (batchNo) params.batch_no = batchNo
  return client.get(`/api/enterprises/${encodeURIComponent(name)}`, { params })
}

export function getEnterpriseFacts(
  name: string,
  params: {
    batch_no?: string
    record_type?: string
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
  } = {}
): Promise<FactResponse> {
  return client.get(`/api/enterprises/${encodeURIComponent(name)}/facts`, { params })
}

export function getEnterpriseBatches(name: string): Promise<any[]> {
  return client.get(`/api/enterprises/batches/${encodeURIComponent(name)}`)
}
