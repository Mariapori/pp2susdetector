"""
Stoat (Revolt) Bot for PP2 Suspicious Detector
Provides notifications and interactive commands via Stoat/Revolt chat platform.
Uses Revolt REST API directly + WebSocket for listening to commands.
"""

import os
import shlex
import json
import asyncio
import threading
import subprocess
import sys
import requests
import yaml
from typing import Optional, Callable, Dict, Any, List
from logger import log


class StoatBot:
    """Stoat/Revolt bot for interactive moderation"""

    def __init__(
        self,
        token: str,
        channel_id: Optional[str] = None,
        api_url: str = "https://api.revolt.chat",
        ws_url: str = "wss://ws.revolt.chat",
        banlist_path: Optional[str] = None,
        server_banlists: Optional[Dict[str, str]] = None
    ):
        self.token = token
        self.channel_id = channel_id
        self.api_url = api_url.rstrip("/")
        self.ws_url = ws_url
        self.banlist_paths = server_banlists if server_banlists else {}
        if banlist_path and not self.banlist_paths:
            self.banlist_paths = {"Default": banlist_path}

        self.cmd_callback: Optional[Callable] = None
        self.config_callback: Optional[Callable] = None
        self.is_ready = False
        self.bot_user_id: Optional[str] = None

        # Pending moderation actions keyed by channel message context
        # Key: player_name -> callback info
        self._pending_moderations: Dict[str, dict] = {}

        self._headers = {
            "X-Bot-Token": self.token,
            "Content-Type": "application/json"
        }

    def _parse_command_args(self, args: str) -> list:
        """Parse command arguments, supporting quoted strings for names with spaces.
        E.g. '"Kauno Semenoff" OK' -> ['Kauno Semenoff', 'OK']
        """
        try:
            return shlex.split(args)
        except ValueError:
            # Fallback if quotes are mismatched
            return args.strip().split()

    def set_command_callback(self, callback: Callable[[str], None]):
        """Set the function to call when a PP2 command needs to be executed"""
        self.cmd_callback = callback

    def set_config_callback(self, callback: Callable[[str, Optional[bool]], bool]):
        """Set the function to call when config needs to be read or updated"""
        self.config_callback = callback

    # ── REST API Methods ──────────────────────────────────────────────

    def send_message(self, content: str, channel_id: Optional[str] = None, embeds: Optional[List[dict]] = None) -> Optional[dict]:
        """Send a message to a Stoat/Revolt channel via REST API"""
        target_channel = channel_id or self.channel_id
        if not target_channel:
            log.warning("⚠️ Stoat: Kanavaa ei määritetty viestin lähettämiseen")
            return None

        url = f"{self.api_url}/channels/{target_channel}/messages"
        payload: Dict[str, Any] = {}

        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds

        try:
            response = requests.post(url, headers=self._headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                log.error(f"❌ Stoat: Viestin lähetys epäonnistui: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            log.error(f"❌ Stoat: Virhe viestin lähetyksessä: {e}")
            return None

    def send_notification(self, embed_data: Dict[str, Any]) -> Optional[dict]:
        """Send an embed notification to the configured channel"""
        # Convert Discord-style embed_data to Revolt embed format
        revolt_embeds = self._convert_embed(embed_data)
        return self.send_message(content=None, embeds=revolt_embeds)

    def send_interaction(self, embed_data: Dict[str, Any], callback_confirm: Callable, callback_reject: Callable):
        """
        Send a moderation notification with text-based command instructions.
        Revolt doesn't have interactive buttons, so we append command hints.
        """
        player_name = None
        server_name = None
        for field in embed_data.get('fields', []):
            if field.get('name') == 'Pelaaja':
                player_name = field.get('value', '').strip('`')
            elif field.get('name') == 'Palvelin':
                server_name = field.get('value', '')

        # Store pending moderation for text-command handling
        # Key is server:player to support multi-server
        if player_name:
            key = f"{server_name or 'default'}:{player_name.lower()}"
            self._pending_moderations[key] = {
                'confirm': callback_confirm,
                'reject': callback_reject,
                'severity': embed_data.get('severity', 'MODERATE'),
                'embed_data': embed_data,
                'server_name': server_name or 'default',
                'player_name': player_name
            }

        revolt_embeds = self._convert_embed(embed_data)

        # Append action instructions as text
        # Quote the player name if it contains spaces
        display_name = f'"{player_name}"' if player_name and ' ' in player_name else player_name
        instructions = (
            "\n\n**Toimenpiteet:**\n"
            f"✅ `!vahvista {display_name}` — Suorita toimenpide\n"
            f"✅ `!vahvista {display_name} SEVERE/MODERATE/MINOR/OK` — Valitse taso\n"
            f"❌ `!hylkaa {display_name}` — Hylkää"
        )

        self.send_message(content=instructions, embeds=revolt_embeds)

    def _find_pending(self, player_name: str) -> tuple:
        """Find pending moderation by player name.
        Returns (key, pending_dict) or (None, None) if not found.
        If the same player is pending on multiple servers, returns the first match.
        """
        player_lower = player_name.lower()
        # Search all keys for matching player name
        matches = []
        for key, val in self._pending_moderations.items():
            # Key format: "server:player"
            if key.endswith(f":{player_lower}"):
                matches.append((key, val))

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple servers — return first but log warning
            servers = [m[1].get('server_name', '?') for m in matches]
            log.warning(f"⚠️ Useita odottavia moderointeja pelaajalle {player_name}: {', '.join(servers)}. Käytetään ensimmäistä.")
            return matches[0]
        return None, None

    def _convert_embed(self, embed_data: Dict[str, Any]) -> List[dict]:
        """Convert Discord-style embed_data to Revolt embed format"""
        # Revolt embeds use "colour" (hex string), not "color" (int)
        color_int = embed_data.get('color', 0x808080)
        color_hex = f"#{color_int:06x}"

        # Build description from fields
        description_parts = []
        if embed_data.get('description'):
            description_parts.append(embed_data['description'])

        for field in embed_data.get('fields', []):
            name = field.get('name', '')
            value = field.get('value', '')
            description_parts.append(f"**{name}:** {value}")

        revolt_embed = {
            "type": "Text",
            "title": embed_data.get('title', 'Notification'),
            "description": "\n".join(description_parts),
            "colour": color_hex
        }

        return [revolt_embed]

    # ── WebSocket / Bot Commands ──────────────────────────────────────

    def start_in_thread(self):
        """Run the bot WebSocket listener in a background thread"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._ws_loop())
            except Exception as e:
                log.error(f"❌ Stoat: WebSocket-yhteys katkennut: {e}")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread

    async def _ws_loop(self):
        """Main WebSocket loop for receiving events"""
        try:
            import websockets
        except ImportError:
            log.error("❌ Stoat: 'websockets' kirjastoa ei ole asennettu. Asenna: pip install websockets")
            return

        while True:
            try:
                log.info(f"🔌 Stoat: Yhdistetään WebSocket-palvelimeen: {self.ws_url}")
                async with websockets.connect(self.ws_url) as ws:
                    # Authenticate
                    auth_payload = {
                        "type": "Authenticate",
                        "token": self.token
                    }
                    await ws.send(json.dumps(auth_payload))

                    # Wait for Authenticated event
                    while True:
                        raw = await ws.recv()
                        data = json.loads(raw)
                        event_type = data.get("type", "")

                        if event_type == "Authenticated":
                            log.info("✅ Stoat: WebSocket autentikoitu")
                            self.is_ready = True
                            continue

                        if event_type == "Ready":
                            # Extract bot user ID from ready payload
                            users = data.get("users", [])
                            if users:
                                self.bot_user_id = users[0].get("_id")
                            log.info(f"🤖 Stoat Bot valmis (User ID: {self.bot_user_id})")
                            continue

                        if event_type == "Message":
                            await self._handle_message(data)

                        # Pong to keep alive
                        if event_type == "Ping":
                            await ws.send(json.dumps({"type": "Pong", "data": data.get("data", 0)}))

            except Exception as e:
                log.error(f"❌ Stoat: WebSocket-virhe: {e}")
                self.is_ready = False
                log.info("🔄 Stoat: Yritetään yhdistää uudelleen 10 sekunnin kuluttua...")
                await asyncio.sleep(10)

    async def _handle_message(self, data: dict):
        """Handle incoming Stoat/Revolt message events"""
        author_id = data.get("author")
        content = data.get("content", "").strip()
        channel = data.get("channel")

        # Ignore own messages
        if author_id == self.bot_user_id:
            return

        # Only respond on configured channel (if set)
        if self.channel_id and channel != self.channel_id:
            return

        if not content.startswith("!"):
            return

        # Parse command
        parts = content.split(None, 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "!c":
            await self._cmd_execute(channel, args)
        elif command == "!train":
            await self._cmd_train(channel)
        elif command == "!verify":
            await self._cmd_verify(channel, args)
        elif command == "!unban":
            await self._cmd_unban(channel, args)
        elif command == "!vahvista":
            await self._cmd_confirm(channel, args)
        elif command == "!hylkaa":
            await self._cmd_reject(channel, args)

    async def _cmd_execute(self, channel: str, cmd: str):
        """Execute a PP2 command: !c /kick 1"""
        if not self.cmd_callback:
            self.send_message("❌ Komentojen suoritus ei ole käytössä.", channel)
            return

        if not cmd:
            self.send_message("❌ Käyttö: `!c <komento>`", channel)
            return

        self.send_message(f"🚀 Suoritetaan komento: `{cmd}`...", channel)

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.cmd_callback, cmd)

            if response:
                if len(response) > 1900:
                    response = response[:1900] + "... (katkaistu)"
                self.send_message(f"✅ **Palvelimen vastaus:**\n```\n{response}\n```", channel)
            else:
                self.send_message("✅ Komento lähetetty palvelimelle (ei vastausta).", channel)
        except Exception as e:
            self.send_message(f"❌ Virhe komennon suorituksessa: {str(e)}", channel)

    async def _cmd_train(self, channel: str):
        """Train ML model: !train"""
        self.send_message("🏃 Opetetaan mallia... Tämä voi kestää hetken.", channel)

        try:
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

            # Split if too long (Revolt max ~2000 chars)
            if len(output) > 1950:
                for i in range(0, len(output), 1950):
                    self.send_message(output[i:i+1950], channel)
            else:
                self.send_message(output, channel)
        except Exception as e:
            self.send_message(f"❌ Virhe opetuksen aikana: {str(e)}", channel)

    async def _cmd_verify(self, channel: str, args: str):
        """Toggle verify_all setting: !verify on/off/status"""
        if not self.config_callback:
            self.send_message("❌ Config-callback ei ole käytössä.", channel)
            return

        mode = args.strip().lower() if args.strip() else "status"

        if mode == "status":
            current = self.config_callback("get", None)
            status_emoji = "✅" if current else "❌"
            self.send_message(
                f"📋 **verify_all** on tällä hetkellä: {status_emoji} **{'päällä' if current else 'pois päältä'}**",
                channel
            )
            return

        if mode in ["on", "true", "1", "päällä"]:
            new_value = True
        elif mode in ["off", "false", "0", "pois"]:
            new_value = False
        else:
            self.send_message("❌ Käyttö: `!verify on` tai `!verify off` tai `!verify status`", channel)
            return

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.config_callback, "set", new_value)

            if result:
                status_emoji = "✅" if new_value else "❌"
                self.send_message(
                    f"🔧 **verify_all** asetettu: {status_emoji} **{'päällä' if new_value else 'pois päältä'}**\n*Muutos on voimassa heti.*",
                    channel
                )
            else:
                self.send_message("❌ Asetuksen muuttaminen epäonnistui.", channel)
        except Exception as e:
            self.send_message(f"❌ Virhe: {str(e)}", channel)

    async def _cmd_unban(self, channel: str, args: str):
        """Unban a player: !unban <player_name>"""
        if not self.banlist_paths:
            self.send_message("❌ Ban-listojen polkuja ei ole määritetty asetuksissa.", channel)
            return

        try:
            loop = asyncio.get_event_loop()
            banned_players = await loop.run_in_executor(None, self._read_banlist)

            if not banned_players:
                self.send_message("📋 Ban-lista on tyhjä tai sitä ei voitu lukea.", channel)
                return

            if not args.strip():
                # List banned players
                lines = ["🔓 **Bannatut pelaajat:**\n"]
                for i, p in enumerate(banned_players[:25], 1):
                    lines.append(f"`{i}.` **{p['name']}** ({p['server']}) — IP: `{p['ip']}` — {p['minutes']} min")
                lines.append(f"\nPoista banni: `!unban <pelaajan_nimi>`")
                self.send_message("\n".join(lines), channel)
                return

            parsed = self._parse_command_args(args)
            target_name = parsed[0] if parsed else ""
            # Find matching player (case-insensitive)
            target = None
            for p in banned_players:
                if p['name'].lower() == target_name.lower():
                    target = p
                    break

            if not target:
                self.send_message(f"❌ Pelaajaa **{target_name}** ei löytynyt ban-listalta.", channel)
                return

            success = await self._remove_ban(target['ip'], target['name'], target.get('server'))
            if success:
                self.send_message(f"✅ Banni poistettu: **{target['name']}** ({target.get('server', '?')})", channel)
            else:
                self.send_message(f"❌ Bannin poisto epäonnistui: **{target['name']}**", channel)

        except Exception as e:
            log.error(f"❌ Virhe !unban komennossa (Stoat): {e}")
            self.send_message(f"❌ Virhe: {str(e)}", channel)

    async def _cmd_confirm(self, channel: str, args: str):
        """Confirm a moderation action: !vahvista <player> [SEVERITY]"""
        parsed = self._parse_command_args(args)
        if not parsed:
            self.send_message("❌ Käyttö: `!vahvista <pelaaja> [SEVERE/MODERATE/MINOR/OK]`", channel)
            return

        player_name = parsed[0]
        severity = parsed[1].upper() if len(parsed) > 1 else None

        key, pending = self._find_pending(player_name)
        if not pending:
            self.send_message(f"❌ Ei odottavaa moderointia pelaajalle: **{player_name}**", channel)
            return

        selected_severity = severity if severity in ["SEVERE", "MODERATE", "MINOR", "OK"] else pending['severity']
        server_name = pending.get('server_name', '?')

        self.send_message(f"⌛ Suoritetaan toimenpide tasolla: **{selected_severity}** ({server_name})...", channel)
        try:
            await pending['confirm'](selected_severity)
            self.send_message(f"✅ Toimenpide suoritettu: **{player_name}** ({selected_severity}) — {server_name}", channel)
        except Exception as e:
            self.send_message(f"❌ Virhe: {str(e)}", channel)
        finally:
            self._pending_moderations.pop(key, None)

    async def _cmd_reject(self, channel: str, args: str):
        """Reject a moderation action: !hylkaa <player>"""
        parsed = self._parse_command_args(args)
        if not parsed:
            self.send_message("❌ Käyttö: `!hylkaa <pelaaja>`", channel)
            return

        player_name = parsed[0]
        key, pending = self._find_pending(player_name)

        if not pending:
            self.send_message(f"❌ Ei odottavaa moderointia pelaajalle: **{player_name}**", channel)
            return

        try:
            await pending['reject']()
            self.send_message(f"❌ Hylätty: **{player_name}**", channel)
        except Exception as e:
            self.send_message(f"❌ Virhe: {str(e)}", channel)
        finally:
            self._pending_moderations.pop(key, None)

    # ── Banlist Management (shared logic with discord_bot.py) ─────────

    def _read_banlist(self) -> list:
        """Read and parse the ban.dat files from all servers"""
        all_players = []

        for server_name, path in self.banlist_paths.items():
            if not path or not os.path.exists(path):
                continue

            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

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
                        current_player[key.strip()] = value.strip()

                # Handle last entry
                if 'Name' in current_player and 'Address' in current_player:
                    current_player['server'] = server_name
                    all_players.append(current_player)

            except Exception as e:
                log.error(f"❌ Virhe ban-listan luvussa ({server_name}): {e}")

        # Deduplicate
        unique_players = {}
        for p in all_players:
            name = p.get('Name', 'Unknown')
            ip = p.get('Address', 'Unknown')
            server = p.get('server', 'Unknown')
            key = (server, name, ip)
            unique_players[key] = {
                'name': name, 'ip': ip,
                'minutes': p.get('Minutes', '?'),
                'server': server, 'raw': p
            }

        return list(unique_players.values())

    async def _remove_ban(self, ip: str, name: str, server: Optional[str] = None) -> bool:
        """Remove a ban from the file"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._remove_ban_sync, ip, name, server)
        except Exception as e:
            log.error(f"❌ Stoat: Async wrapper error: {e}")
            return False

    def _remove_ban_sync(self, ip: str, name: str, server: Optional[str] = None) -> bool:
        """Synchronous file operation to remove ban"""
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

            def is_target_block(buf_lines, target_ip, target_name):
                parsed_data = {}
                for line in buf_lines:
                    if '=' in line:
                        parts = line.split('=', 1)
                        parsed_data[parts[0].strip()] = parts[1].strip()
                if 'Name' in parsed_data and 'Address' in parsed_data:
                    return parsed_data['Name'] == target_name and parsed_data['Address'] == target_ip
                return False

            for line in lines:
                if not line.strip():
                    if buffer:
                        if is_target_block(buffer, ip, name):
                            log.info(f"🗑️ Poistetaan ban-lohko (Stoat): {name} / {ip}")
                        else:
                            new_lines.extend(buffer)
                        buffer = []
                    new_lines.append(line)
                    continue
                buffer.append(line)

            if buffer:
                if is_target_block(buffer, ip, name):
                    log.info(f"🗑️ Poistetaan viimeinen ban-lohko (Stoat): {name} / {ip}")
                else:
                    new_lines.extend(buffer)

            with open(target_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            return True

        except Exception as e:
            log.error(f"❌ Virhe ban-listan kirjoituksessa ({target_path}): {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
