# Ambulance Intake App - click patient in sidebar to view their data + update
from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import List

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

CONDITION_TEMPLATES = {
    "Chest Pain & Diaphoresis": {
        "symptoms": ["crushing chest pain", "diaphoresis"],
        "notes": "Likely ACS/STEMI. Onset < 30 min, nitro given in ambulance.",
        "labs": ["Troponin: pending"],
    },
    "Dyspnea with Wheeze": {
        "symptoms": ["shortness of breath", "wheezing"],
        "notes": "Severe respiratory distress, accessory muscle use observed.",
        "labs": ["ABG: pending"],
    },
    "Major Trauma": {
        "symptoms": ["multi-trauma", "uncontrolled bleeding"],
        "notes": "Fall from >15 ft. Pelvic binder applied, IV fluids running.",
        "labs": ["Type & Screen: O-negative requested"],
    },
}

RISK_COLORS = {"critical": "#FF4B4B", "high": "#FF8C00", "guarded": "#00C48C", "deceased": "#555555"}

st.set_page_config(page_title="Ambulance Intake", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.main { background: #0d1117; }
.block-container { padding: 1.2rem 1.8rem 3rem; }
section[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }

.section-header { background:linear-gradient(90deg,#1c2128,#0d1117);border-left:4px solid #388bfd;border-radius:0 6px 6px 0;padding:10px 16px;margin:1.2rem 0 0.8rem;display:flex;align-items:center;gap:10px; }
.section-header.vitals  { border-color:#00C48C; }
.section-header.clinical { border-color:#FF8C00; }
.section-header.labs    { border-color:#a371f7; }
.section-header.precautions { border-color:#FF4B4B; }
.section-header.update  { border-color:#f0883e; }
.section-title { color:#e6edf3;font-size:0.95rem;font-weight:600;margin:0; }
.section-hint  { color:#8b949e;font-size:0.73rem;margin-top:2px; }

label { color:#c9d1d9 !important; font-size:0.88rem !important; font-weight:500 !important; }
input, textarea, select { background:#161b22 !important; border:1px solid #30363d !important; border-radius:6px !important; color:#e6edf3 !important; font-size:0.9rem !important; }

/* Blinking red border — applied via JS below, not CSS class */
@keyframes blink-border {
    0%   { box-shadow: 0 0 0 0px rgba(255,75,75,0); border-color: #FF4B4B; }
    50%  { box-shadow: 0 0 10px 3px rgba(255,75,75,0.55); border-color: #FF4B4B; }
    100% { box-shadow: 0 0 0 0px rgba(255,75,75,0); border-color: #FF4B4B; }
}
.blink-red {
    border: 1.5px solid #FF4B4B !important;
    animation: blink-border 1.4s ease-in-out infinite !important;
    border-radius: 6px !important;
}

/* Sidebar case cards */
.case-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: background 0.15s;
}
.case-card:hover { background: #1c2128; }
.case-card-name  { color:#e6edf3; font-weight:700; font-size:0.88rem; margin-bottom:2px; }
.case-card-risk  { font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; }
.case-card-sub   { color:#8b949e; font-size:0.7rem; margin-top:2px; font-family:monospace; }

.vital-ref { background:#161b22;border:1px solid #21262d;border-radius:8px;padding:10px 14px;margin-bottom:0.8rem;font-size:0.74rem;color:#8b949e;line-height:1.8; }
.vital-ref strong { color:#e6edf3; }
.ref-ok   { color:#00C48C; }
.ref-warn { color:#FF8C00; }
.ref-crit { color:#FF4B4B; }

.stButton > button { background:#238636 !important; color:white !important; border:none !important; border-radius:8px !important; font-size:0.95rem !important; font-weight:600 !important; padding:0.65rem 2rem !important; width:100% !important; }
.stButton > button:hover { background:#2ea043 !important; }

.card { background:#161b22;border:1px solid #21262d;border-radius:10px;padding:1.1rem 1.3rem;margin-bottom:0.9rem; }
.card-title { font-size:0.7rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin-bottom:0.7rem; }
.data-row { display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #21262d; }
.data-row:last-child { border-bottom:none; }
.data-label { color:#8b949e;font-size:0.82rem; }
.data-value { color:#e6edf3;font-size:0.82rem;font-family:monospace;font-weight:500; }
.data-warn  { color:#FF8C00 !important; }
.data-crit  { color:#FF4B4B !important; }

.rec-item { background:#1c2128;border-left:3px solid #FF4B4B;border-radius:0 6px 6px 0;padding:0.6rem 0.9rem;margin-bottom:0.5rem; }
.rec-title  { color:#e6edf3;font-weight:600;font-size:0.84rem; }
.rec-detail { color:#8b949e;font-size:0.78rem;margin-top:3px;line-height:1.4; }

.med-row { display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #21262d; }
.med-row:last-child { border-bottom:none; }
.med-dot { width:9px;height:9px;border-radius:50%;margin-top:4px;flex-shrink:0; }
.med-imm  { background:#FF4B4B; }
.med-prep { background:#FF8C00; }
.med-std  { background:#00C48C; }
.med-name { color:#e6edf3;font-size:0.82rem;font-weight:500; }
.med-purpose { color:#8b949e;font-size:0.75rem; }

.tag { display:inline-block;background:#21262d;color:#c9d1d9;padding:2px 8px;border-radius:10px;font-size:0.74rem;margin:2px; }
.tag-crit { background:#3d0000;color:#FF4B4B; }
.tag-warn { background:#2d1a00;color:#FF8C00; }
.tag-ok   { background:#002d1a;color:#00C48C; }

.summary-box { background:#1c2128;border:1px solid #21262d;border-radius:8px;padding:0.9rem 1.1rem;color:#c9d1d9;font-size:0.83rem;line-height:1.7; }

.update-btn > button { background:#f0883e !important; }
.update-btn > button:hover { background:#d97734 !important; }

#MainMenu { visibility:hidden; }
footer    { visibility:hidden; }

/* Consciousness level radio row */
div[data-testid="stRadio"] > label { display:none !important; }
div[data-testid="stRadio"] > div   { display:flex !important; gap:8px !important; flex-wrap:nowrap !important; }
div[data-testid="stRadio"] > div > label {
    display:flex !important;
    flex:1 !important;
    justify-content:center !important;
    align-items:center !important;
    padding:10px 4px !important;
    border-radius:8px !important;
    border:2px solid #30363d !important;
    cursor:pointer !important;
    font-weight:600 !important;
    font-size:0.82rem !important;
    text-align:center !important;
    transition:all 0.15s !important;
    background:#161b22 !important;
    color:#8b949e !important;
}
div[data-testid="stRadio"] > div > label:hover { border-color:#388bfd !important; color:#e6edf3 !important; }
div[data-testid="stRadio"] > div > label:has(input:checked) { color:#e6edf3 !important; }
div[data-testid="stRadio"] input { display:none !important; }
.cons-alert    label:has(input:checked) { background:#002d1a !important; border-color:#00C48C !important; color:#00C48C !important; }
.cons-verbal   label:has(input:checked) { background:#1a2a00 !important; border-color:#7ee787 !important; color:#7ee787 !important; }
.cons-pain     label:has(input:checked) { background:#2d1a00 !important; border-color:#FF8C00 !important; color:#FF8C00 !important; }
.cons-unresp   label:has(input:checked) { background:#3d0000 !important; border-color:#FF4B4B !important; color:#FF4B4B !important; }
</style>
""", unsafe_allow_html=True)

# ── JS: apply blinking red border to every input/textarea in the form ─────────
# Streamlit renders inputs deep inside shadow-like iframes; we use MutationObserver
# so it re-applies whenever Streamlit re-renders the DOM.
st.markdown("""
<script>
(function applyBlinkToAllInputs() {
    function addBlink() {
        // Target every input and textarea inside the main app area
        document.querySelectorAll(
            'section[data-testid="stMain"] input, ' +
            'section[data-testid="stMain"] textarea'
        ).forEach(function(el) {
            el.classList.add('blink-red');
        });
    }
    // Run immediately and also watch for DOM changes (Streamlit re-renders)
    addBlink();
    const observer = new MutationObserver(addBlink);
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────

def encode_attachments(files) -> List[dict]:
    return [{"filename": f.name, "content_type": f.type or "application/octet-stream",
             "data_b64": base64.b64encode(f.getbuffer()).decode("utf-8")} for f in files]

def submit_case(payload: dict) -> dict:
    r = requests.post(f"{API_BASE}/intake", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_cases() -> list:
    try:
        r = requests.get(f"{API_BASE}/cases", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []

def fetch_case_detail(case_id: str) -> dict:
    r = requests.get(f"{API_BASE}/cases/{case_id}", timeout=10)
    r.raise_for_status()
    return r.json()

def push_update(case_id: str, payload: dict) -> dict:
    r = requests.patch(f"{API_BASE}/cases/{case_id}/update", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def declare_deceased(case_id: str, payload: dict) -> dict:
    r = requests.post(f"{API_BASE}/cases/{case_id}/deceased", json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def acknowledge_suggestion(case_id: str, suggestion_id: str) -> None:
    requests.patch(
        f"{API_BASE}/cases/{case_id}/suggestions/{suggestion_id}/acknowledge",
        timeout=10,
    )

def vital_cls(label: str, val) -> str:
    if val is None: return ""
    try: v = float(val)
    except: return ""
    if "Heart Rate" in label:
        return "data-crit" if v > 140 or v < 40 else ("data-warn" if v > 120 else "")
    if "SpO" in label:
        return "data-crit" if v < 88 else ("data-warn" if v < 94 else "")
    if "Systolic" in label:
        return "data-crit" if v < 80 or v > 180 else ("data-warn" if v < 90 else "")
    if "Resp" in label:
        return "data-crit" if v > 30 or v < 8 else ("data-warn" if v > 24 else "")
    return ""


# ── Sidebar ───────────────────────────────────────────────────────────────────

if "view_mode" not in st.session_state:
    st.session_state["view_mode"]      = "new"   # "new" or "view"
if "viewing_case_id" not in st.session_state:
    st.session_state["viewing_case_id"] = None
if "active_case_id" not in st.session_state:
    st.session_state["active_case_id"]  = None

cases = fetch_cases()

with st.sidebar:
    st.markdown(
        '<div style="color:#e6edf3;font-size:1rem;font-weight:700;margin-bottom:0.2rem;">🚑 Ambulance Panel</div>'
        '<div style="color:#8b949e;font-size:0.71rem;margin-bottom:0.9rem;">Click a patient to view their data</div>',
        unsafe_allow_html=True,
    )

    # New intake button
    if st.button("➕  New Patient Intake", use_container_width=True):
        st.session_state["view_mode"]      = "new"
        st.session_state["viewing_case_id"] = None
        st.rerun()

    st.markdown("---")
    st.markdown('<div style="color:#8b949e;font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Sent Cases</div>', unsafe_allow_html=True)

    if not cases:
        st.markdown('<div style="color:#8b949e;font-size:0.8rem;">No cases sent yet.</div>', unsafe_allow_html=True)
    else:
        for case in cases:
            risk   = case["risk_level"].lower()
            status = case.get("patient_status", "active")
            color  = "#555555" if status == "deceased" else RISK_COLORS.get(risk, "#8b949e")
            name   = case["patient"].get("name") or "Unknown"
            surv   = case["survival_probability"] * 100
            cid    = case["case_id"]
            try:
                ts = datetime.fromisoformat(case["created_at"]).strftime("%H:%M")
            except Exception:
                ts = "—"
            updates   = len(case.get("vitals_history") or [])
            upd_badge = f" · {updates-1} update(s)" if updates > 1 else ""
            icon      = "🕊️ " if status == "deceased" else ""
            lbl_risk  = "DECEASED" if status == "deceased" else f"{risk} risk"
            surv_txt  = "Deceased" if status == "deceased" else f"Survival {surv:.0f}%"

            # Styled card + invisible button overlay
            st.markdown(
                f'<div class="case-card" style="border-left:3px solid {color};">'
                f'<div class="case-card-name">{icon}{name}</div>'
                f'<div class="case-card-risk" style="color:{color};">{lbl_risk}</div>'
                f'<div class="case-card-sub">{surv_txt} · {ts} · {cid[:10]}…{upd_badge}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"btn_{cid}", use_container_width=True):
                st.session_state["view_mode"]       = "view"
                st.session_state["viewing_case_id"] = cid
                st.session_state["active_case_id"]  = cid
                st.rerun()

    st.markdown("---")
    if st.button("🔄 Refresh List", use_container_width=True):
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA — switches between New Intake Form and Patient View
# ─────────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# VIEW MODE — show submitted patient data + AI precautions + update form
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["view_mode"] == "view" and st.session_state["viewing_case_id"]:
    cid = st.session_state["viewing_case_id"]

    try:
        d = fetch_case_detail(cid)
    except Exception as e:
        st.error(f"Could not load case: {e}")
        st.stop()

    v    = d["vitals"]
    p    = d["patient"]
    risk = d["risk_level"].lower()
    color = RISK_COLORS.get(risk, "#8b949e")
    surv  = d["survival_probability"] * 100
    lr    = (d.get("lr_survival_probability") or 0) * 100

    # ── Patient header ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #21262d;'
        f'border-left:4px solid {color};border-radius:10px;padding:1rem 1.4rem;margin-bottom:1rem;'
        f'display:flex;align-items:center;gap:14px;">'
        f'<div style="font-size:2rem;">🧑‍⚕️</div>'
        f'<div style="flex:1;">'
        f'<div style="color:#e6edf3;font-size:1.3rem;font-weight:700;">{p.get("name") or "Unknown Patient"}</div>'
        f'<div style="color:#8b949e;font-size:0.78rem;">'
        f'Age {p.get("age") or "—"} · {p.get("sex") or "—"} · Blood: {p.get("blood_group") or "—"} · '
        f'ID: <span style="font-family:monospace;">{cid[:16]}…</span></div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="background:{color}22;border:1px solid {color};border-radius:20px;'
        f'padding:4px 14px;color:{color};font-weight:700;font-size:0.85rem;text-transform:uppercase;">'
        f'{risk} risk</div>'
        f'<div style="color:#8b949e;font-size:0.72rem;margin-top:4px;">Survival: {surv:.1f}% (GBM)</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Metrics row ───────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Survival (GBM)",    f"{surv:.1f}%")
    m2.metric("Survival (LR)",     f"{lr:.1f}%")
    m3.metric("Cardiac Risk",      f"{d['cardiac_risk_score']:.1f}/10")
    m4.metric("Cardiac Risk Score", f"{d['cardiac_risk_score']:.2f}")

    # ── Row 1: Vitals | Patient details ───────────────────────────────────────
    col_v, col_p = st.columns(2)

    with col_v:
        rows = [
            ("Heart Rate (bpm)",    v.get("heart_rate"),              "bpm"),
            ("SpO₂ (%)",            v.get("spo2"),                    "%"),
            ("Systolic BP (mmHg)",  v.get("blood_pressure_systolic"), "mmHg"),
            ("Diastolic BP (mmHg)", v.get("blood_pressure_diastolic"),"mmHg"),
            ("Resp. Rate (/min)",   v.get("respiratory_rate"),        "/min"),
            ("Temperature (°C)",    v.get("temperature_c"),           "°C"),
            ("Consciousness",       v.get("consciousness_level"),     ""),
        ]
        html = '<div class="card"><div class="card-title">💓 Vitals Sent to Hospital</div>'
        for label, val, unit in rows:
            display = f"{val} {unit}".strip() if val is not None else "—"
            cls = vital_cls(label, val)
            warn = " ⚠️" if cls == "data-warn" else (" 🚨" if cls == "data-crit" else "")
            html += (f'<div class="data-row"><span class="data-label">{label}</span>'
                     f'<span class="data-value {cls}">{display}{warn}</span></div>')
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    with col_p:
        allergies = ", ".join(p.get("allergies") or []) or "None"
        chronic   = ", ".join(p.get("chronic_conditions") or []) or "None"
        symptoms  = ", ".join(d.get("symptoms") or []) or "None"
        meds      = ", ".join(d.get("meds_administered") or []) or "None"
        oxygen    = d.get("oxygen_support") or "—"
        location  = d.get("location") or "—"

        html = '<div class="card"><div class="card-title">🩺 Patient Details</div>'
        for label, val in [("Allergies", allergies), ("Chronic Conditions", chronic),
                            ("Symptoms", symptoms), ("Meds Given", meds),
                            ("Oxygen Support", oxygen), ("Location", location)]:
            html += (f'<div class="data-row"><span class="data-label">{label}</span>'
                     f'<span class="data-value" style="max-width:55%;text-align:right;color:#c9d1d9;">{val}</span></div>')
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    # ── Row 2: AI Precautions | Medication prep ───────────────────────────────
    st.markdown(
        '<div class="section-header precautions"><div>'
        '<div class="section-title">🚨 AI Precautions — Actions to Take in Ambulance</div>'
        '<div class="section-hint">Based on AI risk model (SHAP-driven) — verify with clinical judgement before acting</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="background:#1a1400;border:1px solid #F0B42966;border-left:4px solid #F0B429;'
        'border-radius:6px;padding:8px 12px;margin-bottom:0.8rem;'
        'color:#c9a84c;font-size:0.76rem;line-height:1.5;">'
        '⚠️ <b>AI Caution:</b> The recommendations below are AI-generated and '
        'may not always be correct. Always apply professional clinical judgement '
        'and do not act solely on these suggestions.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_r, col_m = st.columns(2)

    with col_r:
        recs = d.get("recommendations") or []
        if recs:
            for rec in recs:
                st.markdown(
                    f'<div class="rec-item">'
                    f'<div class="rec-title">⚡ {rec["title"]}</div>'
                    f'<div class="rec-detail">{rec["detail"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div style="color:#8b949e;font-size:0.84rem;">No recommendations generated.</div>', unsafe_allow_html=True)

    with col_m:
        plan = d.get("medication_plan") or []
        html = '<div class="card"><div class="card-title">💊 Medication &amp; Equipment to Prepare</div>'
        if not plan:
            html += '<div style="color:#8b949e;font-size:0.83rem;">No specific prep.</div>'
        for item in plan:
            pri = item.get("priority", "standard")
            dot = {"immediate": "med-imm", "prep": "med-prep"}.get(pri, "med-std")
            lbl = {"immediate": "🔴 IMMEDIATE", "prep": "🟡 Prepare", "standard": "🟢 Standard"}.get(pri, pri)
            html += (f'<div class="med-row"><div class="med-dot {dot}"></div>'
                     f'<div><div class="med-name">{item["medication"]} '
                     f'<span style="color:#8b949e;font-size:0.72rem;">({lbl})</span></div>'
                     f'<div class="med-purpose">{item["purpose"]}</div></div></div>')
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    # ── Clinical summary ──────────────────────────────────────────────────────
    summary = d.get("llm_summary", "")
    if summary:
        st.markdown(
            f'<div class="card"><div class="card-title">📝 Clinical Summary</div>'
            f'<div class="summary-box">{summary}</div></div>',
            unsafe_allow_html=True,
        )

    # ── Hospital Suggestions ──────────────────────────────────────────────────
    suggestions = d.get("hospital_suggestions") or []
    PRIORITY_STYLE = {
        "normal":   ("#388bfd", "#0d1b2e", "📋"),
        "urgent":   ("#FF8C00", "#2d1a00", "⚠️"),
        "critical": ("#FF4B4B", "#3d0000", "🚨"),
    }
    unacked = [s for s in suggestions if not s.get("acknowledged")]

    # Blinking alert banner if there are unacknowledged suggestions
    if unacked:
        st.markdown(
            f'<div style="background:#2d1a00;border:2px solid #FF8C00;border-radius:10px;'
            f'padding:10px 16px;margin-bottom:0.8rem;animation:blink-border 1.4s ease-in-out infinite;">'
            f'<span style="color:#FF8C00;font-weight:700;font-size:0.95rem;">📨 '
            f'{len(unacked)} new message(s) from hospital</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-header" style="border-color:#a371f7;margin-top:0.5rem;"><div>'
        '<div class="section-title">📨 Messages from Hospital</div>'
        '<div class="section-hint">Instructions sent by hospital staff — acknowledge each one when actioned</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if not suggestions:
        st.markdown(
            '<div style="color:#8b949e;font-size:0.83rem;padding:6px 0 12px;">No messages from hospital yet.</div>',
            unsafe_allow_html=True,
        )
    else:
        for s in reversed(suggestions):
            pri   = s.get("priority", "normal")
            color, bg, icon = PRIORITY_STYLE.get(pri, PRIORITY_STYLE["normal"])
            acked = s.get("acknowledged", False)
            ts    = s.get("timestamp", "")[:16].replace("T", " ")
            by    = s.get("posted_by", "Hospital Staff")
            sid   = s.get("suggestion_id", "")

            col_msg, col_btn = st.columns([5, 1])
            with col_msg:
                ack_txt = (
                    '<span style="background:#002d1a;color:#00C48C;font-size:0.7rem;'
                    'border-radius:10px;padding:2px 8px;margin-left:8px;">✓ Acknowledged</span>'
                    if acked else ""
                )
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {color};border-left:4px solid {color};'
                    f'border-radius:6px;padding:10px 14px;margin-bottom:6px;">'
                    f'<div style="color:{color};font-weight:700;font-size:0.88rem;">'
                    f'{icon} {s["text"]}{ack_txt}</div>'
                    f'<div style="color:#8b949e;font-size:0.7rem;margin-top:4px;">'
                    f'From: <b style="color:#c9d1d9;">{by}</b> · {ts} UTC · '
                    f'Priority: <b style="color:{color};">{pri.upper()}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_btn:
                if not acked:
                    if st.button("✓ Done", key=f"ack_{sid}_{cid}"):
                        try:
                            acknowledge_suggestion(cid, sid)
                            st.rerun()
                        except Exception:
                            pass
                else:
                    st.markdown(
                        '<div style="color:#00C48C;font-size:0.75rem;padding-top:12px;text-align:center;">✓ Done</div>',
                        unsafe_allow_html=True,
                    )

    # ── Update history if any ─────────────────────────────────────────────────
    history = d.get("vitals_history") or []
    if len(history) > 1:
        st.markdown(
            f'<div style="background:#2d1a00;border:1px solid #FF8C00;border-radius:8px;'
            f'padding:8px 14px;margin-bottom:0.8rem;color:#FF8C00;font-size:0.82rem;">'
            f'⚠️ This case has <b>{len(history)-1} update(s)</b> already sent. '
            f'Latest: {history[-1].get("update_reason","—")}</div>',
            unsafe_allow_html=True,
        )

    # ── Deceased declaration (only if still active) ───────────────────────────
    is_deceased = d.get("patient_status") == "deceased"

    if is_deceased:
        tod  = d.get("time_of_death", "—")
        cause = d.get("cause_notes", "—")
        conf  = d.get("confirmed_by", "—")
        st.markdown(
            f'<div style="background:#1a0a0a;border:2px solid #555;border-radius:12px;'
            f'padding:1.2rem 1.5rem;margin:1rem 0;text-align:center;">'
            f'<div style="font-size:2rem;margin-bottom:0.4rem;">🕊️</div>'
            f'<div style="color:#aaa;font-size:1.1rem;font-weight:700;letter-spacing:0.05em;">PATIENT DECEASED</div>'
            f'<div style="color:#888;font-size:0.82rem;margin-top:8px;line-height:1.8;">'
            f'Time of Death: <b style="color:#bbb;">{tod}</b> &nbsp;·&nbsp; '
            f'Confirmed by: <b style="color:#bbb;">{conf}</b><br>'
            f'Cause: <b style="color:#bbb;">{cause}</b>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Deceased declaration button ────────────────────────────────────────
        st.markdown(
            '<div class="section-header" style="border-color:#555;margin-top:1rem;"><div>'
            '<div class="section-title" style="color:#aaa;">☠️ Declare Patient Deceased</div>'
            '<div class="section-hint">Only use if patient has passed away in the ambulance</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        with st.expander("Open deceased declaration form", expanded=False):
            with st.form(f"deceased_form_{cid}"):
                st.warning("⚠️ This action is irreversible. Please confirm before submitting.")
                d1, d2 = st.columns(2)
                with d1:
                    tod_input  = st.text_input("Time of Death (HH:MM)", placeholder="e.g. 14:32", value="")
                    conf_input = st.text_input("Confirmed By", placeholder="e.g. Paramedic Ravi Kumar", value="")
                with d2:
                    cause_input = st.text_area("Cause / Notes", placeholder="e.g. Cardiac arrest — CPR unsuccessful for 30 min", value="", height=90)

                deceased_btn = st.form_submit_button("🕊️  Confirm — Declare Patient Deceased", use_container_width=True)

            if deceased_btn:
                dec_payload = {
                    "time_of_death": tod_input or None,
                    "cause_notes":   cause_input or None,
                    "confirmed_by":  conf_input or None,
                }
                try:
                    declare_deceased(cid, dec_payload)
                    st.error("Patient has been declared deceased. Hospital has been notified.")
                    st.rerun()
                except requests.HTTPError as err:
                    st.error(f"Failed: {err.response.text}")
                except Exception as exc:
                    st.error(f"Error: {exc}")

        # ── Detailed update form (only for active patients) ────────────────────
        st.markdown(
            '<div class="section-header update"><div>'
            '<div class="section-title">🔄 Send Updated Patient Condition</div>'
            '<div class="section-hint">Fill everything you have — leave vitals at 0 to keep the previous value</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        with st.form(f"update_form_{cid}"):

            # ── Updated Vitals ─────────────────────────────────────────────────
            st.markdown("**💓 Updated Vitals**")
            st.markdown(
                '<div class="vital-ref">Leave at 0 to keep previous value &nbsp;·&nbsp; '
                'Normal: HR <span class="ref-ok">60–100</span> · '
                'SpO₂ <span class="ref-ok">≥95%</span>'
                '<span class="ref-crit"> (critical &lt;88%)</span> · '
                'Systolic <span class="ref-ok">90–140</span> mmHg · '
                'RR <span class="ref-ok">12–20</span>/min</div>',
                unsafe_allow_html=True,
            )

            u1, u2, u3 = st.columns(3)
            with u1:
                u_hr  = st.number_input("❤️ Heart Rate (bpm)",    0, 300, 0,
                                         help=f"Current: {v.get('heart_rate') or '—'} bpm")
                u_sbp = st.number_input("🩸 Systolic BP (mmHg)",  0, 300, 0,
                                         help=f"Current: {v.get('blood_pressure_systolic') or '—'} mmHg")
                u_dbp = st.number_input("🩸 Diastolic BP (mmHg)", 0, 200, 0,
                                         help=f"Current: {v.get('blood_pressure_diastolic') or '—'} mmHg")
            with u2:
                u_spo2 = st.number_input("💨 SpO₂ (%)",            0, 100, 0,
                                          help=f"Current: {v.get('spo2') or '—'}%")
                u_rr   = st.number_input("🫁 Resp. Rate (/min)",   0, 60,  0,
                                          help=f"Current: {v.get('respiratory_rate') or '—'}/min")
                u_temp = st.number_input("🌡️ Temperature (°C)",    30.0, 45.0, 37.0, step=0.1,
                                          help=f"Current: {v.get('temperature_c') or '—'}°C")
            with u3:
                u_pain = st.number_input("😣 Pain Scale (0–10)",   0, 10, 0,
                                          help="0 = no pain · 10 = worst possible")
                u_glu  = st.text_input("🩸 Blood Glucose",          placeholder="e.g. 180 mg/dL", value="")
                u_spo2_probe = st.selectbox("SpO₂ Probe Site",
                                             ["Finger", "Ear", "Forehead", "Other"], index=0)

            cur_cons = v.get("consciousness_level") or "Alert"
            cons_options = ["Alert", "Verbal", "Pain", "Unresponsive"]
            cons_colors  = {"Alert": "#00C48C", "Verbal": "#7ee787", "Pain": "#FF8C00", "Unresponsive": "#FF4B4B"}
            cons_bg      = {"Alert": "#002d1a", "Verbal": "#1a2a00", "Pain": "#2d1a00", "Unresponsive": "#3d0000"}
            cons_icons   = {"Alert": "🟢", "Verbal": "🟡", "Pain": "🟠", "Unresponsive": "🔴"}
            cons_desc    = {"Alert": "Fully conscious", "Verbal": "Responds to voice", "Pain": "Responds to pain", "Unresponsive": "No response"}

            cards_html = '<div style="margin-bottom:4px;color:#c9d1d9;font-size:0.88rem;font-weight:500;">🧠 Consciousness Level</div><div style="display:flex;gap:8px;margin-bottom:0.5rem;">'
            for opt in cons_options:
                c = cons_colors[opt]
                bg = cons_bg[opt]
                ic = cons_icons[opt]
                desc = cons_desc[opt]
                border_w = "2.5px" if opt == cur_cons else "2px"
                opacity = "1" if opt == cur_cons else "0.55"
                cards_html += (
                    f'<div style="flex:1;background:{bg};border:{border_w} solid {c};'
                    f'border-radius:8px;padding:10px 4px;text-align:center;'
                    f'font-weight:700;font-size:0.82rem;color:{c};opacity:{opacity};">'
                    f'{ic} {opt}<br>'
                    f'<span style="font-size:0.66rem;font-weight:400;">{desc}</span></div>'
                )
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)

            u_cons = st.radio(
                "Consciousness Level",
                options=cons_options,
                index=cons_options.index(cur_cons),
                horizontal=True,
                label_visibility="collapsed",
            )

            st.markdown("---")

            # ── Symptoms & Clinical ────────────────────────────────────────────
            st.markdown("**🩺 Updated Clinical Details**")
            u_symptoms = st.text_area(
                "Updated / New Symptoms",
                placeholder="e.g. loss of consciousness, new chest tightness, vomiting  (comma separated)\nLeave blank to keep existing symptoms",
                value="", height=70,
            )

            uc1, uc2 = st.columns(2)
            with uc1:
                u_meds = st.text_area(
                    "Additional Medications Given",
                    placeholder="e.g. Adrenaline 1mg IV, Atropine 0.6mg IV\n(these are ADDED to previous meds)",
                    value="", height=80,
                )
                u_oxygen = st.text_input(
                    "Updated Oxygen Support",
                    placeholder="e.g. Switched to BVM ventilation, Intubated",
                    value="",
                )
            with uc2:
                u_intervention = st.text_area(
                    "Interventions Performed",
                    placeholder="e.g. CPR started, Defibrillation x2, IV access obtained, Tourniquet applied",
                    value="", height=80,
                )
                u_response = st.selectbox(
                    "Patient Response to Treatment",
                    ["— select —", "Improving", "Stable", "Deteriorating", "No response", "CPR in progress"],
                )

            st.markdown("---")

            # ── Reason & Notes ────────────────────────────────────────────────
            st.markdown("**📝 Update Reason & Notes**")
            nc1, nc2 = st.columns(2)
            with nc1:
                u_reason = st.text_input(
                    "⚠️ Primary Reason for Update",
                    placeholder="e.g. BP dropped suddenly · Patient became unresponsive · SpO2 falling",
                    value="",
                )
            with nc2:
                u_eta = st.text_input(
                    "🚑 Updated ETA to Hospital (mins)",
                    placeholder="e.g. 8",
                    value="",
                )

            u_notes = st.text_area(
                "Additional Notes",
                placeholder="e.g. Family reports patient has pacemaker. Second IV line established. "
                            "Defibrillated once at 200J — sinus rhythm restored.",
                value="", height=80,
            )

            update_btn = st.form_submit_button(
                "🔄  Push Update to Hospital", use_container_width=True
            )

        if update_btn:
            vitals_upd = {}
            if u_hr   > 0: vitals_upd["heart_rate"]               = u_hr
            if u_sbp  > 0: vitals_upd["blood_pressure_systolic"]  = u_sbp
            if u_dbp  > 0: vitals_upd["blood_pressure_diastolic"] = u_dbp
            if u_spo2 > 0: vitals_upd["spo2"]                     = u_spo2
            if u_rr   > 0: vitals_upd["respiratory_rate"]         = u_rr
            vitals_upd["temperature_c"]       = u_temp
            vitals_upd["consciousness_level"] = u_cons

            # Build a rich reason string
            reason_parts = []
            if u_reason:        reason_parts.append(u_reason)
            if u_response and u_response != "— select —":
                reason_parts.append(f"Response: {u_response}")
            if u_intervention:  reason_parts.append(f"Interventions: {u_intervention}")
            if u_eta:           reason_parts.append(f"ETA: {u_eta} min")
            full_reason = " | ".join(reason_parts) or "Vitals updated mid-transport"

            # Combine extra notes
            extra_notes = []
            if u_glu:           extra_notes.append(f"Blood glucose: {u_glu}")
            if u_spo2_probe != "Finger": extra_notes.append(f"SpO2 probe: {u_spo2_probe}")
            if u_pain > 0:      extra_notes.append(f"Pain scale: {u_pain}/10")
            if u_notes:         extra_notes.append(u_notes)
            combined_notes = " | ".join(extra_notes) if extra_notes else None

            # Add new meds to existing
            new_meds = [m.strip() for m in u_meds.split(",") if m.strip()]
            existing_meds = d.get("meds_administered") or []
            all_meds = list(dict.fromkeys(existing_meds + new_meds)) if new_meds else None

            upd_payload = {
                "vitals":            vitals_upd,
                "symptoms":          [s.strip() for s in u_symptoms.split(",") if s.strip()] or None,
                "meds_administered": all_meds,
                "oxygen_support":    u_oxygen or None,
                "notes":             combined_notes,
                "update_reason":     full_reason,
            }

            with st.spinner("Pushing update to hospital…"):
                try:
                    res = push_update(cid, upd_payload)
                    new_risk  = res["risk_level"].lower()
                    new_color = RISK_COLORS.get(new_risk, "#388bfd")
                    st.markdown(
                        f'<div style="background:{new_color}11;border:1px solid {new_color};'
                        f'border-radius:8px;padding:0.9rem 1.1rem;margin-top:0.6rem;">'
                        f'<div style="color:{new_color};font-weight:700;">✅ Update Sent — New Risk: {new_risk.upper()}</div>'
                        f'<div style="color:#8b949e;font-size:0.8rem;margin-top:4px;">'
                        f'Survival: {res["survival_probability"]*100:.1f}% · '
                        f'Cardiac Risk: {res["cardiac_risk_score"]:.1f}/10</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.info(res["llm_summary"])
                    st.rerun()
                except requests.HTTPError as err:
                    st.error(f"Update failed: {err.response.text}")
                except Exception as exc:
                    st.error(f"Error: {exc}")




# ══════════════════════════════════════════════════════════════════════════════
# NEW INTAKE MODE — blank form to submit a new patient
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.markdown(
        '<h1 style="color:#e6edf3;font-size:1.5rem;font-weight:700;margin-bottom:0.1rem;">'
        '🚑 New Patient Intake</h1>'
        '<p style="color:#8b949e;font-size:0.8rem;margin-bottom:0.5rem;">'
        'Fill all available fields · Transmit to hospital before arrival</p>',
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
        'margin-bottom:1rem;'
        'display:flex;align-items:flex-start;gap:12px;">'
        '<div style="font-size:1.1rem;margin-top:1px;">⚠️</div>'
        '<div>'
        '<div style="color:#F0B429;font-weight:700;font-size:0.83rem;letter-spacing:0.02em;">'
        'AI DECISION SUPPORT — USE WITH CAUTION</div>'
        '<div style="color:#c9a84c;font-size:0.76rem;margin-top:3px;line-height:1.5;">'
        'Risk scores, recommendations, and medication suggestions shown after submission are generated by an AI model. '
        'They <b>may not always be accurate</b>. '
        'Always apply your clinical training and judgement. Never rely solely on AI output.'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.form("intake_form", clear_on_submit=False):

        # Patient Profile
        st.markdown('<div class="section-header"><div><div class="section-title">👤 Patient Profile</div><div class="section-hint">Leave blank if unavailable</div></div></div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            patient_name = st.text_input("Full Name", placeholder="e.g. John Smith", value="")
        with col2:
            age = st.number_input("Age (years)", 0, 120, 0)
        with col3:
            sex = st.selectbox("Sex", ["Unknown", "Male", "Female", "Other"])

        col4, col5 = st.columns([1, 2])
        with col4:
            blood_group = st.text_input("Blood Group *", placeholder="e.g. O+, A-, B+, AB-", value="")
        with col5:
            allergies = st.text_input("Allergies", placeholder="e.g. Penicillin (comma separated)", value="")
        chronic = st.text_input("Chronic Conditions", placeholder="e.g. Diabetes, Hypertension", value="")

        # Vitals
        st.markdown('<div class="section-header vitals"><div><div class="section-title">💓 Vital Signs</div><div class="section-hint">Enter 0 for any reading you cannot obtain</div></div></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="vital-ref">Normal: HR <span class="ref-ok">60–100</span> · '
            'SpO₂ <span class="ref-ok">≥95%</span> <span class="ref-warn">(warn &lt;94%)</span> '
            '<span class="ref-crit">(critical &lt;88%)</span> · '
            'Systolic <span class="ref-ok">90–140</span> mmHg · '
            'RR <span class="ref-ok">12–20</span>/min · Temp <span class="ref-ok">36–38°C</span></div>',
            unsafe_allow_html=True,
        )
        v1, v2, v3 = st.columns(3)
        with v1:
            heart_rate = st.number_input("❤️ Heart Rate (bpm)",    0, 300, 0)
            systolic   = st.number_input("🩸 Systolic BP (mmHg)",  0, 300, 0)
        with v2:
            spo2       = st.number_input("💨 SpO₂ (%)",            0, 100, 0)
            diastolic  = st.number_input("🩸 Diastolic BP (mmHg)", 0, 200, 0)
        with v3:
            resp_rate  = st.number_input("🫁 Resp. Rate (/min)",   0, 60,  0)
            temperature = st.number_input("🌡️ Temperature (°C)",   30.0, 45.0, 37.0, step=0.1)

        st.markdown(
            '<div style="margin-bottom:4px;color:#c9d1d9;font-size:0.88rem;font-weight:500;">🧠 Consciousness Level</div>'
            '<div style="display:flex;gap:8px;margin-bottom:1rem;">'
            '<div style="flex:1;background:#002d1a;border:2px solid #00C48C;border-radius:8px;padding:10px 4px;text-align:center;font-weight:700;font-size:0.82rem;color:#00C48C;">🟢 Alert<br><span style="font-size:0.68rem;font-weight:400;color:#4caf7d;">Fully conscious</span></div>'
            '<div style="flex:1;background:#1a2a00;border:2px solid #7ee787;border-radius:8px;padding:10px 4px;text-align:center;font-weight:700;font-size:0.82rem;color:#7ee787;">🟡 Verbal<br><span style="font-size:0.68rem;font-weight:400;color:#7ee787;">Responds to voice</span></div>'
            '<div style="flex:1;background:#2d1a00;border:2px solid #FF8C00;border-radius:8px;padding:10px 4px;text-align:center;font-weight:700;font-size:0.82rem;color:#FF8C00;">🟠 Pain<br><span style="font-size:0.68rem;font-weight:400;color:#FF8C00;">Responds to pain</span></div>'
            '<div style="flex:1;background:#3d0000;border:2px solid #FF4B4B;border-radius:8px;padding:10px 4px;text-align:center;font-weight:700;font-size:0.82rem;color:#FF4B4B;">🔴 Unresponsive<br><span style="font-size:0.68rem;font-weight:400;color:#FF4B4B;">No response</span></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        consciousness = st.radio(
            "Consciousness Level",
            options=["Alert", "Verbal", "Pain", "Unresponsive"],
            horizontal=True,
            index=0,
            label_visibility="collapsed",
        )

        # Clinical Details
        st.markdown('<div class="section-header clinical"><div><div class="section-title">🩺 Clinical Details</div></div></div>', unsafe_allow_html=True)
        symptoms = st.text_area("Presenting Symptoms", placeholder="e.g. chest pain, dizziness  (comma separated)", value="", height=70)
        c1, c2 = st.columns(2)
        with c1:
            meds   = st.text_area("Medications Given", placeholder="e.g. Aspirin 325mg, Nitro 0.4mg", value="", height=80)
        with c2:
            oxygen   = st.text_input("Oxygen Support",  placeholder="e.g. NRB mask @ 12 L/min", value="")
            location = st.text_input("📍 Location / GPS", placeholder="e.g. 12.97°N 77.59°E", value="")
        notes = st.text_area("Narrative Notes", placeholder="e.g. Found unresponsive at home, 30min onset", value="", height=70)

        # Labs & Attachments
        st.markdown('<div class="section-header labs"><div><div class="section-title">🔬 Labs &amp; Attachments</div></div></div>', unsafe_allow_html=True)
        labs_input = st.text_area("Lab Results (Name: value, one per line)", placeholder="Troponin: 0.15 ng/mL\nGlucose: 180 mg/dL", value="", height=80)
        uploaded_files = st.file_uploader("Upload ECG / injury photos", accept_multiple_files=True, type=["png","jpg","jpeg","pdf","bmp"])

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚀  Transmit to Hospital", use_container_width=True)

    if submitted:
        allergies_list = [i.strip() for i in allergies.split(",") if i.strip()]
        symptom_list   = [i.strip() for i in symptoms.split(",") if i.strip()]
        notes_text     = notes or ""
        symptom_list   = list(dict.fromkeys(symptom_list))

        labs = []
        for line in labs_input.splitlines():
            if ":" in line:
                name, remainder = line.split(":", 1)
                labs.append({"name": name.strip(), "value": remainder.strip()})

        payload = {
            "patient": {
                "name": patient_name or None,
                "age":  age if age > 0 else None,
                "sex":  None if sex == "Unknown" else sex,
                "blood_group": blood_group or None,
                "allergies": allergies_list,
                "chronic_conditions": [i.strip() for i in chronic.split(",") if i.strip()],
            },
            "vitals": {
                "heart_rate":               heart_rate  if heart_rate  > 0 else None,
                "blood_pressure_systolic":  systolic    if systolic    > 0 else None,
                "blood_pressure_diastolic": diastolic   if diastolic   > 0 else None,
                "respiratory_rate":         resp_rate   if resp_rate   > 0 else None,
                "spo2":                     spo2        if spo2        > 0 else None,
                "temperature_c":            temperature,
                "consciousness_level":      consciousness,
            },
            "labs": labs,
            "symptoms": symptom_list,
            "meds_administered": [i.strip() for i in meds.split(",") if i.strip()],
            "oxygen_support":    oxygen or None,
            "notes":             notes_text or None,
            "location":          location or None,
            "attachments":       encode_attachments(uploaded_files or []),
        }

        with st.spinner("Transmitting to hospital…"):
            try:
                result = submit_case(payload)
                risk   = result["risk_level"].lower()
                color  = RISK_COLORS.get(risk, "#388bfd")
                surv   = result["survival_probability"] * 100
                lr     = result.get("lr_survival_probability", 0) * 100
                card   = result["cardiac_risk_score"]

                # Save and switch to view mode
                st.session_state["active_case_id"]  = result["case_id"]
                st.session_state["viewing_case_id"] = result["case_id"]
                st.session_state["view_mode"]       = "view"

                st.markdown(
                    f'<div style="background:{color}11;border:1px solid {color};border-radius:10px;'
                    f'padding:1rem 1.3rem;margin-top:0.8rem;">'
                    f'<div style="color:{color};font-size:1.05rem;font-weight:700;">✅ Transmitted — Risk: {risk.upper()}</div>'
                    f'<div style="color:#8b949e;font-size:0.76rem;margin-top:4px;font-family:monospace;">Case ID: {result["case_id"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                m1, m2, m3 = st.columns(3)
                m1.metric("Survival (GBM)", f"{surv:.1f}%")
                m2.metric("Survival (LR)",  f"{lr:.1f}%")
                m3.metric("Cardiac Risk",   f"{card:.1f}/10")

                st.info("✅ Case sent! Click the patient name in the left sidebar to view full details and AI precautions.")
                if st.button("👁️  View Patient Now", use_container_width=True):
                    st.rerun()

            except requests.HTTPError as err:
                st.error(f"Transmission failed: {err.response.text}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
                st.info("Make sure backend is running on port 8000.")