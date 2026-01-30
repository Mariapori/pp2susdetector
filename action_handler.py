"""
Action Handler
Handles actions based on violation severity: Discord notifications and logging.
"""

import requests
import json
import asyncio
import csv
import os
from datetime import datetime
from typing import Optional, Any
from ml_analyzer import AnalysisResult, ViolationLevel
from logger import log


class ActionHandler:
    """Handles actions for detected violations"""
    
    def __init__(
        self, 
        discord_webhook_url: Optional[str] = None, 
        discord_enabled: bool = True,
        pp2_admin_url: Optional[str] = None,
        pp2_admin_user: str = "admin",
        pp2_admin_password: Optional[str] = None,
        discord_bot: Optional[Any] = None
    ):
        """
        Initialize action handler
        """
        self.discord_webhook_url = discord_webhook_url
        self.discord_enabled = discord_enabled and discord_webhook_url is not None
        self.pp2_admin_url = pp2_admin_url
        self.pp2_admin_user = pp2_admin_user
        self.pp2_admin_password = pp2_admin_password
        self.discord_bot = discord_bot
    
    def handle_violation(
        self,
        player_name: str,
        violation_type: str,
        content: str,
        analysis: AnalysisResult,
        ip_address: Optional[str] = None,
        ban_command: Optional[str] = None,
        name_with_ids: Optional[str] = None
    ):
        if analysis.level == "OK":
            return
        
        # Log to console
        self._log_violation(player_name, violation_type, content, analysis, ip_address)
        
        # Priority: interaction via Bot first, fallback to standard webhook
        if self.discord_bot and analysis.level in ["SEVERE", "MODERATE", "MINOR"]:
             self._send_interactive_notification(
                player_name, violation_type, content, analysis, ip_address, ban_command, name_with_ids
            )
        elif self.discord_enabled and analysis.level in ["SEVERE", "MODERATE", "MINOR"]:
            self._send_discord_notification(
                player_name, violation_type, content, analysis, ip_address, ban_command
            )

    def handle_help_request(
        self,
        player_name: str,
        content: str,
        ip_address: Optional[str] = None
    ):
        """Handle a help request (!yllapitaja) from a player"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🆘 [{timestamp}] AVUNPYYNTÖ")
        print(f"Pelaaja: {player_name}")
        if ip_address: print(f"IP: {ip_address}")
        print(f"Viesti: {content}")
        print("-" * 80)

        if self.discord_enabled and self.discord_webhook_url:
            color = 0x00FF00 # Green for help requests
            fields = [
                {"name": "Pelaaja", "value": player_name, "inline": True},
                {"name": "Tyyppi", "value": "🆘 Avunpyyntö", "inline": True}
            ]
            if ip_address: fields.append({"name": "IP-osoite", "value": f"`{ip_address}`", "inline": True})
            fields.append({"name": "Viesti", "value": f"```{content}```", "inline": False})
            
            payload = {
                "embeds": [{
                    "title": "🆘 APUA TARVITAAN",
                    "color": color,
                    "fields": fields,
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "PP2 Suspicious Detector"}
                }]
            }
            try:
                requests.post(self.discord_webhook_url, json=payload, timeout=10)
            except Exception as e: print(f"❌ Virhe avunpyynnön lähetyksessä Discordiin: {e}")
    
    def _log_violation(self, player_name, violation_type, content, analysis, ip_address):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_emoji = {"SEVERE": "🚨", "MODERATE": "⚠️", "MINOR": "📝", "OK": "✅"}
        emoji = level_emoji.get(analysis.level, "❓")
        log.info(f"\n{emoji} [{timestamp}] {analysis.level} VIOLATION")
        log.info(f"Player: {player_name}")
        if ip_address: log.info(f"IP: {ip_address}")
        log.info(f"Type: {violation_type}")
        log.info(f"Content: {content}")
        log.info(f"Reason: {analysis.reason}")
        log.info(f"Suggested Action: {analysis.suggested_action}")
        log.info("-" * 80)
    
    def _send_discord_notification(self, player_name, violation_type, content, analysis, ip_address, ban_command):
        if not self.discord_webhook_url: return
        color = {"SEVERE": 0xFF0000, "MODERATE": 0xFFA500, "MINOR": 0xFFFF00}.get(analysis.level, 0x808080)
        title = {"SEVERE": "🚨 VAKAVA RIKKOMUS", "MODERATE": "⚠️ KESKIVAKAVA RIKKOMUS", "MINOR": "📝 LIEVÄ RIKKOMUS"}.get(analysis.level, "❓ Rikkomus")
        fields = [
            {"name": "Pelaaja", "value": player_name, "inline": True},
            {"name": "Tyyppi", "value": "Chat-viesti" if violation_type == "message" else "Nimimerkki", "inline": True}
        ]
        if ip_address: fields.append({"name": "IP-osoite", "value": f"`{ip_address}`", "inline": True})
        fields.append({"name": "Sisältö", "value": f"```{content[:1000]}```", "inline": False})
        fields.append({"name": "Perustelu", "value": analysis.reason, "inline": False})
        fields.append({"name": "Ehdotettu toimenpide", "value": f"`{analysis.suggested_action}`", "inline": False})
        if ban_command and analysis.level == "SEVERE":
            fields.append({"name": "Ban-komento", "value": f"```{ban_command}```", "inline": False})
        payload = {"embeds": [{"title": title, "color": color, "fields": fields, "timestamp": datetime.utcnow().isoformat(), "footer": {"text": "PP2 Suspicious Detector"}}]}
        try:
            requests.post(self.discord_webhook_url, json=payload, timeout=10)
        except Exception as e: log.error(f"❌ Error sending Discord notification: {e}")

    def execute_command(self, command: str) -> Optional[str]:
        """Standard version of command execution (synchronous)
        Returns the server response text if successful.
        """
        if not self.pp2_admin_url or not self.pp2_admin_password: return None
        log.info(f"🚀 Suoritetaan PP2-komento: {command}")
        try:
            from requests.auth import HTTPBasicAuth
            response = requests.post(
                self.pp2_admin_url, data={'c': command},
                auth=HTTPBasicAuth(self.pp2_admin_user, self.pp2_admin_password),
                headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': self.pp2_admin_url},
                timeout=10
            )
            if response.status_code == 200:
                log.info(f"✅ Komento suoritettu")
                return self._parse_admin_response(response.text)
            else:
                log.error(f"❌ Komento epäonnistui: {response.status_code}")
                return f"Virhe: Palvelin vastasi tilakoodilla {response.status_code}"
        except Exception as e:
            log.error(f"❌ Virhe komennon '{command}' suorituksessa: {e}")
            return f"Virhe: {str(e)}"

    def _save_to_training_data(self, text: str, label: str):
        """Save a new sample to the training data CSV"""
        data_file = "data/training_data.csv"
        try:
            # Ensure directory exists but don't overwrite the file
            os.makedirs("data", exist_ok=True)
            
            # Check if file exists to decide whether to write header
            file_exists = os.path.isfile(data_file)
            
            # Sanitize input: remove commas as they break CSV format
            text = text.replace(",", "")
            
            # Check if we need to add a newline before appending
            needs_newline = False
            if file_exists and os.path.getsize(data_file) > 0:
                try:
                    with open(data_file, 'rb') as f:
                        f.seek(-1, os.SEEK_END)
                        last_char = f.read(1)
                        if last_char not in [b'\n', b'\r']:
                            needs_newline = True
                except Exception:
                    pass

            with open(data_file, mode='a', newline='', encoding='utf-8') as f:
                if needs_newline:
                    f.write('\n')
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["text", "label"])
                writer.writerow([text, label])
            
            log.info(f"💾 Tallennettu opetusdataa: '{text[:30]}...' -> {label}")
        except Exception as e:
            log.error(f"❌ Virhe opetusdatan tallennuksessa: {e}")

    def _parse_admin_response(self, html_content: str) -> str:
        """Extract the relevant response content from the admin HTML"""
        try:
            import re
            # PP2 admin response is usually in a <textarea>
            match = re.search(r'<textarea[^>]*>(.*?)</textarea>', html_content, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # Remove common boilerplate if present
                content = content.replace("Command executed.", "").strip()
                return content
            
            # Fallback for other types of success messages
            if "Command executed" in html_content:
                return "Komento suoritettu onnistuneesti."
                
            return "Komento lähetetty, mutta vastausta ei voitu jäsentää."
        except Exception:
            return "Virhe vastauksen käsittelyssä."

    def _get_live_player_index(self, player_name: str) -> Optional[str]:
        if not self.pp2_admin_url or not self.pp2_admin_password: return None
        try:
            import re
            from requests.auth import HTTPBasicAuth
            response = requests.get(
                self.pp2_admin_url, auth=HTTPBasicAuth(self.pp2_admin_user, self.pp2_admin_password), timeout=5
            )
            if response.status_code != 200: return None
            pattern = re.compile(rf"\[(\d+)\]\s+{re.escape(player_name)}", re.IGNORECASE)
            match = pattern.search(response.text)
            if match: return match.group(1)
            fallback_pattern = re.compile(rf"\[(\d+)\]\s+[^<]*{re.escape(player_name)}", re.IGNORECASE)
            match = fallback_pattern.search(response.text)
            if match: return match.group(1)
            return None
        except Exception: return None

    def _send_interactive_notification(
        self,
        player_name: str,
        violation_type: str,
        content: str,
        analysis: AnalysisResult,
        ip_address: Optional[str],
        ban_command: Optional[str],
        name_with_ids: Optional[str]
    ):
        """Send a Discord message with buttons for approval"""
        async def confirm_callback(severity: str):
            # If severity is OK, just return
            if severity == "OK":
                log.info(f"✅ Toimenpide pelaajalle {player_name} valittu 'OK' (ei toimenpiteitä)")
                await asyncio.to_thread(self._save_to_training_data, content, "OK")
                return

            # Determine command template based on selected severity
            if severity == "SEVERE":
                cmd_template = ban_command if ban_command else "/banaddress {ip} 9999999 {full_name}"
            elif severity == "MODERATE":
                cmd_template = "/kick {index}"
            elif severity == "MINOR":
                cmd_template = None # No automated command for minor, maybe just a log?
                log.info(f"📝 {player_name}: {content} (MINOR) - Ei automaattista komentoa")
            else:
                cmd_template = None

            if cmd_template:
                # Basic substitution
                cmd = cmd_template.replace("{name}", player_name)
                if "{full_name}" in cmd:
                    cmd = cmd.replace("{full_name}", name_with_ids if name_with_ids else player_name)
                
                # Resolve index in thread
                if "{index}" in cmd:
                    live_index = await asyncio.to_thread(self._get_live_player_index, player_name)
                    cmd = cmd.replace("{index}", str(live_index) if live_index else player_name)
                
                if ip_address:
                    cmd = cmd.replace("{ip}", ip_address)
                
                # Execute primary command in thread
                await asyncio.to_thread(self.execute_command, cmd)
                
                # Follow up with kick if it was a ban
                if "/banaddress" in cmd:
                    live_index = await asyncio.to_thread(self._get_live_player_index, player_name)
                    kick_cmd = f"/kick {str(live_index) if live_index else player_name}"
                    await asyncio.to_thread(self.execute_command, kick_cmd)
            
            # Save as training data with the SELECTED severity
            await asyncio.to_thread(self._save_to_training_data, content, severity)

        async def reject_callback():
            log.info(f"🚫 Toimenpide pelaajalle {player_name} hylätty Discordin kautta")
            # Save as training data (it was OK)
            await asyncio.to_thread(self._save_to_training_data, content, "OK")

        embed_data = {
            'title': f"🛡️ MODEROINTIPYYNTÖ: {analysis.level}",
            'description': f"Pelaaja **{player_name}** {'tarkastetaan (kaikki viestit)' if analysis.reason == 'Manuaalinen tarkastus (kaikki viestit)' else 'rikkoi sääntöjä.'}",
            'color': 0xFF0000 if analysis.level == "SEVERE" else 0xFFA500 if analysis.level == "MODERATE" else 0x808080,
            'severity': analysis.level, # Initial severity for the dropdown
            'fields': [
                {'name': 'Pelaaja', 'value': f"`{player_name}`", 'inline': True},
                {'name': 'Tyyppi', 'value': violation_type, 'inline': True},
                {'name': 'Sisältö', 'value': f"```{content}```", 'inline': False},
                {'name': 'Syy', 'value': analysis.reason, 'inline': False},
                {'name': 'Suositus', 'value': f"`{analysis.suggested_action}`", 'inline': False}
            ]
        }
        
        asyncio.run_coroutine_threadsafe(
            self.discord_bot.send_interaction(embed_data, confirm_callback, reject_callback),
            self.discord_bot.bot.loop
        )
