import discord
from discord import app_commands

import os

from discord.ext import tasks
import datetime
import html
from zoneinfo import ZoneInfo
import json
import asyncio

TOKEN = os.getenv("TOKEN")

CATEGORIA_ID = 1514756129513799724
CARGO_EQUIPE_ID = 1514762487831072819
BACKUP_CHANNEL_ID = 1514811262813339648
PROCURADOS_CHANNEL_ID = 1515040708971597894
HISTORICO_PROCURADOS_ID = 1515052449776533745
LOGS_CHANNEL_ID = 1515052409532055662

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
def limpar(texto):
    return html.escape(texto or "")

@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("America/Sao_Paulo")))
async def backup_diario():
    for guild in bot.guilds:
        data = datetime.datetime.now().strftime("%d-%m-%Y")
        nome_arquivo = f"backup-{guild.name}-{data}.html".replace(" ", "-")

        conteudo = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Backup {guild.name}</title>
            <style>
                body {{
                    background: #111;
                    color: #eee;
                    font-family: Arial;
                    padding: 20px;
                }}
                h1 {{
                    color: #4da3ff;
                }}
                .canal {{
                    color: #ffd166;
                    margin-top: 30px;
                    border-bottom: 1px solid #444;
                }}
                .msg {{
                    background: #1b1b1b;
                    border: 1px solid #333;
                    border-radius: 8px;
                    padding: 10px;
                    margin: 10px 0;
                }}
                .autor {{
                    color: #7dd3fc;
                    font-weight: bold;
                }}
                .data {{
                    color: #999;
                    font-size: 12px;
                }}
                .anexo {{
                    margin-top: 8px;
                }}
                img {{
                    max-width: 400px;
                    border-radius: 8px;
                    margin-top: 8px;
                }}
                a {{
                    color: #90ee90;
                }}
            </style>
        </head>
        <body>
        <h1>📦 Backup do servidor: {limpar(guild.name)}</h1>
        <h3>Data: {data}</h3>
        """

        for canal in guild.text_channels:
            conteudo += f"<h2 class='canal'># {limpar(canal.name)}</h2>"

            try:
                async for msg in canal.history(limit=500, oldest_first=True):
                    anexos_html = ""

                    for anexo in msg.attachments:
                        url = anexo.url
                        nome = limpar(anexo.filename)

                        if anexo.content_type and anexo.content_type.startswith("image/"):
                            anexos_html += f"""
                            <div class="anexo">
                                📷 <b>Imagem:</b> <a href="{url}">{nome}</a><br>
                                <img src="{url}">
                            </div>
                            """
                        else:
                            anexos_html += f"""
                            <div class="anexo">
                                📎 <b>Arquivo:</b> <a href="{url}">{nome}</a>
                            </div>
                            """

                    conteudo += f"""
                    <div class="msg">
                        <div class="autor">{limpar(str(msg.author))}</div>
                        <div class="data">{msg.created_at.strftime('%d/%m/%Y %H:%M')}</div>
                        <div>{limpar(msg.content)}</div>
                        {anexos_html}
                    </div>
                    """

            except Exception as e:
                conteudo += f"<p>❌ Erro ao salvar canal {limpar(canal.name)}: {limpar(str(e))}</p>"

        conteudo += """
        </body>
        </html>
        """

        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)

        canal_backup = bot.get_channel(BACKUP_CHANNEL_ID)

        if canal_backup:
            await canal_backup.send(
                content=f"📦 Backup diário completo de **{guild.name}**",
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
@tree.command(name="procurado", description="Cadastrar um procurado")
@app_commands.describe(
    nome="Nome do procurado",
    rg="RG do procurado",
    ultimo_avistamento="Último local visto",
    crimes="Crimes imputados",
    foto1="Primeira foto",
    foto2="Segunda foto opcional"
)
async def procurado(
    interaction: discord.Interaction,
    nome: str,
    rg: str,
    ultimo_avistamento: str,
    crimes: str,
    foto1: discord.Attachment,
    foto2: discord.Attachment = None
):
    canal = bot.get_channel(PROCURADOS_CHANNEL_ID)

    texto = f"""
