"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TokenImportRequest(BaseModel):
    access_token: str
    refresh_token: Optional[str] = ""


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Optional[dict | list] = None
