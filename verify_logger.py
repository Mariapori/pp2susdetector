
import sys
import logging
import platform
import os
import importlib
from unittest.mock import MagicMock, patch

# Define a proper mock handler that behaves like a logging.Handler
class MockJournalHandler(logging.Handler):
    def __init__(self, SYSLOG_IDENTIFIER=None):
        super().__init__()
        self.SYSLOG_IDENTIFIER = SYSLOG_IDENTIFIER
    
    def emit(self, record):
        pass

# 1. Prepare Mocks
# We need to control 'platform.system' and 'os.getenv' / 'os.path.exists' BEFORE importing logger
# But logger.py executes code at module level (checking IS_SYSTEMD), so we need to patch before import

def run_tests():
    print("Starting Logger Verification...")

    # CASE 1: Systemd + Library Present
    print("\n--- CASE 1: Systemd + Library Present ---")
    
    # Mock modules
    sys.modules["systemd"] = MagicMock()
    sys.modules["systemd.journal"] = MagicMock()
    sys.modules["systemd.journal"].JournalHandler = MockJournalHandler

    with patch("platform.system", return_value="Linux"), \
         patch("os.getenv", return_value="123456"), \
         patch("os.path.exists", return_value=True):
         
        # Reload logger to pick up environmental mocks
        if 'logger' in sys.modules:
            importlib.reload(sys.modules['logger'])
        else:
            import logger
            
        # Manually force IS_SYSTEMD to true because of how reload interacts with mocks sometimes
        logger.IS_SYSTEMD = True 
        
        # Reset global logger
        logger.log = logger.setup_logger("test_logger_1")
        
        handlers = logger.log.handlers
        handler_types = [type(h).__name__ for h in handlers]
        print(f"Handlers: {handler_types}")
        
        if "MockJournalHandler" in handler_types and "StreamHandler" not in handler_types:
            print("✅ SUCCESS: Only JournalHandler present")
        else:
            print("❌ FAILURE: Expected only JournalHandler")

    # CASE 2: Systemd + Library Missing
    print("\n--- CASE 2: Systemd + Library Missing ---")
    
    # Force ImportError for systemd.journal
    sys.modules["systemd.journal"] = None # This causes ImportError on import
    # OR better: remove it and let a side_effect raise ImportError if we mock the import mechanism
    # But since we already imported it, we need to make sure the import inside the function fails.
    # The 'from systemd.journal import JournalHandler' is inside the setup_logger function in the IS_SYSTEMD block.
    
    # Let's mock the import behavior using sys.modules trickery might be hard for specifically "from X import Y"
    # Alternative: Mock the JournalHandler class itself to raise ImportError on init? No, import happens before.
    
    # Simplest way: Remove from sys.modules and ensure standard import fails
    if "systemd.journal" in sys.modules:
        del sys.modules["systemd.journal"]
    
    # We also need to patch built-ins or use a specific trick to make the import fail
    # Let's try setting it to a mock that raises ImportError when accessed/imported? 
    # Actually, simpler: define a side_effect on a patched import? 
    
    # Let's try a different approach: modifying the logic in logger.py temporarily? No, that's bad.
    
    # Let's just unset the module and hope the internal import triggers reload? 
    # No, python imports are cached.
    
    # Strategy: Close enough is to set IS_SYSTEMD = True, but ensure the import crashes.
    
    # Let's just patch the 'logger.IS_SYSTEMD' to True, and patch 'builtins.__import__' ? Too complex.
    
    # Let's assume we can just patch `sys.modules` to make `systemd.journal` missing, 
    # AND wrap the `import` statement?
    
    # Actually, if I delete `systemd.journal` from sys.modules, the `from systemd.journal` statement WILL try to reload it. 
    # If I ensure it's not findable (it's not installed on this mac), it WILL raise ImportError.
    # The previous test mocked it into existence. So deleting it should work!
    
    del sys.modules["systemd"] # delete parent too just in case
    
    with patch("platform.system", return_value="Linux"):
        # We reuse the logger module but manually reset its state if needed
        logger.IS_SYSTEMD = True
        
        # We need a fresh logger
        log2 = logging.getLogger("test_logger_2")
        # clear existing handlers from previous runs if any
        log2.handlers = []
        
        # We call setup_logger. 
        # It enters IS_SYSTEMD block.
        # It tries `from systemd.journal import JournalHandler`
        # Since systemd.journal is removed from sys.modules and NOT on disk, this fails -> ImportError
        # Catches ImportError -> passes
        # Enters `if not used_systemd_journal` -> sets up StreamHandler
        
        logger.setup_logger("test_logger_2")
        
        handlers = log2.handlers
        handler_types = [type(h).__name__ for h in handlers]
        print(f"Handlers: {handler_types}")
        
        if "StreamHandler" in handler_types and "MockJournalHandler" not in handler_types:
            print("✅ SUCCESS: StreamHandler fallback active")
        else:
            print(f"❌ FAILURE: Expected StreamHandler. Got: {handler_types}")

    # CASE 3: No Systemd
    print("\n--- CASE 3: No Systemd (e.g. Windows/Mac) ---")
    
    logger.IS_SYSTEMD = False
    
    log3 = logging.getLogger("test_logger_3")
    log3.handlers = []
    
    logger.setup_logger("test_logger_3")
    
    handlers = log3.handlers
    handler_types = [type(h).__name__ for h in handlers]
    print(f"Handlers: {handler_types}")
    
    if "StreamHandler" in handler_types:
        print("✅ SUCCESS: StreamHandler active")
    else:
        print("❌ FAILURE: Expected StreamHandler")

if __name__ == "__main__":
    run_tests()
