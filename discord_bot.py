import discord
from discord.ext import commands
from discord import ui
import asyncio
import threading
import subprocess
import sys
from typing import Optional, Callable, Dict, Any
from logger import log

class SeveritySelect(ui.Select):
    """Dropdown menu for selecting violation severity"""
    def __init__(self, current_severity: str):
        options = [
            discord.SelectOption(label="🚨 SEVERE (Ban)", value="SEVERE", emoji="🚨", default=(current_severity == "SEVERE")),
            discord.SelectOption(label="⚠️ MODERATE (Kick)", value="MODERATE", emoji="⚠️", default=(current_severity == "MODERATE")),
            discord.SelectOption(label="📝 MINOR (Warning)", value="MINOR", emoji="📝", default=(current_severity == "MINOR")),
            discord.SelectOption(label="✅ OK (No Action)", value="OK", emoji="✅", default=(current_severity == "OK")),
        ]
        super().__init__(placeholder="Valitse vakavuusaste...", min_values=1, max_values=1, options=options, custom_id="severity_select")

    async def callback(self, interaction: discord.Interaction):
        # Acknowledge the selection immediately to avoid "interaction failed"
        await interaction.response.defer()

class ModerationView(ui.View):
    """Discord buttons for moderation actions"""
    def __init__(self, callback_confirm: Callable, callback_reject: Callable, initial_severity: str = "MODERATE", timeout: int = 3600):
        super().__init__(timeout=timeout)
        self.callback_confirm = callback_confirm
        self.callback_reject = callback_reject
        self.severity = initial_severity
        
        # Add the select menu
        self.select_menu = SeveritySelect(initial_severity)
        self.add_item(self.select_menu)

    @ui.button(label="✅ Vahvista", style=discord.ButtonStyle.danger, custom_id="confirm_ban", row=1)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        # Update severity from select menu if changed
        selected_severity = self.select_menu.values[0] if self.select_menu.values else self.severity
        
        await interaction.response.send_message(f"⌛ Suoritetaan toimenpide tasolla: **{selected_severity}**...", ephemeral=True)
        await self.callback_confirm(selected_severity)
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label="❌ Hylkää", style=discord.ButtonStyle.secondary, custom_id="reject_ban", row=1)
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("❌ Hylätty.", ephemeral=True)
        await self.callback_reject()
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

class DiscordBot:
    """Discord bot for interactive moderation"""
    def __init__(self, token: str, channel_id: Optional[str] = None):
        self.token = token
        self.channel_id = int(channel_id) if channel_id else None
        self.cmd_callback = None # Set later
        
        # We need message_content to read !c commands
        # If this fails, recommend the user to enable it in the portal
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            self.bot = commands.Bot(command_prefix="!", intents=intents)
        except Exception as e:
            log.warning(f"⚠️ Alustuksessa tapahtui virhe: {e}")
            intents = discord.Intents.default()
            self.bot = commands.Bot(command_prefix="!", intents=intents)

        self.is_ready = False
        
        @self.bot.event
        async def on_ready():
            log.info(f"🤖 Discord Bot kirjautunut sisään: {self.bot.user}")
            self.is_ready = True

        @self.bot.command(name="c")
        async def execute_pp2_cmd(ctx, *, cmd: str):
            """Suorita PP2-komento (esim. !c /kick 1)"""
            if not self.cmd_callback:
                await ctx.send("❌ Komentojen suoritus ei ole käytössä (callback puuttuu).")
                return
            
            # Send initial feedback
            status_msg = await ctx.send(f"🚀 Suoritetaan komento: `{cmd}`...")
            
            # Run in executor because it might be a blocking request
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self.cmd_callback, cmd)
                
                if response:
                    # Truncate if too long for Discord (2000 chars)
                    if len(response) > 1900:
                        response = response[:1900] + "... (katkaistu)"
                    
                    await ctx.send(f"✅ **Palvelimen vastaus:**\n```\n{response}\n```")
                else:
                    await ctx.send("✅ Komento lähetetty palvelimelle (ei vastausta).")
            except Exception as e:
                await ctx.send(f"❌ Virhe komennon suorituksessa: {str(e)}")
            finally:
                try:
                    await status_msg.delete()
                except:
                    pass

        @self.bot.command(name="train")
        async def train_ml_model(ctx):
            """Käynnistä ML-mallin opetus"""
            status_msg = await ctx.send("🏃 Opetetaan mallia... Tämä voi kestää hetken.")
            
            try:
                # Run the training script via subprocess
                # We use the current python interpreter to stay in the same environment
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "train_model.py",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                output = ""
                if stdout:
                    output += f"**Output:**\n```\n{stdout.decode('utf-8', errors='replace')}\n```\n"
                if stderr:
                    output += f"**Errors:**\n```\n{stderr.decode('utf-8', errors='replace')}\n```"
                
                if not output:
                    output = "✅ Opetus valmis (ei tulostetta)."
                
                # Split output if it's too long for Discord (max 2000 chars)
                if len(output) > 1950:
                    for i in range(0, len(output), 1950):
                        await ctx.send(output[i:i+1950])
                else:
                    await ctx.send(output)
                    
            except Exception as e:
                await ctx.send(f"❌ Virhe opetuksen aikana: {str(e)}")
            finally:
                try:
                    await status_msg.delete()
                except:
                    pass

    def set_command_callback(self, callback: Callable[[str], None]):
        """Set the function to call when a PP2 command needs to be executed"""
        self.cmd_callback = callback

    async def send_interaction(self, embed_data: Dict[str, Any], callback_confirm: Callable, callback_reject: Callable):
        """Send a message with interactive buttons"""
        if not self.is_ready:
            log.warning("⚠️ Discord Bot ei ole valmis, interaktiivista viestiä ei voitu lähettää")
            return

        channel = None
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
        
        if not channel:
            for guild in self.bot.guilds:
                for text_channel in guild.text_channels:
                    channel = text_channel
                    break
                if channel: break
        
        if not channel:
            log.warning("⚠️ Kanavaa ei löytynyt interaktiivisen viestin lähettämiseen")
            return

        embed = discord.Embed(
            title=embed_data.get('title', 'Moderation Required'),
            description=embed_data.get('description', ''),
            color=embed_data.get('color', discord.Color.blue())
        )
        for field in embed_data.get('fields', []):
            embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', False))

        initial_severity = embed_data.get('severity', 'MODERATE')
        view = ModerationView(callback_confirm, callback_reject, initial_severity=initial_severity)
        await channel.send(embed=embed, view=view)

    def start_in_thread(self):
        """Run the bot in a background thread"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.bot.start(self.token))
            except discord.errors.PrivilegedIntentsRequired:
                log.error("❌ VIRHE: Discord-botti vaatii 'Message Content Intent' -oikeuden.")
                log.error("1. Mene osoitteeseen: https://discord.com/developers/applications/")
                log.error("2. Valitse sovelluksesi -> Bot")
                log.error("3. Ota käyttöön: 'Message Content Intent'")
                log.error("4. Tallenna muutokset ja käynnistä detector uudelleen.")
            except Exception as e:
                log.error(f"❌ Odottamaton virhe Discord-botin käynnistyksessä: {e}")
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
