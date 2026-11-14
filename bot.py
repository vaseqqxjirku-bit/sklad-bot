import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

# --- HTTP SERVER PRO RENDER & UPTIMEROBOT (24/7 BĚH) ---
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
# -------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def create_sklad_embed(items_dict: dict, history_list: list):
    embed = discord.Embed(
        title="📦 SPRÁVA SKLADU & ODPISY",
        color=discord.Color.gold()
    )
    if items_dict:
        items_text = "\n".join([f"**{item}:** `{qty}`" for item, qty in sorted(items_dict.items())])
    else:
        items_text = "*Sklad je prázdný*"
    embed.add_field(name="📊 Aktuální stav skladu", value=items_text, inline=False)
    
    if history_list:
        history_text = "\n".join(history_list[-5:])  # Zobrazí posledních 5 pohybů
    else:
        history_text = "*Zatím žádné pohyby*"
    embed.add_field(name="📜 Poslední pohyby / odpisy", value=history_text, inline=False)
    embed.set_footer(text="Skladový evidenční systém")
    return embed

class SkladModal(discord.ui.Modal):
    def __init__(self, action_type: str):
        title_text = "Vložit / Vrátit na sklad" if action_type == "add" else "Vyzvednout / Odepsat"
        super().__init__(title=title_text)
        self.action_type = action_type  # "add" nebo "remove"
        
        self.item_input = discord.ui.TextInput(
            label="Název položky (např. Meth, Peníze)",
            style=discord.TextStyle.short,
            placeholder="Napiš název položky...",
            required=True,
            max_length=50
        )
        self.amount_input = discord.ui.TextInput(
            label="Množství (číslo)",
            style=discord.TextStyle.short,
            placeholder="Např. 5 nebo 3316",
            required=True,
            max_length=20
        )
        self.reason_input = discord.ui.TextInput(
            label="Důvod / Poznámka",
            style=discord.TextStyle.short,
            placeholder="Např. Odpis, nákup...",
            required=True,
            max_length=100
        )
        self.add_item(self.item_input)
        self.add_item(self.amount_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Kontrola množství
            qty_val = self.amount_input.value.strip()
            qty = int(qty_val)
            if qty <= 0:
                await interaction.response.send_message("❌ Množství musí být větší než 0!", ephemeral=True)
                return

            item_name = self.item_input.value.strip()
            reason = self.reason_input.value.strip()
            user_name = interaction.user.display_name

            if not interaction.message or not interaction.message.embeds:
                await interaction.response.send_message("❌ Nelze načíst zprávu skladu. Napiš prosím nový příkaz `!sklad`.", ephemeral=True)
                return

            embed = interaction.message.embeds[0]
            items_dict = {}
            history_list = []

            # Bezpečné načtení stavu z embedu
            for field in embed.fields:
                if "Aktuální stav skladu" in field.name and field.value != "*Sklad je prázdný*":
                    for line in field.value.split("\n"):
                        if "**" in line and ":" in line:
                            parts = line.split(":", 1)
                            name = parts[0].replace("*", "").strip()
                            try:
                                q = int(parts[1].replace("`", "").strip())
                                items_dict[name] = q
                            except ValueError:
                                pass
                elif "Poslední pohyby" in field.name and field.value != "*Zatím žádné pohyby*":
                    history_list = field.value.split("\n")

            # Výpočet nového množství
            current_qty = items_dict.get(item_name, 0)
            if self.action_type == "add":
                items_dict[item_name] = current_qty + qty
                sign_str = f"+{qty}"
                action_desc = "přidal / vrátil"
            else:
                items_dict[item_name] = current_qty - qty
                sign_str = f"-{qty}"
                action_desc = "odebral / odepsal"

            # Přidání záznamu do historie
            log_entry = f"• **{user_name}** {action_desc}: `{sign_str} {item_name}` (*{reason}*)"
            history_list.append(log_entry)

            # Aktualizace panelu
            new_embed = create_sklad_embed(items_dict, history_list)
            await interaction.response.edit_message(embed=new_embed, view=SkladView())

            # Veřejná zpráva s mazáním po 5 minutách
            alert_msg = await interaction.channel.send(
                content=f"📦 **POHYB NA SKLADĚ**\nUživatel {interaction.user.mention} **{action_desc}**: `{sign_str} {item_name}` (Aktuálně na skladě: `{items_dict[item_name]}`)\n**Důvod:** *{reason}*\n*(Zpráva se za 5 minut sama smaže)*"
            )
            await asyncio.sleep(300)
            try:
                await alert_msg.delete()
            except discord.HTTPException:
                pass

        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Nastala chyba při zpracování: `{e}`", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Nastala chyba při zpracování: `{e}`", ephemeral=True)

class SkladView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vložit / Vrátit", style=discord.ButtonStyle.success, emoji="➕", custom_id="sklad_add_btn")
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SkladModal(action_type="add"))

    @discord.ui.button(label="Vyzvednout / Odepsat", style=discord.ButtonStyle.danger, emoji="➖", custom_id="sklad_remove_btn")
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SkladModal(action_type="remove"))

@bot.event
async def on_ready():
    bot.add_view(SkladView())
    print(f"Bot je online jako {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def sklad(ctx):
    await ctx.message.delete()
    embed = create_sklad_embed({}, [])
    await ctx.send(embed=embed, view=SkladView())

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
