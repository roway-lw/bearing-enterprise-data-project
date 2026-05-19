<template>
  <div style="max-width: 720px; margin: 0 auto; padding: 24px">
    <a-card title="大模型配置" :bordered="false">
      <template #extra>
        <a-tag :color="form.enabled ? 'green' : 'default'">
          {{ form.enabled ? '已启用' : '未启用' }}
        </a-tag>
      </template>

      <a-form :model="form" layout="vertical" @finish="onSave">
        <a-form-item label="启用大模型增强">
          <a-switch v-model:checked="form.enabled" />
          <div style="color: #999; font-size: 12px; margin-top: 4px">
            启用后，清洗和打标阶段会使用大模型补充正则未能提取的字段和标签
          </div>
        </a-form-item>

        <a-form-item label="API Base URL" required>
          <a-input
            v-model:value="form.base_url"
            placeholder="例如: https://api.openai.com/v1"
          />
        </a-form-item>

        <a-form-item label="API Key" required>
          <a-input-password
            v-model:value="form.api_key"
            placeholder="sk-..."
          />
        </a-form-item>

        <a-form-item label="模型名称" required>
          <a-input
            v-model:value="form.model"
            placeholder="例如: gpt-4o-mini"
          />
        </a-form-item>

        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="saving">
              保存配置
            </a-button>
            <a-button :loading="testing" @click="onTest">
              测试连接
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <!-- 测试结果 -->
      <a-alert
        v-if="testResult"
        :type="testResult.ok ? 'success' : 'error'"
        :message="testResult.ok ? '连接成功' : '连接失败'"
        :description="testResult.ok ? testResult.reply : testResult.error"
        show-icon
        style="margin-top: 16px"
      />

      <!-- 保存成功提示 -->
      <a-alert
        v-if="saveMsg"
        type="success"
        message="配置已保存"
        show-icon
        closable
        style="margin-top: 16px"
        @close="saveMsg = false"
      />
    </a-card>

    <!-- 使用说明 -->
    <a-card title="使用说明" :bordered="false" style="margin-top: 16px" size="small">
      <a-typography-paragraph>
        <ul style="margin: 0; padding-left: 20px">
          <li>大模型集成采用<strong>可插拔式</strong>设计，关闭后不影响纯规则流程</li>
          <li><strong>清洗阶段</strong>：当正则未能提取注册资本、法人、地址等关键字段时，自动调用大模型补充</li>
          <li><strong>打标阶段</strong>：当规则方法生成"未明确"标签时，自动调用大模型分析并补充</li>
          <li>支持任何 OpenAI 兼容 API（OpenAI / Kimi / DeepSeek / 通义千问等）</li>
          <li>配置保存在项目根目录的 <code>llm_config.json</code> 文件中</li>
        </ul>
      </a-typography-paragraph>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getLlmConfig, updateLlmConfig, testLlmConnection } from '@/api/llm'

const form = reactive({
  enabled: false,
  base_url: '',
  api_key: '',
  model: '',
})

const saving = ref(false)
const testing = ref(false)
const saveMsg = ref(false)
const testResult = ref<{ ok: boolean; reply?: string; error?: string } | null>(null)

onMounted(async () => {
  try {
    const cfg = await getLlmConfig()
    form.enabled = cfg.enabled
    form.base_url = cfg.base_url
    form.api_key = cfg.api_key
    form.model = cfg.model
  } catch (e) {
    console.error('加载配置失败', e)
  }
})

async function onSave() {
  saving.value = true
  saveMsg.value = false
  try {
    await updateLlmConfig({
      enabled: form.enabled,
      base_url: form.base_url,
      api_key: form.api_key,
      model: form.model,
    })
    saveMsg.value = true
    // 刷新配置（脱敏后的 api_key）
    const cfg = await getLlmConfig()
    form.api_key = cfg.api_key
  } catch (e) {
    console.error('保存失败', e)
  } finally {
    saving.value = false
  }
}

async function onTest() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testLlmConnection({
      base_url: form.base_url,
      api_key: form.api_key,
      model: form.model,
    })
  } catch (e: any) {
    testResult.value = { ok: false, error: e.message || '测试失败' }
  } finally {
    testing.value = false
  }
}
</script>
