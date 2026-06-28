from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import get_password_hash
from app.database.session import get_db_context
from app.models.user import User


async def bootstrap_admin(email: str, password: str, full_name: str | None, department: str | None) -> None:
    async with get_db_context() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if user is None:
            user = User(email=email)
            db.add(user)

        user.password_hash = get_password_hash(password)
        user.role = "hr_admin"
        user.is_active = True
        if full_name:
            user.full_name = full_name
        if department:
            user.department = department

        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the first HR admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default=None)
    parser.add_argument("--department", default="HR")
    args = parser.parse_args()

    asyncio.run(bootstrap_admin(args.email, args.password, args.full_name, args.department))
    print(f"Admin user ready: {args.email}")


if __name__ == "__main__":
    main()
