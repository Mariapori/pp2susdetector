"""
PP2 Suspicious Detector
Main application that monitors PP2 host logs and detects rule violations using Machine Learning.
"""

import os
import time
import yaml
import threading
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from log_parser import LogParser, ChatMessage, PlayerJoinEvent
from ml_analyzer import MLAnalyzer
from action_handler import ActionHandler
from discord_bot import DiscordBot
from database import Database
from logger import log


class ServerMonitor:
    """Monitors a single PP2 server instance"""
    
    def __init__(self, server_config: dict, detector: 'PP2Detector'):
        self.server_config = server_config
        self.detector = detector
        self.name = server_config.get('name', 'Unknown Server')
        self.chatlog_path = server_config.get('chatlog_path')
        self.playlog_path = server_config.get('playlog_path')
        
        self.processed_messages = set()
        self.processed_players = set()
        self.player_sessions = {}
        
        # Admin password discovery for this server
        self.admin_password = server_config.get('admin_password') or os.getenv('ADMIN_PASSWORD')
        if not self.admin_password:
             self.admin_password = self._discover_admin_password()
             # Update config in memory so we don't scan again
             self.server_config['admin_password'] = self.admin_password

    def _discover_admin_password(self) -> Optional[str]:
        container_name = self.server_config.get('container_name')
        if not container_name: return None
        
        log.info(f"🔍 Etsitään admin-salasanaa palvelimelle '{self.name}' (kontti: {container_name})...")
        
        try:
            import docker
        except ImportError:
            log.warning(f"⚠️ 'docker' kirjastoa ei ole asennettu. Ohitetaan automaattinen salasanan etsintä ({self.name}).")
            return None

        max_retries = 3
        
        for i in range(max_retries):
            try:
                client = docker.from_env()
                try:
                    container = client.containers.get(container_name)
                    logs = container.logs().decode('utf-8')
                    import re
                    match = re.search(r"Generated password: (\w+)", logs)
                    if match:
                        log.info(f"✅ Admin-salasana löytyi Docker-kontista '{container_name}'")
                        return match.group(1).strip()
                except Exception as e:
                    log.warning(f"⚠️ Konttia '{container_name}' ei löytynyt tai lokien luku epäonnistui: {e}")
            except Exception as e:
                log.warning(f"⚠️ Docker-virhe: {e}")
            
            if i < max_retries - 1:
                time.sleep(2)
        return None

    def start(self):
        log.info(f"🚀 Käynnistetään valvonta palvelimelle: {self.name}")
        if self.chatlog_path:
            threading.Thread(target=self.monitor_chatlog, daemon=True, name=f"ChatMon-{self.name}").start()
        if self.playlog_path:
            threading.Thread(target=self.monitor_playlog, daemon=True, name=f"PlayMon-{self.name}").start()

    def tail_file(self, filepath: str, label: str, start_at_end: bool = True):
        """Tail a file and yield new lines with heartbeat"""
        if not os.path.exists(filepath):
            log.error(f"🛑 Tiedostoa ei löydy ({self.name}): {filepath}")
            return
            
        log.info(f"📖 Aloitetaan seuranta [{self.name}] ({label}): {filepath} (alusta: {not start_at_end})")
        
        pos = 0
        if start_at_end:
            pos = os.path.getsize(filepath)
        
        last_heartbeat = time.time()
        
        while True:
            try:
                if not os.path.exists(filepath):
                     time.sleep(5)
                     continue
                     
                current_size = os.path.getsize(filepath)
                if current_size < pos:
                    log.info(f"🔄 Tiedosto muuttunut merkittävästi [{self.name}] ({label}), resetoidaan indeksi.")
                    pos = 0

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        f.seek(pos)
                        while True:
                            line = f.readline()
                            if line:
                                yield line
                                pos = f.tell()
                                last_heartbeat = time.time()
                            else:
                                break
                except UnicodeDecodeError:
                    with open(filepath, 'r', encoding='cp1252', errors='replace') as f:
                        f.seek(pos)
                        while True:
                            line = f.readline()
                            if line:
                                yield line
                                pos = f.tell()
                                last_heartbeat = time.time()
                            else:
                                break

                # Heartbeat
                current_size = os.path.getsize(filepath)
                if time.time() - last_heartbeat > 120:
                    log.debug(f"💓 Seuranta käynnissä [{self.name}] ({label}) - Pos: {pos}")
                    last_heartbeat = time.time()
                
                time.sleep(1)
                if os.path.exists(filepath) and os.path.getsize(filepath) != current_size:
                    continue
            except Exception as e:
                log.error(f"❌ Virhe tiedoston {label} luvussa [{self.name}]: {e}")
                time.sleep(5)

    def monitor_chatlog(self):
        log.info(f"👀 Valvotaan chat-lokia [{self.name}]: {self.chatlog_path}")
        pending_name_line = None
        
        for line in self.tail_file(self.chatlog_path, "chat", start_at_end=True):
            line = line.strip('\r\n')
            if not line: continue
            
            import re
            name_time_match = re.search(r'^(.+?):\s+\[(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\]\s*$', line)
            
            if name_time_match:
                pending_name_line = line
                continue
            
            if pending_name_line:
                full_entry = f"{pending_name_line}\n{line}"
                message = self.detector.parser.parse_chat_message(full_entry, "")
                if message:
                    self.process_chat_message(message)
                pending_name_line = None

    def monitor_playlog(self):
        log.info(f"👀 Valvotaan pelaajalokia [{self.name}]: {self.playlog_path}")
        for line in self.tail_file(self.playlog_path, "play", start_at_end=True):
            try:
                je = self.detector.parser.parse_player_join(line)
                if je: self.process_player_join(je)
            except Exception as e: log.error(f"❌ Virhe pelaaja-monitorissa [{self.name}]: {e}")

    def _find_historical_session(self, player_name: str) -> Optional[dict]:
        try:
            with open(self.playlog_path, 'r', encoding='latin-1', errors='replace') as f:
                for line in f:
                    if player_name in line:
                        je = self.detector.parser.parse_player_join(line)
                        if je and je.player_name == player_name:
                            return {'ip': je.ip_address, 'ban_command': je.ban_command, 'name_with_ids': je.name_with_ids}
            return None
        except Exception: return None

    def process_chat_message(self, message: ChatMessage):
        msg_id = f"{message.timestamp}:{message.player_name}:{message.message}"
        if msg_id in self.processed_messages: return

        player_ip = None
        ban_command = None
        name_with_ids = None

        session = self.player_sessions.get(message.player_name)
        if not session:
            session = self._find_historical_session(message.player_name)
            if session: self.player_sessions[message.player_name] = session
        
        if session:
            player_ip = session.get('ip')
            ban_command = session.get('ban_command')
            name_with_ids = session.get('name_with_ids')

        ignored_senders = ["Server", "ADMIN", "system"]
        if message.player_name in ignored_senders or not message.player_name.strip():
            self.processed_messages.add(msg_id)
            return

        self.processed_messages.add(msg_id)
        log.info(f"📨 [{self.name}] Viesti ({message.player_name}): {message.message[:100]}")
        
        if message.message.strip().startswith("!yllapitaja"):
            log.info(f"🆘 Avunpyyntö [{self.name}]: {message.player_name}")
            self.detector.action_handler.handle_help_request(
                message.player_name, message.message, player_ip
            )
            return

        analysis = self.detector.analyzer.analyze_message(message.player_name, message.message)
        
        verify_all = self.detector.config.get('discord', {}).get('verify_all', False)
        
        if analysis.level != "OK" or verify_all:
            if analysis.level == "OK" and verify_all:
                log.info(f"🔍 Tarkastetaan viesti (verify_all) [{self.name}]: {message.message[:100]}")
                analysis.reason = "Manuaalinen tarkastus (kaikki viestit)"
                if analysis.level == "OK":
                    analysis.level = "MINOR" 
            
            log.warning(f"🚨 RIKKOMUS [{self.name}]: {analysis.level}")
            self.detector.db.add_violation(
                timestamp=message.timestamp, player_name=message.player_name,
                violation_type="message", content=message.message,
                level=analysis.level, reason=analysis.reason,
                suggested_action=analysis.suggested_action, ip_address=player_ip
            )
            self.detector.action_handler.handle_violation(
                self.name, self.server_config,
                message.player_name, "message", message.message, analysis,
                player_ip, ban_command, name_with_ids
            )

    def process_player_join(self, join_event: PlayerJoinEvent):
        self.player_sessions[join_event.player_name] = {
            'ip': join_event.ip_address, 'ban_command': join_event.ban_command,
            'name_with_ids': join_event.name_with_ids
        }
        player_id = f"{join_event.player_name}:{join_event.ip_address}"
        if player_id in self.processed_players: return
        self.processed_players.add(player_id)
        
        log.info(f"👤 [{self.name}] Liittyi: {join_event.player_name} ({join_event.ip_address})")
        analysis = self.detector.analyzer.analyze_nickname(join_event.player_name)
        if analysis.level != "OK":
            log.warning(f"🚨 NIMIRIKKOMUS [{self.name}]: {analysis.level}")
            self.detector.db.add_violation(
                timestamp=join_event.timestamp, player_name=join_event.player_name,
                violation_type="nickname", content=join_event.player_name,
                level=analysis.level, reason=analysis.reason,
                suggested_action=analysis.suggested_action, ip_address=join_event.ip_address
            )
            self.detector.action_handler.handle_violation(
                self.name, self.server_config,
                join_event.player_name, "nickname", join_event.player_name, analysis,
                join_event.ip_address, join_event.ban_command, join_event.name_with_ids
            )
        
        # Welcome message regardless of violation (since actions are manual)
        try:
            # Give server a moment to register the player fully
            time.sleep(1)
            live_index = self.detector.action_handler.get_live_player_index(join_event.player_name, self.server_config)
            if live_index:
                welcome_msg = f"/{live_index} Tervetuloa {join_event.player_name}! Valvon tätä palvelinta. Käytä !yllapitaja komentoa jos tarvitset apua."
                log.info(f"👋 Lähetetään tervetuloviesti pelaajalle {join_event.player_name} (ID: {live_index})")
                threading.Thread(target=self.detector.action_handler.execute_command, args=(welcome_msg, self.server_config)).start()
            else:
                log.warning(f"⚠️ Ei voitu lähettää tervetuloviestiä: Pelaajan ID ei löytynyt ({join_event.player_name})")
        except Exception as e:
            log.error(f"❌ Virhe tervetuloviestin lähetyksessä: {e}")


