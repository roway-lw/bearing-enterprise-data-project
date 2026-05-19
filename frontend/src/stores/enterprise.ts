/** 企业数据状态管理 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { EnterpriseListItem, FactRecord } from '@/types/enterprise'
import { getEnterprises, getEnterpriseDetail, getEnterpriseFacts } from '@/api/enterprise'

export const useEnterpriseStore = defineStore('enterprise', () => {
  const enterprises = ref<EnterpriseListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const keyword = ref('')
  const sortBy = ref('execute_time')
  const sortOrder = ref('desc')

  // 当前企业详情
  const currentDetail = ref<any>(null)
  const currentFacts = ref<FactRecord[]>([])
  const factSummary = ref<Record<string, number>>({})
  const factTotal = ref(0)
  const factPage = ref(1)
  const factPageSize = ref(50)

  async function fetchList() {
    loading.value = true
    try {
      const res = await getEnterprises({
        keyword: keyword.value || undefined,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        page: page.value,
        page_size: pageSize.value,
      })
      enterprises.value = res.enterprises
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(name: string, batchNo?: string) {
    loading.value = true
    try {
      currentDetail.value = await getEnterpriseDetail(name, batchNo)
    } finally {
      loading.value = false
    }
  }

  async function fetchFacts(name: string, recordType?: string) {
    const res = await getEnterpriseFacts(name, {
      record_type: recordType || undefined,
      sort_by: 'confidence',
      sort_order: 'desc',
      page: factPage.value,
      page_size: factPageSize.value,
    })
    currentFacts.value = res.facts
    factSummary.value = res.summary
    factTotal.value = res.total
  }

  return {
    enterprises, total, page, pageSize, loading, keyword, sortBy, sortOrder,
    currentDetail, currentFacts, factSummary, factTotal, factPage, factPageSize,
    fetchList, fetchDetail, fetchFacts,
  }
})
