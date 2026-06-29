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

SERVIDOR_DIC_ID = 1490192785553494167

CARGOS_EQUIPE_IDS = [
    1490200382776021132,  # Delegado
    1490200383614615725,  # Vice-Diretor
    1490200390426165290,  # Investigadores
    1490200388912156692,  # Inspetor
    1490200384818647051   # Delegado Denarc
]

CARGOS_ADMIN_IDS = [
    1490200382776021132,  # Delegado
    1490200383614615725,  # Vice-Diretor
    1490200384818647051,  # Delegado Denarc
    1490200390426165290   # Investigador
]

BACKUP_CHANNEL_ID = 1515165673276440677

PROCURADOS_CHANNEL_ID = 1490200533980545097
HISTORICO_PROCURADOS_ID = 1490200536207855857
LOGS_CHANNEL_ID = 1490205503228477610

CATEGORIA_MESAS_ABERTAS_ID = 1490200456855552192
CATEGORIA_MESAS_FECHADAS_ID = 1515165416815722586

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


def normalizar_busca(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    return texto


def contem_termo(texto, termo):
    return normalizar_busca(termo) in normalizar_busca(texto)


def cortar_texto(texto, limite=170):
    texto = str(texto or "").replace("\n", " ").strip()

    if len(texto) <= limite:
        return texto

    return texto[:limite] + "..."


def dividir_texto(texto, limite=1800):
    partes = []
    atual = ""

    for linha in texto.split("\n"):
        if len(atual) + len(linha) + 1 > limite:
            partes.append(atual)
            atual = linha + "\n"
        else:
            atual += linha + "\n"

    if atual.strip():
        partes.append(atual)

    return partes


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


def usuario_admin(membro):
    for cargo in membro.roles:
        if cargo.id in CARGOS_ADMIN_IDS:
            return True

    return False


def limpar_nome_mesa_fechada(nome):
    nome = nome.replace("🔒 ┃", "")
    nome = nome.replace("🔒┃", "")
    nome = nome.replace("fechada-", "")
    return nome.strip()


def remover_prefixo_fechada(nome):
    nome = nome.replace("🔒 ┃", "")
    nome = nome.replace("🔒┃", "")
    nome = nome.replace("fechada-", "")
    return nome.strip()


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
    guild = bot.get_guild(SERVIDOR_DIC_ID)

    if guild is None:
        await enviar_log(
            "Erro no Backup",
            f"❌ Servidor DIC não encontrado.\nID: `{SERVIDOR_DIC_ID}`"
        )
        return

    data = datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d-%m-%Y_%H-%M")
    nome_arquivo = f"backup-DIC-{data}.html"

    conteudo = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Backup DIC</title>
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
    <h1>📦 Backup do servidor DIC: {limpar(guild.name)}</h1>
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
                        <p>📷 <a href="{url}">{nome}</a></p>
                        <img src="{url}">
                        """
                    else:
                        anexos_html += f"""
                        <p>📎 <a href="{url}">{nome}</a></p>
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
                            <p>📷 <a href="{url}">{nome}</a></p>
                            <img src="{url}">
                            """
                        else:
                            anexos_html += f"""
                            <p>📎 <a href="{url}">{nome}</a></p>
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
            content=f"📦 Backup {'manual' if manual else 'diário'} completo do servidor **DIC**",
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
                f"🚨 **Cadastro de Procurado — DIC**\n\n"
                f"👤 **Nome:** {self.nome.value}\n"
                f"🆔 **RG:** {self.rg.value}\n\n"
                f"📸 **Envio obrigatório de imagens:**\n"
                f"1️⃣ **Foto do indivíduo**\n"
                f"2️⃣ **Foto do RG / identificação**\n\n"
                f"Após enviar as duas imagens solicitadas, clique em **✅ Finalizar Cadastro**.\n\n"
                f"⚠️ Este canal é provisório e será apagado após finalizar ou cancelar o cadastro.",
                view=FinalizarProcuradoView(
                    self.nome.value,
                    self.rg.value,
                    self.ultimo.value,
                    self.crimes.value,
                    interaction.user.id,
                    interaction.user.name
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
                f"✅ Canal provisório criado para anexar as imagens: {canal.mention}",
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
    def __init__(self, nome, rg, ultimo, crimes, autor_id, autor_nome):
        super().__init__(timeout=None)
        self.nome = nome
        self.rg = rg
        self.ultimo = ultimo
        self.crimes = crimes
        self.autor_id = autor_id
        self.autor_nome = autor_nome

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
                "autor": self.autor_nome,
                "autor_id": self.autor_id,
                "mensagem_id": mensagem.id,
                "canal_id": PROCURADOS_CHANNEL_ID,
                "status": "ativo"
            })
            salvar_procurados(lista)

            await enviar_log(
                "Procurado Cadastrado",
                f"👤 Nome: `{self.nome}`\n"
                f"🆔 RG: `{self.rg}`\n"
                f"👮 Responsável: <@{self.autor_id}>\n"
                f"📸 Imagens anexadas: `{len(anexos)}`\n"
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
            except Exception:
                pass

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao cancelar cadastro: `{e}`",
                ephemeral=True
            )


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

            autor_id = int(procurado.get("autor_id", 0))

            if interaction.user.id != autor_id and not usuario_admin(interaction.user):
                await interaction.followup.send(
                    "❌ Você não pode retirar esse procurado. Apenas quem cadastrou ou um admin pode retirar.",
                    ephemeral=True
                )

                await enviar_log(
                    "Tentativa Negada de Retirar Procurado",
                    f"👤 Usuário: {interaction.user.mention}\n"
                    f"🆔 RG: `{procurado['rg']}`\n"
                    f"⚠️ Sem permissão."
                )
                return

            canal_procurados = bot.get_channel(procurado.get("canal_id", PROCURADOS_CHANNEL_ID))
            historico = bot.get_channel(HISTORICO_PROCURADOS_ID)

            if historico is None:
                await interaction.followup.send(
                    "❌ Canal de histórico não encontrado. O post não foi apagado.",
                    ephemeral=True
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
                await historico.send(content=texto_historico)

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

    @discord.ui.button(
        label="Lista de Procurados",
        emoji="📋",
        style=discord.ButtonStyle.primary,
        custom_id="lista_procurados_button"
    )
    async def lista(self, interaction: discord.Interaction, button: discord.ui.Button):
        lista = carregar_procurados()
        ativos = [p for p in lista if p.get("status", "ativo") == "ativo"]

        if not ativos:
            await interaction.response.send_message(
                "📂 Nenhum procurado ativo cadastrado.",
                ephemeral=True
            )
            return

        texto = "🚨 **Lista de Procurados Ativos**\n\n"

        for p in ativos:
            texto += f"👤 **{p['nome']}** | RG: `{p['rg']}`\n"

        await interaction.response.send_message(texto, ephemeral=True)

    @discord.ui.button(
        label="Retirar Procurado",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        custom_id="retirar_procurado_button"
    )
    async def retirar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RetirarProcuradoModal())


