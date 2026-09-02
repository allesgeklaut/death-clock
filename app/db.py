"""Database setup for Death Clock."""
from __future__ import annotations

import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DB_PATH = os.environ.get("DB_PATH", "/data/deathclock.db")
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Bump this when the schema changes to trigger an automatic rebuild.
SCHEMA_VERSION = 2


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(default="Anonymous")
    birth_date: Mapped[str]
    sex: Mapped[str]
    country: Mapped[str]
    education: Mapped[str]

    # Body
    height_cm: Mapped[float]
    weight_kg: Mapped[float]

    # Fitness
    exercise_freq: Mapped[str]
    exercise_intensity: Mapped[str]
    cardio_fitness: Mapped[str]

    # Health markers
    blood_pressure: Mapped[str]
    cholesterol: Mapped[str]
    blood_glucose: Mapped[str]
    hrv_ms: Mapped[float]
    resting_hr: Mapped[float]

    # Lifestyle
    smoking: Mapped[str]
    years_since_quit: Mapped[float]
    alcohol: Mapped[str]
    sleep_hours: Mapped[float]
    stress: Mapped[str]
    diet: Mapped[str]

    # Family
    family_history: Mapped[str]

    # Computed
    estimated_death: Mapped[str]
    created_at: Mapped[str]


engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create tables if they don't exist, or rebuild if the schema version
    has changed (tracked via a _schema_version meta-table)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    async with engine.begin() as conn:
        # Ensure the meta-table exists
        await conn.execute(
            text("CREATE TABLE IF NOT EXISTS _schema_version (id INTEGER PRIMARY KEY, value INTEGER)")
        )

        # Check current version
        result = await conn.execute(
            text("SELECT value FROM _schema_version WHERE id = 1")
        )
        row = result.fetchone()
        current_version = int(row[0]) if row else None

        if current_version != SCHEMA_VERSION:
            print(f"[death-clock] Schema version {current_version} → {SCHEMA_VERSION}, rebuilding tables...")
            await conn.run_sync(Base.metadata.drop_all)

        # Create tables (creates only what doesn't exist yet)
        await conn.run_sync(Base.metadata.create_all)

        # Record the current schema version
        await conn.execute(
            text("INSERT OR REPLACE INTO _schema_version (id, value) VALUES (1, :ver)"),
            {"ver": SCHEMA_VERSION},
        )