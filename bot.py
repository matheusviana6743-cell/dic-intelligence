import discord
from discord import app_commands
from discord.ext import tasks

import os
import json
import html
import asyncio
import datetime
import re
import unicodedata
from zoneinfo import ZoneInfo


TOKEN = os.getenv("TOKEN")

# =========================
# IDS
# =========================

CARGOS_EQUIPE_IDS = [
    1490200382776021132,  # Delegado
    1490200383614615725,  # Vice-Diretor
    1490200390426165290,  # Investigadores
    1490200388912156692,  # Inspetor
    1490200384818647051   # Delegado Denarc
]

BACKUP_CHANNEL_ID = 1514811262813339648

PROCURADOS_CHANNEL_ID = 1515040708971597894
HISTORICO_PROCURADOS_ID = 1515052449776533745
LOGS_CHANNEL_ID = 1515052409532055662

CATEGORIA_MESAS_ABERTAS_ID = 1515079970722938920
CATEGORIA_MESAS_FECHADAS_ID = 1515052497025372160

ARQUIVO_PROCURADOS = "procurados.json"


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
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

views_adicionadas = False


# =========================
# FUNÇÕES BÁSICAS
# =========================

def limpar(texto):
    return html.escape(str(texto or ""))


def nome_seguro(texto):
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9 -]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip()

    if not texto:
        texto = "Sem Nome"

    return texto[:45]


