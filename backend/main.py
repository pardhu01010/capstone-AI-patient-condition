from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from backend.schemas import (
    AttachmentMeta,
    AcknowledgePayload,
    CaseDetail,
    CaseSummary,
    CaseUpdatePayload,
    CaseUpdateResponse,
    DeceasedPayload,
    DeceasedResponse,
    HospitalSuggestion,
    IntakePayload,
    IntakeResponse,
    LabSample,
    MedicationPlan,
    PatientInfo,
    SHAPFeature,
    SuggestionPayload,
    VitalSigns,
    VitalSnapshot,
)
from backend.services.inference import run_structured_models
from backend.services.llm import generate_summary_with_groq
from backend.services.medication import build_medication_plan
from backend.services.rag import retrieve_contextual_protocols, index_case_to_vdb
from backend.storage import CaseStore, db
from fastapi.concurrency import run_in_threadpool


store = CaseStore()

app = FastAPI(title="Intelligent Ambulance Backend", version="0.2.0")

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def healthcheck() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow()}


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------

@app.post("/api/intake", response_model=IntakeResponse)
async def create_case(payload: IntakePayload) -> IntakeResponse:
    inference_result = await run_in_threadpool(run_structured_models, payload)
    protocols = await run_in_threadpool(retrieve_contextual_protocols, payload)
    combined_recommendations = inference_result.recommendations + protocols
    medication_plan = build_medication_plan(payload)

    case_id = str(uuid4())
    created_at = datetime.utcnow()

    llm_summary = await run_in_threadpool(
        _compose_summary, payload, inference_result, medication_plan, combined_recommendations
    )

    case_record = {
        "case_id": case_id,
        "created_at": created_at.isoformat(),
        "patient": payload.patient.dict(),
        "vitals": payload.vitals.dict(),
        "labs": [lab.dict() for lab in payload.labs],
        "symptoms": payload.symptoms,
        "meds_administered": payload.meds_administered,
        "oxygen_support": payload.oxygen_support,
        "notes": payload.notes,
        "location": payload.location,
        "attachments": [att.dict() for att in payload.attachments],
        "risk_level": inference_result.risk_level,
        "survival_probability": inference_result.survival_probability,
        "cardiac_risk_score": inference_result.cardiac_risk_score,
        "recommendations": [rec.dict() for rec in inference_result.recommendations],
        "rag_protocols": [rec.dict() for rec in protocols],
        "medication_plan": [item.dict() for item in medication_plan],
        "llm_summary": llm_summary,
        "shap_local_plot_b64": inference_result.shap_local_plot_b64,
        "shap_global_plot_b64": inference_result.shap_global_plot_b64,
        "lime_local_plot_b64": inference_result.lime_local_plot_b64,
        "lr_survival_probability": inference_result.lr_survival_probability,
        "top_shap_features": inference_result.top_shap_features,
        "vitals_history": [{
            "timestamp": created_at.isoformat(),
            "vitals": payload.vitals.dict(),
            "risk_level": inference_result.risk_level,
            "survival_probability": inference_result.survival_probability,
            "cardiac_risk_score": inference_result.cardiac_risk_score,
            "update_reason": "Initial assessment",
            "symptoms": payload.symptoms,
        }]
    }

    await store.add_case(case_record)
    
    # Save to Vector DB for AI pattern analysis
    await run_in_threadpool(index_case_to_vdb, payload, case_id)

    return IntakeResponse(
        case_id=case_id,
        created_at=created_at,
        risk_level=inference_result.risk_level,
        survival_probability=inference_result.survival_probability,
        cardiac_risk_score=inference_result.cardiac_risk_score,
        recommendations=combined_recommendations,
        llm_summary=llm_summary,
        medication_plan=medication_plan,
        shap_local_plot_b64=inference_result.shap_local_plot_b64,
        shap_global_plot_b64=inference_result.shap_global_plot_b64,
        lime_local_plot_b64=inference_result.lime_local_plot_b64,
        lr_survival_probability=inference_result.lr_survival_probability,
        top_shap_features=[
            SHAPFeature(**f) for f in inference_result.top_shap_features
        ],
    )


