from aiogram.types import User as TgUser
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backnote.db.models import User, UserStatus, utcnow
from backnote.services.base import BaseService, apply_fields


class UserService(BaseService):
    SETTINGS = frozenset({"notify_new_content"})

    def __init__(self, sessionmaker: async_sessionmaker, admin_id: int) -> None:
        super().__init__(sessionmaker)
        self.admin_id = admin_id

    def is_admin(self, user_id: int) -> bool:
        return user_id == self.admin_id

    async def touch(self, tg_user: TgUser) -> tuple[User, bool]:
        """Upsert the Telegram user. Returns (user, created). The admin is always active."""
        async with self._sm() as s:
            user = await s.get(User, tg_user.id)
            created = user is None
            if user is None:
                user = User(id=tg_user.id, status=UserStatus.PENDING)
                s.add(user)
            user.username = tg_user.username
            user.full_name = tg_user.full_name
            user.last_seen_at = utcnow()
            if self.is_admin(tg_user.id):
                user.status = UserStatus.ACTIVE
            await s.commit()
            return user, created

    async def get(self, user_id: int) -> User | None:
        async with self._sm() as s:
            return await s.get(User, user_id)

    async def list_users(self, status: UserStatus | None = None) -> list[User]:
        async with self._sm() as s:
            query = select(User).order_by(User.created_at)
            if status:
                query = query.where(User.status == status)
            return list(await s.scalars(query))

    async def allow(self, user_id: int) -> User:
        """Whitelist a user by id, creating a placeholder row if they never wrote to the bot."""
        async with self._sm() as s:
            user = await s.get(User, user_id)
            if user is None:
                user = User(id=user_id)
                s.add(user)
            user.status = UserStatus.ACTIVE
            await s.commit()
            return user

    async def set_status(self, user_id: int, status: UserStatus) -> User | None:
        if self.is_admin(user_id) and status != UserStatus.ACTIVE:
            raise PermissionError("The admin cannot lose access")
        async with self._sm() as s:
            user = await s.get(User, user_id)
            if user:
                user.status = status
                await s.commit()
            return user

    async def remove(self, user_id: int) -> None:
        if self.is_admin(user_id):
            raise PermissionError("The admin cannot be removed")
        async with self._sm() as s:
            await s.execute(delete(User).where(User.id == user_id))
            await s.commit()

    async def update_settings(self, user_id: int, **fields: bool) -> User:
        async with self._sm() as s:
            user = await s.get(User, user_id)
            if user is None:
                raise LookupError(user_id)
            apply_fields(user, fields, set(self.SETTINGS))
            await s.commit()
            return user

    async def active_ids(
        self, *, exclude: int | None = None, setting: str | None = None
    ) -> list[int]:
        async with self._sm() as s:
            query = select(User.id).where(User.status == UserStatus.ACTIVE)
            if exclude is not None:
                query = query.where(User.id != exclude)
            if setting:
                if setting not in self.SETTINGS:
                    raise ValueError(setting)
                query = query.where(getattr(User, setting).is_(True))
            return list(await s.scalars(query))
