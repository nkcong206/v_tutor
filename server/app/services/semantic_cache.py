
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
        
        # Granular Question Store
        # context_hash: Hash of (Prompt + Files + Temp)
        # question_hash: Hash of the question content itself to prevent duplicates
        # question_type: Type of question for regeneration with same type
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_hash TEXT,
                question_hash TEXT,
                question_type TEXT DEFAULT 'single_choice',
                question_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(context_hash, question_hash)
            )
        """)
        
        # Migration: Add question_type column if it doesn't exist (for existing databases)
        try:
            cursor.execute("SELECT question_type FROM question_cache LIMIT 1")
        except Exception:
            print("🔄 Migrating database: Adding question_type column...")
            cursor.execute("ALTER TABLE question_cache ADD COLUMN question_type TEXT DEFAULT 'single_choice'")
            print("✅ Migration complete!")
        
        self.conn.commit()

    def get(self, key: str):
        """
        Get cached response by SHA256 hash of the key (exact match).
        """
        if not self.conn:
            self.init()
            
        # Hash the key to ensure we don't store massive strings and avoid index issues
        import hashlib
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT response_json FROM cache_entries WHERE key_hash = ?", (key_hash,))
        row = cursor.fetchone()
        
        if row:
            print(f"✅ HASH CACHE HIT (Hash: {key_hash[:8]}...)")
            return row[0]
        
        return None

    def save(self, key: str, response_json: str):
        """Save key hash and response to cache"""
        if not self.conn:
            self.init()
            
        # Hash the key
        import hashlib
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
            
        cursor = self.conn.cursor()
        # Upsert logic (replace if exists)
        cursor.execute("INSERT OR REPLACE INTO cache_entries (key_hash, response_json) VALUES (?, ?)", (key_hash, response_json))
        self.conn.commit()
        
        print(f"💾 Saved to Hash Cache (Hash: {key_hash[:8]}...)")

    def get_questions(self, context_hash: str):
        """Get all questions for a given context"""
        if not self.conn:
            self.init()
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT question_json, question_type FROM question_cache WHERE context_hash = ?", (context_hash,))
        rows = cursor.fetchall()
        
        questions = []
        for row in rows:
            q = json.loads(row[0])
            q['_cached_type'] = row[1]  # Add cached type for reference
            questions.append(q)
        print(f"✅ Retrieved {len(questions)} questions from cache for context {context_hash[:8]}...")
        return questions

    def add_question(self, context_hash: str, question_dict: dict, question_type: str = 'single_choice'):
        """Add a single question to cache if not exists"""
        if not self.conn:
            self.init()
            
        import hashlib
        # Ensure deterministic JSON for hashing
        question_json = json.dumps(question_dict, ensure_ascii=False, sort_keys=True)
        # Hash the question content to enforce uniqueness
        question_hash = hashlib.md5(question_json.encode()).hexdigest()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO question_cache (context_hash, question_hash, question_type, question_json) 
                VALUES (?, ?, ?, ?)
            """, (context_hash, question_hash, question_type, question_json))
            self.conn.commit()
            if cursor.rowcount > 0:
                print(f"💾 Cached new question (type: {question_type}) for context {context_hash[:8]}...")
        except Exception as e:
            print(f"⚠️ Error caching question: {e}")

    def remove_question(self, context_hash: str, question_dict: dict):
        """Remove a specific question from cache and return its type for regeneration"""
        if not self.conn:
            self.init()
            
        import hashlib
        # Ensure deterministic JSON for hashing
        question_json = json.dumps(question_dict, ensure_ascii=False, sort_keys=True)
        question_hash = hashlib.md5(question_json.encode()).hexdigest()
        
        removed_type = None
        try:
            cursor = self.conn.cursor()
            # First, get the question_type before deleting
            cursor.execute("""
                SELECT question_type FROM question_cache 
                WHERE context_hash = ? AND question_hash = ?
            """, (context_hash, question_hash))
            row = cursor.fetchone()
            if row:
                removed_type = row[0]
            
            # Now delete
            cursor.execute("""
                DELETE FROM question_cache 
                WHERE context_hash = ? AND question_hash = ?
            """, (context_hash, question_hash))
            self.conn.commit()
            if cursor.rowcount > 0:
                print(f"🗑️ Removed question (type: {removed_type}) from cache (Context: {context_hash[:8]}...)")
            else:
                print(f"⚠️ Question not found in cache to remove.")
        except Exception as e:
            print(f"⚠️ Error removing question from cache: {e}")
        
        return removed_type

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

def get_cached_questions(context_key: str):
    # Hash the key first as per our convention (or passed hash? let's hash specific context key)
    # Actually context_key from exam.py is full text, we should hash it here.
    import hashlib
    context_hash = hashlib.sha256(context_key.encode("utf-8")).hexdigest()
    return cache_service.get_questions(context_hash)

def add_cached_question(context_key: str, question_dict: dict, question_type: str = 'single_choice'):
    import hashlib
    context_hash = hashlib.sha256(context_key.encode("utf-8")).hexdigest()
    return cache_service.add_question(context_hash, question_dict, question_type)

def remove_cached_question(context_key: str, question_dict: dict):
    """Remove question and return its type for regeneration"""
    import hashlib
    context_hash = hashlib.sha256(context_key.encode("utf-8")).hexdigest()
    return cache_service.remove_question(context_hash, question_dict)

# Aliases for compatibility with exam.py
get_questions = get_cached_questions
add_question = add_cached_question
# Batch is same as single add in loop for now, or just implement pass through if needed
def get_questions_batch(context_keys: list):
    # Not implemented efficiently yet, just loop
    results = {}
    for key in context_keys:
        results[key] = get_cached_questions(key)
    return results