def carregar_procurados():
    if not os.path.exists(ARQUIVO_PROCURADOS):
        return []

    try:
        with open(ARQUIVO_PROCURADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def salvar_procurados(lista):
    with open(ARQUIVO_PROCURADOS, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)


def obter_cargos_equipe(guild):
    cargos = []

    for cargo_id in CARGOS_EQUIPE_IDS:
        cargo = guild.get_role(cargo_id)

        if cargo:
            cargos.append(cargo)

    return cargos


async def enviar_log(titulo, descricao):
    canal = bot.get_channel(LOGS_CHANNEL_ID)

    if canal:
        embed = discord.Embed(
            title=f"👮 {titulo}",
            description=descricao,
            color=0x2B2D31
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

        await canal.send(embed=embed)


# =========================
# SISTEMA DE MESAS
# =========================

class FecharMesaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Mesa",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="fechar_mesa_button"
    )
    async def fechar_mesa(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            canal = interaction.channel
            guild = interaction.guild
            categoria_fechadas = guild.get_channel(CATEGORIA_MESAS_FECHADAS_ID)

            if categoria_fechadas is None:
                await interaction.followup.send(
                    "❌ Categoria de mesas fechadas não encontrada.",
                    ephemeral=True
                )
                await enviar_log(
                    "Erro ao Fechar Mesa",
                    f"❌ Categoria de mesas fechadas não encontrada.\n"
                    f"ID: `{CATEGORIA_MESAS_FECHADAS_ID}`"
                )
                return

            novo_nome = canal.name

            if not novo_nome.startswith("🔒"):
                novo_nome = f"🔒 ┃{novo_nome}"

            await canal.edit(
                name=novo_nome,
                category=categoria_fechadas
            )

            await canal.send("🔒 **Mesa encerrada e movida para a categoria de mesas fechadas.**")

            await enviar_log(
                "Mesa Fechada",
                f"👤 Fechada por: {interaction.user.mention}\n"
                f"📁 Canal: {canal.mention}\n"
                f"📂 Movida para categoria: `{CATEGORIA_MESAS_FECHADAS_ID}`\n"
                f"⚠️ Nenhuma mensagem antiga foi apagada."
            )

            await interaction.followup.send(
                "✅ Mesa fechada e movida para a categoria correta.",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao fechar mesa: `{e}`",
                ephemeral=True
            )

            await enviar_log(
                "Erro ao Fechar Mesa",
                f"👤 Usuário: {interaction.user.mention}\n"
                f"⚠️ Erro: `{e}`"
            )


class CriarMesaModal(discord.ui.Modal, title="Criar Mesa Investigativa"):
    nome_familia = discord.ui.TextInput(
        label="Nome da família / investigação",
        placeholder="Exemplo: Elements, Fazenda, Olimpo...",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await criar_mesa(interaction, self.nome_familia.value)


class CriarMesaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Criar Mesa",
        emoji="🕵️‍♂️",
        style=discord.ButtonStyle.primary,
        custom_id="criar_mesa_button"
    )
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CriarMesaModal())


async def criar_mesa(interaction: discord.Interaction, nome_familia: str):
    await interaction.response.defer(ephemeral=True)

    try:
        guild = interaction.guild

        categoria_abertas = guild.get_channel(CATEGORIA_MESAS_ABERTAS_ID)
        cargos_equipe = obter_cargos_equipe(guild)

        if categoria_abertas is None:
            await interaction.followup.send(
                "❌ Erro: categoria de mesas abertas não encontrada.",
                ephemeral=True
            )
            await enviar_log(
                "Erro ao Criar Mesa",
                f"❌ Categoria de mesas abertas não encontrada.\n"
                f"ID usado: `{CATEGORIA_MESAS_ABERTAS_ID}`"
            )
            return

        if not cargos_equipe:
            await interaction.followup.send(
                "❌ Erro: nenhum cargo da equipe foi encontrado.",
                ephemeral=True
            )
            await enviar_log(
                "Erro ao Criar Mesa",
                "❌ Nenhum cargo da equipe foi encontrado."
            )
            return

        apelido = nome_seguro(interaction.user.display_name)
        familia = nome_seguro(nome_familia)

        nome_canal = f"🕵️‍♂️ ┃{apelido} • {familia}"

        canal_existente = discord.utils.get(
            guild.text_channels,
            name=nome_canal
        )

        if canal_existente:
            await interaction.followup.send(
                f"⚠️ Essa mesa já existe: {canal_existente.mention}",
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
            )
        }

        for cargo in cargos_equipe:
            overwrites[cargo] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            )

        canal = await guild.create_text_channel(
            name=nome_canal,
            category=categoria_abertas,
            overwrites=overwrites
        )

        await canal.send(
            f"📂 **Mesa criada para:** {interaction.user.mention}\n"
            f"🕵️‍♂️ **Investigação/Família:** `{nome_familia}`\n\n"
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

        cargos_texto = "\n".join([f"• {cargo.mention}" for cargo in cargos_equipe])

        await enviar_log(
            "Mesa Criada",
            f"👤 Usuário: {interaction.user.mention}\n"
            f"🕵️‍♂️ Investigação/Família: `{nome_familia}`\n"
            f"📂 Mesa: {canal.mention}\n"
            f"📁 Categoria: `{CATEGORIA_MESAS_ABERTAS_ID}`\n\n"
            f"👥 Cargos com acesso:\n{cargos_texto}"
        )

        await interaction.followup.send(
            f"✅ Mesa criada com sucesso: {canal.mention}",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao criar mesa: `{e}`",
            ephemeral=True
        )

        await enviar_log(
            "Erro ao Criar Mesa",
            f"👤 Usuário: {interaction.user.mention}\n"
            f"⚠️ Erro: `{e}`"
        )


# =========================
# BACKUP
# =========================

async def executar_backup(manual=False, usuario=None):
    for guild in bot.guilds:
        data = datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d-%m-%Y_%H-%M")
        nome_arquivo = f"backup-{guild.name}-{data}.html".replace(" ", "-")

        conteudo = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Backup {limpar(guild.name)}</title>
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

            for thread in canal.threads:
                conteudo += f"<h3 class='canal'>🧵 {limpar(thread.name)}</h3>"

                try:
                    async for msg in thread.history(limit=500, oldest_first=True):
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
                    conteudo += f"<p>❌ Erro ao salvar tópico {limpar(thread.name)}: {limpar(str(e))}</p>"

        conteudo += """
        </body>
        </html>
        """

        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)

        canal_backup = bot.get_channel(BACKUP_CHANNEL_ID)

        if canal_backup:
            await canal_backup.send(
                content=f"📦 Backup {'manual' if manual else 'diário'} completo de **{guild.name}**",
                file=discord.File(nome_arquivo)
            )

        await enviar_log(
            "Backup Executado",
            f"📦 Servidor: `{guild.name}`\n"
            f"🕒 Tipo: {'Manual' if manual else 'Automático'}\n"
            f"👤 Executado por: {usuario.mention if usuario else 'Sistema automático'}"
        )

        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)


