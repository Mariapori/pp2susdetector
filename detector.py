"""
PP2 Suspicious Detector
Main application that monitors PP2 host logs and detects rule violations using Machine Learning.
"""

import os
import time
import yaml
import threading
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from log_parser import LogParser, ChatMessage, PlayerJoinEvent
from ml_analyzer import MLAnalyzer
from action_handler import ActionHandler
from discord_bot import DiscordBot
from database import Database
from logger import log


class PP2Detector:
    """Main detector application"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the detector
        """
        load_dotenv()
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.parser = LogParser()
        model_path = os.getenv('ML_MODEL_PATH') or self.config['ml'].get('model_path', 'models/violation_model.joblib')
        self.analyzer = MLAnalyzer(model_path=model_path)
        
        self.discord_bot = None
        bot_token = os.getenv("DISCORD_BOT_TOKEN")
        if bot_token:
            log.info("🤖 Alustetaan Discord-botti...")
            self.discord_bot = DiscordBot(bot_token)

        pp2_admin_password = os.getenv('ADMIN_PASSWORD') or self.config['pp2'].get('admin_password')
        if not pp2_admin_password:
            pp2_admin_password = self._discover_admin_password()

        self.action_handler = ActionHandler(
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            discord_enabled=self.config['discord']['enabled'],
            pp2_admin_url=self.config['pp2'].get('admin_url'),
            pp2_admin_user=self.config['pp2'].get('admin_user', 'admin'),
            pp2_admin_password=pp2_admin_password,
            discord_bot=self.discord_bot
        )
        
        # Store config path for updates
        self.config_path = config_path
        
        if self.discord_bot:
            self.discord_bot.set_command_callback(self.action_handler.execute_command)
            self.discord_bot.set_config_callback(self._handle_config_update)
        
        Path("data").mkdir(exist_ok=True)
        self.db = Database("data/violations.db")
        
        self.processed_messages = set()
        self.processed_players = set()
        self.player_sessions = {}
        
        log.info("✅ Detector alustettu")

    def _discover_admin_password(self) -> Optional[str]:
        log.info("🔍 Etsitään admin-salasanaa...")
        
        try:
            import docker
        except ImportError:
            log.warning("⚠️ 'docker' kirjastoa ei ole asennettu. Ohitetaan automaattinen salasanan etsintä.")
            return None

        max_retries = 5 # Reduced retries for local execution if docker is present but fails
        retry_delay = 5
        
        container_name = self.config['pp2'].get('container_name', 'pp2host')
        
        for i in range(max_retries):
            try:
                client = docker.from_env()
                # Check if we can even talk to docker
                client.ping()
                
                import re
                try:
                    container = client.containers.get(container_name)
                    logs = container.logs().decode('utf-8')
                    match = re.search(r"Generated password: (\w+)", logs)
                    if match:
                        log.info(f"✅ Admin-salasana löytyi Docker-kontista '{container_name}'")
                        return match.group(1).strip()
                except Exception as e:
                    log.warning(f"⚠️ Konttia '{container_name}' ei löytynyt tai lokien luku epäonnistui: {e}")
                    # If the container isn't found, we can't really retry successfully unless it's starting up
                
            except Exception as e:
                log.warning(f"⚠️ Docker-virhe: {e}")
            
            if i < max_retries - 1:
                log.info(f"🔄 Yritetään uudelleen {retry_delay}s kuluttua ({i+1}/{max_retries})...")
                time.sleep(retry_delay)
        
        return None
    
    def _handle_config_update(self, action: str, value: Optional[bool]) -> bool:
        """Handle config updates from Discord commands"""
        if action == "get":
            # Return current verify_all value
            return self.config.get('discord', {}).get('verify_all', False)
        elif action == "set":
            try:
                # Update in-memory config
                if 'discord' not in self.config:
                    self.config['discord'] = {}
                self.config['discord']['verify_all'] = value
                
                # Save to config file
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                
                if 'discord' not in full_config:
                    full_config['discord'] = {}
                full_config['discord']['verify_all'] = value
                
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(full_config, f, default_flow_style=False, allow_unicode=True)
                
                log.info(f"🔧 verify_all asetettu: {value}")
                return True
            except Exception as e:
                log.error(f"❌ Virhe config-päivityksessä: {e}")
                return False
        return False
    
    def process_chat_message(self, message: ChatMessage, player_ip: str = None, ban_command: str = None, name_with_ids: str = None):
        msg_id = f"{message.timestamp}:{message.player_name}:{message.message}"
        if msg_id in self.processed_messages: return

        if not player_ip or not ban_command or not name_with_ids:
            session = self.player_sessions.get(message.player_name)
            if not session:
                session = self._find_historical_session(message.player_name)
                if session: self.player_sessions[message.player_name] = session
            if session:
                player_ip = player_ip or session.get('ip')
                ban_command = ban_command or session.get('ban_command')
                name_with_ids = name_with_ids or session.get('name_with_ids')

        ignored_senders = ["Server", "ADMIN", "system"]
        if message.player_name in ignored_senders or not message.player_name.strip():
            self.processed_messages.add(msg_id)
            return

        self.processed_messages.add(msg_id)
        log.info(f"📨 Analysoidaan viesti ({message.player_name}): {message.message[:100]}")
        
        # Check for help request command
        if message.message.strip().startswith("!yllapitaja"):
            print(f"🆘 Avunpyyntö havaittu pelaajalta {message.player_name}")
            self.action_handler.handle_help_request(
                message.player_name, message.message, player_ip
            )
            return

        print(f"📨 Analysoidaan viesti ({message.player_name}): {message.message[:100]}")
        
        analysis = self.analyzer.analyze_message(message.player_name, message.message)
        
        # Check if we should verify all messages
        verify_all = self.config.get('discord', {}).get('verify_all', False)
        
        if analysis.level != "OK" or verify_all:
            if analysis.level == "OK" and verify_all:
                # Force verification for OK messages if verify_all is enabled
                log.info(f"🔍 Tarkastetaan viesti (verify_all): {message.message[:100]}")
                # We use a special internal state or just MODERATE to trigger the UI
                # But we want to preserve the fact that ML thought it was OK
                analysis.reason = "Manuaalinen tarkastus (kaikki viestit)"
                # We'll use a slightly different color/title in Discord if we can, 
                # but for now, MODERATE will trigger the interactive buttons.
                if analysis.level == "OK":
                    analysis.level = "MINOR" 
            
            log.warning(f"🚨 RIKKOMUS TAI TARKASTUS HAVAITTU: {analysis.level}")
            self.db.add_violation(
                timestamp=message.timestamp, player_name=message.player_name,
                violation_type="message", content=message.message,
                level=analysis.level, reason=analysis.reason,
                suggested_action=analysis.suggested_action, ip_address=player_ip
            )
            self.action_handler.handle_violation(
                message.player_name, "message", message.message, analysis,
                player_ip, ban_command, name_with_ids
            )
    
    def process_player_join(self, join_event: PlayerJoinEvent):
        # Update session info
        self.player_sessions[join_event.player_name] = {
            'ip': join_event.ip_address, 'ban_command': join_event.ban_command,
            'name_with_ids': join_event.name_with_ids
        }
        player_id = f"{join_event.player_name}:{join_event.ip_address}"
        if player_id in self.processed_players: return
        self.processed_players.add(player_id)
        
        log.info(f"👤 Analysoidaan nimimerkki: {join_event.player_name} ({join_event.ip_address})")
        analysis = self.analyzer.analyze_nickname(join_event.player_name)
        if analysis.level != "OK":
            log.warning(f"🚨 NIMITASON RIKKOMUS: {analysis.level}")
            self.db.add_violation(
                timestamp=join_event.timestamp, player_name=join_event.player_name,
                violation_type="nickname", content=join_event.player_name,
                level=analysis.level, reason=analysis.reason,
                suggested_action=analysis.suggested_action, ip_address=join_event.ip_address
            )
            self.action_handler.handle_violation(
                join_event.player_name, "nickname", join_event.player_name, analysis,
                join_event.ip_address, join_event.ban_command, join_event.name_with_ids
            )
    
    def tail_file(self, filepath: str, label: str, start_at_end: bool = True):
        """Tail a file and yield new lines with heartbeat"""
        if not os.path.exists(filepath):
            log.error(f"🛑 Tiedostoa ei löydy: {filepath}")
            return
            
        log.info(f"📖 Aloitetaan seuranta ({label}): {filepath} (alusta: {not start_at_end})")
        
        pos = 0
        if start_at_end:
            pos = os.path.getsize(filepath)
        
        last_heartbeat = time.time()
        
        while True:
            try:
                current_size = os.path.getsize(filepath)
                if current_size < pos:
                    log.info(f"🔄 Tiedosto muuttunut merkittävästi ({label}), resetoidaan indeksi.")
                    pos = 0

                # Try to read the file. PP2 logs are usually CP1252 or UTF-8.
                # We use 'errors=replace' to avoid crashing, but we try to get the encoding right.
                try:
                    # First attempt with utf-8
                    with open(filepath, 'r', encoding='utf-8') as f:
                        f.seek(pos)
                        while True:
                            line = f.readline()
                            if line:
                                yield line
                                pos = f.tell()
                                last_heartbeat = time.time()
                            else:
                                break # No more lines in this read, break to re-evaluate file state
                except UnicodeDecodeError:
                    # Fallback to cp1252 (Windows)
                    with open(filepath, 'r', encoding='cp1252', errors='replace') as f:
                        f.seek(pos)
                        while True:
                            line = f.readline()
                            if line:
                                yield line
                                pos = f.tell()
                                last_heartbeat = time.time()
                            else:
                                break # No more lines in this read, break to re-evaluate file state

                # Heartbeat and sleep logic
                current_size = os.path.getsize(filepath) # Re-get current size after reading
                if time.time() - last_heartbeat > 120:
                    log.debug(f"💓 Seuranta käynnissä ({label}) - Pos: {pos}, Size: {current_size}")
                    last_heartbeat = time.time()
                
                time.sleep(1)
                # Check if file changed while sleeping
                if os.path.getsize(filepath) != current_size:
                    continue # File changed, re-enter outer loop to re-evaluate size and open
            except Exception as e:
                log.error(f"❌ Virhe tiedoston {label} luvussa: {e}")
                time.sleep(5)

    def monitor_chatlog(self):
        chatlog_path = self.config['pp2']['chatlog_path']
        log.info(f"👀 Valvotaan chat-lokia: {chatlog_path}")
        
        pending_name_line = None
        
        # Start from end to avoid re-analyzing history
        for line in self.tail_file(chatlog_path, "chat", start_at_end=True):
            line = line.strip('\r\n')
            if not line: continue
            
            # Use regex to detect Name: [Timestamp] line
            import re
            name_time_match = re.search(r'^(.+?):\s+\[(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\]\s*$', line)
            
            if name_time_match:
                # If we have a pending name line without a following message, 
                # it means the previous message was empty or something went wrong.
                # Just reset and use the new one.
                pending_name_line = line
                continue
            
            if pending_name_line:
                # We have a name line and now this line is presumably the message
                full_entry = f"{pending_name_line}\n{line}"
                message = self.parser.parse_chat_message(full_entry, "") # timestamp already in entry
                if message:
                    self.process_chat_message(message)
                pending_name_line = None
            else:
                # This line is not a name line and we don't have a pending name line.
                # It might be noise or part of a message we started tracking mid-entry.
                pass
    
    def monitor_playlog(self):
        playlog_path = self.config['pp2']['playlog_path']
        for line in self.tail_file(playlog_path, "play", start_at_end=True):
            try:
                je = self.parser.parse_player_join(line)
                if je: self.process_player_join(je)
            except Exception as e: log.error(f"❌ Virhe pelaaja-monitorissa: {e}")
    
    def _find_historical_session(self, player_name: str) -> Optional[dict]:
        playlog_path = self.config['pp2']['playlog_path']
        latest_session = None
        try:
            with open(playlog_path, 'r', encoding='latin-1', errors='replace') as f:
                for line in f:
                    if player_name in line:
                        je = self.parser.parse_player_join(line)
                        if je and je.player_name == player_name:
                            latest_session = {'ip': je.ip_address, 'ban_command': je.ban_command, 'name_with_ids': je.name_with_ids}
            return latest_session
        except Exception: return None

    def run(self):
        log.info("🚀 Käynnistetään PP2 Suspicious Detector...")
        if self.discord_bot: self.discord_bot.start_in_thread()
        
        threading.Thread(target=self.monitor_chatlog, daemon=True).start()
        threading.Thread(target=self.monitor_playlog, daemon=True).start()
        
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt: log.info("👋 Lopetetaan...")

def main():
    PP2Detector().run()

if __name__ == "__main__":
    main()