🚨 **MANDADO DE PRISÃO E PROCURAÇÃO INVESTIGATIVA** 🚨

A Polícia DENARC de Capital Morada, por intermédio da **Divisão de Investigações Criminais (DIC)**, informa que o indivíduo abaixo encontra-se oficialmente procurado pelas autoridades competentes.

As investigações apontam seu envolvimento em atividades criminosas, havendo mandado ativo para sua localização, abordagem e condução para os procedimentos cabíveis.

📍 **ÚLTIMO AVISTAMENTO:** {ultimo_avistamento}

⚠️ **CRIMES IMPUTADOS:**
{crimes}

━━━━━━━━━━━━━━━━━━━━━━━

🆔 **IDENTIFICAÇÃO DO PROCURADO**

👤 **Nome:** {nome}  
🆔 **RG:** {rg}

━━━━━━━━━━━━━━━━━━━━━━━

📞 Qualquer informação sobre o paradeiro deste indivíduo deverá ser repassada imediatamente a um agente da DENARC ou da DIC.

🔒 O sigilo do denunciante será integralmente preservado.

🔹 Polícia DENARC de Capital Morada  
🔹 Divisão de Investigações Criminais (DIC)
"""

    arquivos = [await foto1.to_file()]

    if foto2:
        arquivos.append(await foto2.to_file())

    await canal.send(content=texto, files=arquivos)

    await interaction.response.send_message(
        "✅ Procurado cadastrado com sucesso.",
        ephemeral=True
    )
ARQUIVO_PROCURADOS = "procurados.json"

def carregar_procurados():
    if not os.path.exists(ARQUIVO_PROCURADOS):
        return []
    with open(ARQUIVO_PROCURADOS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_procurados(lista):
    with open(ARQUIVO_PROCURADOS, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

class ProcuradoModal(discord.ui.Modal, title="Cadastrar Procurado"):
    nome = discord.ui.TextInput(label="Nome do procurado", required=True)
    rg = discord.ui.TextInput(label="RG", required=True)
    ultimo = discord.ui.TextInput(label="Último avistamento", required=True)
    crimes = discord.ui.TextInput(label="Crimes imputados", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        categoria = guild.get_channel(CATEGORIA_ID)
        cargo = guild.get_role(CARGO_EQUIPE_ID)

        nome_canal = f"🚨-procurado-{self.nome.value}".replace(" ", "-").lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
            cargo: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True)
        }

        canal = await guild.create_text_channel(
            name=nome_canal,
            category=categoria,
            overwrites=overwrites
        )

        await canal.send(
            f"🚨 **Cadastro de Procurado**\n\n"
            f"👤 Nome: **{self.nome.value}**\n"
            f"🆔 RG: **{self.rg.value}**\n\n"
            f"📸 Envie até **2 fotos** neste canal.\n"
            f"Depois clique em **✅ Finalizar Cadastro**.",
            view=FinalizarProcuradoView(
                self.nome.value,
                self.rg.value,
                self.ultimo.value,
                self.crimes.value,
                interaction.user.id
            )
        )

        await interaction.response.send_message(
            f"✅ Canal criado: {canal.mention}",
            ephemeral=True
        )

class FinalizarProcuradoView(discord.ui.View):
    def __init__(self, nome, rg, ultimo, crimes, autor_id):
        super().__init__(timeout=None)
        self.nome = nome
        self.rg = rg
        self.ultimo = ultimo
        self.crimes = crimes
        self.autor_id = autor_id

    @discord.ui.button(label="Finalizar Cadastro", emoji="✅", style=discord.ButtonStyle.success)
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        anexos = []

        async for msg in interaction.channel.history(limit=50, oldest_first=True):
            if msg.author.bot:
                continue
            for anexo in msg.attachments:
                if len(anexos) < 2:
                    anexos.append(await anexo.to_file())

        canal_procurados = bot.get_channel(PROCURADOS_CHANNEL_ID)
        canal_logs = bot.get_channel(LOGS_CHANNEL_ID)

        texto = f"""
🚨 **MANDADO DE PRISÃO E PROCURAÇÃO INVESTIGATIVA** 🚨

