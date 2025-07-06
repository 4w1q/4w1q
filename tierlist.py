import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from discord.utils import get

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "tierlist.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@client.event
async def on_ready():
    await client.tree.sync()
    print(f"✅ Bot giriş yaptı: {client.user}")

# ————— Tier komutları —————

@client.tree.command(name="tier_add", description="Kullanıcıyı tier'a ekle ve rol ver.")
@app_commands.describe(user="Kullanıcı", role="Verilecek rol")
async def tier_add(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    data = load_data()
    gid = str(interaction.guild_id)
    rid = str(role.id)
    data.setdefault(gid, {}).setdefault(rid, [])
    if str(user.id) in data[gid][rid]:
        return await interaction.response.send_message(f"{user.mention} zaten `{role.name}` tier'ında.", ephemeral=True)
    data[gid][rid].append(str(user.id))
    save_data(data)
    await user.add_roles(role)
    await interaction.response.send_message(f"{user.mention} `{role.name}` tier'ına eklendi ve rol verildi.")

@client.tree.command(name="tier_remove", description="Kullanıcıyı tier'dan çıkar ve rolünü al.")
@app_commands.describe(user="Kullanıcı", role="Silinecek rol")
async def tier_remove(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    data = load_data()
    gid = str(interaction.guild_id)
    rid = str(role.id)
    if gid not in data or rid not in data[gid] or str(user.id) not in data[gid][rid]:
        return await interaction.response.send_message(f"{user.mention} `{role.name}` tier'ında bulunamadı.", ephemeral=True)
    data[gid][rid].remove(str(user.id))
    save_data(data)
    if role in user.roles:
        await user.remove_roles(role)
        msg = f"`{role.name}` rolü kaldırıldı."
    else:
        msg = f"`{role.name}` kullanıcıda yoktu."
    await interaction.response.send_message(f"{user.mention} `{role.name}` tier'ından çıkarıldı. {msg}")

@client.tree.command(name="tier_show", description="Tüm tier listesini gösterir.")
async def tier_show(interaction: discord.Interaction):
    data = load_data()
    gid = str(interaction.guild_id)
    if gid not in data or not data[gid]:
        return await interaction.response.send_message("Sunucuda kayıtlı tier verisi yok.", ephemeral=True)
    embed = discord.Embed(title="📊 Tier Listesi", color=discord.Color.blurple())
    for rid, uids in data[gid].items():
        role = interaction.guild.get_role(int(rid))
        if not role:
            continue
        mentions = []
        for u in uids:
            m = interaction.guild.get_member(int(u))
            mentions.append(m.mention if m else f"`{u}`")
        embed.add_field(name=role.name, value=", ".join(mentions) if mentions else "-", inline=False)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="tierver", description="Tier sonucu embed mesaj olarak gönderir.")
@app_commands.describe(
    kullanıcı_adı="Başlıkta gözükür",
    kit="Test edilecek kit adı",
    kullanıcı="Oyuncu (etiketle)",
    tester="Tester (etiketle)",
    oyuncu_ismi="Oyun içi isim",
    yeni_tier="Yeni Tier (rol etiketle)",
    eski_tier="Eski Tier (rol etiketle)",
    sonuç="Maç skoru (örn: 2-1)",
    sunucu="Sunucu adı",
    kazanan="Kazanan kullanıcı (etiketle)",
    kanal="Mesajın gideceği kanal"
)
async def tierver(
    interaction: discord.Interaction,
    kullanıcı_adı: str,
    kit: str,
    kullanıcı: discord.Member,
    tester: discord.Member,
    oyuncu_ismi: str,
    yeni_tier: discord.Role,
    eski_tier: discord.Role,
    sonuç: str,
    sunucu: str,
    kazanan: discord.Member,
    kanal: discord.TextChannel
):
    if not any(r.name.lower() == "tester" for r in interaction.user.roles):
        return await interaction.response.send_message("❌ Bu komutu sadece `Tester` rolü kullanabilir.", ephemeral=True)
    if yeni_tier not in kullanıcı.roles:
        await kullanıcı.add_roles(yeni_tier)
    title = f"🏆 {kullanıcı_adı} {kit} Test Sonuçları:"
    embed = discord.Embed(title=title, color=discord.Color.orange())
    embed.add_field(name="Discord:", value=kullanıcı.mention, inline=True)
    embed.add_field(name="Tester:", value=tester.mention, inline=True)
    embed.add_field(name="Oyun içi isim:", value=oyuncu_ismi, inline=False)
    embed.add_field(name="Yeni Tier:", value=yeni_tier.mention, inline=True)
    embed.add_field(name="Eski Tier:", value=eski_tier.mention, inline=True)
    embed.add_field(name="Sonuçlar:", value=sonuç, inline=False)
    embed.add_field(name="Sunucu:", value=sunucu, inline=False)
    embed.add_field(name="Kazanan:", value=f"{kazanan.mention} / {oyuncu_ismi}", inline=False)
    await kanal.send(embed=embed)
    await interaction.response.send_message("✅ Rapor gönderildi ve rol verildi.", ephemeral=True)

# ————— Ticket Panel ve Close —————

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _create_ticket(self, interaction: discord.Interaction, kit_name: str):
        category = get(interaction.guild.categories, name=kit_name)
        if not category:
            return await interaction.response.send_message(f"❌ `{kit_name}` kategorisi bulunamadı!", ephemeral=True)

        name = f"ticket-{interaction.user.name.lower()}-{kit_name.lower()}"
        if get(interaction.guild.channels, name=name):
            return await interaction.response.send_message("❌ Zaten açık bir ticketın var!", ephemeral=True)

        tester_role = get(interaction.guild.roles, name="Tester")
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user:                 discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me:             discord.PermissionOverwrite(view_channel=True)
        }
        if tester_role:
            overwrites[tester_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_chan = await interaction.guild.create_text_channel(
            name=name, category=category, overwrites=overwrites, reason=f"{kit_name} ticket açıldı"
        )

        # Embed formu (boş alanlı)
        form = discord.Embed(title="Formu doldur", color=discord.Color.dark_gold())
        form.add_field(name="Kullanıcı Adı:", value="\u200b", inline=False)
        form.add_field(name="Sunucu:",      value="\u200b", inline=False)
        form.add_field(name="Eski Tier:",   value="\u200b", inline=False)
        await ticket_chan.send(embed=form)

        await interaction.response.send_message(f"🎫 Ticket oluşturuldu: {ticket_chan.mention}", ephemeral=True)

    @discord.ui.button(label="Smp",    style=discord.ButtonStyle.green,  custom_id="ticket_smp")
    async def smp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Smp")

    @discord.ui.button(label="Beast",  style=discord.ButtonStyle.blurple, custom_id="ticket_beast")
    async def beast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Beast")

    @discord.ui.button(label="Nethpot", style=discord.ButtonStyle.red,   custom_id="ticket_nethpot")
    async def nethpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Nethpot")

    @discord.ui.button(label="Gapple", style=discord.ButtonStyle.green, custom_id="ticket_gapple")
    async def gapple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Gapple")

    @discord.ui.button(label="Diapot", style=discord.ButtonStyle.blurple, custom_id="ticket_diapot")
    async def diapot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Diapot")

    @discord.ui.button(label="Crystal", style=discord.ButtonStyle.blurple, custom_id="ticket_crystal")
    async def crystal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Crystal")

    @discord.ui.button(label="Axe",    style=discord.ButtonStyle.red, custom_id="ticket_axe")
    async def axe(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Axe")

    @discord.ui.button(label="Elytra", style=discord.ButtonStyle.green, custom_id="ticket_elytra")
    async def elytra(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Elytra")

@client.tree.command(name="panel", description="Ticket panelini bu kanala kurar.")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="1.9+ Türk Minecraft Tierlist",
        description="Hangi kitte test olmak istiyorsanız aşağıdaki butona tıklayın",
        color=discord.Color.dark_gold()
    )
    await interaction.response.send_message(embed=embed, view=TicketPanel())

@panel.error
async def panel_error(interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Yönetici izni gerekiyor.", ephemeral=True)

@client.tree.command(name="ticket_close", description="Aktif ticket kanalını kapatır.")
@app_commands.describe(ticket="Kapatılacak ticket kanalı (etiketle)")
async def ticket_close(interaction: discord.Interaction, ticket: discord.TextChannel):
    if not any(r.name.lower() == "tester" for r in interaction.user.roles):
        return await interaction.response.send_message("❌ Yalnızca Tester rolü kullanabilir.", ephemeral=True)
    if not ticket.name.startswith("ticket-"):
        return await interaction.response.send_message("❌ Bu bir ticket kanalı değil.", ephemeral=True)
    await ticket.delete(reason=f"Ticket kapatıldı: {interaction.user}")
    await interaction.response.send_message(f"✅ {ticket.name} kapatıldı.", ephemeral=True)

# ——— BOTU BAŞLAT ———
if __name__ == "__main__":
    token = os.getenv("TOKEN")      # Ortam değişkenine TOKEN=... ekle
    if not token:
        raise RuntimeError("TOKEN ortam değişkeni tanımlı değil!")
    client.run(token)
