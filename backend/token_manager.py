"""Token 管理:校验 access_token 过期时间,必要时用 refresh_token 续期。

access_token 是 JWT,payload 里有 exp;refresh_token 是非 JWT 的随机串,
只能通过 oauth/token 的 refresh_token 授权方式换取新 token。
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Optional

import requests

from config import settings
import database as db


class TokenError(Exception):
    """token 无法刷新或无效。"""


def decode_jwt_exp(token: str) -> Optional[int]:
    """解析 JWT 的 exp(秒)。非 JWT 返回 None。"""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return int(data.get("exp", 0))
    except Exception:
        return None


def _oauth_token(params: dict) -> dict:
    """调用 /berserker-auth/oauth/token,返回 JSON。"""
    url = settings.BASE_URL + "/berserker-auth/oauth/token"
    headers = {
        "Authorization": "Basic " + settings.OAUTH_BASIC,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36",
    }
    resp = requests.post(url, data=params, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()


@dataclass
class TokenState:
    access_token: str
    refresh_token: str
    expires_at: int


def _refresh(refresh_token: str) -> TokenState:
    data = _oauth_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "all",
        }
    )
    if "access_token" not in data:
        raise TokenError(f"刷新失败: {data}")
    access = data["access_token"]
    expires_at = decode_jwt_exp(access) or (int(time.time()) + 3600)
    new_refresh = data.get("refresh_token") or refresh_token
    state = TokenState(access_token=access, refresh_token=new_refresh, expires_at=expires_at)
    db.save_token(access, new_refresh, expires_at)
    return state


def get_valid_token(now: Optional[float] = None) -> TokenState:
    """返回一个当前有效的 token,必要时自动刷新。"""
    now = now if now is not None else time.time()
    ahead = settings.TOKEN_REFRESH_AHEAD_SECONDS

    row = db.latest_token()
    # 数据库中可能已有比 .env 更新的 token(导入/刷新产生),过期时间更晚时优先用 DB
    db_exp = row["expires_at"] if row is not None else 0

    env_state: Optional[TokenState] = None
    if settings.ACCESS_TOKEN:
        exp = decode_jwt_exp(settings.ACCESS_TOKEN)
        if exp:
            env_state = TokenState(
                access_token=settings.ACCESS_TOKEN,
                refresh_token=settings.REFRESH_TOKEN,
                expires_at=exp,
            )

    # 1) .env 的 access token 仍有效且在安全期内,且不比 DB 中的旧 → 直接用
    #    (兼容仅配置 ACCESS_TOKEN、未配 REFRESH_TOKEN 的情况)
    if env_state and env_state.expires_at > now + ahead and env_state.expires_at >= db_exp:
        return env_state

    # 2) 数据库 token 仍在安全期内 → 直接用
    if row is not None and db_exp > now + ahead:
        return TokenState(
            access_token=row["access_token"],
            refresh_token=row["refresh_token"] or settings.REFRESH_TOKEN,
            expires_at=db_exp,
        )

    # 3) 已过期/临近过期 → 尝试用 refresh_token 刷新(DB 或 .env)
    refresh_token = (row["refresh_token"] if row is not None else "") or settings.REFRESH_TOKEN
    if refresh_token:
        return _refresh(refresh_token)

    # 4) 无 refresh_token 可用,但 .env 的 access token 尚未过期 → 先用着
    if env_state and env_state.expires_at > now:
        return env_state

    raise TokenError("无可用 token,请在设置页粘贴新的 access/refresh token")


def status(now: Optional[float] = None) -> dict:
    """返回 token 状态信息,供前端展示。"""
    now = now if now is not None else time.time()
    row = db.latest_token()
    token = row["access_token"] if row else settings.ACCESS_TOKEN
    refresh = (row["refresh_token"] if row else settings.REFRESH_TOKEN) or settings.REFRESH_TOKEN

    if not token:
        return {"valid": False, "expires_at": None, "days_left": 0, "has_refresh": bool(refresh)}

    exp = decode_jwt_exp(token)
    if not exp:
        exp = row["expires_at"] if row else None

    days_left = (exp - now) / 86400 if exp else 0
    return {
        "valid": bool(exp and exp > now),
        "expires_at": exp,
        "days_left": round(days_left, 2),
        "has_refresh": bool(refresh),
    }


def import_token(access_token: str, refresh_token: str) -> TokenState:
    """手动导入新 token(Settings 页粘贴)。"""
    exp = decode_jwt_exp(access_token)
    if not exp:
        raise TokenError("access_token 不是有效的 JWT,请检查后重试")
    if exp <= time.time():
        raise TokenError("该 access_token 已过期")
    state = TokenState(access_token=access_token, refresh_token=refresh_token, expires_at=exp)
    db.save_token(access_token, refresh_token, exp)
    return state
