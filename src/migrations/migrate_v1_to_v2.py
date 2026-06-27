import sqlite3
import shutil
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Try to use the AI client to backfill hook_type and emotion
try:
    # Need to append the src folder to path so we can import ai_client
    src_path = Path(__file__).parent.parent
    sys.path.append(str(src_path))
    from utils.ai_client import AIClient
    has_ai_client = True
except ImportError:
    has_ai_client = False

DB_PATH = "data/viral_os.db"
BACKUP_PATH = "data/viral_os_backup.db"

def migrate():
    print("Starting Viral OS v1 to v2 database migration...")
    
    # Check if DB exists
    if not os.path.exists(DB_PATH):
        print("No existing database found.")
        print("No existing data to migrate — new tables created.")
        return

    # Create backup
    print(f"Creating database backup at {BACKUP_PATH}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    
    conn = sqlite3.connect(BACKUP_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Check if this is an empty DB
    try:
        c.execute("SELECT COUNT(*) as count FROM content_memory")
        video_count = c.fetchone()["count"]
    except sqlite3.OperationalError:
        # Table doesn't even exist
        print("No existing data to migrate — new tables created.")
        conn.close()
        # Just init schema on the real DB and we are done
        from core.database import Database
        Database(DB_PATH)
        return
        
    try:
        c.execute("SELECT COUNT(*) as count FROM pipeline_runs")
        run_count = c.fetchone()["count"]
    except sqlite3.OperationalError:
        run_count = 0

    if video_count == 0 and run_count == 0:
        print("No existing data to migrate — new tables created.")
        conn.close()
        # Initialize schema directly to ensure it has everything
        sys.path.append(str(Path(__file__).parent.parent))
        from core.database import Database
        Database(DB_PATH)
        return
        
    print(f"Found {video_count} videos and {run_count} pipeline runs.")
    
    # 1. Add new columns to content_memory if they don't exist
    columns_to_add = {
        "hook_type": "TEXT",
        "emotion": "TEXT"
    }
    
    c.execute("PRAGMA table_info(content_memory)")
    existing_columns = [row["name"] for row in c.fetchall()]
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            print(f"Adding column {col_name} to content_memory...")
            c.execute(f"ALTER TABLE content_memory ADD COLUMN {col_name} {col_type}")
    
    # 2. Backfill hook_type and emotion using Gemini if AI Client is available
    if has_ai_client:
        load_dotenv()
        ai = AIClient()
        c.execute("SELECT id, title, concept FROM content_memory WHERE hook_type IS NULL OR emotion IS NULL")
        videos_to_backfill = c.fetchall()
        
        if videos_to_backfill:
            print(f"Backfilling {len(videos_to_backfill)} videos with hook_type and emotion...")
            for row in videos_to_backfill:
                vid_id = row["id"]
                title = row["title"] or ""
                concept = row["concept"] or ""
                
                prompt = f"""
                Analyze this video title and concept:
                Title: {title}
                Concept: {concept}
                
                Return a JSON object with two fields:
                "hook_type": (one of: curiosity, shock, question, story, value, contrarian)
                "emotion": (one of: excitement, fear, curiosity, anger, joy, surprise)
                
                Return ONLY valid JSON.
                """
                
                try:
                    response_text = ai.generate(prompt=prompt, system_prompt="You are a data classifier. Return ONLY valid JSON, without any markdown formatting.")
                    
                    # Basic JSON extraction
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                        h_type = data.get("hook_type", "curiosity")
                        emotion = data.get("emotion", "curiosity")
                        
                        c.execute(
                            "UPDATE content_memory SET hook_type = ?, emotion = ? WHERE id = ?",
                            (h_type, emotion, vid_id)
                        )
                        print(f"  Updated ID {vid_id}: {h_type} / {emotion}")
                except Exception as e:
                    print(f"  Failed to backfill ID {vid_id}: {e}")
    
    conn.commit()
    conn.close()
    
    # 3. Replace real DB with migrated backup
    print("Applying migration to live database...")
    shutil.copy2(BACKUP_PATH, DB_PATH)
    
    # 4. Also run Database._init_schema to ensure all brand new tables are created
    sys.path.append(str(Path(__file__).parent.parent))
    from core.database import Database
    db = Database(DB_PATH)
    
    print(f"Migration complete! Migrated {video_count} videos, {run_count} pipeline_runs.")

if __name__ == "__main__":
    migrate()
