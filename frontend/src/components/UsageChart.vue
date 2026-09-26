<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
import http from '../api/index'

const props = defineProps({
  period: { type: String, default: 'daily' },
  price: { type: Number, default: 0.56 },
  refreshTick: { type: Number, default: 0 },
  day: { type: String, default: '' } // 每小时视图查看的历史日期(YYYY-MM-DD), 空则取今天
})

const chartEl = ref(null)
let chart = null

function nowParam() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return { day: `${y}-${m}-${day}`, month: `${y}-${m}` }
}

function buildSeries(data) {
  const labels = data.map((it) => it.hour ?? it.day ?? it.month)
  const kwh = data.map((it) => Number(it.usage_kwh) || 0)
  const cost = data.map((it) => Number(it.cost) || 0)
  return { labels, kwh, cost }
}

async function load() {
  let url = ''
  const day = props.day || nowParam().day
  if (props.period === 'hourly') url = `/usage/hourly?day=${day}`
  else if (props.period === 'daily') url = `/usage/daily?month=${nowParam().month}`
  else url = '/usage/monthly'

  try {
    const res = await http.get(url)
    const { labels, kwh, cost } = buildSeries(res.data || [])
    render(labels, kwh, cost)
  } catch (e) {
    console.error(e)
    render([], [], [])
  }
}

function render(labels, kwh, cost) {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['用电量(度)', '电费(元)'] },
    grid: { left: 50, right: 60, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: labels.length > 20 ? 45 : 0 } },
    yAxis: [
      { type: 'value', name: '度' },
      { type: 'value', name: '元' }
    ],
    series: [
      { name: '用电量(度)', type: 'bar', data: kwh, itemStyle: { color: '#409eff' } },
      { name: '电费(元)', type: 'line', yAxisIndex: 1, data: cost, itemStyle: { color: '#f56c6c' } }
    ]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value)
  load()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})

function resize() { chart?.resize() }

watch(() => props.period, load)
watch(() => props.day, load)
watch(() => props.refreshTick, load)
</script>

<template>
  <div ref="chartEl" style="width: 100%; height: 360px;"></div>
</template>
