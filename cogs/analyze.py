from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord
import json
import io
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
    
    def format_results(self, query_name: str, results: list) -> str:
        """Format results based on query type"""
        
        # Queries that should show numbered rankings with user mentions
        ranking_queries = [
            "Top Ticket Count (30d)",
            "Top Ticket Count (All Time)",
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

async def setup(client: commands.Bot):
    await client.add_cog(Analyze(client))
