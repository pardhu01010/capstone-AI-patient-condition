from __future__ import annotations

from typing import Dict, List

from backend.schemas import IntakePayload, MedicationPlan


SYMPTOM_MED_MAP: Dict[str, List[MedicationPlan]] = {
    "chest pain": [
        MedicationPlan(
            medication="Aspirin",
            purpose="Antiplatelet loading dose prior to suspected ACS",
            priority="immediate",
        ),
        MedicationPlan(
            medication="Nitroglycerin",
            purpose="Relieve ischemic chest pain and reduce preload",
            priority="immediate",
        ),
    ],
    "shortness of breath": [
        MedicationPlan(
            medication="Bronchodilator Nebs",
            purpose="Open airways for respiratory distress/COPD/asthma",
            priority="prep",
        ),
        MedicationPlan(
            medication="IV Steroids",
            purpose="Reduce inflammatory airway response",
            priority="prep",
        ),
    ],
    "trauma": [
        MedicationPlan(
            medication="TXA",
            purpose="Early hemorrhage control within 3 hours of trauma",
            priority="prep",
        ),
        MedicationPlan(
            medication="O-negative blood units",
            purpose="Immediate transfusion readiness",
            priority="immediate",
        ),
    ],
    "arrhythmia": [
        MedicationPlan(
            medication="Amiodarone",
            purpose="Stabilize wide-complex tachyarrhythmia",
            priority="prep",
        ),
        MedicationPlan(
            medication="Magnesium Sulfate",
            purpose="Torsades or prolonged QT management",
            priority="prep",
        ),
    ],
}

DEFAULT_PLAN = [
    MedicationPlan(
        medication="IV Access Kit",
        purpose="Ensure at least two large-bore IV lines for meds/fluids",
        priority="standard",
    ),
    MedicationPlan(
        medication="Advanced Airway Cart",
        purpose="Intubation backup on patient arrival",
        priority="standard",
    ),
]


def build_medication_plan(payload: IntakePayload) -> List[MedicationPlan]:
    symptoms = [symptom.lower() for symptom in payload.symptoms]
    plan: List[MedicationPlan] = []

    for symptom in symptoms:
        for keyword, meds in SYMPTOM_MED_MAP.items():
            if keyword in symptom:
                plan.extend(meds)

    if payload.vitals.spo2 and payload.vitals.spo2 < 90:
        plan.append(
            MedicationPlan(
                medication="High-flow oxygen supplies",
                purpose="Rapid oxygenation for hypoxic patient",
                priority="immediate",
            )
        )

    if not plan:
        plan = DEFAULT_PLAN.copy()

    # Deduplicate by medication name while preserving priority.
    seen = {}
    for item in plan:
        if item.medication not in seen:
            seen[item.medication] = item

    return list(seen.values())