# ---------------------------------------------------------------------------
# Case list
# ---------------------------------------------------------------------------

@app.get("/api/cases", response_model=List[CaseSummary])
async def list_cases() -> List[CaseSummary]:
    summaries: List[CaseSummary] = []
    cases = await store.list_cases()
    for record in cases:
        summaries.append(
            CaseSummary(
                case_id=record["case_id"],
                created_at=datetime.fromisoformat(record["created_at"]),
                patient=record["patient"],
                vitals=record["vitals"],
                risk_level=record["risk_level"],
                survival_probability=record["survival_probability"],
                patient_status=record.get("patient_status", "active"),
            )
        )
    return summaries


# ---------------------------------------------------------------------------
# Case detail  (with XAI back-fill for old records)
# ---------------------------------------------------------------------------

@app.get("/api/cases/{case_id}", response_model=CaseDetail)
async def get_case(case_id: str) -> CaseDetail:
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    # ------------------------------------------------------------------
    # Back-fill XAI fields for cases saved before the XAI update.
    # Detected when shap_local_plot_b64 is absent or empty.
    # Re-runs inference from stored vitals & symptoms, then persists
    # the enriched record so subsequent fetches are instant.
    # ------------------------------------------------------------------
    if not record.get("shap_local_plot_b64"):
        try:
            backfill_payload = IntakePayload(
                patient=PatientInfo(**record["patient"]),
                vitals=VitalSigns(**record["vitals"]),
                labs=[LabSample(**l) for l in record.get("labs", [])],
                symptoms=record.get("symptoms", []),
                meds_administered=record.get("meds_administered", []),
                oxygen_support=record.get("oxygen_support"),
                notes=record.get("notes"),
                location=record.get("location"),
                attachments=[],   # skip binary re-encode for back-fill
            )
            xai = run_structured_models(backfill_payload)
            record["shap_local_plot_b64"]     = xai.shap_local_plot_b64
            record["shap_global_plot_b64"]    = xai.shap_global_plot_b64
            record["lime_local_plot_b64"]     = xai.lime_local_plot_b64
            record["lr_survival_probability"] = xai.lr_survival_probability
            record["top_shap_features"]       = xai.top_shap_features
            if not record.get("rag_protocols"):
                record["rag_protocols"] = []
            await store.add_case(record)   # persist so next fetch is instant
        except Exception:
            # Safe fallback: dashboard renders without XAI plots
            record.setdefault("shap_local_plot_b64", "")
            record.setdefault("shap_global_plot_b64", "")
            record.setdefault("lime_local_plot_b64", "")
            record.setdefault("lr_survival_probability", 0.0)
            record.setdefault("top_shap_features", [])
            record.setdefault("rag_protocols", [])

    return CaseDetail(
        case_id=record["case_id"],
        created_at=datetime.fromisoformat(record["created_at"]),
        patient=record["patient"],
        vitals=record["vitals"],
        labs=record.get("labs", []),
        symptoms=record.get("symptoms", []),
        meds_administered=record.get("meds_administered", []),
        oxygen_support=record.get("oxygen_support"),
        notes=record.get("notes"),
        location=record.get("location"),
        risk_level=record["risk_level"],
        survival_probability=record["survival_probability"],
        cardiac_risk_score=record["cardiac_risk_score"],
        recommendations=(
            record.get("recommendations", []) + record.get("rag_protocols", [])
        ),
        llm_summary=record["llm_summary"],
        attachments=_sanitize_attachments_list(record.get("attachments", [])),
        medication_plan=[
            MedicationPlan(**item) for item in record.get("medication_plan", [])
        ],
        shap_local_plot_b64=record.get("shap_local_plot_b64", ""),
        shap_global_plot_b64=record.get("shap_global_plot_b64", ""),
        lime_local_plot_b64=record.get("lime_local_plot_b64", ""),
        lr_survival_probability=record.get("lr_survival_probability", 0.0),
        top_shap_features=[
            SHAPFeature(**f) for f in record.get("top_shap_features", [])
        ],
        patient_status=record.get("patient_status", "active"),
        time_of_death=record.get("time_of_death"),
        cause_notes=record.get("cause_notes"),
        confirmed_by=record.get("confirmed_by"),
        declared_at=datetime.fromisoformat(record["declared_at"]) if record.get("declared_at") else None,
        hospital_suggestions=[
            HospitalSuggestion(**s) for s in record.get("hospital_suggestions", [])
        ],
        vitals_history=[VitalSnapshot(**s) for s in (record.get("vitals_history") or [])],
    )


