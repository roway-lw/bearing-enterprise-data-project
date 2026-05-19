/** Axios 实例和 API 封装 */
import axios from 'axios'

const client = axios.create({
  baseURL: '',
  timeout: 300000, // 5分钟超时（流水线执行较久）
})

// 请求拦截
client.interceptors.request.use((config) => {
  return config
})

// 响应拦截
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

export default client
