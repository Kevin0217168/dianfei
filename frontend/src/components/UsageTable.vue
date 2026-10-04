<script setup>
import { onMounted, ref, watch } from 'vue'
import http from '../api/index'

const props = defineProps({
  period: { type: String, default: 'daily' },
  price: { type: Number, default: 0.56 },
  refreshTick: { type: Number, default: 0 },
  day: { type: String, default: '' }, // 每小时视图查看的历史日期(YYYY-MM-DD), 空则取今天
  month: { type: String, default: '' }
})

const rows = ref([])
const loading = ref(false)

const periodLabel = { hourly: '小时', daily: '日期', monthly: '月份' }

function nowParam() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return { day: `${y}-${m}-${day}`, month: `${y}-${m}` }
}

async function load() {
  let url = ''
  const day = props.day || nowParam().day
  if (props.period === 'hourly') url = `/usage/hourly?day=${day}`
  else if (props.period === 'daily') url = `/usage/daily?month=${props.month || nowParam().month}`
  else url = '/usage/monthly'

  loading.value = true
  try {
    const res = await http.get(url)
    rows.value = res.data || []
  } catch (e) {
    console.error(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function keyLabel(row) {
  return row.hour ? `${row.hour}:00` : (row.day ?? row.month)
}

onMounted(load)
watch(() => props.period, load)
watch(() => props.day, load)
watch(() => props.month, load)
watch(() => props.refreshTick, load)
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>{{ periodLabel[period] }}</th>
          <th>用电量(度)</th>
          <th>电费(元)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td colspan="3" class="empty">加载中...</td></tr>
        <tr v-else-if="!rows.length"><td colspan="3" class="empty">暂无数据</td></tr>
        <tr v-for="(row, i) in rows" :key="i">
          <td>{{ keyLabel(row) }}</td>
          <td>{{ Number(row.usage_kwh).toFixed(3) }}</td>
          <td>{{ Number(row.cost).toFixed(3) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { margin-top: 16px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #ebeef5; }
th { color: #909399; font-weight: 500; background: #fafafa; }
td { color: #303133; }
.empty { text-align: center; color: #909399; }
</style>