A Polícia DENARC de Capital Morada, por intermédio da **Divisão de Investigações Criminais (DIC)**, informa que o indivíduo abaixo encontra-se oficialmente procurado pelas autoridades competentes.

As investigações apontam seu envolvimento em atividades criminosas, havendo mandado ativo para sua localização, abordagem e condução para os procedimentos cabíveis.

📍 **ÚLTIMO AVISTAMENTO:** {self.ultimo}

⚠️ **CRIMES IMPUTADOS:**
{self.crimes}

━━━━━━━━━━━━━━━━━━━━━━━

🆔 **IDENTIFICAÇÃO DO PROCURADO**

👤 **Nome:** {self.nome}
🆔 **RG:** {self.rg}

━━━━━━━━━━━━━━━━━━━━━━━

📞 Qualquer informação sobre o paradeiro deste indivíduo deverá ser repassada imediatamente a um agente da DENARC ou da DIC.

🔒 O sigilo do denunciante será integralmente preservado.

🔹 Polícia DENARC de Capital Morada
🔹 Divisão de Investigações Criminais (DIC)
"""

        mensagem = await canal_procurados.send(content=texto, files=anexos)

        lista = carregar_procurados()
        lista.append({
            "nome": self.nome,
            "rg": self.rg,
            "ultimo": self.ultimo,
            "crimes": self.crimes,
            "autor": interaction.user.name,
            "mensagem_id": mensagem.id
        })
        salvar_procurados(lista)

        if canal_logs:
            await canal_logs.send(
                f"👮 **Novo procurado cadastrado**\n"
                f"👤 Nome: {self.nome}\n"
                f"🆔 RG: {self.rg}\n"
                f"📌 Cadastrado por: {interaction.user.mention}"
            )

        await interaction.response.send_message("✅ Procurado publicado com sucesso.", ephemeral=True)

        await asyncio.sleep(10)
        await interaction.channel.delete()

class PainelProcuradosView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Novo Procurado", emoji="➕", style=discord.ButtonStyle.danger)
    async def novo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ProcuradoModal())

@tree.command(name="painelprocurados", description="Criar painel de procurados")
async def painelprocurados(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚨 Sistema de Procurados - DIC",
        description="Clique no botão abaixo para cadastrar um novo procurado.",
        color=0x8B0000
    )

    await interaction.response.send_message(embed=embed, view=PainelProcuradosView())

@tree.command(name="listarprocurados", description="Lista os procurados cadastrados")
async def listarprocurados(interaction: discord.Interaction):
    lista = carregar_procurados()

    if not lista:
        await interaction.response.send_message("📂 Nenhum procurado cadastrado.", ephemeral=True)
        return

    texto = "🔍 **Lista de Procurados**\n\n"

    for p in lista:
        texto += f"👤 **{p['nome']}** | RG: `{p['rg']}`\n"

    await interaction.response.send_message(texto, ephemeral=True)

@tree.command(name="retirarprocurado", description="Retira um procurado pelo RG")
@app_commands.describe(rg="RG do procurado")
async def retirarprocurado(interaction: discord.Interaction, rg: str):
    lista = carregar_procurados()
    procurado = None

    for p in lista:
        if p["rg"] == rg:
            procurado = p
            break

    if procurado is None:
        await interaction.response.send_message("❌ Procurado não encontrado.", ephemeral=True)
        return

    lista.remove(procurado)
    salvar_procurados(lista)

    historico = bot.get_channel(HISTORICO_PROCURADOS_ID)
    logs = bot.get_channel(LOGS_CHANNEL_ID)

    if historico:
        await historico.send(
            f"📂 **Procurado removido do sistema**\n\n"
            f"👤 Nome: {procurado['nome']}\n"
            f"🆔 RG: {procurado['rg']}\n"
            f"⚠️ Crimes: {procurado['crimes']}"
        )

    if logs:
        await logs.send(
            f"❌ **Procurado retirado**\n"
            f"👤 Nome: {procurado['nome']}\n"
            f"🆔 RG: {procurado['rg']}\n"
            f"👮 Retirado por: {interaction.user.mention}"
        )

    await interaction.response.send_message(
        f"✅ Procurado **{procurado['nome']}** removido com sucesso.",
        ephemeral=True
    )
bot.run(TOKEN)