# ---------------------------------------------------------------------------
# Case update  (PATCH) — mid-transport vitals change
# ---------------------------------------------------------------------------

@app.patch("/api/cases/{case_id}/update", response_model=CaseUpdateResponse)
async def update_case(case_id: str, payload: CaseUpdatePayload) -> CaseUpdateResponse:
    """
    Update an existing case with new vitals mid-transport.
    - Merges new vitals over the existing ones (only provided fields change).
    - Re-runs full inference + SHAP + LIME on the merged vitals.
    - Appends a VitalSnapshot to the case history timeline.
    - Persists updated record to cases.json.
    """
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    updated_at = datetime.utcnow()

    # -- Merge: start from existing vitals, overwrite only provided fields --
    existing_vitals = record["vitals"].copy()
    new_vitals_dict = payload.vitals.dict(exclude_none=True)
    merged_vitals = {**existing_vitals, **new_vitals_dict}

    # -- Merge symptoms and meds if provided --
    merged_symptoms = payload.symptoms if payload.symptoms is not None else record.get("symptoms", [])
    merged_meds = payload.meds_administered if payload.meds_administered is not None else record.get("meds_administered", [])
    merged_oxygen = payload.oxygen_support if payload.oxygen_support is not None else record.get("oxygen_support")

    # -- Re-run inference on merged vitals --
    update_payload = IntakePayload(
        patient=PatientInfo(**record["patient"]),
        vitals=VitalSigns(**merged_vitals),
        labs=[LabSample(**l) for l in record.get("labs", [])],
        symptoms=merged_symptoms,
        meds_administered=merged_meds,
        oxygen_support=merged_oxygen,
        notes=payload.notes or record.get("notes"),
        location=record.get("location"),
        attachments=[],
    )

    inference_result = run_structured_models(update_payload)
    protocols = retrieve_contextual_protocols(update_payload)
    combined_recommendations = inference_result.recommendations + protocols
    medication_plan = build_medication_plan(update_payload)
    llm_summary = _compose_summary(
        update_payload, inference_result, medication_plan, combined_recommendations
    )

    # -- Build snapshot entry for timeline --
    snapshot = {
        "timestamp": updated_at.isoformat(),
        "vitals": merged_vitals,
        "risk_level": inference_result.risk_level,
        "survival_probability": inference_result.survival_probability,
        "cardiac_risk_score": inference_result.cardiac_risk_score,
        "update_reason": payload.update_reason or "Vitals updated",
        "symptoms": merged_symptoms,
    }

    # -- Append to history (keep original as first entry if not yet done) --
    if "vitals_history" not in record:
        # First update: save original as baseline
        original_snapshot = {
            "timestamp": record["created_at"],
            "vitals": record["vitals"],
            "risk_level": record["risk_level"],
            "survival_probability": record["survival_probability"],
            "cardiac_risk_score": record["cardiac_risk_score"],
            "update_reason": "Initial assessment",
            "symptoms": record.get("symptoms", []),
        }
        record["vitals_history"] = [original_snapshot]

    record["vitals_history"].append(snapshot)

    # -- Update the live fields in the record --
    record["vitals"]               = merged_vitals
    record["symptoms"]             = merged_symptoms
    record["meds_administered"]    = merged_meds
    record["oxygen_support"]       = merged_oxygen
    record["risk_level"]           = inference_result.risk_level
    record["survival_probability"] = inference_result.survival_probability
    record["cardiac_risk_score"]   = inference_result.cardiac_risk_score
    record["recommendations"]      = [r.dict() for r in inference_result.recommendations]
    record["rag_protocols"]        = [r.dict() for r in protocols]
    record["medication_plan"]      = [m.dict() for m in medication_plan]
    record["llm_summary"]          = llm_summary
    record["shap_local_plot_b64"]  = inference_result.shap_local_plot_b64
    record["shap_global_plot_b64"] = inference_result.shap_global_plot_b64
    record["lime_local_plot_b64"]  = inference_result.lime_local_plot_b64
    record["lr_survival_probability"] = inference_result.lr_survival_probability
    record["top_shap_features"]    = inference_result.top_shap_features
    record["last_updated_at"]      = updated_at.isoformat()

    await store.add_case(record)

    return CaseUpdateResponse(
        case_id=case_id,
        updated_at=updated_at,
        risk_level=inference_result.risk_level,
        survival_probability=inference_result.survival_probability,
        cardiac_risk_score=inference_result.cardiac_risk_score,
        recommendations=combined_recommendations,
        llm_summary=llm_summary,
        update_reason=payload.update_reason,
    )


