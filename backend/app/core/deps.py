"""FastAPI dependencies: current user, RBAC, etc."""
from typing import Annotated, Callable
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.models.user import User, Role

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Требуется авторизация")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedError("Неверный тип токена")
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise UnauthorizedError("Недействительный токен")

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("Пользователь не найден или деактивирован")
    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except UnauthorizedError:
        return None


def require_roles(*role_names: str) -> Callable:
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        user_roles = {r.name for r in user.roles}
        if not user_roles.intersection(set(role_names)):
            raise ForbiddenError("Недостаточно прав")
        return user
    return checker


def require_permissions(*perm_codes: str) -> Callable:
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if any(r.name == "OWNER" for r in user.roles):
            return user
        user_perms: set[str] = set()
        for role in user.roles:
            for p in role.permissions:
                user_perms.add(p.code)
        if not set(perm_codes).issubset(user_perms):
            raise ForbiddenError(f"Требуются права: {', '.join(perm_codes)}")
        return user
    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
