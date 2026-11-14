import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sklad Bot is online 24/7!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Sklad Bot je online jako {bot.user}")

@bot.command()
async def sklad(ctx):
    embed = discord.Embed(
        title="📦 HLAVNÍ SKLAD",
        description="Aktuální stav položek v obecném skladu.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Zbraně & Munice", value="Skladem: Dostatek", inline=False)
    embed.add_field(name="Materiál", value="Skladem: Standardní zásoby", inline=False)
    embed.set_footer(text="General Warehouse System")
    await ctx.send(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))
