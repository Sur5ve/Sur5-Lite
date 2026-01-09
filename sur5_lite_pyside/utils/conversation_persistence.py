#!/usr/bin/env python3
"""
Conversation Persistence
Handles saving, loading, and exporting chat conversations with portable path support
"""

import json
import os
import shutil
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path

# Import portable paths for USB-compatible path resolution
try:
    from utils.portable_paths import get_conversations_dir, is_portable_mode
    PORTABLE_PATHS_AVAILABLE = True
except ImportError:
    PORTABLE_PATHS_AVAILABLE = False
    print("⚠️ Portable paths not available - using legacy Documents path")


class ConversationPersistence:
    """Handles conversation file operations with portable mode support"""
    
    def __init__(self):
        self.default_extension = ".sur5chat"
        
        # Determine conversation directory based on portable mode
        if PORTABLE_PATHS_AVAILABLE:
            self.default_dir = str(get_conversations_dir())
            self.portable_mode = is_portable_mode()
            self.legacy_dir = str(Path.home() / "Documents" / "Sur5" / "Conversations")
        else:
            # Fallback to legacy location
            self.default_dir = str(Path.home() / "Documents" / "Sur5" / "Conversations")
            self.portable_mode = False
            self.legacy_dir = self.default_dir
        
        self._ensure_default_dir()
        
        # Migrate legacy conversations on first run (portable mode only)
        if self.portable_mode and PORTABLE_PATHS_AVAILABLE:
            self._migrate_legacy_conversations()
    
    def _ensure_default_dir(self):
        """Create default conversation directory if it doesn't exist"""
        try:
            os.makedirs(self.default_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Could not create default conversation directory: {e}")
    
    def _migrate_legacy_conversations(self):
        """Migrate conversations from legacy Documents location to portable UserData (first run only)"""
        try:
            legacy_path = Path(self.legacy_dir)
            portable_path = Path(self.default_dir)
            
            # Check if legacy location exists and has conversations
            if not legacy_path.exists():
                return
            
            # Check if migration already happened (portable dir has .migrated marker)
            migration_marker = portable_path / ".migrated_from_documents"
            if migration_marker.exists():
                return
            
            # Find all conversation files in legacy location
            conversation_files = list(legacy_path.glob(f"*{self.default_extension}"))
            
            if conversation_files:
                print(f"📦 Migrating {len(conversation_files)} conversations to portable storage...")
                
                migrated_count = 0
                for conv_file in conversation_files:
                    try:
                        # Copy to portable location
                        dest_file = portable_path / conv_file.name
                        
                        # Don't overwrite if file already exists
                        if not dest_file.exists():
                            shutil.copy2(conv_file, dest_file)
                            migrated_count += 1
                        
                    except Exception as e:
                        print(f"⚠️ Failed to migrate {conv_file.name}: {e}")
                
                if migrated_count > 0:
                    print(f"✓ Migrated {migrated_count} conversations from Documents to portable storage")
                    
                    # Create migration marker to prevent re-migration
                    try:
                        with open(migration_marker, 'w') as f:
                            f.write(f"Migration completed: {datetime.now().isoformat()}\n")
                            f.write(f"Source: {legacy_path}\n")
                            f.write(f"Migrated: {migrated_count} files\n")
                    except Exception:
                        pass
                else:
                    print("📁 No new conversations to migrate")
                    
        except Exception as e:
            print(f"⚠️ Error during conversation migration: {e}")
    
    def save_conversation(self, conversation_data: Dict[str, Any], filepath: str) -> bool:
        """
        Save conversation to JSON file
        
        Args:
            conversation_data: Dictionary containing conversation history and metadata
            filepath: Full path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add save metadata
            save_data = {
                "version": "2.0",
                "saved_at": datetime.now().isoformat(),
                "conversation": conversation_data
            }
            
            # Write to file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Conversation saved: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
            return False
    
    def load_conversation(self, filepath: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Load conversation from JSON file
        
        Args:
            filepath: Full path to conversation file
            
        Returns:
            Tuple of (conversation_data, error_message)
            conversation_data is None if error occurred
        """
        try:
            if not os.path.exists(filepath):
                return None, f"File not found: {filepath}"
            
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # Handle different file versions
            version = save_data.get("version", "1.0")
            
            if version == "2.0":
                conversation_data = save_data.get("conversation", {})
            else:
                # Legacy format (version 1.0 or unversioned)
                conversation_data = save_data
            
            print(f"📂 Conversation loaded: {filepath}")
            return conversation_data, None
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid conversation file format: {e}"
            print(f"❌ {error_msg}")
            return None, error_msg
            
        except Exception as e:
            error_msg = f"Error loading conversation: {e}"
            print(f"❌ {error_msg}")
            return None, error_msg
    
    def export_to_text(self, conversation_data: Dict[str, Any], filepath: str) -> bool:
        """
        Export conversation to plain text file
        
        Args:
            conversation_data: Dictionary containing conversation history
            filepath: Full path to export file (.txt)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            history = conversation_data.get("history", [])
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("SUR5 CONVERSATION EXPORT\n")
                f.write("=" * 60 + "\n\n")
                
                # Write export metadata
                export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"Exported: {export_time}\n")
                f.write(f"Total Messages: {len(history)}\n\n")
                f.write("=" * 60 + "\n\n")
                
                # Write conversation
                for i, msg in enumerate(history, 1):
                    role = msg.get("role", "unknown").upper()
                    content = msg.get("content", "")
                    thinking = msg.get("thinking", "")
                    timestamp = msg.get("timestamp", 0)
                    
                    # Format timestamp
                    msg_time = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else "N/A"
                    
                    f.write(f"[{i}] {role} ({msg_time})\n")
                    f.write("-" * 60 + "\n")
                    
                    # Write thinking if present
                    if thinking:
                        f.write("\n[THINKING]\n")
                        f.write(thinking + "\n\n")
                    
                    # Write content
                    f.write(content + "\n\n")
                    f.write("=" * 60 + "\n\n")
            
            print(f"📄 Conversation exported to text: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting to text: {e}")
            return False
    
    def export_to_markdown(self, conversation_data: Dict[str, Any], filepath: str) -> bool:
        """
        Export conversation to Markdown file
        
        Args:
            conversation_data: Dictionary containing conversation history
            filepath: Full path to export file (.md)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            history = conversation_data.get("history", [])
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# Sur5 Conversation Export\n\n")
                
                # Write metadata
                export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"**Exported:** {export_time}  \n")
                f.write(f"**Total Messages:** {len(history)}  \n\n")
                f.write("---\n\n")
                
                # Write conversation
                for i, msg in enumerate(history, 1):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    thinking = msg.get("thinking", "")
                    timestamp = msg.get("timestamp", 0)
                    
                    # Format timestamp
                    msg_time = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else "N/A"
                    
                    # Role emoji
                    emoji = "👤" if role == "user" else "🤖"
                    
                    f.write(f"## {emoji} {role.title()} - Message {i}\n\n")
                    f.write(f"*Time: {msg_time}*\n\n")
                    
                    # Write thinking if present
                    if thinking:
                        f.write("### 🧠 Thinking Process\n\n")
                        f.write(f"```\n{thinking}\n```\n\n")
                    
                    # Write content
                    f.write(f"{content}\n\n")
                    f.write("---\n\n")
            
            print(f"📝 Conversation exported to Markdown: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting to Markdown: {e}")
            return False
    
    def get_default_filename(self, prefix: str = "conversation") -> str:
        """
        Generate a default filename with timestamp
        
        Args:
            prefix: Filename prefix (default: "conversation")
            
        Returns:
            Filename string with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}"
    
    def get_conversation_info(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation file information without loading full content
        
        Args:
            filepath: Path to conversation file
            
        Returns:
            Dictionary with file info or None if error
        """
        try:
            if not os.path.exists(filepath):
                return None
            
            # Get file stats
            stat_info = os.stat(filepath)
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)
            file_size = stat_info.st_size
            
            # Quick parse to get message count
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            history = data.get("conversation", {}).get("history", [])
            if not history:
                history = data.get("history", [])
            
            return {
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "modified": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                "size_bytes": file_size,
                "message_count": len(history),
                "version": data.get("version", "1.0")
            }
            
        except Exception as e:
            print(f"⚠️ Error reading conversation info: {e}")
            return None
