from __future__ import annotations

from collections import Counter

import discord
from discord.ext import commands

from core.database import execute
from core.logging.config_helpers import guild_id, ignored_channel_ids, log_flag, recruitment_channel_ids
from core.logging.embed_builder import format_channel, format_user, truncate
from core.logging.events import LogCategory, LogPayload, LogSeverity
from core.logging.listener_helpers import ordinal_suffix, permission_differences
from core.logging.permissions import is_admin_member, is_admin_message, is_staff_message
from services.log_service import get_log_service

_EDIT_SKIP_CHANNELS = {915687893811470405, 941111737225199696, 915687894172188722}


class LoggingListeners(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @property
    def logs(self):
        return get_log_service(self.client)

    async def _emit(self, payload: LogPayload, *, message_context=None) -> None:
        await self.logs.record(payload, message_context=message_context)

    def _gid(self, guild: discord.Guild | None) -> int:
        return guild.id if guild else guild_id()

    # ── Message moderation (no log embed) ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.channel.id in ignored_channel_ids():
            return

        if not is_staff_message(message) and not message.author.bot:
            if "[" in message.content and "]" in message.content and "(" in message.content and ")" in message.content:
                for word in message.content.split(" "):
                    if "[" in word and "]" in word and "(" in word and ")" in word:
                        await message.delete()
                        if log_flag("LOG_AUTO_MODERATION", True):
                            await self._emit(
                                LogPayload(
                                    event_type="message.auto_moderated",
                                    category=LogCategory.MODERATION,
                                    title="Message",
                                    action="Auto Moderated",
                                    guild_id=message.guild.id,
                                    actor_id=message.author.id,
                                    channel_id=message.channel.id,
                                    fields={
                                        "Target": format_user(message.author),
                                        "Channel": format_channel(message.channel),
                                        "Details": "Hyperlink removed",
                                    },
                                )
                            )
                        break

        if not is_staff_message(message):
            if "discord.gg/" in message.content or "discord.com/invite" in message.content:
                if message.channel.id not in recruitment_channel_ids():
                    await message.delete()
                    if log_flag("LOG_AUTO_MODERATION", True):
                        await self._emit(
                            LogPayload(
                                event_type="message.auto_moderated",
                                category=LogCategory.MODERATION,
                                title="Message",
                                action="Auto Moderated",
                                guild_id=message.guild.id,
                                actor_id=message.author.id,
                                channel_id=message.channel.id,
                                fields={
                                    "Target": format_user(message.author),
                                    "Channel": format_channel(message.channel),
                                    "Details": "Invite link removed",
                                },
                            )
                        )

    # ── Members ───────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        count = len(member.guild.members)
        suffix = ordinal_suffix(count)
        created = member.created_at.strftime("%a, %#d %B %Y, %I:%M %p")
        await self._emit(
            LogPayload(
                event_type="member.join",
                category=LogCategory.MEMBER,
                title="Member",
                action="Joined",
                guild_id=member.guild.id,
                target_id=member.id,
                fields={
                    "Target": format_user(member),
                    "Details": f"Member #{count}{suffix}\nCreated: {created}",
                },
                thumbnail_url=str(member.display_avatar.url),
            )
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await self.logs.audit.ban(guild, user.id)
        staff = entry.user if entry else None
        reason = entry.reason if entry and entry.reason else "None provided"
        fields = {
            "Target": format_user(user),
            "Details": f"Reason: {reason}",
        }
        if staff:
            fields["Actor"] = format_user(staff)
        await self._emit(
            LogPayload(
                event_type="member.ban",
                category=LogCategory.MODERATION,
                title="Member",
                action="Banned",
                guild_id=guild.id,
                actor_id=staff.id if staff else None,
                target_id=user.id,
                fields=fields,
                thumbnail_url=str(user.display_avatar.url),
                severity=LogSeverity.WARN,
            )
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        count = len(member.guild.members)
        suffix = ordinal_suffix(count)

        try:
            banned = await member.guild.fetch_ban(member)
        except discord.NotFound:
            banned = None

        if banned:
            entry = await self.logs.audit.ban(member.guild, member.id)
            staff = entry.user if entry else None
            fields = {
                "Target": format_user(member),
                "Details": f"Reason: {banned.reason or 'None provided'}",
            }
            if staff:
                fields["Actor"] = format_user(staff)
            await self._emit(
                LogPayload(
                    event_type="member.ban",
                    category=LogCategory.MODERATION,
                    title="Member",
                    action="Banned",
                    guild_id=member.guild.id,
                    actor_id=staff.id if staff else None,
                    target_id=member.id,
                    fields=fields,
                    severity=LogSeverity.WARN,
                )
            )
        else:
            entry = await self.logs.audit.kick(member.guild, member.id)
            if entry and getattr(entry.target, "id", None) == member.id:
                staff = entry.user
                reason = entry.reason or "None provided"
                await self._emit(
                    LogPayload(
                        event_type="member.kick",
                        category=LogCategory.MODERATION,
                        title="Member",
                        action="Kicked",
                        guild_id=member.guild.id,
                        actor_id=staff.id if staff else None,
                        target_id=member.id,
                        fields={
                            "Target": format_user(member),
                            "Actor": format_user(staff) if staff else "—",
                            "Details": f"Reason: {reason}",
                        },
                        severity=LogSeverity.WARN,
                    )
                )
            else:
                joined = member.joined_at.strftime("%a, %#d %B %Y, %I:%M %p") if member.joined_at else "—"
                created = member.created_at.strftime("%a, %#d %B %Y, %I:%M %p")
                await self._emit(
                    LogPayload(
                        event_type="member.leave",
                        category=LogCategory.MEMBER,
                        title="Member",
                        action="Left",
                        guild_id=member.guild.id,
                        target_id=member.id,
                        fields={
                            "Target": format_user(member),
                            "Details": f"Member #{count}{suffix}\nCreated: {created}\nJoined: {joined}",
                        },
                        thumbnail_url=str(member.display_avatar.url),
                    )
                )

        rows = await execute(
            "SELECT * FROM `tickets` WHERE `owner_id` = %s AND `is_active` = 1",
            (member.id,),
        )
        for row in rows:
            channel = discord.utils.get(member.guild.channels, id=int(row["channel_id"]))
            staff_role = discord.utils.get(member.guild.roles, name="Staff Team")
            if channel and staff_role:
                embed = discord.Embed(
                    title=f"{member.name} Left the Discord",
                    description="The ticket creator has left the discord. I guess he didn't need the support...",
                    color=discord.Color.from_str("#F1C40F"),
                )
                await channel.send(embed=embed, content=staff_role.mention)

            await self._emit(
                LogPayload(
                    event_type="custom.ticket_owner_left",
                    category=LogCategory.CUSTOM,
                    title="Custom",
                    action="Ticket Owner Left",
                    guild_id=member.guild.id,
                    target_id=member.id,
                    channel_id=int(row["channel_id"]),
                    fields={
                        "Target": format_user(member),
                        "Channel": f"<#{row['channel_id']}> (`{row['channel_id']}`)",
                    },
                )
            )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self._emit(
            LogPayload(
                event_type="member.unban",
                category=LogCategory.MODERATION,
                title="Member",
                action="Unbanned",
                guild_id=guild.id,
                target_id=user.id,
                fields={"Target": format_user(user)},
                thumbnail_url=str(user.display_avatar.url),
            )
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            await self._emit(
                LogPayload(
                    event_type="member.nickname",
                    category=LogCategory.MEMBER,
                    title="Member",
                    action="Nickname Changed",
                    guild_id=after.guild.id,
                    target_id=after.id,
                    fields={
                        "Target": format_user(after),
                        "Details": f"Before: {before.display_name}\nAfter: {after.display_name}",
                    },
                    thumbnail_url=str(after.display_avatar.url),
                )
            )

        if before.roles != after.roles:
            if len(before.roles) > len(after.roles):
                action = "Role Removed"
                diff = list((Counter(r.mention for r in before.roles) - Counter(r.mention for r in after.roles)).elements())
            else:
                action = "Role Added"
                diff = list((Counter(r.mention for r in after.roles) - Counter(r.mention for r in before.roles)).elements())
            await self._emit(
                LogPayload(
                    event_type="member.roles",
                    category=LogCategory.ROLE,
                    title="Member",
                    action=action,
                    guild_id=after.guild.id,
                    target_id=after.id,
                    fields={
                        "Target": format_user(after),
                        "Details": diff[0] if diff else "—",
                    },
                    thumbnail_url=str(after.display_avatar.url),
                )
            )

        if before.guild_permissions != after.guild_permissions:
            entry = await self.logs.audit.member_update(after)
            differences = await permission_differences(after, before.guild_permissions, after.guild_permissions, entry)
            if not differences:
                return
            await self._emit(
                LogPayload(
                    event_type="member.permissions",
                    category=LogCategory.MODERATION,
                    title="Member",
                    action="Permissions Changed",
                    guild_id=after.guild.id,
                    target_id=after.id,
                    fields={
                        "Target": format_user(after),
                        "Details": "\n".join(differences),
                    },
                    route_admin=True,
                    immediate=True,
                    thumbnail_url=str(after.display_avatar.url),
                )
            )

    # ── Messages ──────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if not before.guild:
            return
        if before.channel.id in _EDIT_SKIP_CHANNELS:
            return
        if any(s in before.content for s in ("https", "http")):
            return
        if len(before.content) > 1000 or len(after.content) > 1000:
            return

        admin = is_admin_message(before)
        await self._emit(
            LogPayload(
                event_type="message.edit",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Edited",
                guild_id=before.guild.id,
                actor_id=before.author.id,
                channel_id=before.channel.id,
                fields={
                    "Actor": format_user(before.author),
                    "Channel": format_channel(before.channel),
                    "Before": truncate(before.content),
                    "After": truncate(after.content),
                },
                jump_url=before.jump_url,
                route_admin=admin,
                immediate=admin,
                thumbnail_url=str(before.author.display_avatar.url),
            ),
            message_context=before,
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        entry = await self.logs.audit.message_delete(message.guild, message.author.id)
        if entry and getattr(entry.target, "id", None) == message.author.id:
            deleter = entry.user
        else:
            deleter = message.author

        fake = type("FakeMsg", (), {"author": deleter, "guild": message.guild})()
        admin = is_admin_message(message) or is_admin_message(fake)

        await self._emit(
            LogPayload(
                event_type="message.delete",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Deleted",
                guild_id=message.guild.id,
                actor_id=deleter.id,
                target_id=message.author.id,
                channel_id=message.channel.id,
                fields={
                    "Target": format_user(message.author),
                    "Actor": format_user(deleter),
                    "Channel": format_channel(message.channel),
                    "Details": truncate(message.content),
                },
                route_admin=admin,
                immediate=admin,
                thumbnail_url=str(message.author.display_avatar.url),
            ),
        )

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        if not messages:
            return
        guild = messages[0].guild
        if guild is None:
            return
        channel = messages[0].channel
        entry = await self.logs.audit.bulk_message_delete(guild)
        actor = entry.user if entry else None
        fields = {
            "Channel": format_channel(channel),
            "Details": f"Deleted {len(messages)} message(s)",
        }
        if actor:
            fields["Actor"] = format_user(actor)
        await self._emit(
            LogPayload(
                event_type="message.bulk_delete",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Bulk Deleted",
                guild_id=guild.id,
                actor_id=actor.id if actor else None,
                channel_id=channel.id,
                fields=fields,
                severity=LogSeverity.WARN,
            )
        )

    # ── Reactions ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return
        await self._emit(
            LogPayload(
                event_type="reaction.add",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Reaction Added",
                guild_id=reaction.message.guild.id,
                actor_id=user.id,
                channel_id=reaction.message.channel.id,
                fields={
                    "Actor": format_user(user),
                    "Details": f"Emoji: {reaction.emoji}\nCount: {reaction.count}",
                },
                jump_url=reaction.message.jump_url,
            )
        )

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User):
        if not reaction.message.guild:
            return
        await self._emit(
            LogPayload(
                event_type="reaction.remove",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Reaction Removed",
                guild_id=reaction.message.guild.id,
                actor_id=user.id,
                channel_id=reaction.message.channel.id,
                fields={
                    "Actor": format_user(user),
                    "Details": f"Emoji: {reaction.emoji}\nCount: {reaction.count}",
                },
                jump_url=reaction.message.jump_url,
            )
        )

    @commands.Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, reactions: list):
        if not message.guild:
            return
        await self._emit(
            LogPayload(
                event_type="reaction.clear",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Reactions Cleared",
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                fields={"Channel": format_channel(message.channel), "Details": str(reactions)},
                jump_url=message.jump_url,
            )
        )

    @commands.Cog.listener()
    async def on_reaction_clear_emoji(self, reaction: discord.Reaction):
        if not reaction.message.guild:
            return
        await self._emit(
            LogPayload(
                event_type="reaction.clear_emoji",
                category=LogCategory.MESSAGE,
                title="Message",
                action="Reaction Emoji Cleared",
                guild_id=reaction.message.guild.id,
                channel_id=reaction.message.channel.id,
                fields={"Details": str(reaction.emoji)},
                jump_url=reaction.message.jump_url,
            )
        )

    # ── Invites ───────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if not invite.guild:
            return
        created = invite.created_at.strftime("%a, %b %d, %Y, %I:%M %p") if invite.created_at else "—"
        await self._emit(
            LogPayload(
                event_type="invite.create",
                category=LogCategory.SERVER,
                title="Server",
                action="Invite Created",
                guild_id=invite.guild.id,
                actor_id=invite.inviter.id if invite.inviter else None,
                channel_id=invite.channel.id if invite.channel else None,
                fields={
                    "Actor": format_user(invite.inviter),
                    "Channel": format_channel(invite.channel),
                    "Details": (
                        f"Code: {invite.code}\nMax age: {invite.max_age}s\n"
                        f"Max uses: {invite.max_uses}\nTemporary: {invite.temporary}\nCreated: {created} UTC"
                    ),
                },
            )
        )

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if not invite.guild:
            return
        await self._emit(
            LogPayload(
                event_type="invite.delete",
                category=LogCategory.SERVER,
                title="Server",
                action="Invite Deleted",
                guild_id=invite.guild.id,
                channel_id=invite.channel.id if invite.channel else None,
                fields={
                    "Channel": format_channel(invite.channel),
                    "Details": f"Code: {invite.code}",
                },
            )
        )

    # ── Channels & threads ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self._emit(
            LogPayload(
                event_type="channel.create",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Created",
                guild_id=channel.guild.id,
                channel_id=channel.id,
                fields={"Channel": format_channel(channel), "Details": f"Type: {channel.type}"},
            )
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self._emit(
            LogPayload(
                event_type="channel.delete",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Deleted",
                guild_id=channel.guild.id,
                fields={"Details": f"#{channel.name}\nType: {channel.type}"},
            )
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        attrs = [
            ("name", "Name"),
            ("topic", "Topic"),
            ("category", "Category"),
            ("slowmode_delay", "Slowmode"),
            ("nsfw", "NSFW"),
            ("permissions_synced", "Permissions Synced"),
        ]
        for attr, label in attrs:
            if isinstance(before, discord.VoiceChannel) and attr == "topic":
                continue
            if getattr(before, attr, None) != getattr(after, attr, None):
                await self._emit(
                    LogPayload(
                        event_type="channel.update",
                        category=LogCategory.CHANNEL,
                        title="Channel",
                        action=f"{label} Changed",
                        guild_id=after.guild.id,
                        channel_id=after.id,
                        fields={
                            "Channel": format_channel(after),
                            "Details": f"Before: {getattr(before, attr)}\nAfter: {getattr(after, attr)}",
                        },
                    )
                )
                break

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        tags = ", ".join(t.name for t in thread.applied_tags)
        details = f"Parent: {thread.parent.mention if thread.parent else '—'}\nTags: {tags}"
        if thread.owner:
            details += f"\nCreator: {thread.owner.mention}"
        if thread.starter_message:
            details += f"\n{truncate(thread.starter_message.content, 500)}"
        await self._emit(
            LogPayload(
                event_type="thread.create",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Thread Created",
                guild_id=thread.guild.id,
                channel_id=thread.id,
                fields={"Channel": format_channel(thread), "Details": details},
            )
        )

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        for attr in ("name", "archived", "locked", "invitable", "slowmode_delay"):
            if getattr(before, attr, None) != getattr(after, attr, None):
                await self._emit(
                    LogPayload(
                        event_type="thread.update",
                        category=LogCategory.CHANNEL,
                        title="Channel",
                        action="Thread Updated",
                        guild_id=after.guild.id,
                        channel_id=after.id,
                        fields={
                            "Channel": format_channel(after),
                            "Details": f"{attr}: {getattr(before, attr)} → {getattr(after, attr)}",
                        },
                    )
                )
                break

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        await self._emit(
            LogPayload(
                event_type="thread.delete",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Thread Deleted",
                guild_id=thread.guild.id,
                fields={"Details": f"#{thread.name} (`{thread.id}`)"},
            )
        )

    @commands.Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember):
        user_line = f"<@{member.id}> (`{member.id}`)"
        await self._emit(
            LogPayload(
                event_type="thread.member_join",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Thread Member Joined",
                guild_id=member.thread.guild.id,
                actor_id=member.id,
                channel_id=member.thread.id,
                fields={
                    "Actor": user_line,
                    "Channel": format_channel(member.thread),
                },
            )
        )

    @commands.Cog.listener()
    async def on_thread_member_remove(self, member: discord.ThreadMember):
        user_line = f"<@{member.id}> (`{member.id}`)"
        await self._emit(
            LogPayload(
                event_type="thread.member_remove",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Thread Member Left",
                guild_id=member.thread.guild.id,
                actor_id=member.id,
                channel_id=member.thread.id,
                fields={
                    "Actor": user_line,
                    "Channel": format_channel(member.thread),
                },
            )
        )

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel: discord.abc.GuildChannel, last_pin: discord.Message | None):
        await self._emit(
            LogPayload(
                event_type="channel.pins",
                category=LogCategory.CHANNEL,
                title="Channel",
                action="Pins Updated",
                guild_id=channel.guild.id,
                channel_id=channel.id,
                fields={"Channel": format_channel(channel), "Details": str(last_pin)},
            )
        )

    # ── Voice & stage ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return
        if before.channel is None:
            action = "Joined"
        elif after.channel is None:
            action = "Left"
        else:
            action = "Switched"
        await self._emit(
            LogPayload(
                event_type="voice.state",
                category=LogCategory.VOICE,
                title="Voice",
                action=action,
                guild_id=member.guild.id,
                target_id=member.id,
                fields={
                    "Target": format_user(member),
                    "Details": (
                        f"Left: {before.channel.mention if before.channel else 'N/A'}\n"
                        f"Joined: {after.channel.mention if after.channel else 'N/A'}"
                    ),
                },
                thumbnail_url=str(member.display_avatar.url),
            )
        )

    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage: discord.StageInstance):
        await self._emit(
            LogPayload(
                event_type="stage.create",
                category=LogCategory.VOICE,
                title="Voice",
                action="Stage Created",
                guild_id=stage.guild.id,
                channel_id=stage.channel.id,
                fields={"Channel": format_channel(stage.channel), "Details": f"Topic: {stage.topic}"},
            )
        )

    @commands.Cog.listener()
    async def on_stage_instance_update(self, before: discord.StageInstance, after: discord.StageInstance):
        if before.topic != after.topic:
            await self._emit(
                LogPayload(
                    event_type="stage.update",
                    category=LogCategory.VOICE,
                    title="Voice",
                    action="Stage Updated",
                    guild_id=after.guild.id,
                    channel_id=after.channel.id,
                    fields={
                        "Channel": format_channel(after.channel),
                        "Details": f"Before: {before.topic}\nAfter: {after.topic}",
                    },
                )
            )

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage: discord.StageInstance):
        await self._emit(
            LogPayload(
                event_type="stage.delete",
                category=LogCategory.VOICE,
                title="Voice",
                action="Stage Deleted",
                guild_id=stage.guild.id,
                fields={"Details": f"Topic: {stage.topic}"},
            )
        )

    # ── Roles ─────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        await self._emit(
            LogPayload(
                event_type="role.create",
                category=LogCategory.ROLE,
                title="Role",
                action="Created",
                guild_id=role.guild.id,
                target_id=role.id,
                fields={"Target": role.mention, "Details": f"Color: {role.color}\nPermissions: {role.permissions.value}"},
            )
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self._emit(
            LogPayload(
                event_type="role.delete",
                category=LogCategory.ROLE,
                title="Role",
                action="Deleted",
                guild_id=role.guild.id,
                fields={"Details": f"{role.name}\nColor: {role.color}"},
            )
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        for attribute in ("color", "hoist", "mentionable", "permissions"):
            bv, av = getattr(before, attribute, None), getattr(after, attribute, None)
            if bv == av:
                continue
            if attribute == "permissions":
                diff = set(av) - set(bv)
                for perm, enabled in diff:
                    await self._emit(
                        LogPayload(
                            event_type="role.permissions",
                            category=LogCategory.ROLE,
                            title="Role",
                            action="Permissions Updated",
                            guild_id=after.guild.id,
                            target_id=after.id,
                            fields={
                                "Target": after.mention,
                                "Details": f"{perm}: {not enabled} → {enabled}",
                            },
                            route_admin=True,
                            immediate=True,
                        )
                    )
            else:
                await self._emit(
                    LogPayload(
                        event_type="role.update",
                        category=LogCategory.ROLE,
                        title="Role",
                        action=f"{attribute.title()} Updated",
                        guild_id=after.guild.id,
                        target_id=after.id,
                        fields={
                            "Target": after.mention,
                            "Details": f"Before: {bv}\nAfter: {av}",
                        },
                    )
                )
            break

    # ── Server / guild ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        attrs = [
            "name", "afk_channel", "afk_timeout", "banner", "default_notifications",
            "description", "discovery_splash", "features", "icon", "premium_progress_bar_enabled",
            "premium_tier", "rules_channel", "safety_alerts_channel", "system_channel",
            "vanity_url", "verification_level",
        ]
        for attribute in attrs:
            bv, av = getattr(before, attribute), getattr(after, attribute)
            if bv == av:
                continue
            if attribute in ("banner", "icon", "discovery_splash") and av:
                details = f"[Before]({bv.url if bv else '—'})\n[After]({av.url})"
            else:
                details = f"Before: {bv}\nAfter: {av}"
            await self._emit(
                LogPayload(
                    event_type="guild.update",
                    category=LogCategory.SERVER,
                    title="Server",
                    action=f"{attribute.replace('_', ' ').title()} Changed",
                    guild_id=after.id,
                    fields={"Details": details},
                )
            )
            break

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list, after: list):
        if len(before) == len(after):
            return
        if len(before) > len(after):
            msg = "Emoji Removed"
            names = list((Counter(r.name for r in before) - Counter(r.name for r in after)).elements())
            ids = list((Counter(r.id for r in before) - Counter(r.id for r in after)).elements())
        else:
            msg = "Emoji Added"
            names = list((Counter(r.name for r in after) - Counter(r.name for r in before)).elements())
            ids = list((Counter(r.id for r in after) - Counter(r.id for r in before)).elements())
        await self._emit(
            LogPayload(
                event_type="emoji.update",
                category=LogCategory.SERVER,
                title="Server",
                action="Emoji Changed",
                guild_id=guild.id,
                fields={"Details": f"{msg}: {names[0]}"},
                thumbnail_url=f"https://cdn.discordapp.com/emojis/{ids[0]}.webp?size=44&quality=lossless",
            )
        )

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list, after: list):
        if len(before) == len(after):
            return
        if len(before) > len(after):
            msg = "Sticker Removed"
            names = list((Counter(r.name for r in before) - Counter(r.name for r in after)).elements())
            ids = list((Counter(r.id for r in before) - Counter(r.id for r in after)).elements())
        else:
            msg = "Sticker Added"
            names = list((Counter(r.name for r in after) - Counter(r.name for r in before)).elements())
            ids = list((Counter(r.id for r in after) - Counter(r.id for r in before)).elements())
        await self._emit(
            LogPayload(
                event_type="sticker.update",
                category=LogCategory.SERVER,
                title="Server",
                action="Sticker Changed",
                guild_id=guild.id,
                fields={"Details": f"{msg}: {names[0]}"},
                thumbnail_url=f"https://media.discordapp.net/stickers/{ids[0]}.webp?size=44&quality=lossless",
            )
        )

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        await self._emit(
            LogPayload(
                event_type="webhook.update",
                category=LogCategory.SERVER,
                title="Server",
                action="Webhook Updated",
                guild_id=channel.guild.id,
                channel_id=channel.id,
                fields={"Channel": format_channel(channel)},
            )
        )

    def _integration_fields(self, integration: discord.Integration) -> dict[str, str]:
        user = integration.user
        return {
            "Details": (
                f"Account: {integration.account.name} ({integration.account.id})\n"
                f"Name: {integration.name}\nType: {integration.type}\nEnabled: {integration.enabled}\n"
                f"User: {format_user(user) if user else '—'}"
            ),
        }

    @commands.Cog.listener()
    async def on_integration_create(self, integration: discord.Integration):
        await self._emit(
            LogPayload(
                event_type="integration.create",
                category=LogCategory.SERVER,
                title="Server",
                action="Integration Created",
                guild_id=integration.guild.id,
                fields=self._integration_fields(integration),
            )
        )

    @commands.Cog.listener()
    async def on_integration_update(self, integration: discord.Integration):
        await self._emit(
            LogPayload(
                event_type="integration.update",
                category=LogCategory.SERVER,
                title="Server",
                action="Integration Updated",
                guild_id=integration.guild.id,
                fields=self._integration_fields(integration),
            )
        )

    @commands.Cog.listener()
    async def on_integration_delete(self, integration: discord.Integration):
        await self._emit(
            LogPayload(
                event_type="integration.delete",
                category=LogCategory.SERVER,
                title="Server",
                action="Integration Deleted",
                guild_id=integration.guild.id,
                fields=self._integration_fields(integration),
            )
        )

    # ── Scheduled events ──────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        await self._emit(
            LogPayload(
                event_type="scheduled.create",
                category=LogCategory.SCHEDULED,
                title="Scheduled",
                action="Event Created",
                guild_id=event.guild.id,
                fields={
                    "Details": (
                        f"Name: {event.name}\nStart: {event.start_time}\n"
                        f"Creator: {format_user(event.creator)}\nLocation: {event.location}"
                    ),
                },
                jump_url=event.url,
            )
        )

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        await self._emit(
            LogPayload(
                event_type="scheduled.delete",
                category=LogCategory.SCHEDULED,
                title="Scheduled",
                action="Event Deleted",
                guild_id=event.guild.id,
                fields={"Details": f"Name: {event.name}"},
                jump_url=event.url,
            )
        )

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        for attribute in ("channel", "description", "end_time", "location", "name", "status", "user_count"):
            if getattr(before, attribute) != getattr(after, attribute):
                await self._emit(
                    LogPayload(
                        event_type="scheduled.update",
                        category=LogCategory.SCHEDULED,
                        title="Scheduled",
                        action=f"Event {attribute.title()} Updated",
                        guild_id=after.guild.id,
                        fields={
                            "Details": (
                                f"Name: {before.name}\nBefore: {getattr(before, attribute)}\n"
                                f"After: {getattr(after, attribute)}"
                            ),
                        },
                        jump_url=before.url,
                    )
                )
                break

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
        await self._emit(
            LogPayload(
                event_type="scheduled.user_add",
                category=LogCategory.SCHEDULED,
                title="Scheduled",
                action="Member Added",
                guild_id=event.guild.id,
                target_id=user.id,
                fields={"Target": format_user(user), "Details": f"Event: {event.name}"},
            )
        )

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
        await self._emit(
            LogPayload(
                event_type="scheduled.user_remove",
                category=LogCategory.SCHEDULED,
                title="Scheduled",
                action="Member Removed",
                guild_id=event.guild.id,
                target_id=user.id,
                fields={"Target": format_user(user), "Details": f"Event: {event.name}"},
            )
        )

    # ── Automod ───────────────────────────────────────────────────────────────

    def _automod_fields(self, rule: discord.AutoModRule) -> dict[str, str]:
        actions = "\n".join(f"{a.type} / {a.duration}" for a in rule.actions)
        return {
            "Details": (
                f"Name: {rule.name}\nEnabled: {rule.enabled}\nCreator: {rule.creator}\n"
                f"Actions:\n{actions}\nTrigger type: {rule.trigger.type}"
            ),
        }

    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule: discord.AutoModRule):
        if not log_flag("LOG_AUTO_MODERATION", True):
            return
        await self._emit(
            LogPayload(
                event_type="automod.rule_create",
                category=LogCategory.SECURITY,
                title="Moderation",
                action="Automod Rule Created",
                guild_id=rule.guild.id,
                fields=self._automod_fields(rule),
            )
        )

    @commands.Cog.listener()
    async def on_automod_rule_update(self, rule: discord.AutoModRule):
        if not log_flag("LOG_AUTO_MODERATION", True):
            return
        await self._emit(
            LogPayload(
                event_type="automod.rule_update",
                category=LogCategory.SECURITY,
                title="Moderation",
                action="Automod Rule Updated",
                guild_id=rule.guild.id,
                fields=self._automod_fields(rule),
            )
        )

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule: discord.AutoModRule):
        if not log_flag("LOG_AUTO_MODERATION", True):
            return
        await self._emit(
            LogPayload(
                event_type="automod.rule_delete",
                category=LogCategory.SECURITY,
                title="Moderation",
                action="Automod Rule Deleted",
                guild_id=rule.guild.id,
                fields=self._automod_fields(rule),
            )
        )

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModActionExecution):
        if not log_flag("LOG_AUTO_MODERATION", True):
            return
        rule_id = execution.rule_id
        content = execution.content or execution.matched_content or "—"
        user = execution.user
        await self._emit(
            LogPayload(
                event_type="automod.action",
                category=LogCategory.SECURITY,
                title="Moderation",
                action="Automod Action",
                guild_id=execution.guild_id,
                actor_id=user.id if user else None,
                channel_id=execution.channel_id,
                fields={
                    "Target": format_user(user),
                    "Channel": f"<#{execution.channel_id}>" if execution.channel_id else "—",
                    "Details": f"Rule ID: {rule_id}\n{truncate(content, 500)}",
                },
                severity=LogSeverity.WARN,
            )
        )

    # ── Gateway (optional) ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_connect(self):
        if not log_flag("LOG_GATEWAY_CONNECT"):
            return
        await self._emit(
            LogPayload(
                event_type="bot.connect",
                category=LogCategory.BOT,
                title="Bot",
                action="Connected",
                guild_id=guild_id(),
                summary="Client connected to Discord.",
            )
        )

    @commands.Cog.listener()
    async def on_shard_connect(self):
        if not log_flag("LOG_GATEWAY_CONNECT"):
            return
        await self._emit(
            LogPayload(
                event_type="bot.shard_connect",
                category=LogCategory.BOT,
                title="Bot",
                action="Shard Connected",
                guild_id=guild_id(),
            )
        )

    @commands.Cog.listener()
    async def on_disconnect(self):
        if not log_flag("LOG_GATEWAY_CONNECT"):
            return
        await self._emit(
            LogPayload(
                event_type="bot.disconnect",
                category=LogCategory.BOT,
                title="Bot",
                action="Disconnected",
                guild_id=guild_id(),
                summary="Discord will usually reconnect automatically.",
                severity=LogSeverity.WARN,
            )
        )

    @commands.Cog.listener()
    async def on_shard_disconnect(self):
        if not log_flag("LOG_GATEWAY_CONNECT"):
            return
        await self._emit(
            LogPayload(
                event_type="bot.shard_disconnect",
                category=LogCategory.BOT,
                title="Bot",
                action="Shard Disconnected",
                guild_id=guild_id(),
                severity=LogSeverity.WARN,
            )
        )

    # ── Interactions (optional) ───────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            if not log_flag("LOG_SLASH_COMMANDS"):
                return
            name = interaction.command.name if interaction.command else (interaction.data or {}).get("name", "unknown")
            opts = " ".join(
                f"{o['name']}:{o.get('value')}" for o in ((interaction.data or {}).get("options") or [])
            )
            await self._emit(
                LogPayload(
                    event_type="interaction.command",
                    category=LogCategory.INTERACTION,
                    title="Interaction",
                    action="Slash Command",
                    guild_id=interaction.guild.id if interaction.guild else guild_id(),
                    actor_id=interaction.user.id,
                    channel_id=interaction.channel.id if interaction.channel else None,
                    fields={
                        "Actor": format_user(interaction.user),
                        "Channel": format_channel(interaction.channel),
                        "Details": f"/{name} {opts}".strip(),
                    },
                )
            )
        elif interaction.type == discord.InteractionType.component:
            if not log_flag("LOG_COMPONENT_INTERACTIONS"):
                return
            jump = interaction.message.jump_url if interaction.message else None
            await self._emit(
                LogPayload(
                    event_type="interaction.component",
                    category=LogCategory.INTERACTION,
                    title="Interaction",
                    action="Component",
                    guild_id=interaction.guild.id if interaction.guild else guild_id(),
                    actor_id=interaction.user.id,
                    channel_id=interaction.channel.id if interaction.channel else None,
                    fields={"Actor": format_user(interaction.user), "Channel": format_channel(interaction.channel)},
                    jump_url=jump,
                )
            )
        elif interaction.type == discord.InteractionType.modal_submit:
            if not log_flag("LOG_MODAL_SUBMISSIONS"):
                return
            jump = interaction.message.jump_url if interaction.message else None
            await self._emit(
                LogPayload(
                    event_type="interaction.modal",
                    category=LogCategory.INTERACTION,
                    title="Interaction",
                    action="Modal Submitted",
                    guild_id=interaction.guild.id if interaction.guild else guild_id(),
                    actor_id=interaction.user.id,
                    channel_id=interaction.channel.id if interaction.channel else None,
                    fields={"Actor": format_user(interaction.user), "Channel": format_channel(interaction.channel)},
                    jump_url=jump,
                )
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(LoggingListeners(client))
