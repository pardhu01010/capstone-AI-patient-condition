from __future__ import annotations

import json
from typing import Dict, List, Optional
from prisma import Client, Json

class CaseStore:
    """Prisma-backed persistence layer using PostgreSQL (Supabase)."""

    def __init__(self) -> None:
        pass

    async def add_case(self, case_dict: Dict) -> None:
        db = Client()
        await db.connect()
        
        # Convert any None values logic if necessary.
        # Prisma JSON handles dict lists well in Python
        try:
            raw_vitals = case_dict.get("vitals")
            
            existing = await db.case.find_unique(where={"case_id": case_dict["case_id"]})
            if existing:
                await db.case.update(
                    where={"case_id": case_dict["case_id"]},
                    data={
                        "last_updated_at": case_dict.get("last_updated_at"),
                        "vitals": Json(raw_vitals) if raw_vitals else None,
                        "risk_level": case_dict.get("risk_level"),
                        "survival_probability": float(case_dict.get("survival_probability", 0)),
                        "cardiac_risk_score": float(case_dict.get("cardiac_risk_score", 0)),
                        "llm_summary": case_dict.get("llm_summary", ""),
                        "patient_status": case_dict.get("patient_status", "active"),
                        "vitals_history": Json(case_dict.get("vitals_history", []))
                    }
                )
            else:
                await db.case.create(
                    data={
                        "case_id": case_dict["case_id"],
                        "created_at": case_dict["created_at"],
                        "patient": Json(case_dict.get("patient", {})),
                        "vitals": Json(raw_vitals) if raw_vitals else None,
                        "labs": Json(case_dict.get("labs", [])),
                        "symptoms": Json(case_dict.get("symptoms", [])),
                        "meds_administered": Json(case_dict.get("meds_administered", [])),
                        "oxygen_support": case_dict.get("oxygen_support"),
                        "notes": case_dict.get("notes"),
                        "location": case_dict.get("location"),
                        "attachments": Json(case_dict.get("attachments", [])),
                        
                        "risk_level": case_dict.get("risk_level", "unknown"),
                        "survival_probability": float(case_dict.get("survival_probability", 0)),
                        "cardiac_risk_score": float(case_dict.get("cardiac_risk_score", 0)),
                        
                        "recommendations": Json(case_dict.get("recommendations", [])),
                        "rag_protocols": Json(case_dict.get("rag_protocols", [])),
                        "medication_plan": Json(case_dict.get("medication_plan", [])),
                        "llm_summary": case_dict.get("llm_summary", ""),
                        
                        "shap_local_plot_b64": case_dict.get("shap_local_plot_b64", ""),
                        "shap_global_plot_b64": case_dict.get("shap_global_plot_b64", ""),
                        "lime_local_plot_b64": case_dict.get("lime_local_plot_b64", ""),
                        "lr_survival_probability": float(case_dict.get("lr_survival_probability", 0)),
                        "top_shap_features": Json(case_dict.get("top_shap_features", [])),
                        
                        "hospital_suggestions": Json(case_dict.get("hospital_suggestions", []))
                    }
                )
        finally:
            await db.disconnect()

    async def list_cases(self) -> List[Dict]:
        db = Client()
        await db.connect()
        try:
            cases = await db.case.find_many(order={"created_at": "desc"})
            return [c.model_dump() for c in cases]
        finally:
            await db.disconnect()

    async def get_case(self, case_id: str) -> Optional[Dict]:
        db = Client()
        await db.connect()
        try:
            c = await db.case.find_unique(where={"case_id": case_id})
            if not c:
                return None
            return c.model_dump()
        finally:
            await db.disconnect()