class PP2Detector:
    """Main detector application"""
    
    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Convert single server config to list if needed
        self._normalize_config()

        self.parser = LogParser()
        model_path = os.getenv('ML_MODEL_PATH') or self.config['ml'].get('model_path', 'models/violation_model.joblib')
        self.analyzer = MLAnalyzer(model_path=model_path)
        
        self.discord_bot = None
        bot_token = os.getenv("DISCORD_BOT_TOKEN")
        
        # We need to pick a banlist path for the bot if possible. 
        # With multiple servers, there are multiple banlists.
        # Ideally the bot can handle multiple, or we aggregate.
        # For now, let's use the first server's banlist as 'default' for global bot ops.
        if bot_token:
            log.info("🤖 Alustetaan Discord-botti...")
            server_banlists = {}
            if self.config.get('servers'):
                for srv in self.config['servers']:
                    if srv.get('banlist_path'):
                        server_banlists[srv.get('name', 'Unknown')] = srv.get('banlist_path')
            
            self.discord_bot = DiscordBot(bot_token, server_banlists=server_banlists)
        
        # Action Handler (global)
        # We don't pass specific admin creds here anymore effectively, 
        # or we pass defaults. But execute_command will require server_config now.
        self.action_handler = ActionHandler(
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            discord_enabled=self.config['discord']['enabled'],
            # Globals/Defaults if needed:
            pp2_admin_url=None, 
            pp2_admin_user="admin",
            pp2_admin_password=None,
            discord_bot=self.discord_bot
        )
        
        self.config_path = config_path
        
        if self.discord_bot:
            self.discord_bot.set_command_callback(self._handle_bot_command)
            self.discord_bot.set_config_callback(self._handle_config_update)
            # Pass full server list to bot if needed, or bot calls back to us
        
        Path("data").mkdir(exist_ok=True)
        self.db = Database("data/violations.db")
        
        self.monitors: List[ServerMonitor] = []
        for server_conf in self.config['servers']:
            self.monitors.append(ServerMonitor(server_conf, self))
            
        log.info(f"✅ Detector alustettu - Valvottavia palvelimia: {len(self.monitors)}")

    def _normalize_config(self):
        """Convert old config format to new format if necessary"""
        if 'servers' not in self.config:
            log.info("ℹ️ Muunnetaan vanha konfiguraatio uuteen monipalvelinmuotoon...")
            pp2_conf = self.config.get('pp2', {})
            server_config = {
                'name': 'Main Server',
                'chatlog_path': pp2_conf.get('chatlog_path'),
                'playlog_path': pp2_conf.get('playlog_path'),
                'banlist_path': pp2_conf.get('banlist_path'),
                'container_name': pp2_conf.get('container_name'),
                'admin_url': pp2_conf.get('admin_url'),
                'admin_user': pp2_conf.get('admin_user', 'admin'),
                'admin_password': pp2_conf.get('admin_password')
            }
            self.config['servers'] = [server_config]
            # Keep 'pp2' for legacy reasons or remove? Let's keep it in memory but not rely on it.

    def _handle_bot_command(self, full_command: str) -> Optional[str]:
        """
        Handle commands from bot:
        !c /kick 1  -> executes on first server
        !c server2 /kick 1 -> executes on server2
        """
        parts = full_command.strip().split(' ', 1)
        if not parts: return "Tyhjä komento"
        
        first_part = parts[0]
        
        # Check if first part matches a server name
        target_monitor = None
        cmd_to_run = full_command
        
        # Try exact match or partial match
        for mon in self.monitors:
            if mon.name.lower() == first_part.lower():
                target_monitor = mon
                cmd_to_run = parts[1] if len(parts) > 1 else ""
                break
        
        if not target_monitor:
            # Default to first server
            if self.monitors:
                target_monitor = self.monitors[0]
            else:
                return "Virhe: Ei palvelimia määritetty."

        log.info(f"🤖 Bot-komento ohjataan palvelimelle '{target_monitor.name}': {cmd_to_run}")
        return self.action_handler.execute_command(cmd_to_run, target_monitor.server_config)

    def _handle_config_update(self, action: str, value: Optional[bool]) -> bool:
        if action == "get":
            return self.config.get('discord', {}).get('verify_all', False)
        elif action == "set":
            try:
                if 'discord' not in self.config:
                    self.config['discord'] = {}
                self.config['discord']['verify_all'] = value
                
                # Careful: if we write back, we might overwrite the user's manual config structure
                # if we did internal normalization. 
                # Ideally, we should update the file preserving comments, but yaml lib kills comments.
                # For now, just dumping the structure is safer for functionality.
                
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                
                log.info(f"🔧 verify_all asetettu: {value}")
                return True
            except Exception as e:
                log.error(f"❌ Virhe config-päivityksessä: {e}")
                return False
        return False

    def run(self):
        log.info("🚀 Käynnistetään PP2 Suspicious Detector (Multi-Server)...")
        if self.discord_bot: self.discord_bot.start_in_thread()
        
        for monitor in self.monitors:
            monitor.start()
        
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt: log.info("👋 Lopetetaan...")

def main():
    PP2Detector().run()

if __name__ == "__main__":
    main()
