# 家属区电费监控

自动采集校园一卡通站点的电表读数,存储到 SQLite,并提供可视化趋势图(每小时/每日/每月用电量 + 电费,电价可配置)。

## 架构

- **后端**: FastAPI + APScheduler,每小时(可配置)定时采集,自动刷新 token
- **数据库**: SQLite(零部署)
- **前端**: Vue3 + Vite + ECharts

## 目录结构

```
dianfei/
├── backend/            # FastAPI 后端
│   ├── app.py          # 入口 + 调度器
│   ├── config.py       # 配置(读 .env)
│   ├── database.py     # SQLite 访问层
│   ├── token_manager.py# token 校验/刷新
│   ├── collector.py    # 采集任务
│   ├── routers/        # API 路由
│   ├── requirements.txt
│   └── .env            # 实际配置(含 token,勿提交)
├── frontend/           # Vue3 前端
├── data/               # SQLite 数据库落盘
└── scripts/            # 启动脚本
```

## 快速开始

### 1. 配置

```bash
cd backend
cp .env.example .env
# 编辑 .env,填入 BASE_URL、凭据与缴费项参数(见下表)
```

关键配置项(标 ✅ 的为必填,缺失会导致启动失败):

| 变量 | 说明 | 必填 | 默认 |
|---|---|---|---|
| `BASE_URL` | 一卡通站点地址 | ✅ | 无 |
| `OAUTH_BASIC` | oauth/token 的 Basic 凭据,base64(`client_id:client_secret`) | ✅ | 无 |
| `CHARGE_BASIC` | charge 接口的 Basic 凭据,格式同上 | ✅ | 无 |
| `FEEITEM_ID` / `XIAOQU_ID` / `LOUDONG_ID` / `LOUCENG_ID` / `ROOM_ID` | 缴费项定位参数,格式 `<id>&<名称>` | ✅ | 无 |
| `ACCESS_TOKEN` | 登录后抓包得到的 bearer token | ❌ | 空 |
| `REFRESH_TOKEN` | 刷新 token | ❌ | 空 |
| `PRICE_PER_KWH` | 电价(元/度) | ❌ | 0.56 |
| `COLLECT_INTERVAL_MINUTES` | 采集间隔(分钟) | ❌ | 60 |

### 2. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

前端通过 Vite 代理把 `/api` 转发到后端 8000 端口。

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/auth/status` | token 状态 |
| POST | `/api/auth/token` | 手动导入 token |
| GET | `/api/auth/logs` | 采集日志 |
| GET | `/api/electricity/current` | 当前读数 |
| GET | `/api/usage/hourly?day=YYYY-MM-DD` | 每小时用电 |
| GET | `/api/usage/daily?month=YYYY-MM` | 每日用电 |
| GET | `/api/usage/monthly` | 每月用电 |
| GET | `/api/summary` | 汇总卡片数据 |
| POST | `/api/collect` | 手动触发一次采集 |

## 说明

- 用电量 = 相邻两次采集的 `usedAmp` 差值;电费 = 用电量 × 电价
- token 到期前 3 天会自动用 refresh_token 续期;若 refresh_token 也失效,需在「设置」页手动粘贴新 token
