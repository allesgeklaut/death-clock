"""FastAPI application — Death Clock."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import Profile, async_session, init_db
from .lifespan import estimate, remaining_seconds
from .models import SurveyIn, SurveyOut
from .seed import seed_if_empty

app = FastAPI(title="Death Clock", version="0.2.0")


@app.on_event("startup")
async def _startup() -> None:
    await init_db()
    await seed_if_empty()


def _row_to_survey_out(row: Profile) -> SurveyOut:
    """Recompute the full estimate from stored survey fields."""
    est_death, baseline, adjusted, factors = estimate(
        row.birth_date, row.sex, row.country, row.education,
        row.height_cm, row.weight_kg,
        row.exercise_freq, row.exercise_intensity, row.cardio_fitness,
        row.blood_pressure, row.cholesterol, row.blood_glucose,
        row.hrv_ms, row.resting_hr,
        row.smoking, row.years_since_quit,
        row.alcohol, row.sleep_hours, row.stress, row.diet,
        row.family_history,
    )
    return SurveyOut(
        id=row.id,
        name=row.name,
        birth_date=row.birth_date,
        estimated_death=row.estimated_death,
        remaining_seconds=remaining_seconds(est_death),
        baseline_life_expectancy=round(baseline, 1),
        adjusted_life_expectancy=round(adjusted, 1),
        total_adjustment=round(adjusted - baseline, 1),
        factors=factors,
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/profile", response_model=SurveyOut)
async def get_active_profile() -> SurveyOut:
    """Return the single stored profile, or 404 if none exists."""
    from sqlalchemy import select

    async with async_session() as session:
        row = await session.scalar(select(Profile).order_by(Profile.id.desc()).limit(1))
        if row is None:
            raise HTTPException(status_code=404, detail="No profile found")
        return _row_to_survey_out(row)


@app.post("/api/survey", response_model=SurveyOut)
async def submit_survey(survey: SurveyIn) -> SurveyOut:
    """Create or replace the single stored profile."""
    from sqlalchemy import delete

    est_death, baseline, adjusted, factors = estimate(
        survey.birth_date, survey.sex, survey.country, survey.education,
        survey.height_cm, survey.weight_kg,
        survey.exercise_freq, survey.exercise_intensity, survey.cardio_fitness,
        survey.blood_pressure, survey.cholesterol, survey.blood_glucose,
        survey.hrv_ms, survey.resting_hr,
        survey.smoking, survey.years_since_quit,
        survey.alcohol, survey.sleep_hours, survey.stress, survey.diet,
        survey.family_history,
    )
    now_iso = datetime.now(timezone.utc).isoformat()

    async with async_session() as session:
        await session.execute(delete(Profile))

        profile = Profile(
            name=survey.name,
            birth_date=survey.birth_date,
            sex=survey.sex,
            country=survey.country,
            education=survey.education,
            height_cm=survey.height_cm,
            weight_kg=survey.weight_kg,
            exercise_freq=survey.exercise_freq,
            exercise_intensity=survey.exercise_intensity,
            cardio_fitness=survey.cardio_fitness,
            blood_pressure=survey.blood_pressure,
            cholesterol=survey.cholesterol,
            blood_glucose=survey.blood_glucose,
            hrv_ms=survey.hrv_ms,
            resting_hr=survey.resting_hr,
            smoking=survey.smoking,
            years_since_quit=survey.years_since_quit,
            alcohol=survey.alcohol,
            sleep_hours=survey.sleep_hours,
            stress=survey.stress,
            diet=survey.diet,
            family_history=survey.family_history,
            estimated_death=est_death.isoformat(),
            created_at=now_iso,
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

    return _row_to_survey_out(profile)


@app.delete("/api/profile")
async def delete_active_profile() -> dict:
    """Delete the stored profile (reset)."""
    from sqlalchemy import delete

    async with async_session() as session:
        await session.execute(delete(Profile))
        await session.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")