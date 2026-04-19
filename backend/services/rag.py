from __future__ import annotations

from typing import List

from backend.schemas import IntakePayload, Recommendation

PROTOCOL_LIBRARY = [
    {
        "title": "Acute Coronary Syndrome Prep",
        "detail": "Activate cath lab pathway, prepare antiplatelet therapy, have troponin kits ready.",
        "keywords": ["chest pain", "pressure", "stemi", "heart"],
    },
    {
        "title": "Respiratory Distress Bundle",
        "detail": "Set up BiPAP, bronchodilators, steroids, and airway adjuncts.",
        "keywords": ["shortness of breath", "wheezing", "spo2", "respiratory"],
    },
    {
        "title": "Trauma Readiness",
        "detail": "Notify surgery, prep blood products, and ensure imaging suite availability.",
        "keywords": ["bleeding", "trauma", "injury", "fracture"],
    },
]


def retrieve_contextual_protocols(payload: IntakePayload) -> List[Recommendation]:
    """Simulates a RAG search over curated hospital protocols."""

    symptoms_text = " ".join(payload.symptoms).lower()
    matches: List[Recommendation] = []

    for entry in PROTOCOL_LIBRARY:
        if any(keyword in symptoms_text for keyword in entry["keywords"]):
            matches.append(
                Recommendation(title=entry["title"], detail=entry["detail"])
            )

    # Default fallback
    if not matches:
        matches.append(
            Recommendation(
                title="General Stabilization",
                detail="Allocate resuscitation bay, IV access, and rapid assessment team.",
            )
        )

    return matches

