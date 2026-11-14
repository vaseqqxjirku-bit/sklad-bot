import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def create_sklad_embed(items_dict: dict, history_list: list):
    embed = discord.Embed(
        title="📦 SPRÁVA SKLADU & ODPISY",
        color=discord.Color.gold()
    )
    
    if items_dict:
        items_text = "\n".join([f"**{item}:** `{qty}`" for item, qty in items_dict.items()])
    else:
        items_text = "*Sklad je prázdný*"
    embed.add_field(name="Aktuální stav skladu", value=items_text, inline=False)
    
    if history_list:
        history_text = "\n".join(history_list[-5:])  # Zobrazí posledních 5 pohybů
    else:
        history_text = "*Zatím žádné pohyby*"
    embed.add_field(name="📜 Poslední pohyby / odpisy", value=history_text, inline=False)
    
    embed.set_footer(text="Skladový evidenční systém")
    return embed

class SkladModal(discord.ui.Modal):
    def __init__(self, action_type: str):
        super().__init__(title="Skladová operace")
        self.action_type = action_type  # "add" nebo "remove"
        
        self.item_input = discord.ui.TextInput(
            label="Předmět (např. Meth, Špinavé peníze)",
            style=discord.TextStyle.short,
            placeholder="Meth / Špinavé peníze...",
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
            placeholder="Např. Přidání od dealera, odpis...",
            required=True,
            max_length=100
        )
        
        self.add_item(self.item_input)
        self.add_item(self.amount_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.amount_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Množství musí být platné číslo!", ephemeral=True)
            return

        item_name = self.item_input.value.strip()
        reason = self.reason_input.value.strip()
        user_name = interaction.user.display_name

        embed = interaction.message.embeds[0]
        items_dict = {}
        history_list = []
        
        # Načtení aktuálního stavu z embedu
        for field in embed.fields:
            if field.name == "Aktuální stav skladu" and field.value != "*Sklad je prázdný*":
                lines = field.value.split("\n")
                for line in lines:
                    if "**" in line and ":" in line:
                        parts = line.split(":")
                        name = parts[0].replace("*", "").strip()
                        try:
                            q = int(parts[1].replace("`", "").strip())
                            items_dict[name] = q
                        except ValueError:
                            pass
            elif field.name == "📜 Poslední pohyby / odpisy" and field.value != "*Zatím žádné pohyby*":
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

        # Aktualizace hlavního panelu
        new_embed = create_sklad_embed(items_dict, history_list)
        await interaction.response.edit_message(embed=new_embed, view=SkladView())

        # Veřejná zpráva s upozorněním, která se za 5 minut sama smaže
        alert_msg = await interaction.channel.send(
            content=f"📦 **POHYB NA SKLADĚ**\nUživatel {interaction.user.mention} **{action_desc}**: `{sign_str} {item_name}`\n**Důvod:** *{reason}*\n*(Zpráva se za 5 minut sama smaže)*"
        )
        await asyncio.sleep(300)
        try:
            await alert_msg.delete()
        except discord.HTTPException:
            pass

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
    initial_items = {"Meth": 0, "Špinavé peníze": 0}
    embed = create_sklad_embed(initial_items, [])
    await ctx.send(embed=embed, view=SkladView())

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
