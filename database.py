"""
Database Module
SQLite database for storing violations and analysis history.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from ml_analyzer import ViolationLevel


class Database:
    """SQLite database for storing violation records"""
    
    def __init__(self, db_path: str = "data/violations.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create violations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                player_name TEXT NOT NULL,
                ip_address TEXT,
                violation_type TEXT NOT NULL,
                content TEXT NOT NULL,
                level TEXT NOT NULL,
                reason TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create index on player_name for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_player_name ON violations(player_name)
        """)
        
        # Create index on level for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_level ON violations(level)
        """)
        
        conn.commit()
        conn.close()
    
    def add_violation(
        self,
        timestamp: str,
        player_name: str,
        violation_type: str,
        content: str,
        level: ViolationLevel,
        reason: str,
        suggested_action: str,
        ip_address: Optional[str] = None
    ) -> int:
        """
        Add a violation record to the database
        
        Args:
            timestamp: Timestamp from the log
            player_name: Name of the player
            violation_type: Type of violation ("message" or "nickname")
            content: The violating content
            level: Violation severity level
            reason: ML's reasoning
            suggested_action: Suggested action to take
            ip_address: Player's IP address (optional)
            
        Returns:
            ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO violations (
                timestamp, player_name, ip_address, violation_type,
                content, level, reason, suggested_action, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            player_name,
            ip_address,
            violation_type,
            content,
            level,
            reason,
            suggested_action,
            datetime.now().isoformat()
        ))
        
        violation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return violation_id
    
    def get_player_violations(
        self,
        player_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent violations for a specific player
        
        Args:
            player_name: Name of the player
            limit: Maximum number of records to return
            
        Returns:
            List of violation records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM violations
            WHERE player_name = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (player_name, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_recent_violations(
        self,
        level: Optional[ViolationLevel] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent violations, optionally filtered by level
        
        Args:
            level: Filter by violation level (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of violation records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if level:
            cursor.execute("""
                SELECT * FROM violations
                WHERE level = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (level, limit))
        else:
            cursor.execute("""
                SELECT * FROM violations
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get violation statistics
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total violations
        cursor.execute("SELECT COUNT(*) FROM violations")
        total = cursor.fetchone()[0]
        
        # Violations by level
        cursor.execute("""
            SELECT level, COUNT(*) as count
            FROM violations
            GROUP BY level
        """)
        by_level = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Top violators
        cursor.execute("""
            SELECT player_name, COUNT(*) as count
            FROM violations
            GROUP BY player_name
            ORDER BY count DESC
            LIMIT 10
        """)
        top_violators = [{"player": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total": total,
            "by_level": by_level,
            "top_violators": top_violators
        }
