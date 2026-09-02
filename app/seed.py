"""Seed the Death Clock database with a default profile on first run.

This runs at container startup (via app/main.py lifespan). If the profiles
table is empty, it inserts the default user. If a profile already exists
(e.g. from a previous run or a manual survey submission), it does nothing.

The seed profile is loaded from `seed_profile.json` in the project root if
that file exists (it is gitignored — keep personal data there). Otherwise a
generic demo profile is used.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, delete

from .db import Profile, async_session
from .lifespan import estimate


SEED_FILE = Path(__file__).resolve().parent.parent / "seed_profile.json"

# Generic demo profile used when no seed_profile.json is present.
DEFAULT_PROFILE = {
    "name": "Demo",
    "birth_date": "1990-01-01",
    "sex": "male",
    "country": "AT",
    "education": "master",
    "height_cm": 180.0,
    "weight_kg": 80.0,
    "exercise_freq": "3-4",
    "exercise_intensity": "moderate",
    "cardio_fitness": "moderate",
    "blood_pressure": "normal",
    "cholesterol": "normal",
    "blood_glucose": "normal",
    "hrv_ms": 50.0,
    "resting_hr": 60.0,
    "smoking": "never",
    "years_since_quit": 0.0,
    "alcohol": "rare",
    "sleep_hours": 7.0,
    "stress": "medium",
    "diet": "balanced",
    "family_history": "none",
}


def _load_profile() -> dict:
    if SEED_FILE.exists():
        data = json.loads(SEED_FILE.read_text())
        return {**DEFAULT_PROFILE, **data}
    return DEFAULT_PROFILE


async def seed_if_empty() -> bool:
    """Insert the default profile if no profile exists.

    Returns True if a seed was inserted, False if the table was already
    populated.
    """
    profile_data = _load_profile()

    async with async_session() as session:
        existing = await session.scalar(select(Profile).limit(1))
        if existing is not None:
            return False

        # Compute the estimate from the seed profile data
        est_death, _, _, _ = estimate(
            profile_data["birth_date"],
            profile_data["sex"],
            profile_data["country"],
            profile_data["education"],
            profile_data["height_cm"],
            profile_data["weight_kg"],
            profile_data["exercise_freq"],
            profile_data["exercise_intensity"],
            profile_data["cardio_fitness"],
            profile_data["blood_pressure"],
            profile_data["cholesterol"],
            profile_data["blood_glucose"],
            profile_data["hrv_ms"],
            profile_data["resting_hr"],
            profile_data["smoking"],
            profile_data["years_since_quit"],
            profile_data["alcohol"],
            profile_data["sleep_hours"],
            profile_data["stress"],
            profile_data["diet"],
            profile_data["family_history"],
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        profile = Profile(
            **profile_data,
            estimated_death=est_death.isoformat(),
            created_at=now_iso,
        )
        session.add(profile)
        await session.commit()

        print(f"[death-clock] Seeded default profile: {profile_data['name']} "
              f"(estimated death: {est_death.date()})")
        return True


if __name__ == "__main__":
    # Allow running standalone: python -m app.seed
    asyncio.run(seed_if_empty())