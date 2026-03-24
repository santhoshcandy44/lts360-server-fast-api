from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import JOB_DATABASE_URL

job_engine = create_async_engine(
    JOB_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,      
    pool_recycle=1800 ,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=job_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_job_db():
    async with job_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_job_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise