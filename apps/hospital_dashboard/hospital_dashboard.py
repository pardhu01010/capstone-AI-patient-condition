# Hospital Command Dashboard - Redesigned for clarity and real-world usability
from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

FEATURE_LABELS = {
    "heart_rate":            "Heart Rate",
    "systolic_bp":           "Systolic BP",
    "diastolic_bp":          "Diastolic BP",
    "spo2":                  "SpO₂ (Oxygen Level)",
    "respiratory_rate":      "Respiratory Rate",
    "temperature_c":         "Body Temperature",
    "consciousness_numeric": "Consciousness Level",
    "age":                   "Patient Age",
    "has_chest_pain":        "Chest Pain Present",
    "has_dyspnea":           "Breathing Difficulty",
    "has_trauma":            "Trauma Present",
    "has_arrhythmia":        "Irregular Heartbeat",
    "missing_hr":            "Heart Rate (missing data)",
    "missing_spo2":          "SpO₂ (missing data)",
    "missing_sbp":           "Systolic BP (missing data)",
}

RISK_COLORS = {
    "critical": "#FF4B4B",
    "high":     "#FF8C00",
    "guarded":  "#00C48C",
    "deceased": "#555555",
}

st.set_page_config(
    page_title="Hospital Command",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
section[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
.main { background: #0d1117; }
.block-container { padding: 1.5rem 2rem; }
.risk-badge { display:inline-block;padding:4px 14px;border-radius:20px;font-weight:600;font-size:0.82rem;letter-spacing:0.05em;text-transform:uppercase; }
.risk-critical { background:#3d0000;color:#FF4B4B;border:1px solid #FF4B4B; }
.risk-high     { background:#2d1a00;color:#FF8C00;border:1px solid #FF8C00; }
.risk-guarded  { background:#002d1a;color:#00C48C;border:1px solid #00C48C; }
.card { background:#161b22;border:1px solid #21262d;border-radius:10px;padding:1.2rem 1.4rem;margin-bottom:1rem; }
.card-title { font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin-bottom:0.8rem; }
.metric-row { display:flex;gap:12px;flex-wrap:wrap;margin-bottom:1rem; }
.metric-box { flex:1;min-width:110px;background:#161b22;border:1px solid #21262d;border-radius:8px;padding:0.8rem 1rem;text-align:center; }
.metric-label { font-size:0.68rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.08em; }
.metric-value { font-size:1.45rem;font-weight:600;color:#e6edf3;font-family:'IBM Plex Mono',monospace; }
.metric-sub   { font-size:0.68rem;color:#8b949e; }
.vital-row { display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #21262d; }
.vital-row:last-child { border-bottom:none; }
.vital-name  { color:#8b949e;font-size:0.83rem; }
.vital-value { color:#e6edf3;font-size:0.83rem;font-family:'IBM Plex Mono',monospace;font-weight:500; }
.vital-warn  { color:#FF8C00 !important; }
.vital-crit  { color:#FF4B4B !important; }
.rec-item { background:#1c2128;border-left:3px solid #388bfd;border-radius:0 6px 6px 0;padding:0.6rem 0.9rem;margin-bottom:0.5rem; }
.rec-title  { color:#e6edf3;font-weight:600;font-size:0.83rem; }
.rec-detail { color:#8b949e;font-size:0.78rem;margin-top:2px;line-height:1.4; }
.med-item { display:flex;align-items:flex-start;gap:10px;padding:7px 0;border-bottom:1px solid #21262d; }
.med-item:last-child { border-bottom:none; }
.med-dot { width:10px;height:10px;border-radius:50%;margin-top:4px;flex-shrink:0; }
.med-imm { background:#FF4B4B; }
.med-prep { background:#FF8C00; }
.med-std  { background:#00C48C; }
.med-name { color:#e6edf3;font-size:0.83rem;font-weight:500; }
.med-purpose { color:#8b949e;font-size:0.76rem;line-height:1.3; }
.shap-row { display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #21262d; }
.shap-row:last-child { border-bottom:none; }
.shap-feat { color:#e6edf3;font-size:0.8rem; }
.shap-val  { font-family:'IBM Plex Mono',monospace;font-size:0.78rem; }
.shap-up   { color:#FF4B4B; }
.shap-dn   { color:#00C48C; }
.summary-box { background:#1c2128;border:1px solid #21262d;border-radius:8px;padding:1rem 1.2rem;color:#c9d1d9;font-size:0.84rem;line-height:1.7; }
.case-header { background:linear-gradient(135deg,#161b22 0%,#1c2128 100%);border:1px solid #21262d;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1.2rem;display:flex;align-items:center;gap:16px; }
.case-id   { font-family:'IBM Plex Mono',monospace;color:#8b949e;font-size:0.76rem; }
.case-name { color:#e6edf3;font-size:1.25rem;font-weight:600; }
.sidebar-card { background:#161b22;border:1px solid #21262d;border-radius:6px;padding:8px 10px;margin-bottom:8px;cursor:pointer; }
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


def fetch_cases() -> List[Dict]:
    r = requests.get(f"{API_BASE}/cases", timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_case_detail(case_id: str) -> Dict:
    r = requests.get(f"{API_BASE}/cases/{case_id}", timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_attachment_blob(case_id: str, index: int) -> bytes:
    r = requests.get(f"{API_BASE}/cases/{case_id}/attachments/{index}", timeout=30)
    r.raise_for_status()
    return r.content

def fetch_case_history(case_id: str) -> list:
    r = requests.get(f"{API_BASE}/cases/{case_id}/history", timeout=15)
    r.raise_for_status()
    return r.json()

def b64_img(b64: str) -> bytes:
    return base64.b64decode(b64)

def fmt_feat(name: str) -> str:
    return FEATURE_LABELS.get(name, name.replace("_", " ").title())

def vital_class(metric: str, value) -> str:
    if value is None: return ""
    try: v = float(value)
    except: return ""
    if metric == "Heart Rate (bpm)":
        return "vital-crit" if v > 140 or v < 40 else ("vital-warn" if v > 120 or v < 50 else "")
    if metric == "SpO₂ (%)":
        return "vital-crit" if v < 88 else ("vital-warn" if v < 94 else "")
    if metric == "Systolic BP (mmHg)":
        return "vital-crit" if v < 80 or v > 180 else ("vital-warn" if v < 90 or v > 160 else "")
    if metric == "Resp. Rate (/min)":
        return "vital-crit" if v > 30 or v < 8 else ("vital-warn" if v > 24 else "")
    return ""


def render_sidebar(cases: List[Dict]) -> str:
    with st.sidebar:
        st.markdown(
            '<div style="color:#e6edf3;font-size:1rem;font-weight:600;margin-bottom:0.8rem;">🏥 Incoming Cases</div>',
            unsafe_allow_html=True,
        )
        for case in cases:
            risk   = case["risk_level"].lower()
            status = case.get("patient_status", "active")
            color  = "#555555" if status == "deceased" else RISK_COLORS.get(risk, "#8b949e")
            name   = case["patient"].get("name") or "Unknown"
            surv   = case["survival_probability"] * 100
            cid    = case["case_id"][:8]
            t      = datetime.fromisoformat(case["created_at"]).strftime("%H:%M")
            icon   = "🕊️ " if status == "deceased" else ""
            lbl    = "DECEASED" if status == "deceased" else f"{risk} risk"
            surv_txt = "Deceased" if status == "deceased" else f"Survival {surv:.0f}%"
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;border-left:3px solid {color};'
                f'border-radius:6px;padding:8px 10px;margin-bottom:6px;">'
                f'<div style="color:#e6edf3;font-weight:600;font-size:0.84rem;">{icon}{name}</div>'
                f'<div style="color:{color};font-size:0.7rem;text-transform:uppercase;font-weight:600;">{lbl}</div>'
                f'<div style="color:#8b949e;font-size:0.7rem;">{surv_txt} · {t} · {cid}…</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")
        case_map = {c["case_id"]: c for c in cases}
        selected = st.selectbox(
            "Open case",
            options=list(case_map.keys()),
            format_func=lambda cid: (
                f"{'🕊️ ' if case_map[cid].get('patient_status') == 'deceased' else ''}"
                f"{case_map[cid]['patient'].get('name') or 'Unknown'} "
                f"({'DECEASED' if case_map[cid].get('patient_status') == 'deceased' else case_map[cid]['risk_level'].upper()}) · {cid[:8]}…"
            ),
        )
    return selected


def render_case_header(detail: Dict):
    risk   = detail["risk_level"].lower()
    status = detail.get("patient_status", "active")
    color  = "#555555" if status == "deceased" else RISK_COLORS.get(risk, "#8b949e")
    name   = detail["patient"].get("name") or "Unknown Patient"
    age    = detail["patient"].get("age", "—")
    sex    = detail["patient"].get("sex") or "—"
    blood  = detail["patient"].get("blood_group") or "—"
    loc    = detail.get("location") or "—"
    cid    = detail["case_id"]
    ts     = datetime.fromisoformat(detail.get("created_at", datetime.utcnow().isoformat())).strftime("%d %b %Y, %H:%M UTC")

    badge_text  = "DECEASED" if status == "deceased" else f"{risk} risk"
    badge_class = "risk-deceased" if status == "deceased" else f"risk-{risk}"

    st.markdown(
        f'<div class="case-header">'
        f'<div style="width:50px;height:50px;background:{color}22;border:2px solid {color};'
        f'border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.4rem;flex-shrink:0;">'
        f'{"🕊️" if status == "deceased" else "🧑‍⚕️"}</div>'
        f'<div style="flex:1;">'
        f'<div class="case-name">{name}</div>'
        f'<div class="case-id">Age {age} · {sex} · Blood: {blood} · Location: {loc}</div>'
        f'<div class="case-id">Received: {ts} · ID: {cid}</div>'
        f'</div>'
        f'<div><span class="risk-badge" style="background:{color}22;color:{color};border:1px solid {color};">'
        f'{badge_text.upper()}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Deceased banner — shown prominently if patient has passed
    if status == "deceased":
        tod   = detail.get("time_of_death", "—")
        cause = detail.get("cause_notes", "—")
        conf  = detail.get("confirmed_by", "—")
        try:
            decl = datetime.fromisoformat(detail["declared_at"]).strftime("%d %b %Y, %H:%M UTC") if detail.get("declared_at") else "—"
        except Exception:
            decl = "—"

        st.markdown(
            f'<div style="background:#111;border:2px solid #555;border-radius:12px;'
            f'padding:1.2rem 1.5rem;margin:0.5rem 0 1rem;display:flex;align-items:center;gap:20px;">'
            f'<div style="font-size:2.5rem;">🕊️</div>'
            f'<div>'
            f'<div style="color:#aaa;font-size:1rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;">Patient Deceased</div>'
            f'<div style="color:#777;font-size:0.82rem;margin-top:6px;line-height:1.9;">'
            f'Time of Death: <b style="color:#999;">{tod}</b> &nbsp;·&nbsp; '
            f'Declared: <b style="color:#999;">{decl}</b><br>'
            f'Confirmed by: <b style="color:#999;">{conf}</b><br>'
            f'Cause / Notes: <b style="color:#999;">{cause}</b>'
            f'</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_metrics(detail: Dict):
    surv_gbm = detail["survival_probability"] * 100
    surv_lr  = (detail.get("lr_survival_probability") or 0) * 100
    cardiac  = detail["cardiac_risk_score"]
    age      = detail["patient"].get("age", "—")
    risk     = detail["risk_level"].lower()
    color    = RISK_COLORS.get(risk, "#8b949e")

    st.markdown(
        f'<div class="metric-row">'
        f'<div class="metric-box" style="border-color:{color}33;">'
        f'<div class="metric-label">Risk Level</div>'
        f'<div class="metric-value" style="color:{color};font-size:1.2rem;">{risk.title()}</div>'
        f'</div>'
        f'<div class="metric-box">'
        f'<div class="metric-label">Survival — GBM</div>'
        f'<div class="metric-value">{surv_gbm:.1f}%</div>'
        f'<div class="metric-sub">XGBoost model</div>'
        f'</div>'
        f'<div class="metric-box">'
        f'<div class="metric-label">Survival — LR Baseline</div>'
        f'<div class="metric-value">{surv_lr:.1f}%</div>'
        f'<div class="metric-sub">Logistic regression</div>'
        f'</div>'
        f'<div class="metric-box">'
        f'<div class="metric-label">Cardiac Risk Score</div>'
        f'<div class="metric-value">{cardiac:.1f}<span style="font-size:0.85rem;color:#8b949e;">/10</span></div>'
        f'</div>'
        f'<div class="metric-box">'
        f'<div class="metric-label">Age</div>'
        f'<div class="metric-value">{age}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_vitals(detail: Dict):
    v = detail["vitals"]
    rows = [
        ("Heart Rate (bpm)",    v.get("heart_rate"),              "bpm"),
        ("Systolic BP (mmHg)",  v.get("blood_pressure_systolic"),  "mmHg"),
        ("Diastolic BP (mmHg)", v.get("blood_pressure_diastolic"), "mmHg"),
        ("SpO₂ (%)",            v.get("spo2"),                     "%"),
        ("Resp. Rate (/min)",   v.get("respiratory_rate"),         "/min"),
        ("Temperature (°C)",    v.get("temperature_c"),            "°C"),
        ("Consciousness",       v.get("consciousness_level"),      ""),
    ]
    html = '<div class="card"><div class="card-title">📊 Vitals Snapshot</div>'
    for label, val, unit in rows:
        if val is None:
            display = "—"
            cls = ""
        else:
            display = f"{val} {unit}".strip()
            cls = vital_class(label, val)
        warn_icon = " ⚠️" if cls == "vital-warn" else (" 🚨" if cls == "vital-crit" else "")
        html += (
            f'<div class="vital-row">'
            f'<span class="vital-name">{label}</span>'
            f'<span class="vital-value {cls}">{display}{warn_icon}</span>'
            f'</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_patient_info(detail: Dict):
    p         = detail["patient"]
    allergies = ", ".join(p.get("allergies") or []) or "None reported"
    chronic   = ", ".join(p.get("chronic_conditions") or []) or "None reported"
    symptoms  = ", ".join(detail.get("symptoms") or []) or "None recorded"
    meds      = ", ".join(detail.get("meds_administered") or []) or "None"
    oxygen    = detail.get("oxygen_support") or "—"
    notes     = detail.get("notes") or "—"

    html = (
        f'<div class="card"><div class="card-title">🩺 Patient Details</div>'
        f'<div class="vital-row"><span class="vital-name">Allergies</span><span class="vital-value" style="max-width:60%;text-align:right;">{allergies}</span></div>'
        f'<div class="vital-row"><span class="vital-name">Chronic Conditions</span><span class="vital-value" style="max-width:60%;text-align:right;">{chronic}</span></div>'
        f'<div class="vital-row"><span class="vital-name">Symptoms</span><span class="vital-value" style="max-width:60%;text-align:right;">{symptoms}</span></div>'
        f'<div class="vital-row"><span class="vital-name">Meds Administered</span><span class="vital-value" style="max-width:60%;text-align:right;">{meds}</span></div>'
        f'<div class="vital-row"><span class="vital-name">Oxygen Support</span><span class="vital-value">{oxygen}</span></div>'
        f'<div class="vital-row"><span class="vital-name">Notes</span><span class="vital-value" style="max-width:60%;text-align:right;color:#8b949e;">{notes}</span></div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_recommendations(detail: Dict):
    recs = detail.get("recommendations", [])
    html = (
        '<div class="card">'
        '<div class="card-title">🤖 AI Recommendations (SHAP-driven)</div>'
        '<div style="background:#1a1400;border:1px solid #F0B42966;border-radius:6px;'
        'padding:7px 10px;margin-bottom:10px;color:#c9a84c;font-size:0.73rem;line-height:1.4;">'
        '⚠️ <b>Caution:</b> AI suggestions may not always be correct. '
        'Verify with clinical expertise before acting.'
        '</div>'
    )
    if not recs:
        html += '<div style="color:#8b949e;font-size:0.83rem;">No recommendations generated.</div>'
    for rec in recs:
        html += (
            f'<div class="rec-item">'
            f'<div class="rec-title">{rec["title"]}</div>'
            f'<div class="rec-detail">{rec["detail"]}</div>'
            f'</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_medications(detail: Dict):
    plan = detail.get("medication_plan", [])
    html = '<div class="card"><div class="card-title">💊 Medication &amp; Equipment Prep</div>'
    if not plan:
        html += '<div style="color:#8b949e;font-size:0.83rem;">No specific prep required.</div>'
    for item in plan:
        p   = item.get("priority", "standard")
        dot = {"immediate": "med-imm", "prep": "med-prep"}.get(p, "med-std")
        lbl = {"immediate": "🔴 Immediate", "prep": "🟡 Prepare", "standard": "🟢 Standard"}.get(p, p)
        html += (
            f'<div class="med-item">'
            f'<div class="med-dot {dot}"></div>'
            f'<div><div class="med-name">{item["medication"]} '
            f'<span style="color:#8b949e;font-size:0.72rem;">({lbl})</span></div>'
            f'<div class="med-purpose">{item["purpose"]}</div></div>'
            f'</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_shap_features(detail: Dict):
    feats = detail.get("top_shap_features", [])
    if not feats:
        return
    html = (
        '<div class="card"><div class="card-title">🔢 Top Risk Drivers (SHAP Values)</div>'
        '<div style="color:#8b949e;font-size:0.72rem;margin-bottom:8px;">'
        'Red ↑ = increases risk &nbsp;·&nbsp; Green ↓ = decreases risk</div>'
    )
    for f in feats:
        name  = fmt_feat(f["feature"])
        val   = f["shap_value"]
        cls   = "shap-up" if val > 0 else "shap-dn"
        arrow = "↑" if val > 0 else "↓"
        bar_w = min(int(abs(val) * 40), 100)
        bar_c = "#FF4B4B44" if val > 0 else "#00C48C44"
        bar_b = "#FF4B4B" if val > 0 else "#00C48C"
        html += (
            f'<div class="shap-row">'
            f'<span class="shap-feat">{name}</span>'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="width:{bar_w}px;height:8px;background:{bar_c};border:1px solid {bar_b};border-radius:4px;"></div>'
            f'<span class="shap-val {cls}">{arrow} {abs(val):.3f}</span>'
            f'</div></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_xai_plots(detail: Dict):
    st.markdown(
        '<div class="card-title" style="margin-top:0.5rem;">🔍 Explainable AI (XAI) — Local &amp; Global Explanations</div>',
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Local SHAP — This Patient**")
        st.caption("Red bars increase risk · Blue bars decrease risk · Based on this patient's exact vitals.")
        b64 = detail.get("shap_local_plot_b64", "")
        if b64:
            st.image(b64_img(b64), width=460)
        else:
            st.info("Loading… select this case again in a few seconds.")
    with col2:
        st.markdown("**LIME — Independent Sanity Check**")
        st.caption("A separate linear model cross-checks the SHAP findings. Disagreements flag edge cases.")
        b64 = detail.get("lime_local_plot_b64", "")
        if b64:
            st.image(b64_img(b64), width=460)
        else:
            st.info("LIME plot loading…")

    st.markdown("**Global SHAP — Feature Importance Across All Patients**")
    st.caption(
        "Shows which features most influence risk predictions across the whole population. "
        "SpO₂, Heart Rate, and BP are expected to dominate."
    )
    b64 = detail.get("shap_global_plot_b64", "")
    if b64:
        st.image(b64_img(b64), width=460)
    else:
        st.info("Global SHAP plot loading…")


def post_suggestion(case_id: str, text: str, posted_by: str, priority: str) -> dict:
    r = requests.post(
        f"{API_BASE}/cases/{case_id}/suggestions",
        json={"text": text, "posted_by": posted_by, "priority": priority},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def render_suggestion_box(detail: Dict):
    """Hospital staff suggestion box — notes sent to ambulance in real-time."""
    case_id     = detail["case_id"]
    suggestions = detail.get("hospital_suggestions", [])
    is_deceased = detail.get("patient_status") == "deceased"

    st.markdown("---")
    st.markdown(
        '<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;'
        'padding:1.1rem 1.4rem;margin-bottom:1rem;">'
        '<div style="font-size:0.72rem;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#8b949e;margin-bottom:0.8rem;">📨 Hospital Suggestions to Ambulance</div>',
        unsafe_allow_html=True,
    )

    PRIORITY_STYLE = {
        "normal":   ("#388bfd", "#0d1b2e", "📋"),
        "urgent":   ("#FF8C00", "#2d1a00", "⚠️"),
        "critical": ("#FF4B4B", "#3d0000", "🚨"),
    }

    # Show existing suggestions
    if not suggestions:
        st.markdown(
            '<div style="color:#8b949e;font-size:0.82rem;padding:6px 0;">'
            'No suggestions sent yet. Use the form below to notify the ambulance.</div>',
            unsafe_allow_html=True,
        )
    else:
        for s in reversed(suggestions):   # newest first
            pri   = s.get("priority", "normal")
            color, bg, icon = PRIORITY_STYLE.get(pri, PRIORITY_STYLE["normal"])
            ack   = s.get("acknowledged", False)
            ts    = s.get("timestamp", "")[:16].replace("T", " ")
            by    = s.get("posted_by", "Hospital Staff")
            sid   = s.get("suggestion_id", "")
            ack_badge = (
                '<span style="background:#002d1a;color:#00C48C;font-size:0.68rem;'
                'border-radius:10px;padding:1px 8px;margin-left:8px;">✓ Seen by ambulance</span>'
                if ack else
                '<span style="background:#21262d;color:#8b949e;font-size:0.68rem;'
                'border-radius:10px;padding:1px 8px;margin-left:8px;">⏳ Awaiting acknowledgement</span>'
            )
            st.markdown(
                f'<div style="background:{bg};border:1px solid {color};border-left:4px solid {color};'
                f'border-radius:6px;padding:10px 14px;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="color:{color};font-weight:700;font-size:0.85rem;">{icon} {s["text"]}</span>'
                f'{ack_badge}</div>'
                f'<div style="color:#8b949e;font-size:0.7rem;margin-top:4px;">'
                f'Posted by <b style="color:#c9d1d9;">{by}</b> · {ts} UTC · '
                f'Priority: <b style="color:{color};">{pri.upper()}</b> · ID: {sid}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # Post new suggestion form
    if not is_deceased:
        st.markdown(
            '<div style="background:#1c2128;border:1px solid #30363d;border-radius:8px;'
            'padding:1rem 1.3rem;margin-top:0.5rem;">',
            unsafe_allow_html=True,
        )
        with st.form(f"suggestion_form_{case_id}"):
            st.markdown(
                '<div style="color:#e6edf3;font-weight:600;font-size:0.9rem;margin-bottom:0.6rem;">'
                '✍️ Send New Suggestion to Ambulance</div>',
                unsafe_allow_html=True,
            )

            sc1, sc2 = st.columns([3, 1])
            with sc1:
                suggestion_text = st.text_area(
                    "Suggestion",
                    placeholder=(
                        "e.g. Prepare OT Room 2\n"
                        "Alert cardiologist Dr. Sharma\n"
                        "Blood O-negative ready at ER\n"
                        "Trauma team standing by Bay 3"
                    ),
                    height=90,
                    label_visibility="collapsed",
                )
            with sc2:
                posted_by = st.text_input(
                    "Your Name / Role",
                    placeholder="e.g. Dr. Sharma",
                    value="",
                )
                priority = st.selectbox(
                    "Priority",
                    options=["normal", "urgent", "critical"],
                    format_func=lambda x: {
                        "normal": "📋 Normal",
                        "urgent": "⚠️ Urgent",
                        "critical": "🚨 Critical",
                    }[x],
                )

            # Quick action buttons as preset text
            st.markdown(
                '<div style="color:#8b949e;font-size:0.72rem;margin-bottom:4px;">'
                'Quick presets (click to copy into box above):</div>',
                unsafe_allow_html=True,
            )
            presets_col = st.columns(4)
            presets = [
                "Prepare OT",
                "Alert cardiologist",
                "Blood O- ready",
                "Trauma team standby",
            ]
            # Show as info chips
            preset_html = "".join(
                f'<span style="background:#21262d;color:#c9d1d9;border:1px solid #30363d;'
                f'border-radius:10px;padding:3px 10px;font-size:0.74rem;margin-right:6px;">'
                f'{p}</span>'
                for p in presets
            )
            st.markdown(
                f'<div style="margin-bottom:8px;">{preset_html}</div>',
                unsafe_allow_html=True,
            )

            send_btn = st.form_submit_button(
                "📨  Send to Ambulance", use_container_width=True
            )

        if send_btn:
            if not suggestion_text.strip():
                st.warning("Please enter a suggestion before sending.")
            else:
                try:
                    post_suggestion(
                        case_id,
                        suggestion_text.strip(),
                        posted_by.strip() or "Hospital Staff",
                        priority,
                    )
                    st.success("✅ Suggestion sent! The ambulance will see it immediately.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to send: {exc}")

        st.markdown('</div>', unsafe_allow_html=True)


def render_summary(detail: Dict):
    text = detail.get("llm_summary", "No summary available.")
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">📝 Clinical Narrative Summary</div>'
        f'<div class="summary-box">{text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_attachments(detail: Dict):
    atts = detail.get("attachments", [])
    st.markdown('<div class="card-title">📎 Attachments</div>', unsafe_allow_html=True)
    if not atts:
        st.markdown('<div style="color:#8b949e;font-size:0.83rem;">No attachments uploaded with this case.</div>', unsafe_allow_html=True)
        return
    for idx, att in enumerate(atts):
        label = f"{att['filename']} ({att['content_type']})"
        st.write(f"- {label}")
        if att["content_type"].startswith("image/"):
            try:
                img = fetch_attachment_blob(detail["case_id"], idx)
                st.image(img, caption=label, use_container_width=True)
            except Exception:
                st.warning(f"Could not load {att['filename']}")


def render_history(case_id: str):
    """Render the vitals history timeline — all updates during transport."""
    try:
        history = fetch_case_history(case_id)
    except Exception:
        return

    if len(history) <= 1:
        return   # only one entry = no updates yet, skip section

    st.markdown(
        '<div class="card-title" style="margin-top:0.5rem;">🔄 Mid-Transport Update Timeline</div>',
        unsafe_allow_html=True,
    )
    st.caption("Shows how the patient condition changed during ambulance transport.")

    # Build comparison table
    rows = []
    for i, snap in enumerate(history):
        v   = snap["vitals"]
        ts  = snap["timestamp"][:16].replace("T", "  ")
        lbl = "🟢 Initial" if i == 0 else f"🔄 Update {i}"
        reason = snap.get("update_reason") or ""
        rows.append({
            "Entry":         f"{lbl}",
            "Time":          ts,
            "Reason":        reason,
            "Heart Rate":    v.get("heart_rate",               "—"),
            "SpO₂ %":       v.get("spo2",                     "—"),
            "Systolic BP":   v.get("blood_pressure_systolic",  "—"),
            "Resp. Rate":    v.get("respiratory_rate",          "—"),
            "Consciousness": v.get("consciousness_level",      "—"),
            "Risk Level":    snap["risk_level"].upper(),
            "Survival %":    f"{snap['survival_probability']*100:.1f}%",
        })

    import pandas as pd
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Trend chart — survival probability across updates
    trend_df = pd.DataFrame([
        {
            "Update":       f"#{i} {s.get('update_reason','')[:20]}" if i > 0 else "Initial",
            "Survival %":   round(s["survival_probability"] * 100, 1),
            "Cardiac Risk": round(s["cardiac_risk_score"], 2),
        }
        for i, s in enumerate(history)
    ])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Survival Probability Trend**")
        st.line_chart(trend_df, x="Update", y="Survival %")
    with col2:
        st.markdown("**Cardiac Risk Score Trend**")
        st.line_chart(trend_df, x="Update", y="Cardiac Risk")


def render_timeline(cases: List[Dict]):
    if len(cases) < 2:
        return
    df = pd.DataFrame([
        {
            "Time":            datetime.fromisoformat(c["created_at"]).strftime("%H:%M"),
            "GBM Survival %":  round(c["survival_probability"] * 100, 1),
            "LR Survival %":   round((c.get("lr_survival_probability") or 0) * 100, 1),
        }
        for c in sorted(cases, key=lambda x: x["created_at"])
    ])
    st.markdown('<div class="card-title" style="margin-top:0.5rem;">📈 Historical Survival Trend — GBM vs LR</div>', unsafe_allow_html=True)
    st.line_chart(df, x="Time", y=["GBM Survival %", "LR Survival %"])


def main():
    st.markdown(
        '<h1 style="color:#e6edf3;font-family:IBM Plex Sans,sans-serif;font-weight:600;margin-bottom:0.2rem;">'
        '🏥 Hospital Command Dashboard</h1>'
        '<p style="color:#8b949e;font-size:0.83rem;margin-bottom:0.8rem;">'
        'Real-time ambulance intake · XGBoost GBM + Logistic Regression · SHAP &amp; LIME explanations</p>',
        unsafe_allow_html=True,
    )

    # ── AI Caution Banner ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="'
        'background:#1a1400;'
        'border:1.5px solid #F0B429;'
        'border-left:5px solid #F0B429;'
        'border-radius:8px;'
        'padding:10px 16px;'
        'margin-bottom:1.2rem;'
        'display:flex;align-items:flex-start;gap:12px;">'
        '<div style="font-size:1.2rem;margin-top:1px;">⚠️</div>'
        '<div>'
        '<div style="color:#F0B429;font-weight:700;font-size:0.85rem;letter-spacing:0.02em;">'
        'AI DECISION SUPPORT — NOT A SUBSTITUTE FOR CLINICAL JUDGEMENT</div>'
        '<div style="color:#c9a84c;font-size:0.78rem;margin-top:3px;line-height:1.5;">'
        'All risk scores, recommendations, SHAP explanations, and medication suggestions are generated by an AI model '
        'trained on synthetic data. They <b>may not always be accurate</b>. '
        'Always apply professional medical judgement. Do not solely rely on AI output for critical decisions.'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        cases = fetch_cases()
    except Exception as exc:
        st.error(f"Cannot connect to backend: {exc}")
        st.info("Make sure the backend is running: `uvicorn backend.main:app --reload --port 8000`")
        return

    if not cases:
        st.info("No ambulance cases yet. Submit one from the Ambulance Intake app (port 8501).")
        return

    selected_id = render_sidebar(cases)

    try:
        detail = fetch_case_detail(selected_id)
    except Exception as exc:
        st.error(f"Could not load case details: {exc}")
        return

    render_case_header(detail)
    render_metrics(detail)

    col_v, col_r = st.columns([1, 1])
    with col_v:
        render_vitals(detail)
    with col_r:
        render_recommendations(detail)

    col_p, col_m, col_s = st.columns([1, 1, 1])
    with col_p:
        render_patient_info(detail)
    with col_m:
        render_medications(detail)
    with col_s:
        render_shap_features(detail)

    render_summary(detail)

    # Hospital → Ambulance suggestion box
    render_suggestion_box(detail)

    # Mid-transport update history timeline
    st.markdown("---")
    render_history(detail["case_id"])

    st.markdown("---")
    render_xai_plots(detail)

    st.markdown("---")
    render_attachments(detail)

    render_timeline(cases)


if __name__ == "__main__":
    main()