@app.get("/api/cases/{case_id}/history", response_model=List[VitalSnapshot])
async def get_case_history(case_id: str) -> List[VitalSnapshot]:
    """Return full vitals history timeline for a case."""
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    history = record.get("vitals_history", [])
    if not history:
        # No updates yet — return just the original snapshot
        history = [{
            "timestamp": record["created_at"],
            "vitals": record["vitals"],
            "risk_level": record["risk_level"],
            "survival_probability": record["survival_probability"],
            "cardiac_risk_score": record["cardiac_risk_score"],
            "update_reason": "Initial assessment",
            "symptoms": record.get("symptoms", []),
        }]

    return [VitalSnapshot(**s) for s in history]


# ---------------------------------------------------------------------------
# Deceased declaration endpoint
# ---------------------------------------------------------------------------

@app.post("/api/cases/{case_id}/deceased", response_model=DeceasedResponse)
async def declare_deceased(case_id: str, payload: DeceasedPayload) -> DeceasedResponse:
    """Mark a patient as deceased — records TOD, cause, and confirming person."""
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    if record.get("patient_status") == "deceased":
        raise HTTPException(status_code=400, detail="Patient already marked as deceased")

    declared_at   = datetime.utcnow()
    time_of_death = payload.time_of_death or declared_at.strftime("%H:%M")

    record["patient_status"]       = "deceased"
    record["time_of_death"]        = time_of_death
    record["cause_notes"]          = payload.cause_notes or "Not specified"
    record["confirmed_by"]         = payload.confirmed_by or "Not specified"
    record["declared_at"]          = declared_at.isoformat()
    record["risk_level"]           = "deceased"
    record["survival_probability"] = 0.0

    final_snapshot = {
        "timestamp":            declared_at.isoformat(),
        "vitals":               record["vitals"],
        "risk_level":           "deceased",
        "survival_probability": 0.0,
        "cardiac_risk_score":   record.get("cardiac_risk_score", 0),
        "update_reason":        f"Patient declared deceased at {time_of_death}. {payload.cause_notes or ''}",
        "symptoms":             record.get("symptoms", []),
    }
    if "vitals_history" not in record:
        record["vitals_history"] = []
    record["vitals_history"].append(final_snapshot)
    await store.add_case(record)

    return DeceasedResponse(
        case_id=case_id,
        patient_status="deceased",
        time_of_death=time_of_death,
        cause_notes=payload.cause_notes,
        confirmed_by=payload.confirmed_by,
        declared_at=declared_at,
    )




# ---------------------------------------------------------------------------
# Hospital Suggestion endpoints
# ---------------------------------------------------------------------------

