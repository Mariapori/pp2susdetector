import discord
import os
from discord.ext import commands
from discord import ui
import asyncio
import threading
import subprocess
import sys
import yaml
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

class UnbanSelect(ui.Select):
    """Dropdown menu for selecting a player to unban"""
    def __init__(self, banned_players: list):
        options = []
        # Discord allows max 25 options
        for player in banned_players[:25]:
            label = f"{player['name']} ({player['server']})"
            # Use a unique value to identify the entry
            # IP|Name|Server
            value = f"{player['ip']}|{player['name']}|{player['server']}"
            description = f"Banned: {player['minutes']} min ({player['ip']})"
            options.append(discord.SelectOption(label=label, value=value, description=description, emoji="🔓"))
        
        super().__init__(placeholder="Valitse pelaaja, jonka banni poistetaan...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

class UnbanView(ui.View):
    """View for the unban command"""
    def __init__(self, banned_players: list, callback_unban: Callable):
        super().__init__(timeout=180)
        self.callback_unban = callback_unban
        self.select_menu = UnbanSelect(banned_players)
        self.add_item(self.select_menu)

    @ui.button(label="✅ Poista Banni", style=discord.ButtonStyle.success, row=1)
    async def confirm_unban(self, interaction: discord.Interaction, button: ui.Button):
        if not self.select_menu.values:
            await interaction.response.send_message("❌ Valitse ensin pelaaja listasta.", ephemeral=True)
            return

        selected_value = self.select_menu.values[0]
        # value is ip|name|server
        parts = selected_value.split("|")
        if len(parts) >= 3:
            ip, name, server = parts[0], parts[1], parts[2]
        else:
            ip, name = parts[0], parts[1]
            server = None
        
        success = await self.callback_unban(ip, name, server)
        
        if success:
            await interaction.message.edit(content=f"✅ Banni poistettu: **{name}** ({server or '?'})", view=None)
        else:
            await interaction.message.edit(content=f"❌ Bannin poisto epäonnistui: **{name}**", view=None)
        
        self.stop()
        
    @ui.button(label="❌ Peruuta", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.message.edit(content="❌ Toiminto peruttu.", view=None)
        self.stop()

class DiscordBot:
    """Discord bot for interactive moderation"""
    def __init__(self, token: str, channel_id: Optional[str] = None, banlist_path: Optional[str] = None, server_banlists: Optional[Dict[str, str]] = None):
        self.banlist_paths = server_banlists if server_banlists else {}
        if banlist_path and not self.banlist_paths:
            self.banlist_paths = {"Default": banlist_path}
            
        self.token = token
        self.channel_id = int(channel_id) if channel_id else None
        self.cmd_callback = None # Set later
        self.config_callback = None  # Callback for config updates
        
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

        @self.bot.command(name="verify")
        async def toggle_verify_all(ctx, mode: str = None):
            """Säädä verify_all asetusta: !verify on/off/status"""
            if not self.config_callback:
                await ctx.send("❌ Config-callback ei ole käytössä.")
                return
            
            if mode is None or mode.lower() == "status":
                # Show current status
                current = self.config_callback("get", None)
                status_emoji = "✅" if current else "❌"
                await ctx.send(f"📋 **verify_all** on tällä hetkellä: {status_emoji} **{'päällä' if current else 'pois päältä'}**")
                return
            
            mode_lower = mode.lower()
            if mode_lower in ["on", "true", "1", "päällä"]:
                new_value = True
            elif mode_lower in ["off", "false", "0", "pois"]:
                new_value = False
            else:
                await ctx.send("❌ Käyttö: `!verify on` tai `!verify off` tai `!verify status`")
                return
            
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.config_callback, "set", new_value)
                
                if result:
                    status_emoji = "✅" if new_value else "❌"
                    await ctx.send(f"🔧 **verify_all** asetettu: {status_emoji} **{'päällä' if new_value else 'pois päältä'}**\n*Muutos on voimassa heti.*")
                else:
                    await ctx.send("❌ Asetuksen muuttaminen epäonnistui.")
            except Exception as e:
                await ctx.send(f"❌ Virhe: {str(e)}")

        @self.bot.command(name="unban")
        async def unban_player(ctx):
            """Poista banni pelaajalta: !unban"""
            if not self.banlist_paths:
                await ctx.send("❌ Ban-listojen polkuja ei ole määritetty asetuksissa.")
                return

            try:
                banned_players = await asyncio.to_thread(self._read_banlist)
                if not banned_players:
                    await ctx.send("📋 Ban-lista on tyhjä tai sitä ei voitu lukea.")
                    return

                # Send the selection view
                view = UnbanView(banned_players, self._remove_ban)
                await ctx.send("🔓 Valitse pelaaja, jonka banni poistetaan:", view=view)
                
            except Exception as e:
                log.error(f"❌ Virhe !unban komennossa: {e}")
                await ctx.send(f"❌ Virhe: {str(e)}")

    def set_command_callback(self, callback: Callable[[str], None]):
        """Set the function to call when a PP2 command needs to be executed"""
        self.cmd_callback = callback

    def set_config_callback(self, callback: Callable[[str, Optional[bool]], bool]):
        """Set the function to call when config needs to be read or updated"""
        self.config_callback = callback

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

    def _read_banlist(self) -> list:
        """Read and parse the ban.dat files from all servers"""
        all_players = []
        
        for server_name, path in self.banlist_paths.items():
            if not path or not os.path.exists(path):
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Helper to parse blocks
                current_player = {}
                for line in content.splitlines():
                    line = line.strip()
                    if not line:
                        if 'Name' in current_player and 'Address' in current_player:
                            current_player['server'] = server_name
                            all_players.append(current_player)
                        current_player = {}
                        continue
                
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        current_player[key] = value
            
                # Handle last entry if no trailing newline
                if 'Name' in current_player and 'Address' in current_player:
                    current_player['server'] = server_name
                    all_players.append(current_player)

            except Exception as e:
                log.error(f"❌ Virhe ban-listan luvussa ({server_name}): {e}")

        # Filter duplicates or clean up if needed
        clean_players = []
        for p in all_players:
            clean_players.append({
                'name': p.get('Name', 'Unknown'),
                'ip': p.get('Address', 'Unknown'),
                'minutes': p.get('Minutes', '?'),
                'server': p.get('server', 'Unknown'),
                'raw': p 
            })
        
        return clean_players

    async def _remove_ban(self, ip: str, name: str, server: Optional[str] = None) -> bool:
        """Remove a ban block from the file"""
        try:
            return await asyncio.to_thread(self._remove_ban_sync, ip, name, server)
        except Exception as e:
            log.error(f"❌ Async wrapper error: {e}")
            return False

    def _remove_ban_sync(self, ip: str, name: str, server: Optional[str] = None) -> bool:
        """Synchronous file operation to remove ban"""
        
        # Determine which file to modify
        target_path = None
        if server and server in self.banlist_paths:
            target_path = self.banlist_paths[server]
        elif len(self.banlist_paths) == 1:
            target_path = list(self.banlist_paths.values())[0]
            
        if not target_path or not os.path.exists(target_path):
            log.error(f"❌ Ban-listaa ei löydy palvelimelle: {server}")
            return False
            
        try:
            with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            new_lines = []
            buffer = []
            
            # Function to check if buffer contains the target player
            def is_target_block(buf_lines, target_ip, target_name):
                block_content = "".join(buf_lines)
                parsed_data = {}
                for line in buf_lines:
                    if '=' in line:
                        parts = line.split('=', 1)
                        key = parts[0].strip()
                        val = parts[1].strip()
                        parsed_data[key] = val
                
                # Check for match (case-sensitive for now, or match existing logic)
                # Existing logic used inclusion, which is weak.
                # Let's match exact values if present.
                if 'Name' in parsed_data and 'Address' in parsed_data:
                    return parsed_data['Name'] == target_name and parsed_data['Address'] == target_ip
                return False

            for line in lines:
                if not line.strip(): 
                    # End of block
                    if buffer:
                        if is_target_block(buffer, ip, name):
                            log.info(f"🗑️ Poistetaan ban-lohko: {name} / {ip}")
                            # Skip this block
                        else:
                            new_lines.extend(buffer)
                        buffer = []
                    new_lines.append(line) # Keep the empty line separator
                    continue
                
                buffer.append(line)
            
            # Flush last buffer
            if buffer:
                if is_target_block(buffer, ip, name):
                   log.info(f"🗑️ Poistetaan viimeinen ban-lohko: {name} / {ip}")
                else:
                    new_lines.extend(buffer)

            with open(target_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            return True
            
        except Exception as e:
            log.error(f"❌ Virhe ban-listan kirjoituksessa: {e}")
            return False