@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("America/Sao_Paulo")))
async def backup_diario():
    await executar_backup(manual=False)


# =========================
# SISTEMA DE PROCURADOS
# =========================

class ProcuradoModal(discord.ui.Modal, title="Cadastrar Procurado"):
    nome = discord.ui.TextInput(label="Nome do procurado", required=True)
    rg = discord.ui.TextInput(label="RG", required=True)
    ultimo = discord.ui.TextInput(label="Último avistamento", required=True)
    crimes = discord.ui.TextInput(
        label="Crimes imputados",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            categoria = guild.get_channel(CATEGORIA_MESAS_ABERTAS_ID)
            cargos_equipe = obter_cargos_equipe(guild)

            if categoria is None:
                await interaction.followup.send(
                    "❌ Categoria para canal provisório não encontrada.",
                    ephemeral=True
                )
                return

            if not cargos_equipe:
                await interaction.followup.send(
                    "❌ Nenhum cargo da equipe foi encontrado.",
                    ephemeral=True
                )
                return

            nome_canal = f"procurado-{nome_seguro(self.nome.value)}"

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True
                )
            }

            for cargo in cargos_equipe:
                overwrites[cargo] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True
                )

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
                f"Depois clique em **✅ Finalizar Cadastro**.\n\n"
                f"⚠️ Este canal é provisório e será apagado após finalizar ou cancelar.",
                view=FinalizarProcuradoView(
                    self.nome.value,
                    self.rg.value,
                    self.ultimo.value,
                    self.crimes.value,
                    interaction.user.id
                )
            )

            await enviar_log(
                "Canal Provisório de Procurado Criado",
                f"👤 Responsável: {interaction.user.mention}\n"
                f"🚨 Procurado: `{self.nome.value}`\n"
                f"🆔 RG: `{self.rg.value}`\n"
                f"📂 Canal provisório: {canal.mention}\n"
                f"🗑️ Será apagado após finalizar ou cancelar."
            )

            await interaction.followup.send(
                f"✅ Canal provisório criado para anexar fotos: {canal.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao criar canal provisório: `{e}`",
                ephemeral=True
            )

            await enviar_log(
                "Erro ao Criar Canal Provisório",
                f"👤 Usuário: {interaction.user.mention}\n"
                f"⚠️ Erro: `{e}`"
            )


class FinalizarProcuradoView(discord.ui.View):
    def __init__(self, nome, rg, ultimo, crimes, autor_id):
        super().__init__(timeout=None)
        self.nome = nome
        self.rg = rg
        self.ultimo = ultimo
        self.crimes = crimes
        self.autor_id = autor_id

    @discord.ui.button(
        label="Finalizar Cadastro",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            anexos = []

            async for msg in interaction.channel.history(limit=50, oldest_first=True):
                if msg.author.bot:
                    continue

                for anexo in msg.attachments:
                    if len(anexos) < 2:
                        anexos.append(await anexo.to_file())

            canal_procurados = bot.get_channel(PROCURADOS_CHANNEL_ID)

            if canal_procurados is None:
                await interaction.followup.send(
                    "❌ Canal de procurados não encontrado.",
                    ephemeral=True
                )
                return

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
                "autor_id": interaction.user.id,
                "mensagem_id": mensagem.id,
                "canal_id": PROCURADOS_CHANNEL_ID,
                "status": "ativo"
            })
            salvar_procurados(lista)

            await enviar_log(
                "Procurado Cadastrado",
                f"👤 Nome: `{self.nome}`\n"
                f"🆔 RG: `{self.rg}`\n"
                f"👮 Responsável: {interaction.user.mention}\n"
                f"📸 Fotos anexadas: `{len(anexos)}`\n"
                f"📌 Mensagem: {mensagem.jump_url}\n"
                f"🗑️ Canal provisório apagado após finalizar."
            )

            await interaction.followup.send(
                "✅ Procurado publicado. O canal provisório será apagado em 10 segundos.",
                ephemeral=True
            )

            await asyncio.sleep(10)

            try:
                await interaction.channel.delete()
            except Exception as e:
                await enviar_log(
                    "Erro ao Apagar Canal Provisório",
                    f"📂 Canal: {interaction.channel.mention}\n"
                    f"⚠️ Erro: `{e}`"
                )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao finalizar procurado: `{e}`",
                ephemeral=True
            )

            await enviar_log(
                "Erro ao Finalizar Procurado",
                f"👤 Usuário: {interaction.user.mention}\n"
                f"⚠️ Erro: `{e}`"
            )

    @discord.ui.button(
        label="Cancelar Cadastro",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            await enviar_log(
                "Cadastro de Procurado Cancelado",
                f"👤 Cancelado por: {interaction.user.mention}\n"
                f"📂 Canal provisório: {interaction.channel.mention}\n"
                f"🗑️ Canal provisório apagado após cancelar."
            )

            await interaction.followup.send(
                "🗑️ Cadastro cancelado. O canal provisório será apagado em 5 segundos.",
                ephemeral=True
            )

            await asyncio.sleep(5)

            try:
                await interaction.channel.delete()
            except Exception as e:
                await enviar_log(
                    "Erro ao Apagar Canal Provisório",
                    f"📂 Canal: {interaction.channel.mention}\n"
                    f"⚠️ Erro: `{e}`"
                )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao cancelar cadastro: `{e}`",
                ephemeral=True
            )


