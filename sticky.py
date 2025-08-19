# sticky_handler.py

import discord
from discord.ext import commands
import os
import json
import asyncio
from datetime import datetime
from discord import ui, Interaction, Embed, ButtonStyle

# Variables globales que se usarán también desde main
pending_sticky_tasks = {}
sticky_messages = {}
sticky_embeds = {}
STICKY_FILE = "sticky_data.json"
STICKY_DELAY_SECONDS = 5

def load_stickies():
    if not os.path.exists(STICKY_FILE):
        return {}
    with open(STICKY_FILE, "r") as f:
        return json.load(f)

def save_stickies(data):
    with open(STICKY_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("💾 Sticky guardado en archivo.")

sticky_config_data = load_stickies()

async def try_delete_message(channel, message_id):
    try:
        msg = await channel.fetch_message(message_id)
        await msg.delete()
    except:
        pass

def setup_stickies(bot: commands.Bot):
    # --- on_ready ---
    @bot.event
    async def on_ready():
        for channel_id_str, config in sticky_config_data.items():
            try:
                channel_id = int(channel_id_str)
                channel = bot.get_channel(channel_id)
                if channel is None:
                    continue

                embed = discord.Embed(
                    title=config["title"],
                    description=config["description"],
                    color=int(config["color"].replace("#", ""), 16)
                )

                if config.get("image_url"):
                    embed.set_image(url=config["image_url"])
                if config.get("thumbnail_url"):
                    embed.set_thumbnail(url=config["thumbnail_url"])
                if config.get("footer_text") or config.get("footer_icon_url"):
                    embed.set_footer(
                        text=config.get("footer_text") or None,
                        icon_url=config.get("footer_icon_url") or None
                    )
                if config.get("author_name"):
                    embed.set_author(
                        name=config["author_name"],
                        icon_url=config.get("author_icon_url") or None
                    )
                if config.get("use_timestamp"):
                    embed.timestamp = datetime.utcnow()

                sticky_embeds[channel_id] = embed

                last_message_id = config.get("last_message_id")
                if last_message_id:
                    await try_delete_message(channel, int(last_message_id))

                sent = await channel.send(embed=embed)
                sticky_messages[channel_id] = sent
                sticky_config_data[channel_id_str]["last_message_id"] = sent.id
                save_stickies(sticky_config_data)

            except Exception as e:
                print(f"⚠️ Error al cargar sticky en canal {channel_id_str}: {e}")

    # --- on_message ---
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        await bot.process_commands(message)
        channel = message.channel
        channel_id = channel.id

        if channel_id not in sticky_embeds:
            return

        if channel_id in pending_sticky_tasks:
            pending_sticky_tasks[channel_id].cancel()

        async def delayed_sticky():
            try:
                await asyncio.sleep(STICKY_DELAY_SECONDS)
                embed = sticky_embeds[channel_id]

                if channel_id in sticky_messages:
                    try:
                        await sticky_messages[channel_id].delete()
                    except:
                        pass

                sent = await channel.send(embed=embed)
                sticky_messages[channel_id] = sent
                sticky_config_data[str(channel_id)]["last_message_id"] = sent.id
                save_stickies(sticky_config_data)
            except asyncio.CancelledError:
                pass

        pending_sticky_tasks[channel_id] = asyncio.create_task(delayed_sticky())

    # --- Slash commands ---
    @bot.tree.command(name="setsticky", description="Configura un sticky embed para este canal")
    async def setsticky(interaction: discord.Interaction, title: str, description: str, color: str,
                        image_url: str = None, thumbnail_url: str = None,
                        footer_text: str = None, footer_icon_url: str = None,
                        author_name: str = None, author_icon_url: str = None,
                        use_timestamp: bool = False):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            embed_color = int(color.replace("#", ""), 16)
            embed = discord.Embed(title=title, description=description, color=embed_color)
            if image_url: embed.set_image(url=image_url)
            if thumbnail_url: embed.set_thumbnail(url=thumbnail_url)
            if footer_text or footer_icon_url:
                embed.set_footer(text=footer_text or None, icon_url=footer_icon_url or None)
            if author_name:
                embed.set_author(name=author_name, icon_url=author_icon_url or None)
            if use_timestamp:
                embed.timestamp = datetime.utcnow()

            channel_id = interaction.channel_id
            sticky_embeds[channel_id] = embed

            sticky_config_data[str(channel_id)] = {
                "title": title,
                "description": description,
                "color": color,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "footer_text": footer_text,
                "footer_icon_url": footer_icon_url,
                "author_name": author_name,
                "author_icon_url": author_icon_url,
                "use_timestamp": use_timestamp,
                "last_message_id": None
            }
            save_stickies(sticky_config_data)

            await interaction.followup.send("✅ Sticky configurado correctamente.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error al crear el sticky: {e}")

    # --- Lista de stickies ---
    class StickyListView(ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.index = 0

        def get_channel_ids(self):
            return list(sticky_embeds.keys())

        async def update_message(self, interaction: Interaction):
            channel_ids = self.get_channel_ids()
            if self.index >= len(channel_ids):
                self.index = max(0, len(channel_ids) - 1)

            channel_id = channel_ids[self.index]
            embed = sticky_embeds.get(channel_id, Embed(description="⚠️ Sticky no encontrado"))
            content = f"Sticky {self.index + 1} de {len(channel_ids)} - Canal ID: <#{channel_id}>"
            await interaction.response.edit_message(content=content, embed=embed, view=self)

        @ui.button(label="Anterior", style=ButtonStyle.secondary)
        async def prev_button(self, interaction: Interaction, button: ui.Button):
            self.index = (self.index - 1) % len(self.get_channel_ids())
            await self.update_message(interaction)

        @ui.button(label="Siguiente", style=ButtonStyle.secondary)
        async def next_button(self, interaction: Interaction, button: ui.Button):
            self.index = (self.index + 1) % len(self.get_channel_ids())
            await self.update_message(interaction)

        @ui.button(label="Borrar Sticky", style=ButtonStyle.danger)
        async def delete_button(self, interaction: Interaction, button: ui.Button):
            channel_id = self.get_channel_ids()[self.index]
            sticky_config_data.pop(str(channel_id), None)
            sticky_embeds.pop(channel_id, None)
            sticky_messages.pop(channel_id, None)
            save_stickies(sticky_config_data)
            await interaction.response.send_message("✅ Sticky borrado.", ephemeral=True)

    @bot.tree.command(name="listarstickies", description="Muestra los stickies con botones")
    async def listarstickies(interaction: discord.Interaction):
        if not sticky_embeds:
            await interaction.response.send_message("⚠️ No hay stickies.", ephemeral=True)
            return

        view = StickyListView()
        channel_ids = view.get_channel_ids()
        embed = sticky_embeds[channel_ids[0]]
        await interaction.response.send_message(
            content=f"Sticky 1 de {len(channel_ids)} - Canal ID: <#{channel_ids[0]}>",
            embed=embed,
            view=view,
            ephemeral=True
        )
