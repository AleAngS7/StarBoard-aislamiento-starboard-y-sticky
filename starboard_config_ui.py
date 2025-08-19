import discord
from discord.ext import commands
from discord import app_commands
import starboard_config
import asyncio


class StarboardConfigView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🧷 Cambiar Emoji", style=discord.ButtonStyle.secondary)
    async def change_emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Envía el nuevo emoji:", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id  # Solo verifica autor

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            starboard_config.config["emoji"] = msg.content.strip()
            starboard_config.save_config()
            await interaction.followup.send(f"✅ Emoji actualizado a {msg.content.strip()}", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tiempo agotado o error.", ephemeral=True)

    @discord.ui.button(label="🔢 Cambiar Cantidad", style=discord.ButtonStyle.secondary)
    async def change_threshold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Envíame el nuevo número mínimo de reacciones:", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            nuevo = int(msg.content.strip())
            starboard_config.config["threshold"] = nuevo
            starboard_config.save_config()
            await interaction.followup.send(f"✅ Umbral actualizado a {nuevo}", ephemeral=True)
        except (ValueError, asyncio.TimeoutError):
            await interaction.followup.send("❌ Entrada inválida o tiempo agotado.", ephemeral=True)

    @discord.ui.button(label="📺 Cambiar Canal", style=discord.ButtonStyle.secondary)
    async def change_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Menciona el canal destino (ejemplo: #general):", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            if not msg.channel_mentions:
                await interaction.followup.send("❌ No se detectó un canal válido.", ephemeral=True)
                return
            canal = msg.channel_mentions[0]
            starboard_config.config["channel_id"] = canal.id
            starboard_config.save_config()
            await interaction.followup.send(f"✅ Canal actualizado a {canal.mention}", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tiempo agotado o error.", ephemeral=True)

    @discord.ui.button(label="💾 Ver Configuración", style=discord.ButtonStyle.success)
    async def mostrar_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = starboard_config.config
        canal = interaction.guild.get_channel(cfg["channel_id"])
        embed = discord.Embed(
            title="⚙️ Configuración actual del Starboard",
            color=discord.Color.blue(),
            description=(
                f"**Emoji:** {cfg['emoji']}\n"
                f"**Cantidad mínima:** {cfg['threshold']}\n"
                f"**Canal destino:** {canal.mention if canal else 'No encontrado'}"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class StarboardConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurar_starboard", description="Configura el canal, emoji y cantidad para el starboard.")
    async def configurar_starboard(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Configuración del Starboard",
            description="Usa los botones de abajo para cambiar los valores.",
            color=discord.Color.blurple()
        )
        view = StarboardConfigView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(StarboardConfig(bot))
