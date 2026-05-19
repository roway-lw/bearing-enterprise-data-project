/** WebSocket 连接管理 composable */
import { ref, watch, onUnmounted, type Ref } from 'vue'
import type { ProgressMessage } from '@/types/pipeline'
import { usePipelineStore } from '@/stores/pipeline'

export function useWebSocket(taskId: Ref<string | null>) {
  const status = ref<'connecting' | 'connected' | 'disconnected'>('disconnected')
  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null

  function connect() {
    if (!taskId.value) return

    const url = `ws://127.0.0.1:8000/ws/pipeline/${taskId.value}`

    status.value = 'connecting'
    ws = new WebSocket(url)

    ws.onopen = () => {
      status.value = 'connected'
      ws?.send('ping')
    }

    ws.onmessage = (event) => {
      try {
        const msg: ProgressMessage = JSON.parse(event.data)
        const store = usePipelineStore()

        if (msg.type === 'pong') return

        if (msg.type === 'progress') {
          store.updateProgress(msg)
        } else if (msg.type === 'enterprise_complete') {
          store.addResult(msg)
        } else if (msg.type === 'batch_complete') {
          store.setCompleted()
        }
      } catch (e) {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      status.value = 'disconnected'
      const store = usePipelineStore()
      if (store.isRunning && taskId.value) {
        reconnectTimer = window.setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => {
      const store = usePipelineStore()
      if (store.isRunning) {
        store.finishAsFailed('进度连接失败，请确认后端服务是否正在运行')
      }
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
    status.value = 'disconnected'
  }

  // 监听 taskId 变化，自动连接
  watch(taskId, (newId) => {
    disconnect()
    if (newId) connect()
  })

  onUnmounted(disconnect)

  return { status, connect, disconnect }
}
