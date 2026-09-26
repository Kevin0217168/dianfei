<script setup>
import { ref } from 'vue'
import Dashboard from './views/Dashboard.vue'
import Settings from './views/Settings.vue'

const tab = ref('dashboard')
</script>

<template>
  <div class="app">
    <header class="navbar">
      <div class="brand">⚡ 家属区电费监控</div>
      <nav class="tabs">
        <button :class="{ active: tab === 'dashboard' }" @click="tab = 'dashboard'">仪表盘</button>
        <button :class="{ active: tab === 'settings' }" @click="tab = 'settings'">设置</button>
      </nav>
    </header>
    <main class="content">
      <Dashboard v-if="tab === 'dashboard'" />
      <Settings v-else />
    </main>
  </div>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #1f2d3d; }
.app { min-height: 100vh; }
.navbar { display: flex; align-items: center; justify-content: space-between; padding: 0 24px; height: 56px; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.brand { font-size: 18px; font-weight: 700; }
.tabs button { border: none; background: transparent; padding: 8px 16px; margin-left: 8px; cursor: pointer; font-size: 14px; color: #606266; border-radius: 6px; }
.tabs button.active { background: #409eff; color: #fff; }
.content { padding: 24px; max-width: 1200px; margin: 0 auto; }
</style>
