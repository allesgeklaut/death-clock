"""Lifespan estimation engine for the Death Clock.

A multi-factor heuristic inspired by epidemiological literature and
public longevity research.  Each factor returns a delta in years
(positive = longer life) plus a human-readable detail string.

This is NOT a medical prediction.  It is a memento mori — meant to spark
reflection, not foretell death.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .models import FactorDetail

# ---------------------------------------------------------------------------
# Baseline life expectancy (years) by country & sex.
# Values approximate WHO / national statistics (2023-era data).
# ---------------------------------------------------------------------------
_BASELINE: dict[str, dict[str, float]] = {
    "AT": {"male": 81.5, "female": 85.5},
    "AU": {"male": 81.0, "female": 85.0},
    "BE": {"male": 79.5, "female": 84.5},
    "BR": {"male": 73.0, "female": 80.0},
    "BG": {"male": 71.0, "female": 78.0},
    "CA": {"male": 80.0, "female": 84.0},
    "CH": {"male": 82.0, "female": 86.0},
    "CY": {"male": 79.0, "female": 83.0},
    "CZ": {"male": 76.0, "female": 82.0},
    "DE": {"male": 79.0, "female": 83.5},
    "DK": {"male": 79.5, "female": 83.5},
    "EE": {"male": 74.0, "female": 82.0},
    "ES": {"male": 80.5, "female": 86.0},
    "FI": {"male": 79.0, "female": 84.5},
    "FR": {"male": 80.0, "female": 86.0},
    "GB": {"male": 79.5, "female": 83.0},
    "GR": {"male": 78.5, "female": 84.0},
    "HR": {"male": 75.0, "female": 81.0},
    "HU": {"male": 72.0, "female": 79.0},
    "IE": {"male": 80.5, "female": 84.0},
    "IS": {"male": 81.0, "female": 84.0},
    "IT": {"male": 80.5, "female": 85.0},
    "JP": {"male": 81.5, "female": 87.5},
    "KR": {"male": 80.0, "female": 86.0},
    "LT": {"male": 70.0, "female": 80.0},
    "LU": {"male": 80.0, "female": 85.0},
    "LV": {"male": 70.5, "female": 79.5},
    "MT": {"male": 80.0, "female": 84.0},
    "NL": {"male": 80.5, "female": 83.5},
    "NO": {"male": 81.0, "female": 84.5},
    "NZ": {"male": 80.0, "female": 83.5},
    "PL": {"male": 74.0, "female": 82.0},
    "PT": {"male": 78.0, "female": 84.5},
    "RO": {"male": 71.0, "female": 79.0},
    "SE": {"male": 81.0, "female": 84.5},
    "SI": {"male": 78.0, "female": 84.0},
    "SK": {"male": 73.0, "female": 80.0},
    "TR": {"male": 73.0, "female": 78.0},
    "US": {"male": 76.0, "female": 81.0},
    "ZA": {"male": 62.0, "female": 68.0},
}

_GLOBAL_AVG = {"male": 73.0, "female": 78.0}

# Hard ceiling — even with optimal factors, individual life expectancy
# without major medical breakthroughs doesn't realistically exceed this.
_HARD_CEILING = 100.0


def _baseline(country: str, sex: str) -> float:
    return _BASELINE.get(country.upper(), _GLOBAL_AVG)[sex]


# ---------------------------------------------------------------------------
# Individual factor functions
# Each returns (years_delta, detail_string)
# ---------------------------------------------------------------------------

def f_bmi(height_cm: float, weight_kg: float) -> tuple[float, str]:
    bmi = weight_kg / (height_cm / 100) ** 2
    if bmi < 18.5:
        return -1.5, f"BMI {bmi:.1f} (underweight) — associated with fragility and nutrient deficiency"
    if 18.5 <= bmi < 25:
        return 1.0, f"BMI {bmi:.1f} (optimal range) — lowest all-cause mortality risk"
    if 25 <= bmi < 30:
        return -0.5, f"BMI {bmi:.1f} (overweight) — slightly elevated cardiovascular risk"
    if 30 <= bmi < 35:
        return -3.0, f"BMI {bmi:.1f} (obese class I) — significant cardiovascular and metabolic risk"
    return -6.0, f"BMI {bmi:.1f} (obese class II+) — major risk factor for multiple conditions"


def f_exercise(freq: str, intensity: str) -> tuple[float, str]:
    """Exercise frequency × intensity. Based on studies showing 40-50%
    all-cause mortality reduction for fit vs unfit adults."""
    table = {
        "none":      {"light": -2.5, "moderate": -2.5, "intense": -2.5},
        "1-2":       {"light": 1.0,  "moderate": 1.5,  "intense": 2.0},
        "3-4":       {"light": 2.0,  "moderate": 3.0,  "intense": 3.5},
        "5-6":       {"light": 3.0,  "moderate": 4.0,  "intense": 4.5},
        "7+":        {"light": 3.5,  "moderate": 4.0,  "intense": 4.0},  # diminishing / overtraining
    }
    years = table[freq][intensity]
    freq_desc = {"none": "sedentary", "1-2": "1-2×/week", "3-4": "3-4×/week",
                 "5-6": "5-6×/week", "7+": "7+×/week"}
    return years, f"{freq_desc[freq]} at {intensity} intensity"


def f_cardio_fitness(level: str) -> tuple[float, str]:
    table = {"low": -1.0, "moderate": 0.5, "high": 1.5, "elite": 2.0}
    desc = {"low": "low cardio capacity", "moderate": "moderate cardio fitness",
            "high": "high cardio fitness — strong VO₂ proxy", "elite": "elite cardio fitness"}
    return table[level], desc[level]


def f_education(level: str) -> tuple[float, str]:
    """Higher education correlates with longevity via health literacy,
    income, and access to care."""
    table = {"secondary": -0.5, "bachelor": 0.5, "master": 1.0, "doctorate": 1.5}
    desc = {"secondary": "secondary education", "bachelor": "bachelor's degree",
            "master": "master's degree", "doctorate": "doctorate"}
    return table[level], desc[level]


def f_blood_pressure(category: str) -> tuple[float, str]:
    table = {"normal": 1.0, "elevated": -0.5, "high": -3.0, "unknown": 0.0}
    desc = {"normal": "normal BP (<120/80) — optimal",
            "elevated": "elevated BP (120-139/80-89)",
            "high": "high BP (140+/90+) — major cardiovascular risk",
            "unknown": "blood pressure unknown — no adjustment"}
    return table[category], desc[category]


def f_cholesterol(category: str) -> tuple[float, str]:
    table = {"normal": 0.5, "elevated": -1.0, "high": -2.5, "unknown": 0.0}
    desc = {"normal": "normal cholesterol",
            "elevated": "elevated cholesterol (LDL 130-160)",
            "high": "high cholesterol (LDL 160+) — atherosclerotic risk",
            "unknown": "cholesterol unknown — no adjustment"}
    return table[category], desc[category]


def f_blood_glucose(category: str) -> tuple[float, str]:
    table = {"normal": 0.5, "prediabetic": -1.5, "diabetic": -4.0, "unknown": 0.0}
    desc = {"normal": "normal blood glucose (HbA1c <5.7)",
            "prediabetic": "prediabetic (HbA1c 5.7-6.4)",
            "diabetic": "diabetic (HbA1c ≥6.5) — significant metabolic risk",
            "unknown": "blood glucose unknown — no adjustment"}
    return table[category], desc[category]


def f_hrv(hrv_ms: float) -> tuple[float, str]:
    if hrv_ms <= 0:
        return 0.0, "HRV unknown — no adjustment"
    if hrv_ms < 20:
        return -1.0, f"HRV {hrv_ms:.0f} ms — low autonomic resilience"
    if hrv_ms < 40:
        return 0.0, f"HRV {hrv_ms:.0f} ms — below average"
    if hrv_ms < 60:
        return 1.0, f"HRV {hrv_ms:.0f} ms — solid recovery capacity"
    if hrv_ms < 80:
        return 1.5, f"HRV {hrv_ms:.0f} ms — strong cardiovascular fitness proxy"
    return 2.0, f"HRV {hrv_ms:.0f} ms — excellent autonomic health"


def f_resting_hr(resting_hr: float) -> tuple[float, str]:
    if resting_hr <= 0:
        return 0.0, "Resting HR unknown — no adjustment"
    if resting_hr < 50:
        return 1.5, f"RHR {resting_hr:.0f} bpm — athletic resting bradycardia"
    if resting_hr < 60:
        return 1.0, f"RHR {resting_hr:.0f} bpm — excellent"
    if resting_hr < 70:
        return 0.5, f"RHR {resting_hr:.0f} bpm — healthy range"
    if resting_hr < 80:
        return -0.5, f"RHR {resting_hr:.0f} bpm — slightly elevated"
    if resting_hr < 90:
        return -1.5, f"RHR {resting_hr:.0f} bpm — elevated, cardiovascular concern"
    return -2.5, f"RHR {resting_hr:.0f} bpm — high, significant risk marker"


def f_smoking(smoking: str, years_since_quit: float) -> tuple[float, str]:
    if smoking == "never":
        return 0.5, "Never smoked — baseline"
    if smoking == "former_light":
        if years_since_quit >= 5:
            return -0.3, f"Former light smoker, quit {years_since_quit:.0f} years ago — risk near-normalized"
        return -0.5, f"Former light smoker, quit {years_since_quit:.0f} years ago — still normalizing"
    if smoking == "former_heavy":
        if years_since_quit >= 10:
            return -1.5, f"Former heavy smoker, quit {years_since_quit:.0f} years ago — partially recovered"
        return -3.0, f"Former heavy smoker, quit {years_since_quit:.0f} years ago — residual risk"
    if smoking == "light":
        return -3.0, "Current light smoker — cumulative cardiovascular and cancer risk"
    # heavy
    return -7.0, "Current heavy smoker — major mortality risk factor"


def f_alcohol(category: str) -> tuple[float, str]:
    table = {"none": 0.5, "rare": 0.0, "moderate": -1.0, "heavy": -3.5}
    desc = {"none": "no alcohol consumption",
            "rare": "rare/occasional alcohol",
            "moderate": "moderate alcohol (1-2 drinks/day)",
            "heavy": "heavy alcohol — liver, cancer, and CV risk"}
    return table[category], desc[category]


def f_sleep(hours: float) -> tuple[float, str]:
    if 7 <= hours <= 8.5:
        return 1.0, f"{hours:.1f}h sleep — optimal range"
    if 6 <= hours < 7 or 8.5 < hours <= 9.5:
        return 0.0, f"{hours:.1f}h sleep — suboptimal but acceptable"
    if 5 <= hours < 6 or 9.5 < hours <= 10.5:
        return -1.5, f"{hours:.1f}h sleep — chronic deprivation or excess"
    return -3.0, f"{hours:.1f}h sleep — severe sleep dysregulation"


def f_stress(level: str) -> tuple[float, str]:
    table = {"low": 1.0, "medium": -0.5, "high": -2.5}
    desc = {"low": "low chronic stress", "medium": "moderate chronic stress",
            "high": "high chronic stress — cortisol-driven damage"}
    return table[level], desc[level]


def f_diet(quality: str) -> tuple[float, str]:
    table = {"mediterranean": 2.0, "balanced": 1.0, "average": 0.0, "poor": -2.0}
    desc = {"mediterranean": "Mediterranean-style diet — gold standard for longevity",
            "balanced": "balanced whole-food diet",
            "average": "average Western diet",
            "poor": "poor diet — processed foods, low vegetable intake"}
    return table[quality], desc[quality]


def f_family_history(category: str) -> tuple[float, str]:
    table = {"none": 0.5, "minor": -0.5, "significant": -2.5}
    desc = {"none": "no family history of early CV/cancer deaths",
            "minor": "minor family history (e.g. one relative, late-onset)",
            "significant": "significant family history — early CV/cancer in close relatives"}
    return table[category], desc[category]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate(
    birth_date_str: str, sex: str, country: str, education: str,
    height_cm: float, weight_kg: float,
    exercise_freq: str, exercise_intensity: str, cardio_fitness: str,
    blood_pressure: str, cholesterol: str, blood_glucose: str,
    hrv_ms: float, resting_hr: float,
    smoking: str, years_since_quit: float,
    alcohol: str, sleep_hours: float, stress: str, diet: str,
    family_history: str,
) -> tuple[datetime, float, float, list[FactorDetail]]:
    """Return (estimated_death_dt, baseline_le, adjusted_le, factors_list)."""
    birth = date.fromisoformat(birth_date_str)
    baseline = _baseline(country, sex)

    # Compute all factors
    raw_factors = [
        ("BMI / Body Composition", *f_bmi(height_cm, weight_kg)),
        ("Exercise Volume", *f_exercise(exercise_freq, exercise_intensity)),
        ("Cardio Fitness", *f_cardio_fitness(cardio_fitness)),
        ("Education", *f_education(education)),
        ("Blood Pressure", *f_blood_pressure(blood_pressure)),
        ("Cholesterol", *f_cholesterol(cholesterol)),
        ("Blood Glucose", *f_blood_glucose(blood_glucose)),
        ("Heart Rate Variability", *f_hrv(hrv_ms)),
        ("Resting Heart Rate", *f_resting_hr(resting_hr)),
        ("Smoking History", *f_smoking(smoking, years_since_quit)),
        ("Alcohol", *f_alcohol(alcohol)),
        ("Sleep", *f_sleep(sleep_hours)),
        ("Stress", *f_stress(stress)),
        ("Diet", *f_diet(diet)),
        ("Family History", *f_family_history(family_history)),
    ]

    factors = [
        FactorDetail(label=label, years=round(yrs, 1), detail=detail)
        for label, yrs, detail in raw_factors
    ]

    total_adjustment = sum(f.years for f in factors)
    adjusted = baseline + total_adjustment
    adjusted = max(adjusted, 1.0)
    adjusted = min(adjusted, _HARD_CEILING)

    estimated_death_date = birth + timedelta(days=adjusted * 365.25)
    estimated_death = datetime.combine(
        estimated_death_date, datetime.min.time(), tzinfo=timezone.utc
    )

    return estimated_death, baseline, adjusted, factors


def remaining_seconds(estimated_death: datetime) -> int:
    now = datetime.now(timezone.utc)
    delta = estimated_death - now
    return max(int(delta.total_seconds()), 0)