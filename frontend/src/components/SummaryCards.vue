<script setup>
defineProps({
  summary: { type: Object, default: null }
})

function fmt(v) {
  return v == null ? '--' : Number(v).toFixed(2)
}
</script>

<template>
  <div class="cards">
    <div class="card primary">
      <div class="label">当前剩余电量</div>
      <div class="value">{{ fmt(summary?.surplus) }}<span class="unit"> 度</span></div>
    </div>
    <div class="card">
      <div class="label">今日用电</div>
      <div class="value">{{ fmt(summary?.today?.usage_kwh) }}<span class="unit"> 度</span></div>
    </div>
    <div class="card">
      <div class="label">今日电费</div>
      <div class="value">{{ fmt(summary?.today?.cost) }}<span class="unit"> 元</span></div>
    </div>
    <div class="card">
      <div class="label">本月电费</div>
      <div class="value">{{ fmt(summary?.month?.cost) }}<span class="unit"> 元</span></div>
    </div>
  </div>
</template>

<style scoped>
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 16px; }
.card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.card.primary { background: linear-gradient(135deg, #409eff, #3a8ee6); color: #fff; }
.card.primary .label { color: rgba(255,255,255,.85); }
.label { font-size: 13px; color: #909399; margin-bottom: 10px; }
.value { font-size: 28px; font-weight: 700; }
.unit { font-size: 14px; font-weight: 400; opacity: .7; }
</style>
