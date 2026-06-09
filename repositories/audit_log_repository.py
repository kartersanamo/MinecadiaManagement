from __future__ import annotations

import json
import time
from typing import Any

from core.database import execute
from core.loggers import log_tasks


ENSURE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_logs (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  event_id      CHAR(36) NOT NULL,
  event_type    VARCHAR(64) NOT NULL,
  category      VARCHAR(32) NOT NULL,
  severity      ENUM('info','warn','critical') NOT NULL DEFAULT 'info',
  guild_id      BIGINT UNSIGNED NOT NULL,
  actor_id      BIGINT UNSIGNED NULL,
  target_id     BIGINT UNSIGNED NULL,
  channel_id    BIGINT UNSIGNED NULL,
  source_bot    VARCHAR(32) NOT NULL DEFAULT 'Management',
  title         VARCHAR(256) NOT NULL,
  summary       TEXT NULL,
  payload_json  JSON NULL,
  created_at    INT UNSIGNED NOT NULL,
  UNIQUE KEY uq_audit_event_id (event_id),
  KEY idx_audit_created (created_at),
  KEY idx_audit_actor (actor_id, created_at),
  KEY idx_audit_target (target_id, created_at),
  KEY idx_audit_channel (channel_id, created_at),
  KEY idx_audit_type (event_type, created_at),
  KEY idx_audit_source (source_bot, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


class AuditLogRepository:
    _table_ready = False

    @classmethod
    async def ensure_table(cls) -> None:
        if cls._table_ready:
            return
        await execute(ENSURE_TABLE_SQL)
        cls._table_ready = True

    @classmethod
    async def insert(
        cls,
        *,
        event_id: str,
        event_type: str,
        category: str,
        severity: str,
        guild_id: int,
        actor_id: int | None,
        target_id: int | None,
        channel_id: int | None,
        source_bot: str,
        title: str,
        summary: str | None,
        payload_json: dict[str, Any] | None,
    ) -> None:
        await cls.ensure_table()
        await execute(
            """
            INSERT INTO audit_logs
              (event_id, event_type, category, severity, guild_id, actor_id, target_id,
               channel_id, source_bot, title, summary, payload_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_id,
                event_type[:64],
                category[:32],
                severity,
                guild_id,
                actor_id,
                target_id,
                channel_id,
                source_bot[:32],
                title[:256],
                summary,
                json.dumps(payload_json) if payload_json else None,
                int(time.time()),
            ),
        )

    @classmethod
    async def search(
        cls,
        *,
        guild_id: int,
        actor_id: int | None = None,
        target_id: int | None = None,
        channel_id: int | None = None,
        event_type: str | None = None,
        source_bot: str | None = None,
        since: int | None = None,
        until: int | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[dict]:
        await cls.ensure_table()
        clauses = ["guild_id = %s"]
        params: list[Any] = [guild_id]
        if actor_id:
            clauses.append("actor_id = %s")
            params.append(actor_id)
        if target_id:
            clauses.append("target_id = %s")
            params.append(target_id)
        if channel_id:
            clauses.append("channel_id = %s")
            params.append(channel_id)
        if event_type:
            clauses.append("event_type = %s")
            params.append(event_type)
        if source_bot:
            clauses.append("source_bot = %s")
            params.append(source_bot)
        if since:
            clauses.append("created_at >= %s")
            params.append(since)
        if until:
            clauses.append("created_at <= %s")
            params.append(until)
        params.extend([limit, offset])
        where = " AND ".join(clauses)
        return await execute(
            f"""
            SELECT event_id, event_type, category, severity, actor_id, target_id, channel_id,
                   source_bot, title, summary, created_at
            FROM audit_logs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )

    @classmethod
    async def get_by_event_id(cls, event_id: str) -> dict | None:
        await cls.ensure_table()
        rows = await execute(
            """
            SELECT event_id, event_type, category, severity, guild_id, actor_id, target_id,
                   channel_id, source_bot, title, summary, payload_json, created_at
            FROM audit_logs WHERE event_id = %s OR event_id LIKE %s LIMIT 1
            """,
            (event_id, f"{event_id}%"),
        )
        return rows[0] if rows else None

    @classmethod
    async def stats(cls, guild_id: int, since: int) -> list[dict]:
        await cls.ensure_table()
        return await execute(
            """
            SELECT category, event_type, COUNT(*) AS cnt
            FROM audit_logs
            WHERE guild_id = %s AND created_at >= %s
            GROUP BY category, event_type
            ORDER BY cnt DESC
            LIMIT 100
            """,
            (guild_id, since),
        )

    @classmethod
    async def export_rows(cls, guild_id: int, since: int, until: int, limit: int = 5000) -> list[dict]:
        await cls.ensure_table()
        return await execute(
            """
            SELECT event_id, event_type, category, severity, actor_id, target_id, channel_id,
                   source_bot, title, summary, created_at
            FROM audit_logs
            WHERE guild_id = %s AND created_at >= %s AND created_at <= %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (guild_id, since, until, limit),
        )
