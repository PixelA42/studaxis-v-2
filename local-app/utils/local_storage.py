"""
Local Storage Manager
Handles JSON-based persistence for user stats and session data
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path


class LocalStorage:
    """Manages local JSON storage with backup/restore capabilities"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.user_stats_path = self.base_path / "user_stats.json"
        self.backup_dir = self.base_path / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def initialize_user_stats(self, user_id: str) -> Dict:
        """Initialize default user stats structure"""
        default_stats = {
            "user_id": user_id,
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "streak": {
                "current": 0,
                "longest": 0,
                "last_activity_date": datetime.utcnow().date().isoformat()
            },
            "quiz_stats": {
                "total_attempted": 0,
                "total_correct": 0,
                "average_score": 0.0,
                "by_topic": {}
            },
            "flashcard_stats": {
                "total_reviewed": 0,
                "mastered": 0,
                "due_for_review": 0
            },
            "chat_history": [],
            "preferences": {
                "difficulty_level": "Beginner",
                "theme": "light",
                "language": "English"
            },
            "hardware_info": {}
        }
        
        self.save_user_stats(default_stats)
        return default_stats
    
    def load_user_stats(self) -> Optional[Dict]:
        """Load user stats from JSON file"""
        try:
            if not self.user_stats_path.exists():
                return None
            
            with open(self.user_stats_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except json.JSONDecodeError as e:
            print(f"⚠️ Corrupted user_stats.json: {e}")
            return self._restore_from_backup()
        
        except Exception as e:
            print(f"❌ Error loading user stats: {e}")
            return None
    
    def save_user_stats(self, stats: Dict, create_backup: bool = True) -> bool:
        """Save user stats to JSON file with optional backup"""
        try:
            if create_backup and self.user_stats_path.exists():
                self._create_backup()
            
            temp_path = self.user_stats_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            temp_path.replace(self.user_stats_path)
            return True
        
        except Exception as e:
            print(f"❌ Error saving user stats: {e}")
            return False
    
    def update_user_stats(self, updates: Dict) -> bool:
        """Update specific fields in user stats"""
        stats = self.load_user_stats()
        if not stats:
            return False
        
        # Deep merge updates
        self._deep_merge(stats, updates)
        stats['last_sync_timestamp'] = datetime.utcnow().isoformat()
        
        return self.save_user_stats(stats)
    
    def _deep_merge(self, base: Dict, updates: Dict):
        """Recursively merge updates into base dict"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _create_backup(self):
        """Create timestamped backup of user stats"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"user_stats_{timestamp}.json"
            shutil.copy2(self.user_stats_path, backup_path)
            
            # Keep only last 7 backups
            self._cleanup_old_backups(keep=7)
        
        except Exception as e:
            print(f"⚠️ Backup creation failed: {e}")
    
    def _cleanup_old_backups(self, keep: int = 7):
        """Remove old backups, keeping only the most recent N"""
        backups = sorted(self.backup_dir.glob("user_stats_*.json"))
        if len(backups) > keep:
            for old_backup in backups[:-keep]:
                old_backup.unlink()
    
    def _restore_from_backup(self) -> Optional[Dict]:
        """Restore user stats from most recent backup"""
        try:
            backups = sorted(self.backup_dir.glob("user_stats_*.json"))
            if not backups:
                print("❌ No backups available")
                return None
            
            latest_backup = backups[-1]
            print(f"🔄 Restoring from backup: {latest_backup.name}")
            
            with open(latest_backup, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            
            # Save restored data
            self.save_user_stats(stats, create_backup=False)
            return stats
        
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return None
    
    def add_chat_message(self, role: str, content: str, topic: str = "General"):
        """Add message to chat history"""
        stats = self.load_user_stats()
        if not stats:
            return False
        
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "content": content,
            "topic": topic
        }
        
        stats['chat_history'].append(message)
        
        # Keep only last 50 messages
        if len(stats['chat_history']) > 50:
            stats['chat_history'] = stats['chat_history'][-50:]
        
        return self.save_user_stats(stats)
    
    def update_streak(self):
        """Update daily streak based on activity"""
        stats = self.load_user_stats()
        if not stats:
            return False
        
        today = datetime.utcnow().date().isoformat()
        last_activity = stats['streak']['last_activity_date']
        
        if last_activity == today:
            # Already counted today
            return True
        
        # Check if streak continues
        from datetime import date, timedelta
        last_date = date.fromisoformat(last_activity)
        today_date = date.fromisoformat(today)
        
        if (today_date - last_date).days == 1:
            # Streak continues
            stats['streak']['current'] += 1
            stats['streak']['longest'] = max(
                stats['streak']['longest'],
                stats['streak']['current']
            )
        else:
            # Streak broken
            stats['streak']['current'] = 1
        
        stats['streak']['last_activity_date'] = today
        return self.save_user_stats(stats)
    
    def get_sync_delta(self, last_sync: str) -> Dict:
        """Get changes since last sync timestamp"""
        stats = self.load_user_stats()
        if not stats:
            return {}
        
        # return full stats
        return {
            "user_id": stats['user_id'],
            "streak": stats['streak'],
            "quiz_stats": stats['quiz_stats'],
            "flashcard_stats": stats['flashcard_stats'],
            "last_sync_timestamp": stats['last_sync_timestamp']
        }


# Standalone test
if __name__ == "__main__":
    print("Testing Local Storage...")
    
    storage = LocalStorage("./test_data")
    
    # Initialize
    stats = storage.initialize_user_stats("test_user_123")
    print(f"✅ Initialized user stats for {stats['user_id']}")
    
    # Update streak
    storage.update_streak()
    print("✅ Updated streak")
    
    # Add chat message
    storage.add_chat_message("user", "What is photosynthesis?", "Biology")
    storage.add_chat_message("assistant", "Photosynthesis is...", "Biology")
    print("✅ Added chat messages")
    
    # Load and verify
    loaded = storage.load_user_stats()
    print(f"\nCurrent Stats:")
    print(f"  Streak: {loaded['streak']['current']}")
    print(f"  Chat History: {len(loaded['chat_history'])} messages")
    
    # Test backup/restore
    storage._create_backup()
    print("✅ Created backup")
    
    # Cleanup
    shutil.rmtree("./test_data")
    print("✅ Cleanup complete")
