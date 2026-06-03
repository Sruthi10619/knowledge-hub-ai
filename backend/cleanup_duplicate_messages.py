"""
One-shot cleanup script: removes duplicate message rows caused by the mem_store.add_message
double-write bug that has now been fixed in chat_service.py.

The bug wrote each message TWICE per query:
  1. db.add(user_msg) / db.add(assistant_msg)  ← direct ORM write
  2. mem_store.add_message(...)                 ← SQLiteMemoryStore also called db.add()

This leaves consecutive rows with identical (conversation_id, role, content).
This script keeps the FIRST occurrence of each duplicate pair and deletes the rest.

Usage:
  cd backend
  python cleanup_duplicate_messages.py
"""

import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal


DEDUPLICATE_SQL = """
DELETE FROM messages
WHERE id IN (
    SELECT id FROM (
        SELECT
            id,
            role,
            content,
            conversation_id,
            created_at,
            LAG(role) OVER (PARTITION BY conversation_id ORDER BY created_at) AS prev_role,
            LAG(content) OVER (PARTITION BY conversation_id ORDER BY created_at) AS prev_content
        FROM messages
    ) t
    WHERE role = prev_role AND content = prev_content
);
"""

COUNT_DUPLICATES_SQL = """
SELECT COUNT(*) FROM (
    SELECT
        id,
        role,
        content,
        conversation_id,
        created_at,
        LAG(role) OVER (PARTITION BY conversation_id ORDER BY created_at) AS prev_role,
        LAG(content) OVER (PARTITION BY conversation_id ORDER BY created_at) AS prev_content
    FROM messages
) t
WHERE role = prev_role AND content = prev_content;
"""


async def main():
    async with AsyncSessionLocal() as db:
        # First count
        result = await db.execute(text(COUNT_DUPLICATES_SQL))
        count = result.scalar()
        print(f"Found {count} duplicate message rows to remove.")

        if count == 0:
            print("Database is already clean. Nothing to do.")
            return

        # Perform deletion
        await db.execute(text(DEDUPLICATE_SQL))
        await db.commit()

        # Verify
        result2 = await db.execute(text(COUNT_DUPLICATES_SQL))
        remaining = result2.scalar()
        print(f"Cleanup complete. Removed {count} rows. Remaining duplicates: {remaining}.")


if __name__ == "__main__":
    asyncio.run(main())