class PainelProcuradosView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Novo Procurado",
        emoji="➕",
        style=discord.ButtonStyle.danger,
        custom_id="novo_procurado_button"
    )
    async def novo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ProcuradoModal())


class RetirarProcuradoModal(discord.ui.Modal, title="Retirar Procurado"):
    rg = discord.ui.TextInput(label="RG do procurado", required=True)
    motivo = discord.ui.TextInput(
        label="Motivo da retirada",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            lista = carregar_procurados()
            procurado = None

            for p in lista:
                if str(p["rg"]) == str(self.rg.value) and p.get("status", "ativo") == "ativo":
                    procurado = p
                    break

            if procurado is None:
                await interaction.followup.send(
                    "❌ Procurado não encontrado ou já retirado.",
                    ephemeral=True
                )
                return

            canal_procurados = bot.get_channel(procurado.get("canal_id", PROCURADOS_CHANNEL_ID))
            historico = bot.get_channel(HISTORICO_PROCURADOS_ID)

            if historico is None:
                await interaction.followup.send(
                    "❌ Canal de histórico não encontrado. O post não foi apagado.",
                    ephemeral=True
                )

                await enviar_log(
                    "Erro ao Retirar Procurado",
                    f"❌ Canal de histórico não encontrado.\n"
                    f"🆔 RG: `{procurado['rg']}`\n"
                    f"⚠️ Post original não foi apagado."
                )
                return

            arquivos_historico = []
            mensagem_original = None
            apagou_post = False

            if canal_procurados:
                try:
                    mensagem_original = await canal_procurados.fetch_message(procurado["mensagem_id"])

                    for anexo in mensagem_original.attachments:
                        try:
                            arquivos_historico.append(await anexo.to_file())
                        except Exception:
                            pass

                except Exception:
                    mensagem_original = None

            texto_historico = f"""
📂 **HISTÓRICO DE PROCURADO RETIRADO**

👤 **Nome:** {procurado['nome']}
🆔 **RG:** {procurado['rg']}

📍 **Último avistamento:**
{procurado['ultimo']}

⚠️ **Crimes imputados:**
{procurado['crimes']}

━━━━━━━━━━━━━━━━━━━━━━━

📌 **Motivo da retirada:**
{self.motivo.value}

👮 **Retirado por:** {interaction.user.mention}

⚠️ Registro enviado ao histórico antes da remoção do post original.
"""

            if arquivos_historico:
                await historico.send(
                    content=texto_historico,
                    files=arquivos_historico
                )
            else:
                await historico.send(
                    content=texto_historico
                )

            if mensagem_original:
                try:
                    await mensagem_original.delete()
                    apagou_post = True
                except Exception as e:
                    await enviar_log(
                        "Erro ao Apagar Post do Procurado",
                        f"👤 Nome: `{procurado['nome']}`\n"
                        f"🆔 RG: `{procurado['rg']}`\n"
                        f"⚠️ Erro: `{e}`"
                    )

            procurado["status"] = "retirado"
            procurado["motivo_retirada"] = self.motivo.value
            procurado["retirado_por"] = interaction.user.name
            procurado["retirado_por_id"] = interaction.user.id
            procurado["post_original_apagado"] = apagou_post

            salvar_procurados(lista)

            await enviar_log(
                "Procurado Retirado",
                f"👤 Nome: `{procurado['nome']}`\n"
                f"🆔 RG: `{procurado['rg']}`\n"
                f"📌 Motivo: {self.motivo.value}\n"
                f"👮 Retirado por: {interaction.user.mention}\n"
                f"📂 Enviado para histórico: Sim\n"
                f"🗑️ Post original apagado: {'Sim' if apagou_post else 'Não'}"
            )

            await interaction.followup.send(
                f"✅ Procurado **{procurado['nome']}** foi enviado ao histórico e retirado com sucesso.",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao retirar procurado: `{e}`",
                ephemeral=True
            )

            await enviar_log(
                "Erro ao Retirar Procurado",
                f"👤 Usuário: {interaction.user.mention}\n"
                f"⚠️ Erro: `{e}`"
            )


# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    global views_adicionadas

    await tree.sync()

    if not backup_diario.is_running():
        backup_diario.start()

    if not views_adicionadas:
        bot.add_view(CriarMesaView())
        bot.add_view(PainelProcuradosView())
        bot.add_view(FecharMesaView())
        views_adicionadas = True

    print(f"Bot online como {bot.user}")
    print("Comandos sincronizados!")
    print("Backup diário ativado!")


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    try:
        await enviar_log(
            "Erro no Bot",
            f"👤 Usuário: {interaction.user.mention if interaction.user else 'N/A'}\n"
            f"⚠️ Erro: `{error}`"
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Ocorreu um erro ao executar esse comando.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar esse comando.",
                ephemeral=True
            )

    except Exception:
        pass


# =========================
# COMANDOS
# =========================

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
        color=0x2B2D31
    )

    await interaction.response.send_message(
        embed=embed,
        view=CriarMesaView()
    )

    await enviar_log(
        "Painel de Mesas Criado",
        f"👤 Criado por: {interaction.user.mention}\n"
        f"📍 Canal: {interaction.channel.mention}"
    )


