import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
import starboard  # 👈 Tu módulo starboard
import sticky     # 👈 Tu módulo sticky

from config_aislamiento import get_log_channel_id, set_log_channel_id
from discord import app_commands

from datetime import timedelta

from flask import Flask
from threading import Thread

# Keep-alive web server
app = Flask('')

@app.route('/')
def home():
    return "Bot activo."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.guild_messages = True
intents.moderation = True
intents.reactions = True  # Necesario para el starboard

bot = commands.Bot(command_prefix="!", intents=intents)

# Almacena mensajes de aislamiento por usuario
aislamiento_mensajes = {}

# Configurar sticky messages
sticky.setup_stickies(bot)

@bot.event
async def on_raw_reaction_add(payload):
    await starboard.on_raw_reaction_add(bot, payload)

@bot.event
async def on_raw_reaction_add(payload):
    await starboard.on_raw_reaction_update(bot, payload)

@bot.event
async def on_raw_reaction_remove(payload):
    await starboard.on_raw_reaction_update(bot, payload)



@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        await bot.load_extension("starboard_config_ui")  # ⬅️ Agregado
        await bot.tree.sync()
        print("✅ Comandos slash sincronizados correctamente.")
    except Exception as e:
        print(f"❌ Error sincronizando comandos slash: {e}")

@bot.event
async def on_member_update(before, after):
    # Si el aislamiento fue quitado (manual o automáticamente)
    if before.timed_out_until and not after.timed_out_until:
        mensaje = aislamiento_mensajes.get(after.id)
        if mensaje:
            embed = mensaje.embeds[0]
            embed.title = "🔓 Fin del Aislamiento"
            embed.description = f"{after.mention} ya no está en aislamiento"
            embed.color = discord.Color.green()
            embed.timestamp = discord.utils.utcnow()
            await mensaje.edit(embed=embed)
            aislamiento_mensajes.pop(after.id, None)

# Comando para establecer el canal de logs
@bot.tree.command(name="setlogchannel", description="Establece el canal de logs para los aislamientos")
@app_commands.checks.has_permissions(administrator=True)
async def set_log_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    set_log_channel_id(interaction.guild_id, canal.id)
    await interaction.response.send_message(f"✅ Canal de logs de aislamiento establecido en {canal.mention}", ephemeral=True)

# 🔧 Función para formatear duración (minutos o días)
def formatear_duracion(minutos: int) -> str:
    if minutos >= 1440:  # 1 día = 1440 minutos
        dias = minutos / 1440
        if dias == 1:
            return "1 día"
        elif dias % 1 == 0:
            return f"{int(dias)} días"
        else:
            return f"{dias:.1f} días"
    elif minutos == 1:
        return "1 minuto"
    else:
        return f"{minutos} minutos"

# Comando slash para aislar a un miembro
@bot.tree.command(name="aislar", description="Aísla a un usuario por un tiempo con una razón.")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(
    miembro="Miembro a aislar",
    duracion_minutos="Duración del aislamiento en minutos",
    razon="Razón del aislamiento"
)
async def aislar(
    interaction: discord.Interaction,
    miembro: discord.Member,
    duracion_minutos: int,
    razon: str
):
    await interaction.response.defer(ephemeral=True)

    # Evitar aislar a miembros con igual o mayor rol
    if interaction.user.top_role <= miembro.top_role:
        await interaction.followup.send("❌ No puedes aislar a alguien con un rol igual o superior al tuyo.")
        return

    # Aplicar aislamiento
    timeout_until = discord.utils.utcnow() + timedelta(minutes=duracion_minutos)

    try:
        await miembro.timeout(timeout_until, reason=razon)
    except discord.Forbidden:
        await interaction.followup.send("🚫 No tengo permisos para aislar a ese miembro.")
        return

    # Obtener canal de logs
    log_channel_id = get_log_channel_id(interaction.guild_id)
    canal_log = interaction.guild.get_channel(log_channel_id) if log_channel_id else None

    # Formatear duración correctamente
    duracion_texto = formatear_duracion(duracion_minutos)
    timestamp_unix = int(timeout_until.timestamp())

    embed = discord.Embed(
        title="🔇 Aislamiento Activado",
        description=(
            f"A {miembro.mention} se le ha aplicado una medida de aislamiento por parte de {interaction.user.mention}.\n"
            f"⏳ Finaliza: <t:{timestamp_unix}:R>"
        ),
        color=discord.Color.orange()
    )

    embed.add_field(name="Duración", value=duracion_texto, inline=True)
    embed.add_field(name="Razón", value=razon, inline=False)
    embed.set_thumbnail(url=miembro.display_avatar.url)
    embed.set_footer(text=f"ID del usuario: {miembro.id}")
    embed.timestamp = discord.utils.utcnow()

    if canal_log:
        mensaje = await canal_log.send(embed=embed)
        aislamiento_mensajes[miembro.id] = mensaje
    else:
        mensaje = None

    await interaction.followup.send(f"✅ {miembro.mention} ha sido aislado por {duracion_texto}.", ephemeral=True)

    # ⏳ Editar embed al finalizar el tiempo (si no se quita antes manualmente)
    async def editar_al_terminar():
        await asyncio.sleep(duracion_minutos * 60)
        if miembro.id in aislamiento_mensajes:
            embed.title = "🔓 Fin del Aislamiento"
            embed.description = f"{miembro.mention} ya no está en aislamiento"
            embed.color = discord.Color.green()
            embed.timestamp = discord.utils.utcnow()
            await mensaje.edit(embed=embed)
            aislamiento_mensajes.pop(miembro.id, None)

    asyncio.create_task(editar_al_terminar())

keep_alive()

bot.run(TOKEN)
