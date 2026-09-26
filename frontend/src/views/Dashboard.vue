<script setup>
import { onMounted, ref } from 'vue'
import http from '../api/index'
import SummaryCards from '../components/SummaryCards.vue'
import UsageChart from '../components/UsageChart.vue'
import UsageTable from '../components/UsageTable.vue'

const summary = ref(null)
const price = ref(0.56)
const period = ref('daily') // hourly | daily | monthly
const collecting = ref(false)
const refreshTick = ref(0)
const noticeText = ref('')
const noticeOk = ref(true)

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const day = ref(todayStr()) // 每小时视图查看的历史日期

function onDayChange(e) {
  day.value = e.target.value || todayStr()
}

async function loadSummary() {
  const res = await http.get('/summary')
  summary.value = res.data
  price.value = res.data.price_per_kwh
}

async function refreshNow() {
  if (collecting.value) return
  collecting.value = true
  noticeText.value = ''
  try {
    await http.post('/collect')
    await loadSummary()
    refreshTick.value++ // 通知图表/表格重新拉取
    noticeText.value = '✅ 采集成功, 数据已更新'
    noticeOk.value = true
  } catch (e) {
    noticeText.value = '❌ 采集失败: ' + e.message
    noticeOk.value = false
  } finally {
    collecting.value = false
    window.setTimeout(() => { noticeText.value = '' }, noticeOk.value ? 5000 : 8000)
  }
}

onMounted(() => {
  loadSummary().catch((e) => console.error(e))
})
</script>

<template>
  <div>
    <div class="toolbar">
      <button class="refresh-btn" :disabled="collecting" @click="refreshNow">
        <span v-if="collecting">⏳ 采集中…</span>
        <span v-else>⚡ 立即刷新</span>
      </button>
      <span v-if="noticeText" class="notice" :class="{ err: !noticeOk }">{{ noticeText }}</span>
    </div>

    <SummaryCards :summary="summary" />

    <div class="panel">
      <div class="panel-head">
        <h3>用电趋势</h3>
        <div class="seg">
          <button :class="{ active: period === 'hourly' }" @click="period = 'hourly'">每小时</button>
          <button :class="{ active: period === 'daily' }" @click="period = 'daily'">每日</button>
          <button :class="{ active: period === 'monthly' }" @click="period = 'monthly'">每月</button>
        </div>
      </div>
      <div v-if="period === 'hourly'" class="day-picker">
        <label for="history-day">查看日期</label>
        <input id="history-day" type="date" :value="day" :max="todayStr()" @change="onDayChange" />
        <button class="today-btn" @click="day = todayStr()">今天</button>
      </div>
      <UsageChart :period="period" :price="price" :refresh-tick="refreshTick" :day="day" />
      <UsageTable :period="period" :price="price" :refresh-tick="refreshTick" :day="day" />
    </div>
  </div>
</template>

<style scoped>
.panel { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.panel-head h3 { font-size: 16px; }
.seg { display: inline-flex; background: #f0f2f5; border-radius: 8px; padding: 3px; }
.seg button { border: none; background: transparent; padding: 6px 14px; cursor: pointer; font-size: 13px; color: #606266; border-radius: 6px; }
.seg button.active { background: #fff; color: #409eff; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.day-picker { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 13px; color: #606266; }
.day-picker input[type="date"] { padding: 5px 8px; border: 1px solid #dcdfe6; border-radius: 6px; font-size: 13px; color: #303133; background: #fff; }
.today-btn { border: none; background: #f0f2f5; color: #606266; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.today-btn:hover { background: #e4e7ed; }
.toolbar { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.refresh-btn { background: linear-gradient(135deg, #67c23a, #529b2e); color: #fff; border: none; padding: 9px 22px; border-radius: 8px; font-size: 14px; cursor: pointer; box-shadow: 0 2px 6px rgba(103,194,58,.3); }
.refresh-btn:disabled { opacity: .6; cursor: not-allowed; }
.notice { font-size: 13px; color: #67c23a; }
.notice.err { color: #f56c6c; }
</style>