@tree.command(name="testebackup", description="Executar backup agora")
async def testebackup(interaction: discord.Interaction):
    await interaction.response.send_message(
        "📦 Executando backup...",
        ephemeral=True
    )

    await executar_backup(manual=True, usuario=interaction.user)


@tree.command(name="painelprocurados", description="Criar painel de procurados")
async def painelprocurados(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚨 Sistema de Procurados - DIC",
        description="Clique no botão abaixo para cadastrar um novo procurado.",
        color=0x8B0000
    )

    await interaction.response.send_message(
        embed=embed,
        view=PainelProcuradosView()
    )

    await enviar_log(
        "Painel de Procurados Criado",
        f"👤 Criado por: {interaction.user.mention}\n"
        f"📍 Canal: {interaction.channel.mention}"
    )


@tree.command(name="listarprocurados", description="Lista os procurados ativos cadastrados")
async def listarprocurados(interaction: discord.Interaction):
    lista = carregar_procurados()
    ativos = [p for p in lista if p.get("status", "ativo") == "ativo"]

    if not ativos:
        await interaction.response.send_message(
            "📂 Nenhum procurado ativo cadastrado.",
            ephemeral=True
        )

        await enviar_log(
            "Listagem de Procurados",
            f"👤 Solicitado por: {interaction.user.mention}\n"
            f"📂 Resultado: Nenhum procurado ativo cadastrado."
        )
        return

    texto = "🔍 **Lista de Procurados Ativos**\n\n"

    for p in ativos:
        texto += f"👤 **{p['nome']}** | RG: `{p['rg']}`\n"

    await interaction.response.send_message(texto, ephemeral=True)

    await enviar_log(
        "Listagem de Procurados",
        f"👤 Solicitado por: {interaction.user.mention}\n"
        f"📊 Total ativo listado: `{len(ativos)}`"
    )


@tree.command(name="retirarprocurado", description="Retira um procurado pelo RG e motivo")
async def retirarprocurado(interaction: discord.Interaction):
    await interaction.response.send_modal(RetirarProcuradoModal())


bot.run(TOKEN)