# =========================
# SISTEMA DE TICKET DE CONSULTA
# =========================

async def gerar_resultado_consulta(guild, termo, ignorar_canal_id=None):
    mesas = []
    procurados = []
    mensagens = []
    arquivos = []

    categorias_busca = [
        CATEGORIA_MESAS_ABERTAS_ID,
        CATEGORIA_MESAS_FECHADAS_ID
    ]

    canais_especiais = [
        PROCURADOS_CHANNEL_ID,
        HISTORICO_PROCURADOS_ID
    ]

    for canal in guild.text_channels:
        if canal.id == ignorar_canal_id:
            continue

        if canal.category_id in categorias_busca:
            if contem_termo(canal.name, termo):
                status = "Aberta" if canal.category_id == CATEGORIA_MESAS_ABERTAS_ID else "Fechada"
                mesas.append(f"• {canal.mention} — `{status}`")

        if len(mesas) >= 10:
            break

    lista = carregar_procurados()

    for p in lista:
        texto_base = (
            f"{p.get('nome', '')} "
            f"{p.get('rg', '')} "
            f"{p.get('ultimo', '')} "
            f"{p.get('crimes', '')} "
            f"{p.get('status', '')}"
        )

        if contem_termo(texto_base, termo):
            status = p.get("status", "ativo")
            procurados.append(
                f"• **{p.get('nome')}** | RG: `{p.get('rg')}` | Status: `{status}`"
            )

        if len(procurados) >= 10:
            break

    canais_para_buscar = []

    for canal in guild.text_channels:
        if canal.id == ignorar_canal_id:
            continue

        if canal.category_id in categorias_busca or canal.id in canais_especiais:
            canais_para_buscar.append(canal)

    for canal in canais_para_buscar:
        if len(mensagens) >= 10 and len(arquivos) >= 10:
            break

        try:
            async for msg in canal.history(limit=100, oldest_first=False):
                if msg.content and contem_termo(msg.content, termo) and len(mensagens) < 10:
                    mensagens.append(
                        f"• {canal.mention} — [abrir mensagem]({msg.jump_url})\n"
                        f"  Trecho: `{cortar_texto(msg.content)}`"
                    )

                for anexo in msg.attachments:
                    if contem_termo(anexo.filename, termo) and len(arquivos) < 10:
                        arquivos.append(
                            f"• {canal.mention} — [{anexo.filename}]({anexo.url})"
                        )

        except Exception:
            pass

        for thread in canal.threads:
            if len(mensagens) >= 10 and len(arquivos) >= 10:
                break

            try:
                if contem_termo(thread.name, termo) and len(mensagens) < 10:
                    mensagens.append(f"• 🧵 **Thread encontrada:** {thread.mention}")

                async for msg in thread.history(limit=100, oldest_first=False):
                    if msg.content and contem_termo(msg.content, termo) and len(mensagens) < 10:
                        mensagens.append(
                            f"• {thread.mention} — [abrir mensagem]({msg.jump_url})\n"
                            f"  Trecho: `{cortar_texto(msg.content)}`"
                        )

                    for anexo in msg.attachments:
                        if contem_termo(anexo.filename, termo) and len(arquivos) < 10:
                            arquivos.append(
                                f"• {thread.mention} — [{anexo.filename}]({anexo.url})"
                            )

            except Exception:
                pass

    texto = f"""
🔎 **CONSULTA INVESTIGATIVA — DIC**

🔍 **Termo pesquisado:** `{termo}`

━━━━━━━━━━━━━━━━━━━━━━━

📂 **Mesas encontradas**
{chr(10).join(mesas) if mesas else "Nenhuma mesa encontrada."}

━━━━━━━━━━━━━━━━━━━━━━━

🚨 **Procurados encontrados**
{chr(10).join(procurados) if procurados else "Nenhum procurado encontrado."}

━━━━━━━━━━━━━━━━━━━━━━━

💬 **Mensagens encontradas**
{chr(10).join(mensagens) if mensagens else "Nenhuma mensagem encontrada."}

━━━━━━━━━━━━━━━━━━━━━━━

📎 **Arquivos encontrados**
{chr(10).join(arquivos) if arquivos else "Nenhum arquivo encontrado."}
"""

    return texto


class FecharConsultaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="fechar_ticket_consulta_button"
    )
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔒 Ticket de consulta será apagado em 5 segundos...",
            ephemeral=True
        )

        await enviar_log(
            "Ticket de Consulta Fechado",
            f"👤 Fechado por: {interaction.user.mention}\n"
            f"📂 Canal: {interaction.channel.mention}\n"
            f"🗑️ Canal provisório apagado."
        )

        await asyncio.sleep(5)

        try:
            await interaction.channel.delete()
        except Exception:
            pass


class ConsultaModal(discord.ui.Modal, title="Ticket de Consulta"):
    termo = discord.ui.TextInput(
        label="O que deseja consultar?",
        placeholder="Exemplo: Baiano, 12345, Olimpo, Fazenda...",
        required=True,
        max_length=80
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            cargos_equipe = obter_cargos_equipe(guild)

            categoria = interaction.channel.category

            if categoria is None:
                categoria = guild.get_channel(CATEGORIA_MESAS_ABERTAS_ID)

            if categoria is None:
                await interaction.followup.send(
                    "❌ Categoria não encontrada para criar o ticket.",
                    ephemeral=True
                )
                return

            nome_ticket = f"🔎┃consulta-{nome_seguro(self.termo.value)}"

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
                name=nome_ticket,
                category=categoria,
                overwrites=overwrites
            )

            await interaction.followup.send(
                f"✅ Ticket de consulta criado: {canal.mention}",
                ephemeral=True
            )

            await canal.send(
                f"🔎 **Ticket de Consulta criado por {interaction.user.mention}**\n"
                f"🔍 **Termo pesquisado:** `{self.termo.value}`\n\n"
                f"⏳ Realizando consulta, aguarde..."
            )

            resultado = await gerar_resultado_consulta(
                guild,
                self.termo.value,
                ignorar_canal_id=canal.id
            )

            resultado = f"👤 **Solicitado por:** {interaction.user.mention}\n" + resultado
            partes = dividir_texto(resultado)

            primeira = True

            for parte in partes:
                if primeira:
                    await canal.send(
                        content=parte,
                        view=FecharConsultaView()
                    )
                    primeira = False
                else:
                    await canal.send(content=parte)

            await enviar_log(
                "Ticket de Consulta Criado",
                f"👤 Criado por: {interaction.user.mention}\n"
                f"🔍 Termo: `{self.termo.value}`\n"
                f"📂 Ticket: {canal.mention}"
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao criar ticket de consulta: `{e}`",
                ephemeral=True
            )


class PainelConsultaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Abrir Ticket de Consulta",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="abrir_ticket_consulta_button"
    )
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConsultaModal())


# =========================
# PAINEL ADMIN
# =========================

class AlertaModal(discord.ui.Modal, title="Enviar Alerta"):
    canal_id = discord.ui.TextInput(
        label="ID do canal onde o alerta será enviado",
        placeholder="Exemplo: 123456789012345678",
        required=True
    )

    titulo = discord.ui.TextInput(
        label="Título do alerta",
        placeholder="Exemplo: Operação urgente",
        required=True,
        max_length=100
    )

    mensagem = discord.ui.TextInput(
        label="Mensagem do alerta",
        placeholder="Digite o aviso que será enviado...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not usuario_admin(interaction.user):
            await interaction.followup.send(
                "❌ Você não tem permissão para enviar alertas.",
                ephemeral=True
            )
            return

        try:
            canal = bot.get_channel(int(self.canal_id.value))

            if canal is None:
                canal = await bot.fetch_channel(int(self.canal_id.value))

            embed = discord.Embed(
                title=f"⚠️ {self.titulo.value}",
                description=self.mensagem.value,
                color=0xFF0000
            )

            embed.set_footer(
                text=f"Alerta enviado por {interaction.user.display_name}"
            )

            await canal.send(
                content="@everyone",
                embed=embed
            )

            await enviar_log(
                "Alerta Enviado",
                f"👤 Enviado por: {interaction.user.mention}\n"
                f"📢 Canal: {canal.mention}\n"
                f"⚠️ Título: `{self.titulo.value}`"
            )

            await interaction.followup.send(
                f"✅ Alerta enviado com sucesso em {canal.mention}.",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao enviar alerta: `{e}`",
                ephemeral=True
            )

            await enviar_log(
                "Erro ao Enviar Alerta",
                f"👤 Usuário: {interaction.user.mention}\n"
                f"⚠️ Erro: `{e}`"
            )


class ReabrirMesaModal(discord.ui.Modal, title="Reabrir Mesa"):
    canal_id = discord.ui.TextInput(
        label="ID do canal da mesa fechada",
        placeholder="Cole o ID do canal da mesa fechada",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not usuario_admin(interaction.user):
            await interaction.followup.send(
                "❌ Você não tem permissão para reabrir mesas.",
                ephemeral=True
            )
            return

        try:
            canal = bot.get_channel(int(self.canal_id.value))

            if canal is None:
                canal = await bot.fetch_channel(int(self.canal_id.value))

            categoria_abertas = interaction.guild.get_channel(CATEGORIA_MESAS_ABERTAS_ID)

            if categoria_abertas is None:
                await interaction.followup.send(
                    "❌ Categoria de mesas abertas não encontrada.",
                    ephemeral=True
                )
                return

            novo_nome = limpar_nome_mesa_fechada(canal.name)

            await canal.edit(
                name=novo_nome,
                category=categoria_abertas
            )

            await canal.send(
                f"🔓 **Mesa reaberta por {interaction.user.mention} e movida para mesas abertas.**"
            )

            await enviar_log(
                "Mesa Reaberta pelo Painel Admin",
                f"👤 Reaberta por: {interaction.user.mention}\n"
                f"📂 Mesa: {canal.mention}\n"
                f"📁 Movida para: `{CATEGORIA_MESAS_ABERTAS_ID}`"
            )

            await interaction.followup.send(
                f"✅ Mesa reaberta com sucesso: {canal.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao reabrir mesa: `{e}`",
                ephemeral=True
            )


class PainelAdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Enviar Alerta",
        emoji="⚠️",
        style=discord.ButtonStyle.danger,
        custom_id="admin_enviar_alerta"
    )
    async def enviar_alerta(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not usuario_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar o painel admin.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(AlertaModal())

    @discord.ui.button(
        label="Fazer Backup",
        emoji="📦",
        style=discord.ButtonStyle.primary,
        custom_id="admin_fazer_backup"
    )
    async def fazer_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not usuario_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para fazer backup.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📦 Backup iniciado pelo painel admin...",
            ephemeral=True
        )

        await enviar_log(
            "Backup Iniciado pelo Painel Admin",
            f"👤 Iniciado por: {interaction.user.mention}"
        )

        await executar_backup(manual=True, usuario=interaction.user)

    @discord.ui.button(
        label="Reabrir Mesa",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="admin_reabrir_mesa"
    )
    async def reabrir_mesa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not usuario_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para reabrir mesas.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(ReabrirMesaModal())

    @discord.ui.button(
        label="Ver Histórico",
        emoji="📂",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_ver_historico"
    )
    async def ver_historico(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not usuario_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para ver o histórico.",
                ephemeral=True
            )
            return

        historico = bot.get_channel(HISTORICO_PROCURADOS_ID)

        if historico is None:
            await interaction.response.send_message(
                "❌ Canal de histórico não encontrado.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"📂 **Canal de Histórico:** {historico.mention}",
            ephemeral=True
        )

        await enviar_log(
            "Histórico Acessado pelo Painel Admin",
            f"👤 Acessado por: {interaction.user.mention}\n"
            f"📂 Canal: {historico.mention}"
        )

    @discord.ui.button(
        label="Estatísticas",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_estatisticas"
    )
    async def estatisticas(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not usuario_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para ver estatísticas.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        lista = carregar_procurados()

        mesas_abertas = 0
        mesas_fechadas = 0

        for canal in guild.text_channels:
            if canal.category_id == CATEGORIA_MESAS_ABERTAS_ID:
                mesas_abertas += 1

            if canal.category_id == CATEGORIA_MESAS_FECHADAS_ID:
                mesas_fechadas += 1

        procurados_ativos = len([
            p for p in lista
            if p.get("status", "ativo") == "ativo"
        ])

        procurados_retirados = len([
            p for p in lista
            if p.get("status") == "retirado"
        ])

        embed = discord.Embed(
            title="📊 Estatísticas da DIC",
            color=0x2B2D31
        )

        embed.add_field(name="📂 Mesas Abertas", value=str(mesas_abertas), inline=True)
        embed.add_field(name="🔒 Mesas Fechadas", value=str(mesas_fechadas), inline=True)
        embed.add_field(name="🚨 Procurados Ativos", value=str(procurados_ativos), inline=True)
        embed.add_field(name="📂 Procurados Retirados", value=str(procurados_retirados), inline=True)
        embed.add_field(name="👥 Membros no servidor", value=str(guild.member_count), inline=True)

        embed.set_footer(
            text=f"Solicitado por {interaction.user.display_name}"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        await enviar_log(
            "Estatísticas Consultadas",
            f"👤 Consultado por: {interaction.user.mention}"
        )


# =========================
# COMANDOS EXTRAS
# =========================

@tree.command(name="ajuda", description="Mostra todos os comandos do bot")
async def ajuda(interaction: discord.Interaction):
    texto = """
📌 **COMANDOS DO BOT DIC**

📂 **Mesas**
`/painel` — Cria o painel para abrir mesas.
`/minhasmesas` — Mostra suas mesas.
`/fecharmesa` — Fecha uma mesa e move para fechadas.
`/reabrirmesa` — Reabre uma mesa fechada.
`/addmembro` — Adiciona um membro em uma mesa.
`/removermembro` — Remove um membro de uma mesa.
`/statusmesa` — Define o status da mesa.
`/relatorio` — Gera relatório da mesa.

🚨 **Procurados**
`/painelprocurados` — Cria painel de procurados.
`/listarprocurados` — Lista procurados ativos.
`/procuradoinfo` — Busca um procurado pelo RG.
`/retirarprocurado` — Retira procurado e manda para histórico.

🔎 **Consulta**
`/painelconsulta` — Cria painel para abrir ticket de consulta.

👮 **Admin**
`/paineladmin` — Cria o painel administrativo.
"""

    await interaction.response.send_message(texto, ephemeral=True)

    await enviar_log(
        "Comando Ajuda Usado",
        f"👤 Usuário: {interaction.user.mention}"
    )


@tree.command(name="minhasmesas", description="Mostra as mesas que você tem acesso direto")
async def minhasmesas(interaction: discord.Interaction):
    guild = interaction.guild
    mesas = []

    categorias_ids = [
        CATEGORIA_MESAS_ABERTAS_ID,
        CATEGORIA_MESAS_FECHADAS_ID
    ]

    for canal in guild.text_channels:
        if canal.category_id not in categorias_ids:
            continue

        permissao_usuario = canal.overwrites_for(interaction.user)

        if permissao_usuario.view_channel is True:
            mesas.append(canal)

    if not mesas:
        await interaction.response.send_message(
            "📂 Você não possui mesas próprias no momento.",
            ephemeral=True
        )
        return

    texto = "📂 **Suas mesas:**\n\n"

    for canal in mesas[:25]:
        texto += f"• {canal.mention}\n"

    await interaction.response.send_message(texto, ephemeral=True)

    await enviar_log(
        "Minhas Mesas Consultado",
        f"👤 Usuário: {interaction.user.mention}\n"
        f"📊 Mesas encontradas: `{len(mesas)}`"
    )


@tree.command(name="fecharmesa", description="Fecha uma mesa e move para a categoria de fechadas")
@app_commands.describe(canal="Canal da mesa que será fechada")
async def fecharmesa(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)

    try:
        categoria_fechadas = interaction.guild.get_channel(CATEGORIA_MESAS_FECHADAS_ID)

        if categoria_fechadas is None:
            await interaction.followup.send(
                "❌ Categoria de mesas fechadas não encontrada.",
                ephemeral=True
            )
            return

        novo_nome = canal.name

        if not novo_nome.startswith("🔒"):
            novo_nome = f"🔒 ┃{novo_nome}"

        await canal.edit(
            name=novo_nome,
            category=categoria_fechadas
        )

        await canal.send("🔒 **Mesa fechada por comando e movida para a categoria de fechadas.**")

        await enviar_log(
            "Mesa Fechada por Comando",
            f"👤 Fechada por: {interaction.user.mention}\n"
            f"📁 Mesa: {canal.mention}"
        )

        await interaction.followup.send(
            f"✅ Mesa fechada com sucesso: {canal.mention}",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao fechar mesa: `{e}`",
            ephemeral=True
        )


@tree.command(name="reabrirmesa", description="Reabre uma mesa fechada")
@app_commands.describe(canal="Canal da mesa que será reaberta")
async def reabrirmesa(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)

    try:
        categoria_abertas = interaction.guild.get_channel(CATEGORIA_MESAS_ABERTAS_ID)

        if categoria_abertas is None:
            await interaction.followup.send(
                "❌ Categoria de mesas abertas não encontrada.",
                ephemeral=True
            )
            return

        novo_nome = remover_prefixo_fechada(canal.name)

        await canal.edit(
            name=novo_nome,
            category=categoria_abertas
        )

        await canal.send("📂 **Mesa reaberta e movida para a categoria de mesas abertas.**")

        await enviar_log(
            "Mesa Reaberta",
            f"👤 Reaberta por: {interaction.user.mention}\n"
            f"📂 Mesa: {canal.mention}"
        )

        await interaction.followup.send(
            f"✅ Mesa reaberta com sucesso: {canal.mention}",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao reabrir mesa: `{e}`",
            ephemeral=True
        )


@tree.command(name="addmembro", description="Adiciona um membro em uma mesa")
@app_commands.describe(
    canal="Canal da mesa",
    membro="Membro que será adicionado"
)
async def addmembro(interaction: discord.Interaction, canal: discord.TextChannel, membro: discord.Member):
    await interaction.response.defer(ephemeral=True)

    try:
        await canal.set_permissions(
            membro,
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True
        )

        await canal.send(f"✅ {membro.mention} foi adicionado à mesa por {interaction.user.mention}.")

        await enviar_log(
            "Membro Adicionado à Mesa",
            f"👤 Adicionado: {membro.mention}\n"
            f"👮 Por: {interaction.user.mention}\n"
            f"📂 Mesa: {canal.mention}"
        )

        await interaction.followup.send(
            f"✅ {membro.mention} foi adicionado à mesa {canal.mention}.",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao adicionar membro: `{e}`",
            ephemeral=True
        )


@tree.command(name="removermembro", description="Remove um membro de uma mesa")
@app_commands.describe(
    canal="Canal da mesa",
    membro="Membro que será removido"
)
async def removermembro(interaction: discord.Interaction, canal: discord.TextChannel, membro: discord.Member):
    await interaction.response.defer(ephemeral=True)

    try:
        await canal.set_permissions(membro, overwrite=None)

        await canal.send(f"❌ {membro.mention} foi removido da mesa por {interaction.user.mention}.")

        await enviar_log(
            "Membro Removido da Mesa",
            f"👤 Removido: {membro.mention}\n"
            f"👮 Por: {interaction.user.mention}\n"
            f"📂 Mesa: {canal.mention}"
        )

        await interaction.followup.send(
            f"✅ {membro.mention} foi removido da mesa {canal.mention}.",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao remover membro: `{e}`",
            ephemeral=True
        )


@tree.command(name="statusmesa", description="Define o status de uma mesa")
@app_commands.describe(
    canal="Canal da mesa",
    status="Status da mesa"
)
@app_commands.choices(status=[
    app_commands.Choice(name="🟢 Em andamento", value="🟢 Em andamento"),
    app_commands.Choice(name="🟡 Em análise", value="🟡 Em análise"),
    app_commands.Choice(name="🔴 Prioridade", value="🔴 Prioridade"),
    app_commands.Choice(name="🔒 Fechada", value="🔒 Fechada")
])
async def statusmesa(interaction: discord.Interaction, canal: discord.TextChannel, status: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)

    try:
        await canal.send(
            f"📌 **Status da mesa atualizado:** {status.value}\n"
            f"👮 Alterado por: {interaction.user.mention}"
        )

        await enviar_log(
            "Status da Mesa Atualizado",
            f"📂 Mesa: {canal.mention}\n"
            f"📌 Status: `{status.value}`\n"
            f"👤 Alterado por: {interaction.user.mention}"
        )

        await interaction.followup.send(
            f"✅ Status da mesa atualizado para: **{status.value}**",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao atualizar status: `{e}`",
            ephemeral=True
        )


@tree.command(name="relatorio", description="Gera um relatório de uma mesa")
@app_commands.describe(canal="Canal da mesa")
async def relatorio(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)

    try:
        data = datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d-%m-%Y_%H-%M")
        nome_arquivo = f"relatorio-{nome_seguro(canal.name)}-{data}.html".replace(" ", "-")

        conteudo = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Relatório {limpar(canal.name)}</title>
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
                h2 {{
                    color: #ffd166;
                    border-bottom: 1px solid #444;
                    margin-top: 30px;
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
        <h1>📂 Relatório da Mesa: {limpar(canal.name)}</h1>
        <h3>Gerado por: {limpar(interaction.user.display_name)}</h3>
        <h3>Data: {data}</h3>
        """

        conteudo += "<h2>📌 Mensagens do Canal Principal</h2>"

        async for msg in canal.history(limit=500, oldest_first=True):
            anexos_html = ""

            for anexo in msg.attachments:
                url = anexo.url
                nome = limpar(anexo.filename)

                if anexo.content_type and anexo.content_type.startswith("image/"):
                    anexos_html += f"""
                    <p>📷 <a href="{url}">{nome}</a></p>
                    <img src="{url}">
                    """
                else:
                    anexos_html += f"""
                    <p>📎 <a href="{url}">{nome}</a></p>
                    """

            conteudo += f"""
            <div class="msg">
                <div class="autor">{limpar(str(msg.author))}</div>
                <div class="data">{msg.created_at.strftime('%d/%m/%Y %H:%M')}</div>
                <div>{limpar(msg.content)}</div>
                {anexos_html}
            </div>
            """

        for thread in canal.threads:
            conteudo += f"<h2>🧵 {limpar(thread.name)}</h2>"

            async for msg in thread.history(limit=500, oldest_first=True):
                anexos_html = ""

                for anexo in msg.attachments:
                    url = anexo.url
                    nome = limpar(anexo.filename)

                    if anexo.content_type and anexo.content_type.startswith("image/"):
                        anexos_html += f"""
                        <p>📷 <a href="{url}">{nome}</a></p>
                        <img src="{url}">
                        """
                    else:
                        anexos_html += f"""
                        <p>📎 <a href="{url}">{nome}</a></p>
                        """

                conteudo += f"""
                <div class="msg">
                    <div class="autor">{limpar(str(msg.author))}</div>
                    <div class="data">{msg.created_at.strftime('%d/%m/%Y %H:%M')}</div>
                    <div>{limpar(msg.content)}</div>
                    {anexos_html}
                </div>
                """

        conteudo += """
        </body>
        </html>
        """

        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)

        await interaction.followup.send(
            content=f"📄 Relatório gerado da mesa {canal.mention}",
            file=discord.File(nome_arquivo),
            ephemeral=True
        )

        await enviar_log(
            "Relatório de Mesa Gerado",
            f"👤 Gerado por: {interaction.user.mention}\n"
            f"📂 Mesa: {canal.mention}"
        )

        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)

    except Exception as e:
        await interaction.followup.send(
            f"❌ Erro ao gerar relatório: `{e}`",
            ephemeral=True
        )


@tree.command(name="procuradoinfo", description="Busca informações de um procurado pelo RG")
@app_commands.describe(rg="RG do procurado")
async def procuradoinfo(interaction: discord.Interaction, rg: str):
    lista = carregar_procurados()
    procurado = None

    for p in lista:
        if str(p["rg"]) == str(rg):
            procurado = p
            break

    if procurado is None:
        await interaction.response.send_message(
            "❌ Procurado não encontrado.",
            ephemeral=True
        )
        return

    status = procurado.get("status", "ativo")

    texto = f"""
🚨 **Informações do Procurado**

👤 **Nome:** {procurado.get('nome')}
🆔 **RG:** {procurado.get('rg')}
📌 **Status:** {status}

📍 **Último avistamento:**
{procurado.get('ultimo')}

⚠️ **Crimes:**
{procurado.get('crimes')}
"""

    if status == "retirado":
        texto += f"""

📂 **Retirado do sistema**

📌 **Motivo:**
{procurado.get('motivo_retirada', 'Não informado')}

👮 **Retirado por:**
{procurado.get('retirado_por', 'Não informado')}
"""

    await interaction.response.send_message(texto, ephemeral=True)

    await enviar_log(
        "Consulta de Procurado",
        f"👤 Consultado por: {interaction.user.mention}\n"
        f"🆔 RG: `{rg}`"
    )


# =========================
# COMANDOS PRINCIPAIS
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


@tree.command(name="painelprocurados", description="Criar painel de procurados")
async def painelprocurados(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚨 Sistema de Procurados - DIC",
        description=(
            "Utilize os botões abaixo para gerenciar procurados.\n\n"
            "➕ **Novo Procurado** — Cadastrar um novo procurado.\n"
            "📋 **Lista de Procurados** — Ver procurados ativos.\n"
            "❌ **Retirar Procurado** — Retirar um procurado pelo RG."
        ),
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


@tree.command(name="painelconsulta", description="Cria o painel de ticket de consulta")
async def painelconsulta(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔎 Ticket de Consulta — DIC",
        description=(
            "Abra um ticket provisório para consultar nomes, RGs, facções, mesas, procurados e arquivos.\n\n"
            "🔎 **Abrir Ticket de Consulta** — Cria um canal privado temporário para a consulta.\n\n"
            "Após finalizar, clique em **🔒 Fechar Ticket** para apagar o canal."
        ),
        color=0x2B2D31
    )

    await interaction.response.send_message(
        embed=embed,
        view=PainelConsultaView()
    )

    await enviar_log(
        "Painel de Consulta Criado",
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


@tree.command(name="paineladmin", description="Cria o painel administrativo da DIC")
async def paineladmin(interaction: discord.Interaction):
    if not usuario_admin(interaction.user):
        await interaction.response.send_message(
            "❌ Você não tem permissão para criar o painel admin.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="👮 Painel Administrativo — DIC",
        description=(
            "Central de controle da administração.\n\n"
            "⚠️ **Enviar Alerta** — Envia um aviso em um canal escolhido.\n"
            "📦 **Fazer Backup** — Executa backup imediato do servidor DIC.\n"
            "🔓 **Reabrir Mesa** — Move uma mesa fechada para abertas.\n"
            "📂 **Ver Histórico** — Mostra o canal de histórico.\n"
            "📊 **Estatísticas** — Mostra números gerais da DIC."
        ),
        color=0x2B2D31
    )

    await interaction.response.send_message(
        embed=embed,
        view=PainelAdminView()
    )

    await enviar_log(
        "Painel Admin Criado",
        f"👤 Criado por: {interaction.user.mention}\n"
        f"📍 Canal: {interaction.channel.mention}"
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
        bot.add_view(PainelAdminView())
        bot.add_view(PainelConsultaView())
        bot.add_view(FecharConsultaView())
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


bot.run(TOKEN)
