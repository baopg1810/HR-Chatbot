import asyncio
import sys
import os
import uuid

# Add backend to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database.session import get_db_context
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def seed():
    print("Running database seeding...")
    try:
        async with get_db_context() as db:
            # Seed employee
            res = await db.execute(select(User).filter(User.email == "employee@example.com"))
            if not res.scalars().first():
                print("Seeding employee user...")
                emp = User(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                    email="employee@example.com",
                    employee_code="EMP001",
                    full_name="Nguyen Van An",
                    department="HR",
                    position="Staff",
                    employment_type="Full-time",
                    role="employee",
                    is_active=True,
                    password_hash=get_password_hash("employee123")
                )
                db.add(emp)
            else:
                print("Employee user already exists.")
                
            # Seed admin
            res = await db.execute(select(User).filter(User.email == "admin@example.com"))
            if not res.scalars().first():
                print("Seeding admin user...")
                adm = User(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                    email="admin@example.com",
                    employee_code="ADM001",
                    full_name="Tran Thi HR",
                    department="HR",
                    position="Manager",
                    employment_type="Full-time",
                    role="admin",
                    is_active=True,
                    password_hash=get_password_hash("admin123")
                )
                db.add(adm)
            else:
                print("Admin user already exists.")
                
            await db.commit()
        print("Seeding completed successfully.")
    except Exception as e:
        print(f"Error during seeding: {e}")

if __name__ == "__main__":
    asyncio.run(seed())
