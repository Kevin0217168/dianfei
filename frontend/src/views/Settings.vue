<script setup>
import { onMounted, ref } from 'vue'
import http from '../api/index'

const status = ref(null)
const logs = ref([])
const access = ref('')
const refresh = ref('')
const msg = ref('')
const loading = ref(false)

async function loadStatus() {
  const res = await http.get('/auth/status')
  status.value = res.data
}

async function loadLogs() {
  const res = await http.get('/auth/logs?limit=50')
  logs.value = res.data || []
}

async function saveToken() {
  if (!access.value.trim()) { msg.value = '请粘贴 access_token'; return }
  loading.value = true
  msg.value = ''
  try {
    await http.post('/auth/token', { access_token: access.value.trim(), refresh_token: refresh.value.trim() })
    msg.value = '导入成功'
    access.value = ''
    refresh.value = ''
    await loadStatus()
  } catch (e) {
    msg.value = e.message
  } finally {
    loading.value = false
  }
}

function fmtExp(ts) {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function fmtNum(v) {
  return v == null ? '--' : Number(v).toFixed(3)
}

onMounted(() => {
  loadStatus()
  loadLogs()
})
</script>

<template>
  <div class="settings">
    <div class="panel">
      <h3>Token 状态</h3>
      <div class="status-row">
        <span class="dot" :class="{ ok: status?.valid, bad: !status?.valid }"></span>
        <span>{{ status?.valid ? '有效' : '无效' }}</span>
        <span class="muted">剩余 {{ status?.days_left ?? '--' }} 天</span>
        <span class="muted">过期时间 {{ fmtExp(status?.expires_at) }}</span>
        <span class="muted">refresh_token: {{ status?.has_refresh ? '已配置' : '未配置' }}</span>
      </div>
      <p class="hint">token 到期后会自动用 refresh_token 续期;若续期失败,请在下方手动粘贴新的 token。</p>
    </div>

    <div class="panel">
      <h3>手动导入 Token</h3>
      <textarea v-model="access" class="input" rows="3" placeholder="粘贴 access_token (JWT)"></textarea>
      <textarea v-model="refresh" class="input" rows="2" placeholder="粘贴 refresh_token (可选)"></textarea>
      <button class="btn" :disabled="loading" @click="saveToken">保存</button>
      <p v-if="msg" class="msg">{{ msg }}</p>
    </div>

    <div class="panel">
      <h3>采集日志</h3>
      <table class="log-table">
        <thead><tr><th>时间</th><th>状态</th><th>本次用电(度)</th><th>电费(元)</th><th>剩余(度)</th><th>表读数</th><th>说明</th></tr></thead>
        <tbody>
          <tr v-for="(l, i) in logs" :key="i">
            <td>{{ new Date(l.ts * 1000).toLocaleString('zh-CN') }}</td>
            <td><span :class="l.status">{{ l.status === 'ok' ? '成功' : '失败' }}</span></td>
            <td>{{ fmtNum(l.usage_kwh) }}</td>
            <td>{{ fmtNum(l.cost) }}</td>
            <td>{{ fmtNum(l.surplus) }}</td>
            <td class="muted">{{ fmtNum(l.used_amp) }}</td>
            <td class="muted">{{ l.message }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.settings { display: flex; flex-direction: column; gap: 16px; }
.panel { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.panel h3 { font-size: 16px; margin-bottom: 14px; }
.status-row { display: flex; align-items: center; gap: 14px; font-size: 14px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.ok { background: #67c23a; }
.dot.bad { background: #f56c6c; }
.muted { color: #909399; }
.hint { margin-top: 12px; font-size: 13px; color: #909399; }
.input { width: 100%; border: 1px solid #dcdfe6; border-radius: 6px; padding: 10px; font-size: 13px; margin-bottom: 10px; resize: vertical; font-family: monospace; }
.btn { background: #409eff; color: #fff; border: none; padding: 9px 24px; border-radius: 6px; cursor: pointer; }
.btn:disabled { opacity: .6; }
.msg { margin-top: 10px; font-size: 13px; color: #e6a23c; }
.log-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.log-table th, .log-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #ebeef5; }
.log-table th { color: #909399; font-weight: 500; }
.log-table span.ok { color: #67c23a; }
.log-table span.error { color: #f56c6c; }
</style>
