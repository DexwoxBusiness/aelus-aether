"""Test database connection."""

import asyncio

import asyncpg


async def test_connection():
    """Test PostgreSQL connection."""
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5433,
            user="aelus",
            password="aelus_password",
            database="aelus_aether",
        )

        version = await conn.fetchval("SELECT version()")
        print("✅ Connected successfully!")
        print(f"PostgreSQL version: {version}")

        # Check if user exists
        users = await conn.fetch("SELECT usename FROM pg_user")
        print("\nUsers in database:")
        for user in users:
            print(f"  - {user['usename']}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_connection())
