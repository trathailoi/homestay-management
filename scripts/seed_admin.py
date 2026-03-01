#!/usr/bin/env python3
"""Seed the initial admin user account.

Run: uv run python scripts/seed_admin.py

This creates an admin user with:
- Username: admin
- Password: admin123
- Role: admin

The script is idempotent - if the user already exists, it will
print a message and exit cleanly.

SECURITY: Change the password immediately after first login in production.
"""

import asyncio
import sys

from app.database import SessionLocal
from app.exceptions import HomestayError
from app.services.auth_service import AuthService


async def seed_admin() -> None:
    """Create the admin user if it doesn't exist."""
    async with SessionLocal() as session:
        service = AuthService(session)
        try:
            user = await service.register(
                username="admin",
                password="admin123",
                role="admin",
            )
            print(f"✓ Created admin user: {user.username} (id: {user.id})")
        except HomestayError as e:
            if e.code == "USERNAME_EXISTS":
                print("ℹ Admin user already exists, skipping creation.")
            else:
                print(f"✗ Error creating admin: {e.message}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed_admin())
