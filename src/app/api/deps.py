from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.master import MasterProfile
from app.models.user import User
from app.repositories.masters import MasterRepository
from app.repositories.users import UserRepository
from app.services.sessions import SessionStore, get_session_store

__all__ = [
    "current_user_optional",
    "optional_master_profile",
    "require_master_profile",
    "require_user",
]


async def get_optional_user_id(
    request: Request,
    store: SessionStore = Depends(get_session_store),
) -> UUID | None:
    settings = get_settings()
    token = request.cookies.get(settings.session.cookie_name)
    user_id = await store.lookup_user(token)
    return user_id


async def current_user_optional(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID | None = Depends(get_optional_user_id),
) -> User | None:
    if user_id is None:
        return None
    repo = UserRepository(session)
    return await repo.get_by_id(user_id)


async def require_user(current: User | None = Depends(current_user_optional)) -> User:
    if not current:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if current.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address is not verified",
        )
    return current


async def optional_master_profile(
    session: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(current_user_optional),
) -> MasterProfile | None:
    if not user:
        return None
    return await MasterRepository(session).get_by_user_id(user.id)


async def require_master_profile(profile: MasterProfile | None = Depends(optional_master_profile)) -> MasterProfile:
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master profile not found")
    return profile
