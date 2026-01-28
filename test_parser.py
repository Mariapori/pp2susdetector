"""
Test script for log parser
"""

from log_parser import LogParser

def test_player_join():
    parser = LogParser()
    
    # Test with real log line
    line = "--> Pelaaja joined the game (ip: 178.128.137.111). [25.01.2026 07:29] [/banaddress 178.128.137.111 60 Pelaaja 1124073472 ] [v2.0.7]"
    
    result = parser.parse_player_join(line)
    
    if result:
        print("✅ Player join parsing successful!")
        print(f"   Player: {result.player_name}")
        print(f"   IP: {result.ip_address}")
        print(f"   Timestamp: {result.timestamp}")
        print(f"   Ban command: {result.ban_command}")
    else:
        print("❌ Failed to parse player join")

def test_chat_message():
    parser = LogParser()
    
    # Test with real chat log format
    lines = [
        "Pelaaja:        [25.01.2026 07:30]",
        "moro mitä ääliöt",
        ""
    ]
    
    message, _ = parser.parse_chatlog_entry(lines, 0)
    
    if message:
        print("\n✅ Chat message parsing successful!")
        print(f"   Player: {message.player_name}")
        print(f"   Timestamp: {message.timestamp}")
        print(f"   Message: {message.message}")
    else:
        print("\n❌ Failed to parse chat message")

if __name__ == "__main__":
    print("Testing Log Parser\n")
    test_player_join()
    test_chat_message()
