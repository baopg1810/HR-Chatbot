import bcrypt

from src.models.schemas import User


DEMO_PASSWORD_HASHES = {
    "employee@example.com": "$2b$12$WSLLtKQ4IXfn5OQcyRTRMOkATjWDgWX3o6v6W5yoNmK3Z6RY7JFFS",
    "admin@example.com": "$2b$12$UK.VCiHggJBhdz58jpQl/eh1zfhgg6faiHEw4qPcAcwZqVWejQFrO",
}

DEMO_USERS = {
    "employee@example.com": User(
        id="emp-001",
        email="employee@example.com",
        full_name="Nguyen Van An",
        role="employee",
        department_id="dept-hr-demo",
    ),
    "admin@example.com": User(
        id="hr-001",
        email="admin@example.com",
        full_name="Tran Thi HR",
        role="hr_admin",
        department_id="dept-hr",
    ),
}


def authenticate_demo_user(email: str, password: str) -> User | None:
    password_hash = DEMO_PASSWORD_HASHES.get(email)
    if password_hash is None:
        return None
    if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        return None
    return DEMO_USERS[email]


def get_demo_user(user_id: str) -> User | None:
    for user in DEMO_USERS.values():
        if user.id == user_id:
            return user
    return None
