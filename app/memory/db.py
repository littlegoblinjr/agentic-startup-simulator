import asyncpg
import os
import json
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

    pool = await asyncpg.create_pool(database_url)

    async with pool.acquire() as connection:
        await connection.execute(
            """
            CREATE EXTENSION IF NOT EXISTS vector
            """
        )
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id SERIAL PRIMARY KEY,
                content TEXT,
                embedding VECTOR(384),
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_runs (
                run_id UUID PRIMARY KEY,
                idea TEXT NOT NULL,
                status TEXT NOT NULL,
                results JSONB,
                score INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        await connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_simulation_runs_created_at ON simulation_runs(created_at DESC);
            """
        )
    

async def save_run(run_id: str, idea: str, status: str, results: Optional[Dict] = None, score: Optional[int] = None):
    async with pool.acquire() as connection:
        await connection.execute("""
            INSERT INTO simulation_runs (run_id, idea, status, results, score, updated_at)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
            ON CONFLICT (run_id) 
            DO UPDATE SET 
                status = EXCLUDED.status,
                results = EXCLUDED.results,
                score = EXCLUDED.score,
                updated_at = CURRENT_TIMESTAMP
        """, run_id, idea, status, json.dumps(results) if results else None, score)

async def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as connection:
        row = await connection.fetchrow("SELECT * FROM simulation_runs WHERE run_id = $1", run_id)
        if row:
            data = dict(row)
            if data['results']:
                data['results'] = json.loads(data['results'])
            return data
        return None

async def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    async with pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM simulation_runs ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

async def execute(query, *args):
    async with pool.acquire() as connection:
        return await connection.execute(query, *args)

async def fetch(query, *args):
    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)
    
    