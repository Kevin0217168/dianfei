"""全局配置加载。

所有可配置项均通过环境变量 / .env 文件覆盖,提供默认值。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录(backend 的上一级)
BASE_DIR = Path(__file__).resolve().parent.parent
# 优先加载 backend/.env,其次项目根 .env
load_dotenv(BASE_DIR / "backend" / ".env")
load_dotenv(BASE_DIR / ".env")


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _get_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Settings:
    # ---- 站点与认证 ----
    # 以下项均无默认值,必须在 .env / 环境变量中提供(见文件末尾的启动校验)
    BASE_URL: str = _get("BASE_URL", "")
    # oauth/token 使用的 Basic 认证,内容为 base64("<client_id>:<client_secret>")
    OAUTH_BASIC: str = _get("OAUTH_BASIC", "")
    # charge 接口使用的 Basic 认证,格式同上
    CHARGE_BASIC: str = _get("CHARGE_BASIC", "")
    # 可选:登录后抓包得到的 token,也可以先留空,之后在「设置」页手动粘贴
    ACCESS_TOKEN: str = _get("ACCESS_TOKEN", "")
    REFRESH_TOKEN: str = _get("REFRESH_TOKEN", "")

    # ---- 缴费项参数 ----
    # 格式均为 "<id>&<名称>",名称仅供展示,按自己的表填写
    FEEITEM_ID: str = _get("FEEITEM_ID", "")
    XIAOQU_ID: str = _get("XIAOQU_ID", "")
    LOUDONG_ID: str = _get("LOUDONG_ID", "")
    LOUCENG_ID: str = _get("LOUCENG_ID", "")
    ROOM_ID: str = _get("ROOM_ID", "")
    TYPE: str = _get("TYPE", "IEC")
    LEVEL: str = _get("LEVEL", "4")

    # ---- 计价与采集 ----
    # 电价,元/度
    PRICE_PER_KWH: float = _get_float("PRICE_PER_KWH", 0.56)
    # 采集间隔,分钟
    COLLECT_INTERVAL_MINUTES: int = _get_int("COLLECT_INTERVAL_MINUTES", 60)
    # token 提前多久(秒)判定为"需要刷新",默认 3 天
    TOKEN_REFRESH_AHEAD_SECONDS: int = _get_int("TOKEN_REFRESH_AHEAD_SECONDS", 3 * 24 * 3600)
    # 单次用电量异常阈值(度),超过则告警但仍记录
    USAGE_ANOMALY_KWH: float = _get_float("USAGE_ANOMALY_KWH", 200.0)

    # ---- 数据库 ----
    DB_PATH: str = _get("DB_PATH", str(BASE_DIR / "data" / "dianfei.db"))

    # 必填项:缺失时启动直接失败,避免带着空凭据去请求接口而静默 401
    REQUIRED_KEYS = (
        "BASE_URL",
        "OAUTH_BASIC",
        "CHARGE_BASIC",
        "FEEITEM_ID",
        "XIAOQU_ID",
        "LOUDONG_ID",
        "LOUCENG_ID",
        "ROOM_ID",
    )

    def validate(self) -> None:
        """校验必填配置,缺失则抛出带明确提示的异常。"""
        missing = [k for k in self.REQUIRED_KEYS if not getattr(self, k).strip()]
        if missing:
            raise RuntimeError(
                "缺少必要配置: "
                + ", ".join(missing)
                + ";请在 backend/.env 中填写(可参考 backend/.env.example)"
            )


settings = Settings()
settings.validate()
