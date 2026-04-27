import asyncpg
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

pool = None


def _load_env():
    if load_dotenv is None:
        return
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


async def init_db():
    global pool

    _load_env()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your environment or in a .env file."
        )

    # Optimized pool for Neon serverless
    pool = await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=10,
        max_inactive_connection_lifetime=60.0,
        command_timeout=60.0
    )

    # Initialize tables
    await execute("""
        CREATE EXTENSION IF NOT EXISTS vector
    """)
    await execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR(384),
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    await execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            run_id UUID PRIMARY KEY,
            parent_run_id UUID REFERENCES simulation_runs(run_id),
            iteration INTEGER DEFAULT 1,
            idea TEXT NOT NULL,
            status TEXT NOT NULL,
            feedback TEXT,
            results JSONB,
            score INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await execute("ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS feedback TEXT;")
    await execute("CREATE INDEX IF NOT EXISTS idx_simulation_runs_created_at ON simulation_runs(created_at DESC);")


async def execute(query: str, *args, retries: int = 3):
    """Execute a query with retry logic for connection drops."""
    global pool
    if pool is None:
        await init_db()
        
    last_error = None
    for attempt in range(retries):
        try:
            async with pool.acquire() as connection:
                return await connection.execute(query, *args)
        except (asyncpg.exceptions.ConnectionDoesNotExistError, 
                ConnectionResetError, 
                asyncpg.exceptions.InterfaceError) as e:
            last_error = e
            print(f"DATABASE RETRY ({attempt+1}/{retries}): {e}")
            await asyncio.sleep(1 * (attempt + 1))
    raise last_error


async def fetch(query: str, *args, retries: int = 3):
    """Fetch rows with retry logic."""
    global pool
    if pool is None:
        await init_db()
        
    last_error = None
    for attempt in range(retries):
        try:
            async with pool.acquire() as connection:
                return await connection.fetch(query, *args)
        except (asyncpg.exceptions.ConnectionDoesNotExistError, 
                ConnectionResetError, 
                asyncpg.exceptions.InterfaceError) as e:
            last_error = e
            print(f"DATABASE RETRY ({attempt+1}/{retries}): {e}")
            await asyncio.sleep(1 * (attempt + 1))
    raise last_error


async def fetchrow(query: str, *args, retries: int = 3):
    """Fetch a single row with retry logic."""
    global pool
    if pool is None:
        await init_db()
        
    last_error = None
    for attempt in range(retries):
        try:
            async with pool.acquire() as connection:
                return await connection.fetchrow(query, *args)
        except (asyncpg.exceptions.ConnectionDoesNotExistError, 
                ConnectionResetError, 
                asyncpg.exceptions.InterfaceError) as e:
            last_error = e
            print(f"DATABASE RETRY ({attempt+1}/{retries}): {e}")
            await asyncio.sleep(1 * (attempt + 1))
    raise last_error


async def save_run(run_id: str, idea: str, status: str, results: Optional[Dict] = None,
                   score: Optional[int] = None, parent_run_id: Optional[str] = None,
                   iteration: int = 1, feedback: Optional[str] = None):
    query = """
        INSERT INTO simulation_runs (run_id, idea, status, results, score, 
        parent_run_id, iteration, feedback, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
        ON CONFLICT (run_id) 
        DO UPDATE SET 
            status = EXCLUDED.status,
            results = EXCLUDED.results,
            score = EXCLUDED.score,
            feedback = EXCLUDED.feedback, -- UPDATE FEEDBACK IF RE-SUBMITTED
            updated_at = CURRENT_TIMESTAMP
    """
    # Reverting to json.dumps as the asyncpg driver in this environment
    # expects a string for the JSONB parameter.
    results_json = json.dumps(results) if results else None
    await execute(query, run_id, idea, status, results_json, 
                  score, parent_run_id, iteration, feedback)


async def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    row = await fetchrow("SELECT * FROM simulation_runs WHERE run_id = $1", run_id)
    if row:
        data = dict(row)
        # Results might be a string (if old legacy row) or a dict (native JSONB)
        if data['results'] and isinstance(data['results'], str):
            try:
                data['results'] = json.loads(data['results'])
            except:
                pass 
        return data
    return None


async def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    rows = await fetch("SELECT * FROM simulation_runs ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]