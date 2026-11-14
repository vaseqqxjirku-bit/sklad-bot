import os
import threading
import unicodedata
import ast
import operator
import re
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

def normalize_name(name: str) -> str:
    """Sjednotí název (odstraní diakritiku, mezery, malá písmena)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", name)
        if unicodedata.category(c) != "Mn"
    ).lower().strip()

# Kalkulačka pro políčka ve formuláři (můžeš zadat i příklad)
operator_map = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}

def parse_calc(expr_str: str) -> int:
    expr_str = expr_str.strip().replace(" ", "").replace(",", ".")
    if not expr_str:
        return 0
    try:
        node = ast.parse(expr_str, mode='eval')
        def _eval(n):
            if isinstance(n, ast.Constant):
                if isinstance(n.value, (int, float)):
                    return n.value
                raise TypeError()
            elif isinstance(n, ast.BinOp):
                if type(n.op) in operator_map:
                    return operator_map[type(n.op)](_eval(n.left), _eval(n.right))
                raise TypeError()
            elif isinstance(n, ast.UnaryOp):
                if type(n.op) in operator_map:
                    return operator_map[type(n.op)](_eval(n.operand))
                raise TypeError()
            else:
                raise TypeError()
        return int(round(_eval(node.body)))
    except Exception:
        return int(float(expr_str))

def create_sklad_embed(items_dict: dict, history_list: list):
    embed = discord.Embed(
        title="📦 SPRÁVA SKLADU & ODPISY",
        color=discord.Color.gold()
    )
    
    if items_dict:
        items_text = "\n".join([f"**{item}:** `{qty} ks`" for item, qty in sorted(items_dict.items())])
    else:
        items_text = "*Sklad je prázdný*"
    embed.add_field(name="📊 Aktuální stav skladu", value=items_text, inline=False)
    
    if history_list:
        history_text = "\n".join(history_list[-5:])
    else:
        history_text = "*Zatím žádné pohyby*"
    embed.add_field(name="📜 Poslední pohyby / odpisy", value=history_text, inline=False)
    
    embed.set_footer(text="Skladový evidenční systém")
    return embed

class SkladModal(discord.ui.Modal):
    def __init__(self, action_type: str):
        title_text = "Vložit / Vrátit na sklad" if action_type == "add" else "Vyzvednout / Odepsat"
        super().__init__(title=title_text)
        self.action_type = action_type
        
        self.item_input = discord.ui.TextInput(
            label="Název položky (např. Meth, Guny)",
            style=discord.TextStyle.short,
            placeholder="Napiš název položky...",
            required=True,
            max_length=50
        )
        self.amount_input = discord.ui.TextInput(
            label="Množství (kusy)",
            style=discord.TextStyle.short,
            placeholder="Např. 10 nebo 30-22",
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
            qty = parse_calc(self.amount_input.value)
            
            if qty <= 0:
                await interaction.response.send_message("❌ Množství musí být větší než 0!", ephemeral=True)
                return

            item_name = self.item_input.value.strip()
            item_key = normalize_name(item_name)
            reason = self.reason_input.value.strip()
            user_name = interaction.user.display_name

            if not interaction.message or not interaction.message.embeds:
                await interaction.response.send_message("❌ Nelze načíst zprávu skladu. Napiš nový příkaz `!sklad`.", ephemeral=True)
                return

            embed = interaction.message.embeds[0]
            items_dict = {}
            items_map = {}
            history_list = []
            
            # Načtení aktuálního stavu z embedu
            for field in embed.fields:
                if "Aktuální stav skladu" in field.name and field.value != "*Sklad je prázdný*":
                    for line in field.value.split("\n"):
                        if "**" in line and ":" in line:
                            parts = line.split(":", 1)
                            orig_name = parts[0].replace("*", "").strip()
                            raw_val_str = parts[1]
                            
                            match = re.search(r'(-?\d+)', raw_val_str)
                            if match:
                                try:
                                    q = int(match.group(1))
                                    norm_key = normalize_name(orig_name)
                                    items_dict[orig_name] = q
                                    items_map[norm_key] = orig_name
                                except ValueError:
                                    pass
                elif "Poslední pohyby" in field.name and field.value != "*Zatím žádné pohyby*":
                    history_list = field.value.split("\n")

            real_item_name = items_map.get(item_key, item_name)
            current_qty = items_dict.get(real_item_name, 0)
            
            # MATEMATIKA: Přičítání / Odečítání
            if self.action_type == "add":
                new_qty = current_qty + qty
                sign_str = f"+{qty}"
                action_desc = "přidal / vrátil"
            else:
                new_qty = current_qty - qty
                sign_str = f"-{qty}"
                action_desc = "odebral / odepsal"

            items_dict[real_item_name] = new_qty

            log_entry = f"• **{user_name}** {action_desc}: `{sign_str} {real_item_name}` (*{reason}*)"
            history_list.append(log_entry)

            new_embed = create_sklad_embed(items_dict, history_list)
            
            # Okamžitá a tichá aktualizace panelu bez pingu v chatu
            await interaction.response.edit_message(embed=new_embed, view=SkladView())

        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Nastala chyba: `{e}`", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Nastala chyba: `{e}`", ephemeral=True)

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
    print(f"Sklad Bot je online jako {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def sklad(ctx):
    await ctx.message.delete()
    embed = create_sklad_embed({}, [])
    await ctx.send(embed=embed, view=SkladView())

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
