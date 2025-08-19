import discord
from starboard_config import config  # Configuración dinámica

# Mapeo mensaje original -> mensaje starboard
starboard_messages = {}

class EnlaceButton(discord.ui.View):
    def __init__(self, url):
        super().__init__()
        self.add_item(discord.ui.Button(label="🔗 Ver mensaje", url=url))

async def enviar_o_actualizar_starboard(bot, message, stars):
    canal_destino = bot.get_channel(config["channel_id"])
    if not canal_destino:
        print("Canal starboard no encontrado.")
        return

    mensaje_url = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

    # Extraemos contenido o embed summary
    if message.content:
        contenido_mes = message.content
    elif message.embeds:
        embed = message.embeds[0]
        contenido_mes = embed.title or embed.description or "*Sin texto*"
    else:
        contenido_mes = "*Sin texto*"

    embed = discord.Embed(
        description=f"{config['emoji']} {stars}\n{contenido_mes}",
        color=discord.Color.gold(),
        url=mensaje_url
    )

    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.avatar.url if message.author.avatar else None
    )
    embed.set_footer(
        text=f"Publicado en #{message.channel.name}",
        icon_url=message.guild.icon.url if message.guild.icon else None
    )
    embed.timestamp = message.created_at

    archivos = None
    if message.attachments:
        archivos = [await a.to_file() for a in message.attachments]
        if message.attachments[0].content_type and message.attachments[0].content_type.startswith("image/"):
            embed.set_image(url=message.attachments[0].url)
            archivos = [await a.to_file() for a in message.attachments[1:]]

    view = EnlaceButton(mensaje_url)

    if message.id in starboard_messages:
        # Intentar editar mensaje starboard existente
        try:
            star_msg = await canal_destino.fetch_message(starboard_messages[message.id])
            await star_msg.edit(embed=embed, view=view)
            # No se puede editar archivos directamente en edit()
        except discord.NotFound:
            # Si no existe, lo creamos de nuevo
            starboard_messages.pop(message.id)
            star_msg = await canal_destino.send(embed=embed, view=view, files=archivos if archivos else None)
            await star_msg.add_reaction("👍")
            await star_msg.add_reaction("🔥")
            starboard_messages[message.id] = star_msg.id
    else:
        # Crear nuevo mensaje starboard
        star_msg = await canal_destino.send(embed=embed, view=view, files=archivos if archivos else None)
        await star_msg.add_reaction("👍")
        await star_msg.add_reaction("🔥")
        starboard_messages[message.id] = star_msg.id

async def eliminar_starboard(bot, message):
    if message.id not in starboard_messages:
        return
    canal_destino = bot.get_channel(config["channel_id"])
    if not canal_destino:
        return
    try:
        star_msg = await canal_destino.fetch_message(starboard_messages[message.id])
        await star_msg.delete()
    except discord.NotFound:
        pass
    starboard_messages.pop(message.id, None)

async def on_raw_reaction_update(bot, payload):
    if str(payload.emoji) != config["emoji"]:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return

    stars_count = 0
    for reaction in message.reactions:
        if str(reaction.emoji) == config["emoji"]:
            stars_count = reaction.count
            break

    if stars_count >= config["threshold"]:
        await enviar_o_actualizar_starboard(bot, message, stars_count)
    else:
        await eliminar_starboard(bot, message)
