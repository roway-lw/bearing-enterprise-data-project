<template>
  <div class="db-import">
    <a-form layout="inline" :model="form" style="margin-bottom: 12px">
      <a-form-item label="主机">
        <a-input v-model:value="form.host" style="width: 140px" :disabled="disabled" />
      </a-form-item>
      <a-form-item label="端口">
        <a-input-number v-model:value="form.port" style="width: 80px" :disabled="disabled" />
      </a-form-item>
      <a-form-item label="用户">
        <a-input v-model:value="form.user" style="width: 100px" :disabled="disabled" />
      </a-form-item>
      <a-form-item label="密码">
        <a-input-password v-model:value="form.password" style="width: 120px" :disabled="disabled" />
      </a-form-item>
      <a-form-item label="数据库">
        <a-input v-model:value="form.database" style="width: 140px" :disabled="disabled" />
      </a-form-item>
    </a-form>

    <!-- 连接测试 -->
    <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px">
      <a-button @click="onTestConn" :loading="testing" :disabled="disabled">测试连接</a-button>
      <span v-if="connResult" style="margin-left: 0">
        <a-tag :color="connResult.connected ? 'green' : 'red'">{{ connResult.message }}</a-tag>
      </span>
    </div>

    <!-- 选择表和字段 -->
    <div v-if="connResult?.connected" style="display: flex; gap: 12px; margin-bottom: 12px">
      <a-select v-model:value="selectedTable" style="width: 200px" placeholder="选择表" @change="onTableChange">
        <a-select-option v-for="t in connResult.tables" :key="t" :value="t">{{ t }}</a-select-option>
      </a-select>
      <a-select v-model:value="selectedColumn" style="width: 200px" placeholder="选择企业名称字段">
        <a-select-option v-for="c in columns" :key="c" :value="c">{{ c }}</a-select-option>
      </a-select>
      <a-button type="primary" @click="onLoadNames" :disabled="!selectedTable || !selectedColumn">
        加载企业名称
      </a-button>
    </div>

    <!-- 预览 -->
    <div v-if="previewNames.length > 0">
      <div style="margin-bottom: 6px">
        共 <b>{{ previewNames.length }}</b> 个企业名称
        <a-button type="link" size="small" @click="$emit('selected', previewNames)">填入输入框</a-button>
      </div>
      <a-tag v-for="n in previewNames.slice(0, 20)" :key="n">{{ n }}</a-tag>
      <span v-if="previewNames.length > 20" style="color: #999">...等 {{ previewNames.length }} 个</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { testConnection, queryNames, listColumns } from '@/api/db'

defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ selected: [names: string[]] }>()

const STORAGE_KEY = 'bearing_db_config'

const form = ref({ host: 'localhost', port: 3306, user: 'root', password: '', database: 'bearing_enterprise' })
const testing = ref(false)
const connResult = ref<{ connected: boolean; tables: string[]; database?: string; message: string } | null>(null)
const selectedTable = ref('')
const selectedColumn = ref('')
const columns = ref<string[]>([])
const previewNames = ref<string[]>([])

function saveConfig() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(form.value))
  } catch { /* ignore */ }
}

function loadConfig() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      Object.assign(form.value, parsed)
    }
  } catch { /* ignore */ }
}

async function onTestConn() {
  testing.value = true
  try {
    const result = await testConnection(form.value)
    connResult.value = result
    if (result.connected) {
      form.value.database = result.database || form.value.database
      saveConfig()
      message.success(result.message)
    } else {
      message.error(result.message)
    }
  } finally {
    testing.value = false
  }
}

async function onTableChange(tableName: string) {
  selectedColumn.value = ''
  columns.value = []
  previewNames.value = []
  try {
    const res = await listColumns({ table_name: tableName, name_column: '*' })
    columns.value = res.columns
    const preferred = ['enterprise_name', 'company_name', 'name', '企业名称', '公司名称']
    selectedColumn.value = preferred.find(c => res.columns.includes(c)) || res.columns[0] || ''
  } catch (e: any) {
    message.error(e.message)
  }
}

async function onLoadNames() {
  try {
    const res = await queryNames({
      table_name: selectedTable.value,
      name_column: selectedColumn.value,
    })
    previewNames.value = res.names
    message.success(`加载了 ${res.count} 个企业名称`)
  } catch (e: any) {
    message.error(e.message)
  }
}

onMounted(loadConfig)
</script>
