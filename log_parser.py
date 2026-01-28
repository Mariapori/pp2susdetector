"""
PP2 Log Parser
Parses PP2 host log files (chatlog.txt and playlog.txt) to extract player messages and join events.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PlayerJoinEvent:
    """Represents a player joining the game"""
    timestamp: str
    player_name: str
    ip_address: str
    version: str
    ban_command: str
    name_with_ids: str  # Everything after the minutes in /banaddress
    player_id: str


@dataclass
class ChatMessage:
    """Represents a chat message from a player"""
    timestamp: str
    player_name: str
    message: str


class LogParser:
    """Parser for PP2 host log files"""
    
    # Regex patterns for parsing log entries
    PLAYER_JOIN_PATTERN = re.compile(
        r'-->\s+(.+?)\s+joined the game\s+\(ip:\s+([0-9.]+)\)\.\s+\[(.+?)\]\s+\[\s*(/banaddress\s+.+?)\s*\]\s+\[(.+?)\]'
    )
    
    CHAT_MESSAGE_PATTERN = re.compile(
        r'^(.+?):\s+\[(.+?)\]\s*$',
        re.MULTILINE
    )
    
    TIMESTAMP_PATTERN = re.compile(r'\[(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\]')
    
    def parse_player_join(self, line: str) -> Optional[PlayerJoinEvent]:
        """
        Parse a player join event from playlog.txt
        
        Example line:
        --> Pelaaja joined the game (ip: 178.128.137.111). [25.01.2026 07:29] [/banaddress 178.128.137.111 60 Pelaaja 1124073472 ] [v2.0.7]
        """
        match = self.PLAYER_JOIN_PATTERN.search(line)
        if not match:
            return None
        
        player_name = match.group(1).strip()
        ip_address = match.group(2)
        timestamp = match.group(3)
        raw_ban_command = match.group(4).strip()
        version = match.group(5)
        
        # Extract components from raw ban command to ensure we can modify minutes
        # Usage: /banaddress IP [minutes] [name] [id1] [id2]
        # Example: /banaddress 178.128.137.111 60 Pelaaja 1124073472
        cmd_parts = raw_ban_command.split()
        if len(cmd_parts) >= 3:
            # Usage: /banaddress IP [minutes] [name] [id1] [id2]
            # Replace the minutes (parts[2]) with a permanent ban value
            cmd_parts[2] = "9999999"
            ban_command = " ".join(cmd_parts)
            # name_with_ids is everything after the minutes field
            # We use this primarily for /banaddress where id1/id2 might be needed
            name_with_ids = " ".join(cmd_parts[3:])
        else:
            ban_command = raw_ban_command # Fallback
            name_with_ids = player_name
        
        return PlayerJoinEvent(
            timestamp=timestamp,
            player_name=player_name,
            ip_address=ip_address,
            version=version,
            ban_command=ban_command,
            name_with_ids=name_with_ids,
            player_id=cmd_parts[-1] if len(cmd_parts) > 3 else ""
        )
    
    def parse_chat_message(self, content: str, current_timestamp: str) -> Optional[ChatMessage]:
        """
        Parse a chat message from chatlog.txt
        
        Example:
        Pelaaja:        [25.01.2026 07:30]
        moro mitä ääliöt
        """
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return None
        
        # First line should have player name and timestamp
        first_line = lines[0]
        match = self.CHAT_MESSAGE_PATTERN.match(first_line)
        if not match:
            return None
        
        player_name = match.group(1).strip()
        timestamp = match.group(2)
        
        # Rest is the message
        message = '\n'.join(lines[1:]).strip()
        
        if not message:
            return None
        
        return ChatMessage(
            timestamp=timestamp,
            player_name=player_name,
            message=message
        )
    
    def extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from a log line"""
        match = self.TIMESTAMP_PATTERN.search(line)
        if match:
            return match.group(1)
        return None
    
    def parse_chatlog_entry(self, lines: list[str], start_idx: int) -> tuple[Optional[ChatMessage], int]:
        """
        Parse a chat log entry starting from start_idx
        Returns (ChatMessage or None, next_index_to_check)
        """
        if start_idx >= len(lines):
            return None, start_idx
        
        # Look for player name line with timestamp
        current_line = lines[start_idx]
        
        # Check if this line has a player name and timestamp
        if ':' not in current_line or '[' not in current_line:
            return None, start_idx + 1
        
        # Try to extract player name and timestamp
        parts = current_line.split('[')
        if len(parts) < 2:
            return None, start_idx + 1
        
        player_name = parts[0].replace(':', '').strip()
        timestamp_part = '[' + parts[1]
        timestamp_match = self.TIMESTAMP_PATTERN.search(timestamp_part)
        
        if not timestamp_match:
            return None, start_idx + 1
        
        timestamp = timestamp_match.group(1)
        
        # Next line(s) should be the message
        message_lines = []
        idx = start_idx + 1
        
        # Collect message lines until we hit another player name or end
        while idx < len(lines):
            line = lines[idx].strip()
            
            # Stop if we hit an empty line or another player message
            if not line:
                idx += 1
                break
            
            # Stop if this looks like another player message
            if ':' in line and '[' in line and self.TIMESTAMP_PATTERN.search(line):
                break
            
            message_lines.append(line)
            idx += 1
        
        if not message_lines:
            return None, idx
        
        message = '\n'.join(message_lines)
        
        return ChatMessage(
            timestamp=timestamp,
            player_name=player_name,
            message=message
        ), idx
