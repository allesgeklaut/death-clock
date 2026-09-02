"""Pydantic models for the Death Clock API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SurveyIn(BaseModel):
    # ── Basics ──
    name: str = Field(default="Anonymous", max_length=100)
    birth_date: str = Field(..., description="ISO date YYYY-MM-DD")
    sex: str = Field(..., pattern="^(male|female)$")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    education: str = Field(..., pattern="^(secondary|bachelor|master|doctorate)$",
                           description="Education level")

    # ── Body ──
    height_cm: float = Field(..., gt=50, lt=300)
    weight_kg: float = Field(..., gt=20, lt=500)

    # ── Fitness ──
    exercise_freq: str = Field(..., pattern="^(none|1-2|3-4|5-6|7\\+)$",
                                description="Exercise sessions per week")
    exercise_intensity: str = Field(..., pattern="^(light|moderate|intense)$",
                                     description="Typical session intensity")
    cardio_fitness: str = Field(..., pattern="^(low|moderate|high|elite)$",
                                 description="Self-rated cardio fitness level")

    # ── Health markers ──
    blood_pressure: str = Field(..., pattern="^(normal|elevated|high|unknown)$",
                                 description="Known blood pressure category")
    cholesterol: str = Field(..., pattern="^(normal|elevated|high|unknown)$",
                             description="Known cholesterol levels")
    blood_glucose: str = Field(..., pattern="^(normal|prediabetic|diabetic|unknown)$",
                               description="Known blood glucose status")
    hrv_ms: float = Field(default=0, ge=0, le=200,
                          description="Heart Rate Variability (RMSSD) in ms, 0 if unknown")
    resting_hr: float = Field(default=0, ge=30, le=150,
                               description="Resting heart rate bpm, 0 if unknown")

    # ── Lifestyle ──
    smoking: str = Field(..., pattern="^(never|former_light|former_heavy|light|heavy)$")
    years_since_quit: float = Field(default=0, ge=0,
                                     description="Years since quitting smoking (0 if never/current)")
    alcohol: str = Field(..., pattern="^(none|rare|moderate|heavy)$")
    sleep_hours: float = Field(..., ge=0, le=24)
    stress: str = Field(..., pattern="^(low|medium|high)$")
    diet: str = Field(..., pattern="^(mediterranean|balanced|average|poor)$")

    # ── Family history ──
    family_history: str = Field(..., pattern="^(none|minor|significant)$",
                                 description="Family history of early CV/cancer deaths")


class FactorDetail(BaseModel):
    label: str
    years: float
    detail: str


class SurveyOut(BaseModel):
    id: int
    name: str
    birth_date: str
    estimated_death: str
    remaining_seconds: int
    baseline_life_expectancy: float
    adjusted_life_expectancy: float
    total_adjustment: float
    factors: list[FactorDetail]