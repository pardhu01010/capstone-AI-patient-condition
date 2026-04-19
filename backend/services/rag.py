from __future__ import annotations

import os
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from backend.schemas import IntakePayload, Recommendation

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "hospital_protocols"

# Initialize client. FastEmbed is automatically triggered if using `add` and `query` methods.
# For local Qdrant, API key is usually not required.
try:
    q_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY if QDRANT_API_KEY else None)
except Exception as e:
    q_client = None
    print(f"Failed to connect to Qdrant: {e}")

# Fallback static library if Qdrant isn't seeded/running
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
    """Retrieves context via Qdrant Semantic Search using FastEmbed."""
    symptoms_text = " ".join(payload.symptoms).lower()
    matches: List[Recommendation] = []
    
    # Simple query formulation using symptoms and vitals
    query_text = f"Symptoms: {symptoms_text} | HR: {payload.vitals.heart_rate} | SpO2: {payload.vitals.spo2}"
    
    if q_client and q_client.collection_exists(collection_name=COLLECTION_NAME):
        try:
            # Query Qdrant using the built-in fastembed models
            search_result = q_client.query(
                collection_name=COLLECTION_NAME,
                query_text=query_text,
                limit=2
            )
            for hit in search_result:
                if hit.score > 0.70: # Confidence threshold
                    matches.append(Recommendation(
                        title=hit.metadata.get("title", "Protocol"),
                        detail=hit.metadata.get("detail", "")
                    ))
        except Exception as e:
            print(f"Qdrant query failed, falling back to static search: {e}")
            
    # Fallback to keyword match if vector match failed or returned empty
    if not matches:
        for entry in PROTOCOL_LIBRARY:
            if any(keyword in symptoms_text for keyword in entry["keywords"]):
                matches.append(
                    Recommendation(title=entry["title"], detail=entry["detail"])
                )

    # Absolute fallback
    if not matches:
        matches.append(
            Recommendation(
                title="General Stabilization",
                detail="Allocate resuscitation bay, IV access, and rapid assessment team.",
            )
        )

    return matches
