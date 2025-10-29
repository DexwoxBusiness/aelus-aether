#!/usr/bin/env python3
"""Reset test database by dropping and recreating it.

This is needed when migrations change and the test database needs to be rebuilt.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def reset_test_database():
    """Drop and recreate the test database."""
    # Connect to postgres database to drop/create test db
    postgres_url = settings.db_url.replace("/aelus_aether_test", "/postgres")

    engine = create_async_engine(
        postgres_url,
        isolation_level="AUTOCOMMIT",  # Required for CREATE/DROP DATABASE
    )

    try:
        async with engine.connect() as conn:
            # Terminate existing connections
            await conn.execute(
                text("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = 'aelus_aether_test'
                    AND pid <> pg_backend_pid()
                """)
            )

            # Drop test database
            print("Dropping test database...")
            await conn.execute(text("DROP DATABASE IF EXISTS aelus_aether_test"))

            # Create test database
            print("Creating test database...")
            await conn.execute(text("CREATE DATABASE aelus_aether_test"))

        print("✅ Test database reset successfully!")
        print("Run tests again - migrations will be applied fresh.")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_test_database())
