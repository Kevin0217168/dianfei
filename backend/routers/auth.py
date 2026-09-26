"""鉴权相关路由:token 状态 / 手动导入。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

import database as db
import token_manager
from schemas import TokenImportRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status():
    return {"code": 200, "msg": "success", "data": token_manager.status()}


@router.post("/token")
def import_token(req: TokenImportRequest):
    try:
        state = token_manager.import_token(req.access_token, req.refresh_token)
    except token_manager.TokenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "expires_at": state.expires_at,
            "has_refresh": bool(state.refresh_token),
        },
    }


@router.get("/logs")
def collect_logs(limit: int = 50):
    rows = db.recent_logs(limit)
    return {"code": 200, "msg": "success", "data": [dict(r) for r in rows]}
