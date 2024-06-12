from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from logging_config import setup_logging
import logging
from settings import DATABASE_URL
from models import Base

setup_logging()
logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession,
                            expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info('База данных инициализирована')

__all__ = ['SessionLocal', 'init_db']
