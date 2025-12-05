
import os
import json
import sqlite3
from app.config import settings

class SimpleCache:
    _instance = None
    
    def __init__(self):
        self.base_dir = os.path.abspath(settings.vector_store_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Use a new DB file to avoid schema conflict or just reuse and migrate?
        # Let's reuse prompt as keys. We don't need IDs anymore for FAISS.
        # But for simplicity, we can just use the same DB file but ignore ID index.
        # However, to be clean, let's just stick with sqlite.
        self.db_path = os.path.join(self.base_dir, "simple_hash_cache.db")
        self.conn = None
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SimpleCache()
        return cls._instance

    def init(self):
        """Initialize storage"""
        print("🔄 Initializing Hash Cache...")
            
        # Init SQLite
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_table()
        
        print(f"✅ Hash Cache Ready. DB: {self.db_path}")

    def create_table(self):
        cursor = self.conn.cursor()
        # Simple Key-Value Store
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                key_hash TEXT PRIMARY KEY,
                response_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def get(self, key: str):
        """
        Get cached response by exact key match.
        """
        if not self.conn:
            self.init()
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT response_json FROM cache_entries WHERE key_hash = ?", (key,))
        row = cursor.fetchone()
        
        if row:
            print(f"✅ HASH CACHE HIT")
            return row[0]
        
        return None

    def save(self, key: str, response_json: str):
        """Save key and response to cache"""
        if not self.conn:
            self.init()
            
        cursor = self.conn.cursor()
        # Upsert logic (replace if exists)
        cursor.execute("INSERT OR REPLACE INTO cache_entries (key_hash, response_json) VALUES (?, ?)", (key, response_json))
        self.conn.commit()
        
        print(f"💾 Saved to Hash Cache")

    def flush(self):
        # No-op for SQLite as we commit immediately, but kept for interface compatibility
        pass

# Easy wrapper functions
# Rename to maintain compatibility with imports in other files, but changing logic
# We can keep the module name "semantic_cache" to avoid changing imports in main.py, exam.py, tutor.py
# But the implementation is now simple hash cache.

cache_service = SimpleCache.get_instance()

def init_semantic_cache():
    cache_service.init()

def get_cached_response(prompt: str, threshold: float = None): 
    # threshold arg is ignored now, kept for backward compatibility if callers pass it
    return cache_service.get(prompt)

def save_to_cache(prompt: str, response_json: str):
    return cache_service.save(prompt, response_json)
