from . import models  # noqa
from .database import Base, engine


async def db_create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
