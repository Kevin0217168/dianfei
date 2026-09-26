"""采集任务:调用 getThirdData 获取电表读数,计算用电量并入库。"""
from __future__ import annotations

import time
from typing import Optional

import requests

from config import settings
import database as db
import token_manager


class CollectError(Exception):
    """采集失败。"""


def _fetch_meter(token: str) -> dict:
    """调用 charge/feeitem/getThirdData 返回原始 JSON。"""
    url = settings.BASE_URL + "/charge/feeitem/getThirdData"
    headers = {
        "Authorization": "Basic " + settings.CHARGE_BASIC,
        "synjones-auth": "bearer " + token,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36",
        "Origin": settings.BASE_URL,
        "Referer": settings.BASE_URL + "/charge-app/",
    }
    data = {
        "xiaoqu_id": settings.XIAOQU_ID,
        "loudong_id": settings.LOUDONG_ID,
        "louceng_id": settings.LOUCENG_ID,
        "room_id": settings.ROOM_ID,
        "type": settings.TYPE,
        "level": settings.LEVEL,
        "feeitemid": settings.FEEITEM_ID,
    }
    resp = requests.post(url, data=data, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _parse_meter(raw: dict) -> dict:
    """从原始 JSON 中解析关键读数。"""
    mp = raw.get("map") or {}
    data = mp.get("data") or {}
    try:
        all_amp = float(data.get("allAmp", 0))
        used_amp = float(data.get("usedAmp", 0))
        surplus = float(mp.get("surplusCharge", 0))
    except (TypeError, ValueError) as exc:
        raise CollectError(f"读数解析失败: {exc}") from exc
    return {"all_amp": all_amp, "used_amp": used_amp, "surplus": surplus}


def collect_once(now: Optional[float] = None) -> dict:
    """执行一次采集。返回本次采集结果摘要。"""
    now = now if now is not None else time.time()
    ts = int(now)

    try:
        token_state = token_manager.get_valid_token(now)

        raw = _fetch_meter(token_state.access_token)
        if raw.get("code") != 200:
            raise CollectError(f"接口返回异常: {raw}")

        meter = _parse_meter(raw)
        db.insert_snapshot(ts, meter["all_amp"], meter["used_amp"], meter["surplus"], raw)

        prev = db.latest_snapshot_prev(ts)
        result = {
            "ts": ts,
            "surplus": meter["surplus"],
            "used_amp": meter["used_amp"],
            "usage_kwh": None,
            "cost": None,
            "anomaly": False,
        }

        if prev is not None:
            usage_kwh = round(meter["used_amp"] - prev["used_amp"], 3)
            anomaly = usage_kwh < 0 or usage_kwh > settings.USAGE_ANOMALY_KWH
            if usage_kwh < 0:
                # 读数回退(可能是换表/对时),不写入负数用电
                usage_kwh = 0.0
            cost = round(usage_kwh * settings.PRICE_PER_KWH, 3)
            db.insert_usage(ts, usage_kwh, cost)
            result["usage_kwh"] = usage_kwh
            result["cost"] = cost
            result["anomaly"] = anomaly

        db.log_collect(
            ts,
            "ok",
            "采集成功",
            surplus=result["surplus"],
            used_amp=result["used_amp"],
            usage_kwh=result["usage_kwh"],
            cost=result["cost"],
        )
        return result

    except Exception as exc:  # noqa: BLE001
        db.log_collect(ts, "error", str(exc))
        raise CollectError(str(exc)) from exc
