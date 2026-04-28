from __future__ import annotations

import os
from typing import List, Optional

from backend.schemas import IntakePayload, MedicationPlan, Recommendation
from backend.services.inference import StructuredInferenceResult

try:
    from langfuse.groq import Groq
    # The client automatically picks up GROQ_API_KEY, LANGFUSE_SECRET_KEY, 
    # LANGFUSE_PUBLIC_KEY, and LANGFUSE_HOST from the environment variables.
    client = Groq()
except ImportError:
    client = None

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
    if not api_key or client is None:
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

    try:
        # This call is automatically traced by Langfuse!
        # It logs latency, token usage, the prompt, the response, and model config.
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=float(os.getenv("GROQ_TEMPERATURE", "0.3")),
            max_tokens=300,
            name="triage-handoff-summary" # Distinct name in Langfuse UI
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq/Langfuse Error: {e}")
        return None
