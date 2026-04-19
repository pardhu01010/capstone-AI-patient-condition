from __future__ import annotations

import os
from typing import List, Optional

import requests

from backend.schemas import IntakePayload, MedicationPlan, Recommendation
from backend.services.inference import StructuredInferenceResult


GROQ_API_URL = os.getenv(
    "GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"
)
GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")


def _format_for_prompt(payload: IntakePayload, inference: StructuredInferenceResult) -> str:
    vitals = payload.vitals
    lines = [
        f"Risk level: {inference.risk_level}",
        f"Survival probability: {inference.survival_probability}",
        f"Cardiac risk score: {inference.cardiac_risk_score}",
        f"Heart rate: {vitals.heart_rate}",
        f"Blood pressure: {vitals.blood_pressure_systolic}/{vitals.blood_pressure_diastolic}",
        f"SpO2: {vitals.spo2}",
        f"Respiratory rate: {vitals.respiratory_rate}",
        f"Oxygen support: {payload.oxygen_support}",
        f"Symptoms: {', '.join(payload.symptoms) or 'none provided'}",
        f"Medications administered: {', '.join(payload.meds_administered) or 'none provided'}",
    ]
    return "\n".join(lines)


def generate_summary_with_groq(
    payload: IntakePayload,
    inference: StructuredInferenceResult,
    medication_plan: List[MedicationPlan],
    recommendations: List[Recommendation],
) -> Optional[str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    system_prompt = (
        "You are a hospital triage expert. Summarize incoming ambulance data in under 6 sentences. "
        "Highlight immediate risks, stabilization steps, staffing alerts, and medication preparation."
    )

    meds_text = "; ".join(
        f"{item.medication} ({item.priority}) - {item.purpose}"
        for item in medication_plan
    )
    recs_text = "; ".join(f"{rec.title}: {rec.detail}" for rec in recommendations)

    user_prompt = (
        f"Patient snapshot:\n{_format_for_prompt(payload, inference)}\n"
        f"Medication checklist: {meds_text}\n"
        f"AI recommendations: {recs_text}\n"
        "Create a concise handoff summary and explicit prep instructions."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(os.getenv("GROQ_TEMPERATURE", "0.3")),
        "max_tokens": 300,
    }

    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return content.strip()
    except (requests.RequestException, KeyError, IndexError):
        return None

