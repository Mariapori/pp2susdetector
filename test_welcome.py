import unittest
from unittest.mock import MagicMock, patch
import logging

# Configure logging to suppress output during tests
logging.basicConfig(level=logging.CRITICAL)

from detector import ServerMonitor, PP2Detector
from log_parser import PlayerJoinEvent

class TestWelcomeMessage(unittest.TestCase):
    def setUp(self):
        # Mock Detector
        self.mock_detector = MagicMock(spec=PP2Detector)
        self.mock_detector.config = {'discord': {'verify_all': False}}
        self.mock_detector.analyzer = MagicMock()
        self.mock_detector.analyzer.analyze_nickname.return_value.level = "OK"
        self.mock_detector.db = MagicMock()
        self.mock_detector.action_handler = MagicMock()
        
        # Mock Server Config
        self.server_config = {
            'name': 'Test Server',
            'chatlog_path': 'test_chat.log',
            'playlog_path': 'test_play.log',
            'admin_url': 'http://test',
            'admin_password': 'pass'
        }
        
        # Initialize Monitor
        self.monitor = ServerMonitor(self.server_config, self.mock_detector)
        
        # Mock execute_command to just print or do nothing, avoid threading issues if possible
        # But we are mocking action_handler, so execute_command on it is mocked.
        # Wait, ServerMonitor creates a thread for execute_command.
        # We need to ensure that thread calls the mock.
        
        # Mock get_live_player_index to return a valid ID so welcome message proceeds
        self.mock_detector.action_handler.get_live_player_index.return_value = "1"

    def test_double_join_welcome(self):
        # Create a join event
        join_event = PlayerJoinEvent(
            timestamp="2024-01-31 12:00",
            player_name="TestPlayer",
            ip_address="127.0.0.1",
            version="1.0",
            ban_command="/ban",
            name_with_ids="TestPlayer",
            player_id="123"
        )
        
        # Process first join
        print("Processing first join...")
        self.monitor.process_player_join(join_event)
        
        # Allow thread to start (mock doesn't really sleep but good to separate)
        
        # Process second join (same player)
        print("Processing second join...")
        self.monitor.process_player_join(join_event)
        
        # Check call count
        # ServerMonitor calls: threading.Thread(target=self.detector.action_handler.execute_command, ...).start()
        # We can't easily count how many times the thread target was invoked unless we patch threading.Thread
        # OR we can see if action_handler.execute_command was called. 
        # BUT, since it's in a thread, we might have race conditions in test if we check immediately.
        # HOWEVER, with MagicMock, if we don't actually sleep, the thread might launch and run quickly? 
        # No, standard threading.Thread will run in background.
        
        # Better approach: Patch threading.Thread to run synchronously or mock it to verify it was instantiated twice with correct target.
        pass

    @patch('threading.Thread')
    def test_welcome_message_dispatch(self, mock_thread):
        join_event = PlayerJoinEvent(
            timestamp="2024-01-31 12:00",
            player_name="TestPlayer",
            ip_address="127.0.0.1",
            version="1.0",
            ban_command="/ban",
            name_with_ids="TestPlayer",
            player_id="123"
        )
        
        # First join
        self.monitor.process_player_join(join_event)
        
        # Second join
        self.monitor.process_player_join(join_event)
        
        # Verify that threading.Thread was called twice with target=execute_command
        # We need to filter calls to Thread because other things might use it (like start() method, but we didn't call start())
        
        # Filter calls that are for the welcome message
        welcome_calls = 0
        for call in mock_thread.call_args_list:
            # call.kwargs or call[1]
            target = call.kwargs.get('target')
            if target == self.mock_detector.action_handler.execute_command:
                args = call.kwargs.get('args')
                if args and "Tervetuloa" in args[0]:
                    welcome_calls += 1
        
        self.assertEqual(welcome_calls, 2, "Welcome message should be sent twice for two joins")

if __name__ == '__main__':
    unittest.main()
