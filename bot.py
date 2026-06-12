import discord
from discord import app_commands

import os

from discord.ext import tasks
import datetime
import html
from zoneinfo import ZoneInfo

TOKEN = os.getenv("TOKEN")

CATEGORIA_ID = 1514756129513799724
CARGO_EQUIPE_ID = 1514762487831072819
BACKUP_CHANNEL_ID = 1514811262813339648

TOPICOS = [
    "📋 Painel",
    "👑 Fotos líderes",
    "👥 Fotos dos membros",
    "📻 Rádio",
    "📍 Localização",
    "🚔 Crimes da comunidade",
    "📦 Baú de líder",
    "📦 Baú de membros",
    "🌿 Rota de farm",
    "🏭 Rota de produção",
    "🧪 Ingredientes base e produtos",
    "🕵️ Informante",
    "💬 Chat"
]

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

class FecharMesaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Mesa",
        emoji="🔒",
        style=discord.ButtonStyle.danger
    )
    async def fechar_mesa(self, interaction: discord.Interaction, button: discord.ui.Button):
        canal = interaction.channel

        await canal.edit(name=f"🔒-{canal.name}")

        await canal.send("🔒 **Mesa encerrada com sucesso.**")

        await interaction.response.send_message(
            "✅ Mesa fechada.",
            ephemeral=True
        )

async def criar_mesa(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    categoria = guild.get_channel(CATEGORIA_ID)
    cargo_equipe = guild.get_role(CARGO_EQUIPE_ID)

    nome_canal = f"🕵️‍♂️-{interaction.user.display_name}".replace(" ", "-").lower()
    canal = discord.utils.get(guild.text_channels, name=nome_canal)

    if canal:
        await interaction.followup.send(
            f"⚠️ Você já possui uma mesa: {canal.mention}",
            ephemeral=True
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True
        ),
        cargo_equipe: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True
        )
    }

    canal = await guild.create_text_channel(
        name=nome_canal,
        category=categoria,
        overwrites=overwrites
    )

    await canal.send(
        f"📂 **Mesa criada para:** {interaction.user.mention}\n\n"
        f"Utilize os tópicos abaixo para enviar fotos, documentos e informações.",
        view=FecharMesaView()
    )

    for topico in TOPICOS:
        thread = await canal.create_thread(
            name=topico,
            type=discord.ChannelType.public_thread
        )

        await thread.send(
            f"📌 **{topico}**\n\n"
            f"Envie aqui fotos, documentos, textos e informações deste tópico."
        )

    await interaction.followup.send(
        f"✅ Mesa criada com sucesso: {canal.mention}",
        ephemeral=True
    )

class CriarMesaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Criar Mesa",
        emoji="🕵️‍♂️",
        style=discord.ButtonStyle.primary
    )
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_mesa(interaction)
def limpar(texto):
    return html.escape(texto or "")

@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("America/Sao_Paulo")))
async def backup_diario():
    for guild in bot.guilds:
        data = datetime.datetime.now().strftime("%d-%m-%Y")
        nome_arquivo = f"backup-{guild.name}-{data}.html".replace(" ", "-")

        conteudo = f"<html><body><h1>Backup {guild.name} - {data}</h1>"

        for canal in guild.text_channels:
            conteudo += f"<h2>#{limpar(canal.name)}</h2>"

            try:
                async for msg in canal.history(limit=500, oldest_first=True):
                    conteudo += f"<p><b>{limpar(str(msg.author))}</b>: {limpar(msg.content)}</p>"
            except:
                pass

        conteudo += "</body></html>"

        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)

        canal_backup = bot.get_channel(BACKUP_CHANNEL_ID)

        if canal_backup:
            await canal_backup.send(
                content=f"📦 Backup diário de {guild.name}",
                file=discord.File(nome_arquivo)
            )

        os.remove(nome_arquivo)

@bot.event
async def on_ready():
    await tree.sync()

    if not backup_diario.is_running():
        backup_diario.start()

    print(f"Bot online como {bot.user}")
    print("Comandos sincronizados!")
    print("Backup diário ativado!")

@tree.command(name="painel", description="Painel de criação de mesas")
async def painel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📂 Central de Mesas Investigativas",
        description=(
            "Seja bem-vindo à **central de criação de mesas da DIC**.\n\n"
            "Caso deseje iniciar uma investigação, clique no botão abaixo.\n\n"
            "🕵️‍♂️ **Criar Mesa** — Cria uma mesa privada contendo todos os tópicos necessários.\n\n"
            "Todas as informações enviadas ficarão registradas para análise da equipe."
        ),
        color=0x2b2d31
    )

    await interaction.response.send_message(
        embed=embed,
        view=CriarMesaView()
    )

bot.run(TOKEN)
