"""
Seed: Users
===========
Contains only the first-admin creation helper used by the setup flow.
User accounts are not auto-seeded during installation.
"""
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from app.core.framework.models.auth import User, Role, user_roles


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def _get_role(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def seed_superadmin(
    db: AsyncSession,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
) -> User:
    """
    Create a superadmin user and assign the SystemManager role.
    Caller is responsible for checking that no users exist before calling this.
    Raises ValueError if the username already exists.
    """
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValueError(f"User '{username}' already exists.")

    role = await _get_role(db, "SystemManager")
    if not role:
        role = Role(name="SystemManager", description="Full system access", is_active=True)
        db.add(role)
        await db.flush()

    first = full_name.split()[0] if " " in full_name else full_name
    last = full_name.split()[-1] if " " in full_name else ""

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        first_name=first,
        last_name=last,
        hashed_password=_hash_password(password),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    await db.execute(insert(user_roles).values(user_id=user.id, role_id=role.id))
    await db.commit()
    return user
