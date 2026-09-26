"""SQLite 数据库访问层。

表结构:
  meter_snapshots - 每次采集的原始读数快照(审计 + 容错)
  usage_records    - 用电量明细(由相邻快照的 used_amp 差值得到)
  token_store      - 当前有效的 access/refresh token
  collect_log      - 采集日志
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from config import settings

_lock = threading.RLock()


def _ensure_dir() -> None:
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(settings.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    with _lock, get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meter_snapshots (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         INTEGER NOT NULL,
                all_amp    REAL NOT NULL,
                used_amp   REAL NOT NULL,
                surplus    REAL NOT NULL,
                raw_json   TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(ts)
            );

            CREATE TABLE IF NOT EXISTS usage_records (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        INTEGER NOT NULL,
                usage_kwh REAL NOT NULL,
                cost      REAL NOT NULL,
                UNIQUE(ts)
            );

            CREATE TABLE IF NOT EXISTS token_store (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                access_token  TEXT NOT NULL,
                refresh_token TEXT,
                expires_at    INTEGER NOT NULL,
                updated_at    TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS collect_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         INTEGER NOT NULL,
                status     TEXT NOT NULL,
                message    TEXT,
                surplus    REAL,
                used_amp   REAL,
                usage_kwh  REAL,
                cost       REAL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            """
        )

        # 兼容旧库:collect_log 若缺少电量详情列则补齐
        _cols = {r[1] for r in conn.execute("PRAGMA table_info(collect_log)")}
        for _name, _decl in (("surplus", "REAL"), ("used_amp", "REAL"),
                             ("usage_kwh", "REAL"), ("cost", "REAL")):
            if _name not in _cols:
                conn.execute(f"ALTER TABLE collect_log ADD COLUMN {_name} {_decl}")


# ---------- 快照 ----------

def insert_snapshot(ts: int, all_amp: float, used_amp: float, surplus: float, raw: dict) -> bool:
    with _lock, get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO meter_snapshots (ts, all_amp, used_amp, surplus, raw_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts, all_amp, used_amp, surplus, json.dumps(raw, ensure_ascii=False)),
        )
        return cur.rowcount > 0


def latest_snapshot() -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM meter_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()


def get_snapshot(ts: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM meter_snapshots WHERE ts = ?", (ts,)
        ).fetchone()


def latest_snapshot_prev(ts: int) -> Optional[sqlite3.Row]:
    """返回严格早于 ts 的最新一条快照(用于计算差值)。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM meter_snapshots WHERE ts < ? ORDER BY ts DESC LIMIT 1",
            (ts,),
        ).fetchone()


# ---------- 用电记录 ----------

def insert_usage(ts: int, usage_kwh: float, cost: float) -> bool:
    with _lock, get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO usage_records (ts, usage_kwh, cost) VALUES (?, ?, ?)",
            (ts, usage_kwh, cost),
        )
        return cur.rowcount > 0


# ---------- token ----------

def save_token(access_token: str, refresh_token: str, expires_at: int) -> None:
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO token_store (access_token, refresh_token, expires_at) VALUES (?, ?, ?)",
            (access_token, refresh_token, expires_at),
        )


def latest_token() -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM token_store ORDER BY id DESC LIMIT 1"
        ).fetchone()


# ---------- 日志 ----------

def log_collect(ts: int, status: str, message: str = "",
                surplus: Optional[float] = None,
                used_amp: Optional[float] = None,
                usage_kwh: Optional[float] = None,
                cost: Optional[float] = None) -> None:
    """记录采集日志,可选附带本次读数的结构化信息。"""
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO collect_log (ts, status, message, surplus, used_amp, usage_kwh, cost) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, status, message, surplus, used_amp, usage_kwh, cost),
        )


def recent_logs(limit: int = 50) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM collect_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


# ---------- 聚合查询 ----------

def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def usage_hourly(day: str) -> list[dict[str, Any]]:
    """某天(YYYY-MM-DD)按小时聚合的用电量与电费。"""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%H', ts, 'unixepoch', 'localtime') AS hour,
                   ROUND(SUM(usage_kwh), 3) AS usage_kwh,
                   ROUND(SUM(cost), 3) AS cost
            FROM usage_records
            WHERE strftime('%Y-%m-%d', ts, 'unixepoch', 'localtime') = ?
            GROUP BY hour ORDER BY hour
            """,
            (day,),
        ).fetchall()
    return _rows_to_dicts(rows)


def usage_daily(month: str) -> list[dict[str, Any]]:
    """某月(YYYY-MM)按天聚合。"""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m-%d', ts, 'unixepoch', 'localtime') AS day,
                   ROUND(SUM(usage_kwh), 3) AS usage_kwh,
                   ROUND(SUM(cost), 3) AS cost
            FROM usage_records
            WHERE strftime('%Y-%m', ts, 'unixepoch', 'localtime') = ?
            GROUP BY day ORDER BY day
            """,
            (month,),
        ).fetchall()
    return _rows_to_dicts(rows)


def usage_monthly() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m', ts, 'unixepoch', 'localtime') AS month,
                   ROUND(SUM(usage_kwh), 3) AS usage_kwh,
                   ROUND(SUM(cost), 3) AS cost
            FROM usage_records
            GROUP BY month ORDER BY month
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def summary_today() -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT ROUND(COALESCE(SUM(usage_kwh), 0), 3) AS usage_kwh,
                   ROUND(COALESCE(SUM(cost), 0), 3) AS cost
            FROM usage_records
            WHERE strftime('%Y-%m-%d', ts, 'unixepoch', 'localtime') = date('now', 'localtime')
            """
        ).fetchone()
    return dict(row)


def summary_month() -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT ROUND(COALESCE(SUM(usage_kwh), 0), 3) AS usage_kwh,
                   ROUND(COALESCE(SUM(cost), 0), 3) AS cost
            FROM usage_records
            WHERE strftime('%Y-%m', ts, 'unixepoch', 'localtime') = strftime('%Y-%m', 'now', 'localtime')
            """
        ).fetchone()
    return dict(row)


def summary_total() -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT ROUND(COALESCE(SUM(usage_kwh), 0), 3) AS usage_kwh,
                   ROUND(COALESCE(SUM(cost), 0), 3) AS cost
            FROM usage_records
            """
        ).fetchone()
    return dict(row)
