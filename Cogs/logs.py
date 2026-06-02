from Assets.functions import execute
from discord.ext import commands, tasks
from collections import Counter
import datetime
import discord
import json

"""
List of all event listeners which are not utilized in this file:
- on_automod_action
- on_audit_log_entry_create
"""

class Logs(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
    self.logs = []
    self.admin_logs = []
    self.db_logs = []
    self.flush_logs.start()
    self.flush_admin_logs.start()
    #self.flush_db_logs.start()
    
    with open("Assets/config.json", "r") as file:
        self.data = json.load(file)

  @tasks.loop(minutes=1)
  async def flush_logs(self):
    if not self.logs:
      return
    
    for i in range(0, len(self.logs), 10):
      channel = self.client.get_channel(918928087582916699)
      try:
        await channel.send(embeds=self.logs[i:i+10])

      except Exception as e:
        pass

    self.logs = []

  @tasks.loop(minutes=1)
  async def flush_admin_logs(self):
    if not self.admin_logs:
        return
     
    for i in range(0, len(self.admin_logs), 10):
        channel = self.client.get_channel(1190693196716576878)
        try:
           await channel.send(embeds = self.admin_logs[i:i+10])
        
        except Exception as e:
           pass
    
    self.admin_logs = [] 

  #@tasks.loop(minutes=1)
  #async def flush_db_logs(self):
  #  if not self.db_logs:
  #    return
  #  
  #  connection = mysql.connector.connect(**{**self.data["DATABASE_CONFIG"], 'autocommit': bool(self.data["DATABASE_CONFIG"]['autocommit'])})
  #  cursor = connection.cursor(dictionary=True)
  #  information = "INSERT INTO logs (time, action, user, value, extra) VALUES (%s, %s, %s, %s, %s)"
  #  
  #  cursor.executemany(information, self.db_logs)
  #  self.db_logs = []
  #
  def _member_roles(self, author, guild: discord.Guild | None):
    """Resolve role list; message.author is often User, not Member."""
    if guild is None or author is None:
      return ()
    if isinstance(author, discord.Member):
      return author.roles
    member = guild.get_member(author.id)
    if member is not None:
      return member.roles
    return ()

  def _has_named_role(self, author, guild: discord.Guild | None, role_names: list[str]) -> bool:
    if guild is None:
      return False
    member_roles = self._member_roles(author, guild)
    return any(
      discord.utils.get(guild.roles, name=role_name) in member_roles
      for role_name in role_names
    )

  def is_staff(self, message) -> bool:
    names_of_roles = ["*", "Owner", "Factions Management", "Manager", "Developer", "Sr. Administrator", 
                      "Factions Administrator", "Kitmap Administrator", "Lifesteal Administrator", "Skyblock Administrator", "Staff of the Month", "Staff Team",
                      "Factions Jr. Administrator", "Kitmap Jr. Administrator", "Lifesteal Jr. Administrator", "Skyblock Jr. Administrator",
                      "Factions Sr. Moderator", "Kitmap Sr. Moderator", "Lifesteal Sr. Moderator", "Skyblock Sr. Moderator", 
                      "Factions Moderator", "Kitmap Moderator", "Lifesteal Moderator", "Skyblock Moderator", 
                      "Factions Helper", "Kitmap Helper", "Skyblock Helper", "Skyblock Helper"]
    guild = getattr(message, "guild", None)
    author = getattr(message, "author", None)
    return self._has_named_role(author, guild, names_of_roles)
  
  def is_admin(self, message) -> bool:
    names_of_roles = ["*", "Owner", "Factions Management", "Manager", "Developer", "Sr. Administrator", "Factions Administrator", "Kitmap Administrator", "Lifesteal Administrator", "Skyblock Administrator"]
    guild = getattr(message, "guild", None)
    author = getattr(message, "author", None)
    return self._has_named_role(author, guild, names_of_roles)
    
  @commands.Cog.listener()
  async def on_message(self, message):
    if not message.guild:
      return
    
    extra = ""
    try:
      if message.reference:
        extra += f" R|{message.reference.cached_message.content}||"

      if message.attachments:
        for index, _ in enumerate(message.attachments):
          extra+=f" I|Image #{index}||"

      if message.embeds:
        for embed in message.embeds:
          if embed.author:
            extra+=f" EAN|{embed.author.name}|| EAU{embed.author.icon_url}||"

          if embed.title:
            extra+=f" ET|{embed.title}||"

          if embed.description:
            extra+=f" ED|{embed.description}||"

          if embed.footer:
            extra+=f" EF|{embed.footer}||"

          if embed.colour:
            extra+=f" EC|{embed.colour}||"

          if embed.fields:
            for field in embed.fields:
              extra+=f" EFN|{field.name}|| EFV|{field.value}|| EFI{field.inline}||"

          if embed.image:
            extra+=f" EI|{embed.image.url}||"

          if embed.thumbnail:
            extra+=f" ETN|{embed.thumbnail.url}||"

    except:
      pass

    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Message Sent", 
          message.author.id, 
          message.content, 
          extra
    ))
    
    # Prevents anyone under admin from using hyperlinks for safety
    if not self.is_staff(message) and not message.author.bot:
        if "[" in message.content and "]" in message.content and "(" in message.content and ")" in message.content:
            for word in message.content.split(" "):
                if "[" in word and "]" in word and "(" in word and ")" in word:
                    await message.delete()
    
    # Prevents any discord invite links to be sent besides in recruitment channels & staff bypass
    if not self.is_staff(message):
        if "discord.gg/" in message.content or "discord.com/invite" in message.content:
            if message.channel.id not in self.data['RECRUITMENT_CHANNELS']:
                await message.delete()

  @commands.Cog.listener()
  async def on_member_join(self,member: discord.Member):
    pos = int(str(len(member.guild.members))[-1])
    te = "st" if pos == 1 else "nd" if pos == 2 else "rd" if pos == 3 else "th"

    embed= discord.Embed(
       title="Member joined", 
       description=f"`Member` {member.mention} | {member.name}#{member.discriminator}\n"
                    f"`Number` {len(member.guild.members)}{te} Member\n"
                    f"`Created At` {member.created_at.strftime('%a, %#d %B %Y, %I:%M %p ')}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=member.avatar)

    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Member Joined", 
          member.id, 
          "", 
          ""
    ))

  @commands.Cog.listener()
  async def on_member_remove(self, member):
    pos = int(str(len(member.guild.members))[-1])
    te = "st" if pos == 1 else "nd" if pos == 2 else "rd" if pos == 3 else "th"

    try:
        banned = await member.guild.fetch_ban(member)
    except discord.NotFound:
        banned = False

    if banned:
        staff_member = None
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == member.id:
                staff_member = entry.user
                break 

        log_embed = discord.Embed(
            title="Member Banned", 
            description=f"`Member` {member.mention} ({member.id})\n"
                        f"`Reason` {banned.reason}\n" 
                        f"`Staff` {staff_member.mention} / {staff_member.name}" if staff_member else "",
            color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

      
    else:
      log_embed= discord.Embed(
         title="Member Left", 
         description=f"`Member` {member.mention} | {member.name}#{member.discriminator}\n"
                      f"`Number` {len(member.guild.members)}{te}\n"
                      f"`Created At` {member.created_at.strftime('%a, %#d %B %Y, %I:%M %p ')}\n"
                      f"`Joined at` {member.joined_at.strftime('%a, %#d %B %Y, %I:%M %p ')}", 
         color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
         timestamp=datetime.datetime.now(datetime.timezone.utc)
      )
      log_embed.set_thumbnail(url=member.avatar)

    rows = await execute(f"SELECT * FROM `tickets` WHERE `ownerID` = '{str(member.id)}' AND `active`= 'True'")

    if len(rows)>0:
      for row in rows:
        channel = discord.utils.get(member.guild.channels, id=int(row['channelID']))
        staff = discord.utils.get(member.guild.roles, name="Staff Team")
        left_discord_embed = discord.Embed(
           title=f"{member.name}#{member.discriminator} Left the Discord", 
           description="The ticket creator has left the discord. I guess he didn't need the support...",
           color=discord.Color.from_str(self.data["EMBED_COLOR"]),
           timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await channel.send(embed=left_discord_embed, content=staff.mention)
    
    self.logs.append(log_embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Member Left", 
          member.id, 
          "", 
          ""
    ))
    
  @commands.Cog.listener()
  async def on_member_unban(self, guild, user):
    embed = discord.Embed(
       title="Member Unbanned", 
       description=f"`Member` {user.mention} ({user.id})", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=user.avatar)

    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Member Unbanned", 
          user.id, 
          "", 
          ""
    ))
    
  @commands.Cog.listener()
  async def on_reaction_add(self, reaction, user):
    if user.bot:
      return
    embed = discord.Embed(
       title=f"Reaction Added", 
       description= f"`Reaction` {reaction.emoji}\n"
                    f"`Member` {user.mention} ({user.id})\n"
                    f"`Count` {reaction.count}\n \n"
                    f"[Jump To Message]({reaction.message.jump_url})",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Reaction Added", 
          user.id, 
          str(reaction.emoji), 
          f" RC|{reaction.count} || C|{reaction.message.channel.id} || J|{reaction.message.jump_url}"
    ))
  
  @commands.Cog.listener()
  async def on_reaction_remove(self, reaction, user):
    embed = discord.Embed(
       title=f"Reaction Removed",
       description= f"`Reaction` {reaction.emoji}\n"
                    f"`Member` {user.mention} ({user.id})\n"
                    f"`Count` {reaction.count}\n \n"
                    f"[Jump To Message]({reaction.message.jump_url})",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Reaction Removed", 
          user.id, 
          str(reaction.emoji), 
          f" RC|{reaction.count} || C|{reaction.message.channel.id} || J|{reaction.message.jump_url}"
    ))
    
  @commands.Cog.listener()
  async def on_reaction_clear(self, message, reactions):
    embed = discord.Embed(
       title=f"Reactions Cleared", 
       description= f"`Reactions` {reactions}\n \n"
                    f"[Jump To Message]({message.jump_url})",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Reactions Cleared", 
          "", 
          reactions, 
          f" C|{reactions.message.channel.id} || J|{reactions.message.jump_url}"
    ))
    
  @commands.Cog.listener()
  async def on_reaction_clear_emoji(self, reaction):
    embed = discord.Embed(
       title=f"Reaction Emoji Cleared", 
       description= f"`Reaction` {reaction}\n \n"
                    f"[Jump To Message]({reaction.message.jump_url})",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Reaction Emoji Cleared", 
          "", 
          str(reaction.emoji), 
          f" C|{reaction.message.channel.id} || J|{reaction.message.jump_url}"
    ))
    
  @commands.Cog.listener()
  async def on_scheduled_event_create(self, event):
    embed = discord.Embed(
       title="Event Created", 
       description= f"`Name` {event.name}\n"
                    f"`Description` {event.description}\n"
                    f"`Start Time` {event.start_time}\n"
                    f"`End Time` {event.end_time}\n"
                    f"`Creator` {event.creator.mention} ({event.creator.id})\n"
                    f"`Location` {event.location}\n"
                    f"[Cover Image]({event.cover_image.url})\n"
                    f"`Channel` {event.channel.mention}\n \n"
                    f"[Event URL]({event.url})",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Event Created", 
          "", 
          event.name, 
          f" D|{event.description} || ST|{event.start_time} || ET|{event.end_time} || CR|{event.creator.id} || L|{event.location} || CI|{event.cover_image.url} || C|{event.channel.id} || U|{event.url}"
    ))
    
  @commands.Cog.listener()
  async def on_scheduled_event_delete(self, event):
    embed = discord.Embed(
       title="Event Deleted", 
       description= f"`Name` {event.name}\n"
                    f"`Description` {event.description}\n"
                    f"`Start Time` {event.start_time}\n"
                    f"`End Time` {event.end_time}\n"
                    f"`Creator` {event.creator}\n"
                    f"`Location` {event.location}\n"
                    f"[Cover Image]({event.cover_image.url})\n"
                    f"`Channel` {event.channel.mention}\n \n"
                    f"[Event URL]({event.url})",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Event Deleted", 
          "", 
          event.name, 
          f" D|{event.description} || ST|{event.start_time} || ET|{event.end_time} || CR|{event.creator.id} || L|{event.location} || CI|{event.cover_image.url} || C|{event.channel.id} || U|{event.url}"
    ))
  
  @commands.Cog.listener()
  async def on_scheduled_event_update(self, before, after):
    attributes_to_check = ["channel", "cover_image", "description", "end_time", "location", "name", "status", "user_count"]

    for attribute in attributes_to_check:
        
      before_value = getattr(before, attribute)
      after_value = getattr(after, attribute)

      if before_value != after_value:
            
          embed = discord.Embed(
               title=f"Event {attribute.capitalize()} Updated", 
               description= f"`Name` {before.name}\n"
                            f"`Before` {before_value}\n"
                            f"`After` {after_value}\n \n"
                            f"[Event URL]({before.url})",
               color=discord.Color.from_str(self.data["EMBED_COLOR"]),
               timestamp=datetime.datetime.now(datetime.timezone.utc)
          )
            
          self.db_logs.append((
                  datetime.datetime.now(datetime.timezone.utc).timestamp(), 
                  f"Event {attribute.capitalize()} Updated", 
                  "", 
                  f"{before_value} -> {after_value}", 
                  f" N|{before.name} || D|{before.description} || ST|{before.start_time} || ET|{before.end_time} || CR|{before.creator.id} || L|{before.location} || CI|{before.cover_image.url} || C|{before.channel.id} || U|{before.url}"
          ))
          self.logs.append(embed)

          break
    
  @commands.Cog.listener()
  async def on_scheduled_event_user_add(self, event, user):
    embed = discord.Embed(
       title="Member Added to Event", 
       description= f"`Name` {event.name}\n"
                    f"`Member` {user.mention} ({user.id})", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Member Added to Event", 
          user.id, 
          event.name, 
          f" D|{event.description} || ST|{event.start_time} || ET|{event.end_time} || CR|{event.creator.id} || L|{event.location} || CI|{event.cover_image.url} || C|{event.channel.id} || U|{event.url}"
    ))
    
  @commands.Cog.listener()
  async def on_scheduled_event_user_remove(self, event, user):
    embed = discord.Embed(
       title="Member Removed From Event", 
       description= f"`Name` {event.name}\n"
                    f"`Member` {user.mention} ({user.id})", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Member Removed From Event", 
          user.id, event.name, 
          f" D|{event.description} || ST|{event.start_time} || ET|{event.end_time} || CR|{event.creator.id} || L|{event.location} || CI|{event.cover_image.url} || C|{event.channel.id} || U|{event.url}"
    ))
    
  @commands.Cog.listener()
  async def on_webhooks_update(self, channel):
    embed = discord.Embed(
       title="Webhook Updated", 
       description=f"`Channel` {channel.mention}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc).timestamp()
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Webhook Updated", 
          "", 
          "",
          f" C|{channel.id}"
    ))
  
  @commands.Cog.listener()
  async def on_automod_rule_create(self, rule):

    actions = "\n".join(
          f"{discord.utils.get(rule.guild.channels, id=action.channel_id).mention} | {action.duration} | {action.type}"
          for action in rule.actions
      )

    exempt_channels = " ".join(
          discord.utils.get(rule.guild.channels, id=chn).mention
          for chn in rule.exempt_channel_ids
      )

    exempt_roles = " ".join(
          discord.utils.get(rule.guild.roles, id=role).mention
          for role in rule.exempt_role_ids
      )

    embed = discord.Embed(
          title="Automod Rule Created",
          description=f"`Actions` {actions}\n"
                      f"`Creator` {rule.creator}\n"
                      f"`Enabled` {rule.enabled}\n"
                      f"`Exempt C.` {exempt_channels}\n"
                      f"`Exempt R.` {exempt_roles}\n"
                      f"`Name` {rule.name}\n"
                      f"`Trigger`\nAllow {rule.trigger.allow_list}\n"
                      f"Keyword Filter {rule.trigger.keyword_filter}\n"
                      f"Mention Limit {rule.trigger.mention_limit}\n"
                      f"Type {rule.trigger.type}",
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    self.logs.append(embed)
    self.db_logs.append((
              datetime.datetime.now(datetime.timezone.utc).timestamp(),
              "Automod Rule Created",
              rule.creator.id,
              rule.name,
              f" A|{actions} || E|{rule.enabled} || EXC|{exempt_channels} || EXR|{exempt_roles} "
              f"|| T|Allow {rule.trigger.allow_list} || KF|{rule.trigger.keyword_filter} || "
              f"ML|{rule.trigger.mention_limit} || T|{rule.trigger.type}"
    ))
    
  @commands.Cog.listener()
  async def on_automod_rule_delete(self, rule):

    actions = "\n".join(
          f"{discord.utils.get(rule.guild.channels, id=action.channel_id).mention} | {action.duration} | {action.type}"
          for action in rule.actions
    )

    exempt_channels = " ".join(
          discord.utils.get(rule.guild.channels, id=chn).mention
          for chn in rule.exempt_channel_ids
    )

    exempt_roles = " ".join(
          discord.utils.get(rule.guild.roles, id=role).mention
          for role in rule.exempt_role_ids
    )

    embed = discord.Embed(
          title="Automod Rule Deleted",
          description=f"`Actions` {actions}\n"
                      f"`Creator` {rule.creator}\n"
                      f"`Enabled` {rule.enabled}\n"
                      f"`Exempt C.` {exempt_channels}\n"
                      f"`Exempt R.` {exempt_roles}\n"
                      f"`Name` {rule.name}\n"
                      f"`Trigger`\nAllow {rule.trigger.allow_list}\n"
                      f"Keyword Filter {rule.trigger.keyword_filter}\n"
                      f"Mention Limit {rule.trigger.mention_limit}\n"
                      f"Type {rule.trigger.type}",
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    self.logs.append(embed)
    self.db_logs.append((
              datetime.datetime.now(datetime.timezone.utc).timestamp(),
              "Automod Rule Deleted",
              rule.creator.id,
              rule.name,
              f" A|{actions} || E|{rule.enabled} || EXC|{exempt_channels} || EXR|{exempt_roles} "
              f"|| T|Allow {rule.trigger.allow_list} || KF|{rule.trigger.keyword_filter} || "
              f"ML|{rule.trigger.mention_limit} || T|{rule.trigger.type}"
    ))
  
  @commands.Cog.listener()
  async def on_automod_rule_update(self, rule):

    actions = "\n".join(
          f"{discord.utils.get(rule.guild.channels, id=action.channel_id).mention} | {action.duration} | {action.type}"
          for action in rule.actions
    )

    exempt_channels = " ".join(
          discord.utils.get(rule.guild.channels, id=chn).mention
          for chn in rule.exempt_channel_ids
    )

    exempt_roles = " ".join(
          discord.utils.get(rule.guild.roles, id=role).mention
          for role in rule.exempt_role_ids
    )

    embed = discord.Embed(
          title="Automod Rule Updated",
          description=f"`Actions` {actions}\n"
                      f"`Creator` {rule.creator}\n"
                      f"`Enabled` {rule.enabled}\n"
                      f"`Exempt C.` {exempt_channels}\n"
                      f"`Exempt R.` {exempt_roles}\n"
                      f"`Name` {rule.name}\n"
                      f"`Trigger`\nAllow {rule.trigger.allow_list}\n"
                      f"Keyword Filter {rule.trigger.keyword_filter}\n"
                      f"Mention Limit {rule.trigger.mention_limit}\n"
                      f"Type {rule.trigger.type}",
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    self.logs.append(embed)
    self.db_logs.append((
              datetime.datetime.now(datetime.timezone.utc).timestamp(),
              "Automod Rule Updated",
              rule.creator.id,
              rule.name,
              f" A|{actions} || E|{rule.enabled} || EXC|{exempt_channels} || EXR|{exempt_roles} "
              f"|| T|Allow {rule.trigger.allow_list} || KF|{rule.trigger.keyword_filter} || "
              f"ML|{rule.trigger.mention_limit} || T|{rule.trigger.type}"
    ))
  
  @commands.Cog.listener()
  async def on_connect(self):
    embed = discord.Embed(
       title="Client Connected!", 
       description="Success! The client has been connected to the discord servers.",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=self.client.user.display_name, icon_url = self.client.user.avatar)
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Client Connected", 
          "988616371917180929", 
          "", 
          f""
    ))
  
  @commands.Cog.listener()
  async def on_shard_connect(self):
    embed = discord.Embed(
       title="Client Shard Connected!", 
       description="Success! The client shard has been connected.",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=self.client.user.display_name, icon_url = self.client.user.avatar)
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(),
          "Client Shard Connected", 
          "988616371917180929", 
          "", 
          f""
    ))
    
  @commands.Cog.listener()
  async def on_disconnect(self):
    embed = discord.Embed(
       title="Client Disconnected!", 
       description="*Note: If this was not initiated by a developer, but instead automatically, discord will automatically reconnect usually within a few minutes.*",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=self.client.user.display_name, icon_url = self.client.user.avatar)
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(),
          "Client Disconnected!", 
          "988616371917180929", 
          "", 
          f"*Note: If this was not initiated by a developer, but instead automatically, discord will automatically reconnect usually within a few minutes.*"
    ))
    
  @commands.Cog.listener()
  async def on_shard_disconnect(self):
    embed = discord.Embed(
       title="Client Shard Disonnected!", 
       description="*Note: This does not denote the bot going offline, but is instead just a state of a lost connection. Discord will automatically reconnect usually within a few minutes.*",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]),
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=self.client.user.display_name, icon_url = self.client.user.avatar)
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Client Shard Disconnected", 
          "988616371917180929", 
          "", 
          f"*Note: This does not denote the bot going offline, but is instead just a state of a lost connection. Discord will automatically reconnect usually within a few minutes.*"
    ))
    
  @commands.Cog.listener()
  async def on_message_edit(self, message_before, message_after):

      if message_before.author.bot or \
          any(s in message_before.content for s in ["https", "http"]) or \
          message_before.channel.id in [915687893811470405, 941111737225199696, 915687894172188722] or \
          len(message_after.content) > 1000 or len(message_before.content) > 1000:
          return

      channel = f"`Channel` {message_before.channel.mention}" if hasattr(message_before.channel, 'mention') else "`Channel` DMs"

      embed = discord.Embed(
          title="Message Edited",
          description=f"`Message author` {message_before.author} ({message_before.author.id})\n{channel}",
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
      )

      embed.add_field(name="Before", value=message_before.content, inline=False)
      embed.add_field(name="After", value=f"{message_after.content}\n\n[Jump to Message]({message_before.jump_url})", inline=False)
      embed.set_thumbnail(url=message_before.author.avatar)

      # ---- ADMIN ROUTING (author only) ----
      if self.is_admin(message_before):
          admin_channel = message_before.guild.get_channel(1190693196716576878)
          if admin_channel:
              await admin_channel.send(embed=embed)
      else:
          self.logs.append(embed)

      # DB log
      self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(),
          "Message Edit",
          message_before.author.id,
          f"{message_before.content} -> {message_after.content}",
          f"C|{message_before.channel.id} || J|{message_before.jump_url}"
      ))
  
  @commands.Cog.listener()
  async def on_message_delete(self, message):
      if message.author.bot:
          return

      # Fetch audit log entry
      entry = None
      try:
          async for ent in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
              entry = ent
      except:
          pass

      # Determine deleter
      if entry and entry.target.id == message.author.id:
          deleter = entry.user
      else:
          deleter = message.author

      channel = f"`Channel` {message.channel.mention}" if hasattr(message.channel, 'mention') else "`Channel` DMs"

      embed = discord.Embed(
          title="Message Deleted",
          description=(
              f"`Message author` {message.author} ({message.author.id})\n"
              f"{channel}\n"
              f"`Message` {message.content}\n"
              f"`Deleter` {deleter.mention} ({deleter.name})"
          ),
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
      )
      embed.set_thumbnail(url=message.author.avatar)

      # ---- ADMIN ROUTING RULE ----
      author_is_admin = self.is_admin(message)
      fake_message_for_deleter = type("FakeMsg", (), {"author": deleter, "guild": message.guild})
      deleter_is_admin = self.is_admin(fake_message_for_deleter)

      if author_is_admin or deleter_is_admin:
          admin_channel = message.guild.get_channel(1190693196716576878)
          if admin_channel:
              await admin_channel.send(embed=embed)
      else:
          self.logs.append(embed)

      # DB
      self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(),
          "Message Deleted",
          message.author.id,
          message.content,
          f"C|{message.channel.id}"
      ))

  @commands.Cog.listener()
  async def on_invite_create(self, invite):
    if invite.created_at is not None:
      created_at = invite.created_at.strftime('%a, %b %d, %Y, %I:%M %p')
    else:
      created_at = None

    embed = discord.Embed(
       title="Invite Created", 
       description= f"`Inviter` {invite.inviter.name}#{invite.inviter.discriminator} ({invite.inviter.id})\n"
                    f"`Invite` {invite}\n"
                    f"`Channel` {invite.channel.mention}\n"
                    f"`Max age` {invite.max_age}s\n"
                    f"`Max uses` {invite.max_uses}\n"
                    f"`Created at` {created_at} UTC\n"
                    f"`Temporary` {invite.temporary}\n"
                    f"`Revoked` {invite.revoked}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Invited Created", 
          invite.inviter.id, 
          str(invite), 
          f" C|{invite.channel.id} || MA|{invite.max_age} || MU|{invite.max_uses} || CA|{invite.created_at} UTC || T|{invite.temporary} || R{invite.revoked}"
    ))
  
  @commands.Cog.listener()
  async def on_invite_delete(self, invite):
    embed = discord.Embed(
       title="Invite Deleted", 
       description= f"`Invite` {invite}\n"
                    f"`Channel` {invite.channel.mention}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Invited Deleted", 
          "", 
          str(invite), 
          f" C|{invite.channel.id} || MA|{invite.max_age} || MU|{invite.max_uses} || CA|{invite.created_at} UTC || T|{invite.temporary} || R{invite.revoked}"
    ))
  
  @commands.Cog.listener()
  async def on_guild_channel_delete(self, channel):
    embed = discord.Embed(
       title="Channel Deleted", 
       description= f"`Channel` **#{channel.name}**\n"
                    f"`Type` {channel.type}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Channel Deleted", 
          "", 
          channel.id, 
          f" T|{channel.type}"
    ))

  @commands.Cog.listener()
  async def on_guild_channel_create(self, channel):
    embed = discord.Embed(
       title="Channel Created", 
       description= f"`Channel` {channel.mention}\n"
                    f"`Type` {channel.type}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    self.logs.append(embed)
    self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(), 
          "Channel Created", 
          "", 
          channel.id, 
          f" T|{channel.type}"
    ))

  @commands.Cog.listener()
  async def on_thread_create(self, thread):
    tag_names = [tag.name for tag in thread.applied_tags]
    tags = ", ".join(tag_names)
    desc  =  f"`Parent` {thread.parent.mention}\n`Thread` {thread.mention}\n`Tags` {tags}\n`Creator` {thread.owner.mention}\n" 
    if thread.starter_message:
       desc += thread.starter_message.content[:500]
    embed = discord.Embed(
      title = "Thread Created",
      description = desc,
      color = discord.Color.from_str(self.data["EMBED_COLOR"]),
      timestamp = datetime.datetime.now(datetime.timezone.utc)
    )
    self.logs.append(embed)

  @commands.Cog.listener()
  async def on_guild_channel_update(self, before, after):
    common_attributes = [
        ("name", "Channel Name"),
        ("topic", "Channel Topic"),
        ("category", "Channel Category"),
        ("slowmode_delay", "Channel Slowmode"),
        ("nsfw", "Channel NSFW"),
        ("permissions_synced", "Channel Permissions Synced")
    ]

    for attr, title in common_attributes:
      if type(before)==discord.VoiceChannel and attr=="topic":
        continue
      
      if getattr(before, attr) != getattr(after, attr):
        embed = discord.Embed(
            title=f"{title} Changed",
            description=f"`Channel` {before.mention}\n"
                        f"`Type` {before.type}\n"
                        f"`Before` {getattr(before, attr)}\n"
                        f"`After` {getattr(after, attr)}",
            color=discord.Color.from_str(self.data["EMBED_COLOR"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        self.db_logs.append((
            datetime.datetime.now(datetime.timezone.utc).timestamp(),
            f"{title} Changed",
            "",
            f"{getattr(before, attr)} -> {getattr(after, attr)}",
            f" T|{after.type} || ID|{after.id}"
        ))
        self.logs.append(embed)

  @commands.Cog.listener()
  async def on_member_update(self, before, after):
    # Check if the display name changed
    if before.display_name != after.display_name:
        embed = discord.Embed(
            title="Nickname changed",
            description=f"`Member` {before.mention} | {before.name}#{before.discriminator}\n"
                        f"`Before` {before.display_name}\n"
                        f"`After` {after.display_name}",
            color=discord.Color.from_str(self.data["EMBED_COLOR"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=before.avatar)

        self.logs.append(embed)
        self.db_logs.append((
            datetime.datetime.now(datetime.timezone.utc).timestamp(),
            "Nickname Changed",
            before.id,
            f"{before.display_name} -> {after.display_name}",
            f" TR|{before.top_role.name}"
        ))

    # Check if roles changed
    if before.roles != after.roles:
        msg = "Role Added/Removed"

        if len(before.roles) > len(after.roles):
            msg = "Role Removed"
            newrole = list((Counter(r.mention for r in before.roles) - Counter(r.mention for r in after.roles)).elements())

        elif len(after.roles) > len(before.roles):
            msg = "Role Added"
            newrole = list((Counter(r.mention for r in after.roles) - Counter(r.mention for r in before.roles)).elements())

        embed = discord.Embed(
            title="Roles Changed",
            description=f"`Member` {before.mention} | {before.name}#{before.discriminator}\n"
                        f"`{msg}` {newrole[0]}",
            color=discord.Color.from_str(self.data["EMBED_COLOR"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=before.avatar)

        self.logs.append(embed)
        self.db_logs.append((
            datetime.datetime.now(datetime.timezone.utc).timestamp(),
            msg,
            before.id,
            newrole[0],
            f" TR|{before.top_role.name}"
        ))

    # Check if guild permissions changed
    if before.guild_permissions != after.guild_permissions:

        differences = await self.find_difference(after, before.guild_permissions, after.guild_permissions)

        # If nothing found, exit
        if not differences:
            return

        # Normalize to list
        if isinstance(differences, str):
            differences = [differences]

        # Now safe to join
        differences_text = "\n".join(differences)

        embed = discord.Embed(
            title="Permissions Changed",
            description=f"`Member` {before.mention} | {before.name}#{before.discriminator}",
            color=discord.Color.from_str(self.data["EMBED_COLOR"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Changes", value=differences_text)
        embed.set_thumbnail(url=before.avatar)

        self.admin_logs.append(embed)
        self.db_logs.append((
            datetime.datetime.now(datetime.timezone.utc).timestamp(),
            "Permissions Changed",
            before.id,
            f"{before.guild_permissions} -> {after.guild_permissions}",
            f" TR|{before.top_role.name}"
        ))

  async def find_difference(self, member, permission_obj1, permission_obj2):
    differences = []
    for attr_name in dir(permission_obj1):
        if not callable(getattr(permission_obj1, attr_name)) and not attr_name.startswith("__"):
            value1 = getattr(permission_obj1, attr_name)
            value2 = getattr(permission_obj2, attr_name)
            if value1 != value2:
                if attr_name.title() == "Value":
                    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                        entry = entry
                    if value1 == 703687441843200 or value1 == 703687441843201:
                        return ['`Timeout`: True → False', f'`Staff` {entry.user.mention} ({entry.user.name})']
                    elif value2 == 703687441843200 or value2 == 703687441843201:
                        return ['`Timeout`: False → True', f'`Staff` {entry.user.mention} ({entry.user.name})', f'`Expires` <t:{int(float(member.timed_out_until.timestamp()))}:R>', f'`Reason` {entry.reason}']
                    else:
                       return None
                differences.append(f"`{attr_name.title()}`: {value1} → {value2}")
    return differences

  @commands.Cog.listener()
  async def on_guild_emojis_update(self, guild, before, after):
    if len(before) > len(after):
      msg = "Emoji Removed"
      newemoji = list((Counter(r.name for r in before) - Counter(r.name for r in after)).elements())
      newemojiid= list((Counter(r.id for r in before) - Counter(r.id for r in after)).elements())
      
    elif len(after) > len(before):
      msg = "Emoji Added"
      newemoji = list((Counter(r.name for r in after) - Counter(r.name for r in before)).elements())
      newemojiid = list((Counter(r.id for r in after) - Counter(r.id for r in before)).elements())
      
    embed = discord.Embed(
       title="Emojis Changed", 
       description=f"`{msg}` {newemoji[0]}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{newemojiid[0]}.webp?size=44&quality=lossless")
      
    self.logs.append(embed)
    self.db_logs.append((
       datetime.datetime.now(datetime.timezone.utc).timestamp(), 
       msg, 
       "", 
       f"{newemoji[0]} ({newemojiid[0]})", 
       f" URL|https://cdn.discordapp.com/emojis/{newemojiid[0]}.webp?size=44&quality=lossless"
    ))
  
  @commands.Cog.listener()
  async def on_voice_state_update(self, member, before, after):
    if before.channel == after.channel:
        return

    if before.channel is None:
        action = "Joined"
    elif after.channel is None:
        action = "Left"
    else:
        action = "Switched"

    embed = discord.Embed(
        title=f"Member {action} Voice",
        description=f"`Member` {member.mention} | {member.name}#{member.discriminator}\n"
                    f"`Channel left` {before.channel.mention if before.channel else 'N/A'}\n"
                    f"`Channel joined` {after.channel.mention if after.channel else 'N/A'}",
        color=discord.Color.from_str(self.data["EMBED_COLOR"]),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=member.avatar)

    self.logs.append(embed)
    self.db_logs.append((
        datetime.datetime.now(datetime.timezone.utc).timestamp(),
        f"Member {action} Voice",
        member.id,
        f"{before.channel.name} ({before.channel.id}) -> {after.channel.name} ({after.channel.id})" if action == "Switched" else f"{after.channel.name} ({after.channel.id})" if after.channel else f"{before.channel.name} ({before.channel.id})",
        ""
     ))

  @commands.Cog.listener()
  async def on_guild_channel_pins_update(self, channel, last_pin):
    embed = discord.Embed(
       title="Pinned Message Update", 
       description= f"`Channel` {channel.mention}\n"
                    f"`Pin` {last_pin}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((datetime.datetime.now(datetime.timezone.utc).timestamp(), "Pinned Message Updated", "", last_pin, f" C|{channel.id}"))
    
  @commands.Cog.listener()
  async def on_guild_role_create(self, role):
    perms = list(set(role.permissions))
    embed = discord.Embed(
       title="Role Created", 
       description= f"`Role` {role.mention} | {role.name}\n"
                    f"`Color` {role.color}\n"
                    f"`Created At` {role.created_at}\n"
                    f"`Permissions` {perms}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
       datetime.datetime.now(datetime.timezone.utc).timestamp(), 
       "Role Created", 
       "", 
       role.name, 
       f" C|{role.color} || CA|{role.created_at} || P|{perms}"
    ))
  
  @commands.Cog.listener()
  async def on_guild_role_delete(self, role):
    perms = list(set(role.permissions))
    embed = discord.Embed(
       title="Role Deleted", 
       description= f"`Role`{role.name}\n"
                    f"`Color` {role.color}\n"
                    f"`Created At` {role.created_at}\n"
                    f"`Permissions` {perms}", 
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
       datetime.datetime.now(datetime.timezone.utc).timestamp(), 
       "Role Deleted", 
       "", 
       role.name, 
       f" C|{role.color} || CA|{role.created_at} || P|{perms}"
    ))
  
  @commands.Cog.listener()
  async def on_integreation_create(self, integration):
    embed = discord.Embed(
       title="Integration Created", 
       description= f"`Account` {integration.account.name} ({integration.account.id})\n"
                    f"`Enabled` {integration.enabled}\n"
                    f"`Name` {integration.name}\n"
                    f"`Type` {integration.type}\n"
                    f"`User {integration.user.mention} ({integration.user.id})`",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
       datetime.datetime.now(datetime.timezone.utc).timestamp(), 
       "Integration Created", 
       integration.user.id, 
       integration.name, 
       f" AN|{integration.account.name} || AID|{integration.account.id}|| E|{integration.enabled} || T|{integration.type}"
    ))
  
  @commands.Cog.listener()
  async def on_integreation_update(self, integration):
    embed = discord.Embed(
       title="Integration Updated",  
       description= f"`Account` {integration.account.name} ({integration.account.id})\n"
                    f"`Enabled` {integration.enabled}\n"
                    f"`Name` {integration.name}\n"
                    f"`Type` {integration.type}\n"
                    f"`User {integration.user.mention} ({integration.user.id})`",
       color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
       timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    self.logs.append(embed)
    self.db_logs.append((
       datetime.datetime.now(datetime.timezone.utc).timestamp(), 
       "Integration Updated", 
       integration.user.id, 
       integration.name, 
       f" AN|{integration.account.name} || AID|{integration.account.id}|| E|{integration.enabled} || T|{integration.type}"
    ))
  
  @commands.Cog.listener()
  async def on_guild_role_update(self, before, after):
    attributes_to_check = ['color', 'hoist', 'mentionable', 'is_default', 'permissions']
    embed = None

    for attribute in attributes_to_check:
        before_value = getattr(before, attribute, None)
        after_value = getattr(after, attribute, None)

        if before_value != after_value:
            if attribute == 'permissions':
                diff = set(after_value).difference(set(before_value))

                for changed_perm in diff:
                    opp = not changed_perm[1]
                    embed = discord.Embed(
                        title="Role Permissions Updated",
                        description=f"`Role` {before.mention}\n"
                                    f"`Permission` {changed_perm[0]}\n"
                                    f"`Before` {opp}\n"
                                    f"`After` {changed_perm[1]}",
                        color=discord.Color.from_str(self.data["EMBED_COLOR"]),
                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                    )
                    self.db_logs.append((
                        datetime.datetime.now(datetime.timezone.utc).timestamp(),
                        "Role Permissions Updated",
                        "",
                        f"{opp} -> {changed_perm[1]}",
                        f" P|{changed_perm[0]}"
                    ))

            else:
                embed = discord.Embed(
                    title=f"Role {attribute.capitalize()} Updated",
                    description=f"`Role` {before.mention}\n"
                                f"`Before` {before_value}\n"
                                f"`After` {after_value}",
                    color=discord.Color.from_str(self.data["EMBED_COLOR"]),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                self.db_logs.append((
                    datetime.datetime.now(datetime.timezone.utc).timestamp(),
                    f"Role {attribute.capitalize()} Updated",
                    "",
                    f"{before_value} -> {after_value}",
                    f" RN|{before.name} || RI|{before.id}"
                ))

    if embed:
      self.logs.append(embed)
  
  @commands.Cog.listener()
  async def on_interaction(self, interaction: discord.Interaction):
    embed = None

    if interaction.type == discord.InteractionType.application_command:
      name = f"{interaction.command.name} "
          
      try:
        for option in interaction.data['options']:
          name += f"{option['name']}:{option['value']} "

      except KeyError:
        pass

      embed = discord.Embed(
          title="Slash Command Ran",
          description=f"`Command` /{name}\n"
                        f"`Author` {interaction.user.mention} ({interaction.user.id})\n"
                        f"`Channel` {interaction.channel.mention}\n"
                        f"`Success` {not interaction.command_failed}",
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
      )
      self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(),
          "Slash Command Ran",
          interaction.user.id,
          f"/{name}",
          f" C|{interaction.channel.id} || S|{not interaction.command_failed}"
      ))

    elif interaction.type == discord.InteractionType.component:
        embed = discord.Embed(
            title="Component Interaction",
            description=f"`User` {interaction.user.mention} ({interaction.user.id})\n"
                        f"`Channel` {interaction.channel.mention}\n \n"
                        f"[Jump to Message]({interaction.message.jump_url})",
            color=discord.Color.from_str(self.data["EMBED_COLOR"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        self.db_logs.append((
            datetime.datetime.now(datetime.timezone.utc).timestamp(),
            "Component Interaction",
            interaction.user.id,
            f"",
            f" C|{interaction.channel.id} || J|{interaction.message.jump_url}"
        ))

    elif interaction.type == discord.InteractionType.modal_submit:
      description = (f"`User` {interaction.user.mention} ({interaction.user.id})\n"
                    f"`Channel` {interaction.channel.mention}\n \n")
      try:
        description += f"[Jump to Message]({interaction.message.jump_url})"

      except:
        pass

      embed = discord.Embed(
          title="Modal Submitted",
          description=description,
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
          timestamp=datetime.datetime.now(datetime.timezone.utc)
      )
      self.db_logs.append((
          datetime.datetime.now(datetime.timezone.utc).timestamp(),
          "Modal Submitted",
          interaction.user.id,
          f"",
          f" C|{interaction.channel.id} || J|{interaction.message.jump_url}"
      ))

    if embed:
        self.logs.append(embed)

  @commands.Cog.listener()
  async def on_guild_stickers_update(self, guild, before, after):
    if len(before) > len(after):
      msg = "Sticker Removed"
      newemoji = list((Counter(r.name for r in before) - Counter(r.name for r in after)).elements())
      newemojiid= list((Counter(r.id for r in before) - Counter(r.id for r in after)).elements())
      
    elif len(after) > len(before):
      msg = "Sticker Added"
      newemoji = list((Counter(r.name for r in after) - Counter(r.name for r in before)).elements())
      newemojiid = list((Counter(r.id for r in after) - Counter(r.id for r in before)).elements())
      
    embed = discord.Embed(
      title="Stickers Updated", 
      description=f"`{msg}` {newemoji[0]}", 
      color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
      timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_thumbnail(url=f"https://media.discordapp.net/stickers/{newemojiid[0]}.webp?size=44&quality=lossless")
      
    self.logs.append(embed)
    self.db_logs.append((
      datetime.datetime.now(datetime.timezone.utc).timestamp(), 
      msg, 
      "", 
      f"{newemoji[0]} ({newemojiid[0]})", 
      f" URL|https://cdn.discordapp.com/emojis/{newemojiid[0]}.webp?size=44&quality=lossless"
    ))
   
  @commands.Cog.listener()
  async def on_guild_update(self, before, after):
    attributes_to_check = ["name", "afk_channel", "afk_timeout", "banner", "default_notifications", "description", "discovery_splash", "features", "icon", 
                           "premium_progress_bar_enabled", "premium_tier", "rules_channel", "safety_alerts_channel", "system_channel", "vanity_url", "verification_level",]

    for attribute in attributes_to_check:
      before_value = getattr(before, attribute)
      after_value = getattr(after, attribute)

      if before_value != after_value:
        embed_title = f"Guild {attribute.replace('_', ' ').capitalize()} Changed"
        embed_description = f"`Before` {before_value}\n`After` {after_value}"

        if "banner" in attribute or "icon" in attribute or "discovery_splash" in attribute:
          embed_description = f"[Before]({getattr(before, attribute).url})\n[After]({getattr(after, attribute).url})"
          thumbnail_url = getattr(after, attribute).url

        else:
          thumbnail_url = None

        embed = discord.Embed(
            title=embed_title, 
            description=embed_description, 
            color=discord.Color.from_str(self.data["EMBED_COLOR"]), 
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
            
        if thumbnail_url:
          embed.set_thumbnail(url=thumbnail_url)

        self.db_logs.append((
              datetime.datetime.now(datetime.timezone.utc).timestamp(), 
              f"Guild {attribute.replace('_', ' ').capitalize()} Changed", 
              "", 
              f"{before_value} -> {after_value}", "",
        ))
        self.logs.append(embed)
            
        break
    
async def setup(client:commands.Bot) -> None:
  await client.add_cog(Logs(client))