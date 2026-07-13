"""
Database setup — async SQLAlchemy with SQLite
Auto-creates admin user on first run
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from backend.models.db_models import Base, User
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/strikers.db")

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Create all tables and seed admin user on startup."""
    os.makedirs("./data", exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admin user
    from backend.utils.auth import hash_password
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.username == "strikers-protocol"))
        if not existing.scalar_one_or_none():
            admin = User(
                username  = "strikers-protocol",
                email     = "admin@strikers.local",
                hashed_pw = hash_password("23111526"),
                is_active = True,
            )
            db.add(admin)
            await db.commit()
            print("✓  Admin user created: strikers-protocol")
        else:
            print("✓  Admin user already exists")


async def get_db():
    """FastAPI dependency — yields a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
