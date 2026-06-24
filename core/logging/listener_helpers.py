from __future__ import annotations

import datetime

import discord


def ordinal_suffix(n: int) -> str:
    pos = int(str(n)[-1])
    if 10 <= n % 100 <= 20:
        return "th"
    return "st" if pos == 1 else "nd" if pos == 2 else "rd" if pos == 3 else "th"


def timeout_expires_line(member: discord.Member, entry: discord.AuditLogEntry | None) -> str:
    until = member.timed_out_until
    if until is None and entry and entry.changes:
        until = getattr(entry.changes.after, "timed_out_until", None)
    if until is None:
        return "Unknown"
    if until.tzinfo is None:
        until = until.replace(tzinfo=datetime.timezone.utc)
    return f"<t:{int(until.timestamp())}:R>"


def timeout_staff_line(entry: discord.AuditLogEntry | None) -> str:
    if entry and entry.user:
        return f"{entry.user.mention} (`{entry.user.id}`)"
    return "Unknown"


async def permission_differences(
    member: discord.Member,
    before: discord.Permissions,
    after: discord.Permissions,
    audit_entry: discord.AuditLogEntry | None,
) -> list[str] | None:
    differences: list[str] = []
    for attr_name in dir(before):
        if attr_name.startswith("_") or callable(getattr(before, attr_name)):
            continue
        value1 = getattr(before, attr_name)
        value2 = getattr(after, attr_name)
        if value1 == value2:
            continue
        if attr_name == "value":
            if value1 in (703687441843200, 703687441843201):
                return [
                    "Timeout removed",
                    f"Staff: {timeout_staff_line(audit_entry)}",
                ]
            if value2 in (703687441843200, 703687441843201):
                reason = audit_entry.reason if audit_entry and audit_entry.reason else "None provided"
                return [
                    "Timeout applied",
                    f"Staff: {timeout_staff_line(audit_entry)}",
                    f"Expires: {timeout_expires_line(member, audit_entry)}",
                    f"Reason: {reason}",
                ]
            return None
        differences.append(f"{attr_name}: {value1} → {value2}")
    return differences or None
