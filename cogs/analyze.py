from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord
import json
import io
import re
from datetime import datetime, timezone
from core.database import execute
from core.loggers import log_commands

with open("assets/config.json", "r") as file:
    data = json.load(file)

class Analyze(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
        # Define all SQL queries
        self.queries = {
            "Average Tickets per Day": """
                SELECT AVG(ticket_count_per_day) AS avg_tickets_per_day
                FROM (
                    SELECT 
                        DATE(FROM_UNIXTIME(CAST(opened_at AS UNSIGNED))) AS ticket_date,
                        COUNT(*) AS ticket_count_per_day
                    FROM tickets
                    GROUP BY ticket_date
                ) AS daily_counts;
            """,
            "Top Ticket Count (30d)": """
                SELECT owner_id, COUNT(*) AS ticket_count
                FROM tickets
                WHERE FROM_UNIXTIME(CAST(opened_at AS UNSIGNED)) >= NOW() - INTERVAL 30 DAY
                GROUP BY owner_id
                ORDER BY ticket_count DESC
                LIMIT 20;
            """,
            "Top Ticket Count (All Time)": """
                SELECT owner_id, COUNT(*) AS ticket_count
                FROM tickets
                GROUP BY owner_id
                ORDER BY ticket_count DESC
                LIMIT 20;
            """,
            "Top Tickets Closed (All Time)": """
                SELECT closed_by_id AS owner_id, COUNT(*) AS ticket_count
                FROM tickets
                WHERE closed_at IS NOT NULL
                    AND closed_at != '00000000'
                    AND closed_by_id IS NOT NULL
                GROUP BY closed_by_id
                ORDER BY ticket_count DESC
                LIMIT 20;
            """,
            "Most Tickets/Day": """
                SELECT owner_id, DATE(FROM_UNIXTIME(CAST(opened_at AS UNSIGNED))) AS ticket_date, COUNT(*) AS ticket_count
                FROM tickets
                WHERE owner_id != '837793755838939157' AND owner_id != '220576008372355072'
                GROUP BY owner_id, ticket_date
                ORDER BY ticket_count DESC
                LIMIT 10;
            """,
            "Longest Opened Tickets": """
                SELECT 
                    *,
                    TIMESTAMPDIFF(
                        SECOND, 
                        FROM_UNIXTIME(opened_at), 
                        FROM_UNIXTIME(closed_at)
                    ) AS ticket_duration
                FROM 
                    tickets
                WHERE 
                    closed_at IS NOT NULL 
                    AND closed_at != '00000000'
                ORDER BY 
                    ticket_duration DESC
                LIMIT 5;
            """,
            "Duplicates": """
                SELECT user_id, COUNT(*) FROM staff_statistics GROUP BY user_id HAVING COUNT(*) > 1
            """,
            "Longest Gap No Ticket": """
                WITH Diff AS (
                    SELECT
                        channel_id,
                        opened_at,
                        LAG(channel_id) OVER (ORDER BY opened_at) AS prev_channel_id,
                        LAG(opened_at) OVER (ORDER BY opened_at) AS prev_opened_at
                    FROM tickets
                    WHERE opened_at <> 0
                ),
                MaxGap AS (
                    SELECT
                        channel_id,
                        opened_at,
                        prev_channel_id,
                        prev_opened_at,
                        opened_at - prev_opened_at AS gap
                    FROM Diff
                    WHERE prev_opened_at IS NOT NULL
                    ORDER BY gap DESC
                    LIMIT 1
                )
                SELECT
                    channel_id AS current_channel_id,
                    opened_at AS current_opened_at,
                    prev_channel_id AS previous_channel_id,
                    prev_opened_at AS previous_opened_at,
                    gap AS max_gap
                FROM MaxGap;
            """,
            "Average Time B/n Tickets": """
                WITH Diff AS (
                    SELECT
                        opened_at,
                        LAG(opened_at) OVER (ORDER BY opened_at) AS prev_opened_at
                    FROM tickets
                    WHERE opened_at <> 0
                )
                SELECT
                    AVG(opened_at - prev_opened_at) AS avg_time_between_tickets
                FROM Diff
                WHERE prev_opened_at IS NOT NULL;
            """
        }
    
    @app_commands.command(name="analyze", description="Run predefined SQL analysis queries on ticket data")
    # @app_commands.checks.has_any_role(*ConfigManager.get("ADMIN_ROLES"))
    @app_commands.describe(query="Select which analysis to run")
    async def analyze(
        self, 
        interaction: discord.Interaction, 
        query: Literal[
            "Average Tickets per Day",
            "Top Ticket Count (30d)",
            "Top Ticket Count (All Time)",
            "Top Tickets Closed (All Time)",
            "Most Tickets/Day",
            "Longest Opened Tickets",
            "Duplicates",
            "Longest Gap No Ticket",
            "Average Time B/n Tickets"
        ]
    ):
        await interaction.response.defer(thinking=True)
        
        try:
            # Get the SQL query for the selected analysis
            sql_query = self.queries[query]
            
            # Execute the query
            results = await execute(sql_query)
            
            if not results:
                await interaction.followup.send("No results found for this query.")
                return
            
            # Format results based on query type
            if query == "Top Tickets Closed (All Time)":
                formatted_output = await self.format_closed_ticket_ranking(
                    results, interaction.guild
                )
            else:
                formatted_output = self.format_results(query, results)
            
            # Generate CSV for download
            csv_content = self.generate_csv(results)
            
            # Create a file object
            csv_file = discord.File(
                fp=io.BytesIO(csv_content.encode('utf-8')),
                filename=f"{query.replace(' ', '_').replace('/', '-')}.csv"
            )
            
            # Send formatted output and CSV
            if len(formatted_output) > 2000:
                # If output is too long, send as file
                text_file = discord.File(
                    fp=io.BytesIO(formatted_output.encode('utf-8')),
                    filename=f"{query.replace(' ', '_').replace('/', '-')}.txt"
                )
                await interaction.followup.send(
                    content=f"**Analysis Results: {query}**\n*Output too long, see attached files.*",
                    files=[text_file, csv_file]
                )
            else:
                await interaction.followup.send(
                    content=f"**Analysis Results: {query}**\n{formatted_output}",
                    file=csv_file
                )
                
        except Exception as e:
            await interaction.followup.send(f"Error executing query: {str(e)}")
            log_commands.error(f"/analyze error {e}")

    @app_commands.command(
        name="poll-analyze",
        description="Analyze the server members who reacted to a message",
    )
    @app_commands.describe(message_link="The Discord link to the poll message")
    async def poll_analyze(self, interaction: discord.Interaction, message_link: str):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command can only be used in a server channel.", ephemeral=True
            )
            return

        await interaction.response.defer()

        link_match = re.fullmatch(
            r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/"
            r"(?P<guild_id>\d+)/(?P<channel_id>\d+)/(?P<message_id>\d+)/?",
            message_link.strip(),
        )
        if link_match is None:
            await interaction.followup.send(
                "Please provide a valid Discord message link.", ephemeral=True
            )
            return

        guild_id = int(link_match["guild_id"])
        channel_id = int(link_match["channel_id"])
        message_id = int(link_match["message_id"])
        if guild_id != interaction.guild.id:
            await interaction.followup.send(
                "That message belongs to a different server.", ephemeral=True
            )
            return

        try:
            channel = interaction.guild.get_channel(channel_id)
            if channel is None:
                channel = await interaction.guild.fetch_channel(channel_id)
            if not isinstance(channel, discord.abc.Messageable):
                raise TypeError("linked channel cannot contain messages")
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            await interaction.followup.send(
                "I could not find or access that linked message.", ephemeral=True
            )
            return
        except discord.HTTPException as error:
            log_commands.error("Unable to fetch poll message %s: %s", message_link, error)
            await interaction.followup.send(
                "Discord could not fetch that message right now.", ephemeral=True
            )
            return
        except TypeError:
            await interaction.followup.send(
                "That link does not point to a message channel.", ephemeral=True
            )
            return

        reaction_voters: dict[str, set[int]] = {}
        for reaction in message.reactions:
            reaction_name = str(reaction.emoji)
            reaction_voters.setdefault(reaction_name, set())
            async for user in reaction.users():
                if not user.bot:
                    reaction_voters[reaction_name].add(user.id)

        voter_ids = set().union(*reaction_voters.values()) if reaction_voters else set()
        members_by_id: dict[int, discord.Member | None] = {}
        for user_id in voter_ids:
            member = interaction.guild.get_member(user_id)
            if member is None:
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except (discord.NotFound, discord.HTTPException) as error:
                    log_commands.warning(
                        "Unable to resolve poll voter %s in guild %s: %s",
                        user_id,
                        interaction.guild.id,
                        error,
                    )
            members_by_id[user_id] = member

        voter_ids_list = sorted(voter_ids)
        ticket_counts = await self._poll_ticket_counts(voter_ids_list)
        total_voters = len(voter_ids_list)

        ticket_thresholds = (1, 5, 10, 20, 30, 50, 100)
        server_thresholds = (1, 7, 30, 60, 90, 180, 365)
        server_days_by_id = {
            user_id: (
                (datetime.now(timezone.utc) - member.joined_at).total_seconds() / 86400
                if member is not None and member.joined_at is not None
                else 0
            )
            for user_id, member in members_by_id.items()
        }
        ticket_lines = self._poll_metric_lines(
            "tickets", ticket_thresholds, list(ticket_counts.values()), total_voters
        )
        server_lines = self._poll_metric_lines(
            "days",
            server_thresholds,
            list(server_days_by_id.values()),
            total_voters,
        )
        outcome_embeds = [
            self._poll_outcome_embed(
                title="Poll outcomes by ticket count",
                unit="ticket",
                thresholds=ticket_thresholds,
                reaction_voters=reaction_voters,
                values_by_id=ticket_counts,
            ),
            self._poll_outcome_embed(
                title="Poll outcomes by time in server",
                unit="day",
                thresholds=server_thresholds,
                reaction_voters=reaction_voters,
                values_by_id=server_days_by_id,
            ),
        ]

        view = PollAnalysisView(
            message=message,
            voter_ids=voter_ids_list,
            ticket_lines=ticket_lines,
            server_lines=server_lines,
            total_voters=total_voters,
        )
        await interaction.followup.send(view=view)
        await interaction.followup.send(embeds=outcome_embeds)

    async def _poll_ticket_counts(self, voter_ids: list[int]) -> dict[int, int]:
        if not voter_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(voter_ids))
        rows = await execute(
            f"""
                SELECT owner_id, COUNT(*) AS ticket_count
                FROM tickets
                WHERE owner_id IN ({placeholders})
                GROUP BY owner_id
            """,
            tuple(voter_ids),
        )
        counts_by_user = {int(row["owner_id"]): int(row["ticket_count"]) for row in rows}
        return {user_id: counts_by_user.get(user_id, 0) for user_id in voter_ids}

    @staticmethod
    def _poll_outcome_embed(
        *,
        title: str,
        unit: str,
        thresholds: tuple[int, ...],
        reaction_voters: dict[str, set[int]],
        values_by_id: dict[int, int | float],
    ) -> discord.Embed:
        singular_unit = unit
        plural_unit = f"{unit}s"
        embed = discord.Embed(title=title, color=discord.Color.gold())

        for threshold in thresholds:
            eligible_by_reaction = {
                reaction_name: sum(
                    values_by_id.get(user_id, 0) >= threshold for user_id in voter_ids
                )
                for reaction_name, voter_ids in reaction_voters.items()
            }
            highest_count = max(eligible_by_reaction.values(), default=0)
            winners = [
                reaction_name
                for reaction_name, count in eligible_by_reaction.items()
                if count == highest_count and highest_count > 0
            ]
            if not winners:
                winner_text = "Winner: **No eligible voters**"
            elif len(winners) == 1:
                winner_text = f"Winner: **{winners[0]}**"
            else:
                winner_text = f"Tie: **{'**, **'.join(winners)}**"

            option_lines = []
            for reaction_name, voter_ids in reaction_voters.items():
                count = eligible_by_reaction[reaction_name]
                percentage = count / len(voter_ids) * 100 if voter_ids else 0
                option_lines.append(
                    f"{reaction_name} `{count}` ({percentage:.1f}% of option voters)"
                )
            threshold_unit = singular_unit if threshold == 1 else plural_unit
            embed.add_field(
                name=f"At least {threshold} {threshold_unit}",
                value=f"{winner_text}\n" + "\n".join(option_lines),
                inline=False,
            )

        embed.set_footer(text="Winners are determined by the highest eligible voter count.")
        return embed

    @staticmethod
    def _poll_metric_lines(
        unit: str, thresholds: tuple[int, ...], values: list[int | float], total: int
    ) -> list[str]:
        lines = []
        for threshold in thresholds:
            count = sum(value >= threshold for value in values)
            percentage = count / total * 100 if total else 0
            singular_unit = unit[:-1] if unit.endswith("s") else unit
            display_unit = singular_unit if threshold == 1 else unit
            lines.append(
                f"**At least {threshold} {display_unit}** — `{count}` ({percentage:.1f}%)"
            )
        return lines
    
    def format_results(self, query_name: str, results: list) -> str:
        """Format results based on query type"""
        
        # Queries that should show numbered rankings with user mentions
        ranking_queries = [
            "Top Ticket Count (30d)",
            "Top Ticket Count (All Time)",
            "Top Tickets Closed (All Time)",
            "Most Tickets/Day"
        ]
        
        if query_name in ranking_queries:
            return self.format_ranking(query_name, results)
        elif query_name == "Average Tickets per Day":
            return self.format_average_tickets(results)
        elif query_name == "Longest Opened Tickets":
            return self.format_longest_tickets(results)
        elif query_name == "Duplicates":
            return self.format_duplicates(results)
        elif query_name == "Longest Gap No Ticket":
            return self.format_longest_gap(results)
        elif query_name == "Average Time B/n Tickets":
            return self.format_average_time(results)
        else:
            return self.format_generic(results)
    
    def format_ranking(self, query_name: str, results: list) -> str:
        """Format ranking queries with numbered list and user mentions"""
        output = []
        
        for idx, row in enumerate(results, 1):
            user_id = row.get('owner_id', '')
            ticket_count = row.get('ticket_count', 0)
            
            # Format with user mention
            user_mention = f"<@{user_id}>"
            
            if query_name == "Most Tickets/Day":
                ticket_date = row.get('ticket_date', 'N/A')
                output.append(f"**{idx}.** {user_mention} - **{ticket_count}** tickets on `{ticket_date}`")
            else:
                output.append(f"**{idx}.** {user_mention} - **{ticket_count}** tickets")
        
        return "\n".join(output)

    async def format_closed_ticket_ranking(
        self, results: list, guild: discord.Guild | None
    ) -> str:
        """Format all-time closed-ticket rankings with display names and IDs."""
        output = []

        for idx, row in enumerate(results, 1):
            user_id = str(row.get("owner_id", ""))
            ticket_count = row.get("ticket_count", 0)
            display_name = "Unknown User"

            try:
                member = guild.get_member(int(user_id)) if guild else None
                user = member or self.client.get_user(int(user_id))
                if user is None:
                    user = await self.client.fetch_user(int(user_id))
                display_name = user.display_name
            except (ValueError, discord.HTTPException, discord.NotFound) as error:
                log_commands.warning(
                    "Unable to resolve display name for user %s: %s", user_id, error
                )

            output.append(
                f"**{idx}.** {display_name} (`{user_id}`) - **{ticket_count}** tickets"
            )

        return "\n".join(output)
    
    def format_average_tickets(self, results: list) -> str:
        """Format average tickets per day"""
        avg = results[0].get('avg_tickets_per_day', 0)
        return f"```\nAverage Tickets per Day: {avg:.2f}\n```"
    
    def format_longest_tickets(self, results: list) -> str:
        """Format longest opened tickets"""
        output = []
        
        for idx, row in enumerate(results, 1):
            channel_id = row.get('channel_id', 'N/A')
            owner_id = row.get('owner_id', 'N/A')
            duration = row.get('ticket_duration', 0)
            
            # Convert duration to readable format
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            
            duration_str = f"{hours}h {minutes}m {seconds}s"
            
            output.append(f"**{idx}.** Channel: `{channel_id}` | Owner: <@{owner_id}> | Duration: `{duration_str}`")
        
        return "\n".join(output)
    
    def format_duplicates(self, results: list) -> str:
        """Format duplicate user IDs in statistics"""
        output = []
        
        for idx, row in enumerate(results, 1):
            user_id = row.get('user_id', 'N/A')
            count = row.get('COUNT(*)', 0)
            output.append(f"**{idx}.** <@{user_id}> - **{count}** duplicates")
        
        return "\n".join(output)
    
    def format_longest_gap(self, results: list) -> str:
        """Format longest gap without ticket"""
        row = results[0]
        current_channel = row.get('current_channel_id', 'N/A')
        current_opened = row.get('current_opened_at', 'N/A')
        prev_channel = row.get('previous_channel_id', 'N/A')
        prev_opened = row.get('previous_opened_at', 'N/A')
        max_gap = row.get('max_gap', 0)
        
        # Convert gap to readable format
        days = max_gap // 86400
        hours = (max_gap % 86400) // 3600
        minutes = (max_gap % 3600) // 60
        
        gap_str = f"{days}d {hours}h {minutes}m"
        
        output = f"""**Longest Gap Without Ticket:**
• Previous Ticket: Channel `{prev_channel}` (Opened: <t:{prev_opened}:F>)
• Current Ticket: Channel `{current_channel}` (Opened: <t:{current_opened}:F>)
• Gap Duration: `{gap_str}` ({max_gap} seconds)"""
        
        return output
    
    def format_average_time(self, results: list) -> str:
        """Format average time between tickets"""
        avg_time = results[0].get('avg_time_between_tickets', 0)
        
        if avg_time:
            # Convert to readable format
            days = int(avg_time // 86400)
            hours = int((avg_time % 86400) // 3600)
            minutes = int((avg_time % 3600) // 60)
            seconds = int(avg_time % 60)
            
            time_str = f"{days}d {hours}h {minutes}m {seconds}s"
            return f"```\nAverage Time Between Tickets: {time_str} ({avg_time:.2f} seconds)\n```"
        else:
            return "```\nAverage Time Between Tickets: N/A\n```"
    
    def format_generic(self, results: list) -> str:
        """Generic formatting for any query"""
        output = []
        for idx, row in enumerate(results, 1):
            row_str = " | ".join([f"{key}: {value}" for key, value in row.items()])
            output.append(f"{idx}. {row_str}")
        
        return "```\n" + "\n".join(output) + "\n```"
    
    def generate_csv(self, results: list) -> str:
        """Generate CSV content from results"""
        if not results:
            return ""
        
        # Get headers from first row
        headers = list(results[0].keys())
        csv_lines = [",".join(headers)]
        
        # Add data rows
        for row in results:
            values = [str(row.get(header, '')) for header in headers]
            csv_lines.append(",".join(values))
        
        return "\n".join(csv_lines)


class PollAnalysisView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        message: discord.Message,
        voter_ids: list[int],
        ticket_lines: list[str],
        server_lines: list[str],
        total_voters: int,
    ):
        super().__init__(timeout=900)
        self.message = message
        self.voter_ids = voter_ids

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## Poll analysis\n"
                f"Message [jump link]({message.jump_url})\n"
                f"**{total_voters}** player(s) voted by reacting."
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay("### Ticket count\n" + "\n".join(ticket_lines)),
            discord.ui.Separator(),
            discord.ui.TextDisplay("### Time in server\n" + "\n".join(server_lines)),
        )
        container.accent_color = discord.Color.gold()
        self.add_item(container)

        row = discord.ui.ActionRow()
        row.add_item(
            discord.ui.Button(
                label="View players",
                style=discord.ButtonStyle.primary,
                custom_id=f"poll-analysis:players:{message.id}",
            )
        )
        row.children[0].callback = self.show_players
        self.add_item(row)

    async def show_players(self, interaction: discord.Interaction) -> None:
        mentions = [f"<@{user_id}>" for user_id in self.voter_ids]
        description = "\n".join(mentions) or "No players reacted to this message."
        embed = discord.Embed(
            title="Poll players",
            description=description[:4096],
            color=discord.Color.gold(),
        )
        if len(description) > 4096:
            embed.set_footer(text=f"Showing the first {len(description[:4096].splitlines())} players.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(client: commands.Bot):
    await client.add_cog(Analyze(client))
