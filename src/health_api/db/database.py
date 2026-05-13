import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def conn_str() -> str:
    return (
        f"host={os.environ['DB_HOST']} "
        f"port={os.environ.get('DB_PORT', 5432)} "
        f"dbname={os.environ['DB_NAME']} "
        f"user={os.environ['DB_USER']} "
        f"password={os.environ['DB_PASSWORD']}"
    )


def init_db() -> None:
    """Run schema.sql on startup to create tables if they don't exist."""
    logger.info("Initializing database schema")
    with psycopg.connect(conn_str()) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text())
        conn.commit()
    logger.info("Database schema ready")


def get_conn() -> psycopg.Connection:
    return psycopg.connect(conn_str())


@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield
