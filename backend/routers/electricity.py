"""电量相关路由:当前读数 / 分时统计 / 汇总。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from config import settings
import database as db
import collector

router = APIRouter(prefix="/api", tags=["electricity"])


@router.get("/electricity/current")
def current():
    snap = db.latest_snapshot()
    if snap is None:
        return {"code": 200, "msg": "success", "data": None}
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "ts": snap["ts"],
            "all_amp": snap["all_amp"],
            "used_amp": snap["used_amp"],
            "surplus": snap["surplus"],
        },
    }


@router.get("/usage/hourly")
def hourly(day: str):
    _validate_day(day)
    return {"code": 200, "msg": "success", "data": db.usage_hourly(day)}


@router.get("/usage/daily")
def daily(month: str):
    _validate_month(month)
    return {"code": 200, "msg": "success", "data": db.usage_daily(month)}


@router.get("/usage/monthly")
def monthly():
    return {"code": 200, "msg": "success", "data": db.usage_monthly()}


@router.get("/summary")
def summary():
    today = db.summary_today()
    month = db.summary_month()
    total = db.summary_total()
    snap = db.latest_snapshot()
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "surplus": snap["surplus"] if snap else None,
            "today": today,
            "month": month,
            "total": total,
            "price_per_kwh": settings.PRICE_PER_KWH,
        },
    }


@router.post("/collect")
def collect_now():
    """手动触发一次采集(便于测试/补采)。"""
    try:
        result = collector.collect_once()
    except collector.CollectError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"code": 200, "msg": "success", "data": result}


def _validate_day(day: str) -> None:
    try:
        date.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="day 格式应为 YYYY-MM-DD") from exc


def _validate_month(month: str) -> None:
    try:
        date.fromisoformat(month + "-01")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="month 格式应为 YYYY-MM") from exc
