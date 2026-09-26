"""FastAPI 应用入口:挂载路由 + 启动 APScheduler 定时采集。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
import database as db
import collector
from routers import auth, electricity

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("dianfei")

scheduler: BackgroundScheduler | None = None


def _scheduled_collect():
    try:
        result = collector.collect_once()
        logger.info("定时采集成功: 剩余 %.2f 度, 本时段用电 %s 度",
                    result["surplus"], result["usage_kwh"])
    except collector.CollectError as exc:
        logger.error("定时采集失败: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    db.init_db()

    # 首次启动立即采集一次(无数据时先打一个基准点)
    try:
        collector.collect_once()
    except collector.CollectError as exc:
        logger.warning("启动首采失败(可能 token 未配置): %s", exc)

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _scheduled_collect,
        "interval",
        minutes=settings.COLLECT_INTERVAL_MINUTES,
        id="collect_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("调度器已启动, 采集间隔 %d 分钟", settings.COLLECT_INTERVAL_MINUTES)

    yield

    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="家属区电费监控", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(electricity.router)


@app.get("/api/health")
def health():
    return {"code": 200, "msg": "ok", "data": {"price_per_kwh": settings.PRICE_PER_KWH}}
