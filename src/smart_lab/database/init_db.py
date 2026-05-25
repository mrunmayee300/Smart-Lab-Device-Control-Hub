from smart_lab.database.models import Base
from smart_lab.database.session import engine


async def init_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