@app.post("/api/cases/{case_id}/suggestions", response_model=HospitalSuggestion)
async def post_suggestion(case_id: str, payload: SuggestionPayload) -> HospitalSuggestion:
    """Hospital staff posts a suggestion/note visible to the ambulance."""
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    from uuid import uuid4
    suggestion = HospitalSuggestion(
        suggestion_id=str(uuid4())[:8],
        text=payload.text,
        posted_by=payload.posted_by,
        priority=payload.priority,
        timestamp=datetime.utcnow(),
        acknowledged=False,
    )

    if "hospital_suggestions" not in record:
        record["hospital_suggestions"] = []
    # Convert datetime to ISO string for JSON persistence
    suggestion_dict = suggestion.dict()
    suggestion_dict["timestamp"] = suggestion_dict["timestamp"].isoformat()
    record["hospital_suggestions"].append(suggestion_dict)
    await store.add_case(record)
    return suggestion


@app.get("/api/cases/{case_id}/suggestions", response_model=List[HospitalSuggestion])
async def get_suggestions(case_id: str) -> List[HospitalSuggestion]:
    """Get all hospital suggestions for a case."""
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    return [HospitalSuggestion(**s) for s in record.get("hospital_suggestions", [])]


@app.patch("/api/cases/{case_id}/suggestions/{suggestion_id}/acknowledge")
async def acknowledge_suggestion(case_id: str, suggestion_id: str) -> dict:
    """Ambulance acknowledges a suggestion — marks it as read."""
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    suggestions = record.get("hospital_suggestions", [])
    for s in suggestions:
        if s.get("suggestion_id") == suggestion_id:
            s["acknowledged"] = True
            break
    record["hospital_suggestions"] = suggestions
    await store.add_case(record)
    return {"acknowledged": True, "suggestion_id": suggestion_id}


@app.get("/api/cases/{case_id}/attachments/{attachment_index}")
async def download_attachment(case_id: str, attachment_index: int) -> Response:
    record = await store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    attachments = record.get("attachments", [])
    if attachment_index < 0 or attachment_index >= len(attachments):
        raise HTTPException(status_code=404, detail="Attachment not found")

    attachment = attachments[attachment_index]
    try:
        binary = base64.b64decode(attachment["data_b64"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Attachment corrupted") from exc

    return Response(
        content=binary,
        media_type=attachment.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": (
                f"inline; filename={attachment.get('filename', 'attachment')}"
            )
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_attachments_list(raw_attachments: List[dict]) -> List[AttachmentMeta]:
    return [
        AttachmentMeta(filename=att["filename"], content_type=att["content_type"])
        for att in raw_attachments
    ]


def _compose_summary(payload, inference_result, medication_plan, recommendations) -> str:
    llm_summary = generate_summary_with_groq(
        payload, inference_result, medication_plan, recommendations
    )
    if llm_summary:
        return llm_summary

    vitals = payload.vitals
    top_features = (
        ", ".join(
            f["feature"].replace("_", " ")
            for f in inference_result.top_shap_features[:3]
        )
        if inference_result.top_shap_features
        else "vitals"
    )

    parts = [
        f"Patient '{payload.patient.name or 'Unknown'}' classified as "
        f"{inference_result.risk_level.upper()} risk by GBM model (XGBoost + Platt calibration).",
        f"Estimated survival probability: {inference_result.survival_probability * 100:.1f}% "
        f"(LR baseline: {inference_result.lr_survival_probability * 100:.1f}%).",
        f"Key SHAP drivers: {top_features}.",
        f"Heart rate: {vitals.heart_rate or 'n/a'} bpm, "
        f"SpO\u2082: {vitals.spo2 or 'n/a'}%, "
        f"BP: {vitals.blood_pressure_systolic or 'n/a'}"
        f"/{vitals.blood_pressure_diastolic or 'n/a'}.",
    ]
    if payload.symptoms:
        parts.append(f"Key symptoms: {', '.join(payload.symptoms[:4])}.")
    if medication_plan:
        meds_text = ", ".join(
            f"{m.medication} ({m.priority})" for m in medication_plan[:4]
        )
        parts.append(f"Prep meds/equipment: {meds_text}.")
    parts.append(
        "SHAP and LIME explanations confirm the primary risk drivers. "
        "Hospital should prepare cardiac monitoring, airway management, and pharm readiness."
    )
    return " ".join(parts)