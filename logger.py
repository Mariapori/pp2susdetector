"""
Logger module for PP2 Suspicious Detector
Provides unified logging to both console and systemd journal (Linux only).
Windows: Uses console logging only.
Linux (systemd): Uses both console and journal logging.
"""

import logging
import sys
import os
import platform

# Detect if running under systemd (Linux only)
IS_LINUX = platform.system() == 'Linux'
IS_SYSTEMD = IS_LINUX and (
    os.getenv('INVOCATION_ID') is not None or 
    os.path.exists('/run/systemd/system')
)


def setup_logger(name: str = "pp2susdetector") -> logging.Logger:
    """
    Set up a logger that writes to console, and additionally to systemd journal on Linux.
    
    On Windows and macOS: Console logging only
    On Linux with systemd: Console + Journal logging
    
    Usage:
        from logger import setup_logger, log
        logger = setup_logger()
        logger.info("Viesti")
        # or use global:
        log.info("Viesti")
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        # Already configured
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    logger.setLevel(logging.DEBUG)
    
    # Track if we successfully set up a primary handler
    used_systemd_journal = False

    # Systemd journal handler (Linux with systemd only)
    if IS_SYSTEMD:
        try:
            from systemd.journal import JournalHandler
            journal_handler = JournalHandler(SYSLOG_IDENTIFIER=name)
            journal_handler.setLevel(logging.DEBUG)
            # Journal format without emojis for cleaner syslog
            journal_format = logging.Formatter('[%(levelname)s] %(message)s')
            journal_handler.setFormatter(journal_format)
            logger.addHandler(journal_handler)
            used_systemd_journal = True
            logger.info("✅ Systemd journal logging enabled")
        except ImportError:
            # We are in systemd but missing the library - we will fall back to console
            pass

    # Console handler - used if NOT using systemd journal
    # Systemd automatically captures stdout/stderr, so we don't need both if journal is active
    if not used_systemd_journal:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        if IS_SYSTEMD:
             # We are in systemd but fell back to console
            logger.warning("⚠️ systemd-python not installed, using console logging (journal disabled)")
            logger.warning("   Install with: pip install systemd-python")
        elif IS_LINUX:
            logger.debug("ℹ️ Not running under systemd, using console logging only")
        else:
            # Windows / macOS
            logger.debug(f"ℹ️ Platform: {platform.system()} - using console logging")
    
    return logger


# Global logger instance - automatically configured
log = setup_logger()


# Convenience functions that match print() style
def info(msg: str):
    """Log info message"""
    log.info(msg)

def warning(msg: str):
    """Log warning message"""
    log.warning(msg)

def error(msg: str):
    """Log error message"""
    log.error(msg)

def debug(msg: str):
    """Log debug message"""
    log.debug(msg)
