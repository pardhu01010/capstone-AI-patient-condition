"""
inference.py
------------
Implements the paper's two-model stack:
  1. Primary: XGBoost GBM with Platt-scaling calibration
  2. Baseline: L2-regularised logistic regression

Both models are trained on-the-fly from a small synthetic cohort that
approximates the MIMIC-IV / eICU-CRD prehospital schema mapping described in
Section III-B of the paper.  When real data become available the
`_train_models()` function can be replaced by loading persisted artefacts.

Explainability (Section IV-C):
  - Global SHAP beeswarm summary (population-level)
  - Local SHAP waterfall / bar plot (per-patient)
  - LIME local linear surrogate (secondary, model-agnostic)

Heuristic rule layer (Section IV-B):
  - SpO2 < 88 or HR > 140  →  at-least "critical"
  - SpO2 < 94 or HR > 120  →  at-least "high"
"""

from __future__ import annotations

import base64
import io
import logging
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import shap
import matplotlib
matplotlib.use("Agg")          # headless backend – no display needed
import matplotlib.pyplot as plt
from lime.lime_tabular import LimeTabularExplainer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from backend.schemas import IntakePayload, Recommendation

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature engineering helpers
# ---------------------------------------------------------------------------

FEATURE_NAMES: List[str] = [
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "respiratory_rate",
    "temperature_c",
    "consciousness_numeric",   # 0=Alert 1=Verbal 2=Pain 3=Unresponsive
    "age",
    "has_chest_pain",
    "has_dyspnea",
    "has_trauma",
    "has_arrhythmia",
    "missing_hr",
    "missing_spo2",
    "missing_sbp",
]

# Physiologically plausible clipping ranges (outlier handling – Section III-C)
VITAL_CLIPS: Dict[str, Tuple[float, float]] = {
    "heart_rate":        (20,  250),
    "systolic_bp":       (40,  300),
    "diastolic_bp":      (20,  200),
    "spo2":              (50,  100),
    "respiratory_rate":  (4,   60),
    "temperature_c":     (30,  45),
    "age":               (0,   120),
}

CONSCIOUSNESS_MAP = {"alert": 0, "verbal": 1, "pain": 2, "unresponsive": 3}


def _clip(value: Optional[float], low: float, high: float, impute: float) -> Tuple[float, int]:
    """Clip to physiological range; return (value, missingness_indicator)."""
    if value is None or np.isnan(float(value)):
        return impute, 1
    return float(np.clip(value, low, high)), 0


def payload_to_feature_vector(payload: IntakePayload) -> np.ndarray:
    """Convert an IntakePayload to the 15-dimensional feature vector."""
    v = payload.vitals
    p = payload.patient
    symptoms_lower = " ".join(payload.symptoms).lower()

    hr,  miss_hr  = _clip(v.heart_rate,              *VITAL_CLIPS["heart_rate"],        80)
    sbp, miss_sbp = _clip(v.blood_pressure_systolic, *VITAL_CLIPS["systolic_bp"],       120)
    dbp, _        = _clip(v.blood_pressure_diastolic,*VITAL_CLIPS["diastolic_bp"],      80)
    sp,  miss_sp  = _clip(v.spo2,                    *VITAL_CLIPS["spo2"],              95)
    rr,  _        = _clip(v.respiratory_rate,        *VITAL_CLIPS["respiratory_rate"],  16)
    tc,  _        = _clip(v.temperature_c,           *VITAL_CLIPS["temperature_c"],     37)
    age, _        = _clip(p.age,                     *VITAL_CLIPS["age"],               50)

    cons_raw = (v.consciousness_level or "alert").lower()
    cons = float(CONSCIOUSNESS_MAP.get(cons_raw, 0))

    has_chest  = float(any(k in symptoms_lower for k in ("chest", "cardiac", "stemi", "acs")))
    has_dysp   = float(any(k in symptoms_lower for k in ("breath", "wheez", "dyspn", "spo2", "resp")))
    has_trauma = float(any(k in symptoms_lower for k in ("trauma", "bleed", "injur", "fracture", "fall")))
    has_arr    = float(any(k in symptoms_lower for k in ("arrhy", "palpita", "tachy", "fibrill")))

    return np.array([
        hr, sbp, dbp, sp, rr, tc, cons, age,
        has_chest, has_dysp, has_trauma, has_arr,
        float(miss_hr), float(miss_sp), float(miss_sbp),
    ], dtype=float)


# ---------------------------------------------------------------------------
# Synthetic training cohort  (Section III-B schema mapping approximation)
# ---------------------------------------------------------------------------

def _generate_synthetic_cohort(n: int = 3000, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Balanced synthetic prehospital cohort — approx 40% critical, 60% non-critical.
    Mimics ICU-to-prehospital schema mapping (Section III-B).
    Replace with real MIMIC-IV / eICU records when available.
    """
    rng = np.random.default_rng(seed)

    # --- Healthy / guarded sub-cohort (60%) ---
    n_healthy = int(n * 0.60)
    hr_h  = rng.normal(78,  14, n_healthy).clip(50, 110)
    sbp_h = rng.normal(122, 16, n_healthy).clip(90, 165)
    dbp_h = rng.normal(78,  10, n_healthy).clip(55, 100)
    sp_h  = rng.normal(97,   2, n_healthy).clip(92, 100)
    rr_h  = rng.normal(15,   3, n_healthy).clip(10, 22)
    tc_h  = rng.normal(37.0, 0.5, n_healthy).clip(36, 38.5)
    con_h = rng.choice([0, 1], n_healthy, p=[0.85, 0.15]).astype(float)  # mostly Alert
    age_h = rng.normal(52, 16, n_healthy).clip(18, 90)
    sym_h = rng.integers(0, 2, (n_healthy, 4)).astype(float) * rng.uniform(0, 0.5, (n_healthy, 4))
    mis_h = rng.binomial(1, 0.05, (n_healthy, 3)).astype(float)
    X_h   = np.column_stack([hr_h, sbp_h, dbp_h, sp_h, rr_h, tc_h, con_h, age_h, sym_h, mis_h])
    y_h   = np.zeros(n_healthy, dtype=int)

    # --- Critical / high-risk sub-cohort (40%) ---
    n_crit = n - n_healthy
    hr_c  = rng.normal(118, 22, n_crit).clip(80, 200)
    sbp_c = rng.normal(88,  24, n_crit).clip(40, 130)
    dbp_c = rng.normal(58,  16, n_crit).clip(25, 90)
    sp_c  = rng.normal(89,   6, n_crit).clip(65, 96)
    rr_c  = rng.normal(26,   6, n_crit).clip(14, 50)
    tc_c  = rng.normal(38.2, 0.9, n_crit).clip(36, 42)
    con_c = rng.choice([1, 2, 3], n_crit, p=[0.40, 0.35, 0.25]).astype(float)
    age_c = rng.normal(62, 16, n_crit).clip(18, 95)
    sym_c = rng.integers(0, 2, (n_crit, 4)).astype(float)
    mis_c = rng.binomial(1, 0.12, (n_crit, 3)).astype(float)
    X_c   = np.column_stack([hr_c, sbp_c, dbp_c, sp_c, rr_c, tc_c, con_c, age_c, sym_c, mis_c])
    y_c   = np.ones(n_crit, dtype=int)

    # Shuffle and combine
    X = np.vstack([X_h, X_c])
    y = np.concatenate([y_h, y_c])
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

@dataclass
class _ModelBundle:
    gbm: CalibratedClassifierCV
    lr:  CalibratedClassifierCV
    scaler: StandardScaler
    gbm_explainer: shap.TreeExplainer
    lime_explainer: LimeTabularExplainer
    background_X: np.ndarray          # for global SHAP


_bundle: Optional[_ModelBundle] = None


def _train_models() -> _ModelBundle:
    """Train GBM + LR on the synthetic cohort and build explainers."""
    logger.info("Training ML models on synthetic prehospital cohort …")
    X, y = _generate_synthetic_cohort()

    # 70 / 15 / 15 split (Section V-A)
    n = len(X)
    idx = np.random.default_rng(0).permutation(n)
    train_end = int(0.70 * n)
    val_end   = int(0.85 * n)
    X_train, y_train = X[idx[:train_end]],  y[idx[:train_end]]
    X_val,   y_val   = X[idx[train_end:val_end]], y[idx[train_end:val_end]]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_val_sc   = scaler.transform(X_val)

    # --- GBM (XGBoost) with Platt-scaling calibration (Section IV-B) ---
    raw_gbm = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    gbm = CalibratedClassifierCV(raw_gbm, method="sigmoid", cv=3)
    gbm.fit(X_train, y_train)

    # --- L2-regularised logistic regression baseline (Section IV-B) ---
    raw_lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    lr = CalibratedClassifierCV(raw_lr, method="sigmoid", cv=3)
    lr.fit(X_train_sc, y_train)

    # --- SHAP TreeExplainer on the raw GBM inside the calibrator ---
    # CalibratedClassifierCV wraps multiple estimators; use the first one for SHAP
    inner_gbm = gbm.calibrated_classifiers_[0].estimator
    gbm_explainer = shap.TreeExplainer(inner_gbm)

    # Background sample for global SHAP (100 representative points)
    bg_idx = np.random.default_rng(7).choice(len(X_train), size=100, replace=False)
    background_X = X_train[bg_idx]

    # --- LIME explainer (Section IV-C-b) ---
    lime_explainer = LimeTabularExplainer(
        training_data=X_train,
        feature_names=FEATURE_NAMES,
        class_names=["low_risk", "high_risk"],
        mode="classification",
        discretize_continuous=True,
        random_state=42,
    )

    logger.info("Models trained successfully.")
    return _ModelBundle(
        gbm=gbm,
        lr=lr,
        scaler=scaler,
        gbm_explainer=gbm_explainer,
        lime_explainer=lime_explainer,
        background_X=background_X,
    )


def _get_bundle() -> _ModelBundle:
    global _bundle
    if _bundle is None:
        _bundle = _train_models()
    return _bundle


# ---------------------------------------------------------------------------
# Plotting helpers (return base64 PNG strings for the dashboard)
# ---------------------------------------------------------------------------

def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# Human-readable display names for chart labels
_FEATURE_DISPLAY = {
    "heart_rate":            "Heart Rate",
    "systolic_bp":           "Systolic BP",
    "diastolic_bp":          "Diastolic BP",
    "spo2":                  "SpO2 (Oxygen)",
    "respiratory_rate":      "Resp. Rate",
    "temperature_c":         "Temperature",
    "consciousness_numeric": "Consciousness",
    "age":                   "Age",
    "has_chest_pain":        "Chest Pain",
    "has_dyspnea":           "Dyspnea",
    "has_trauma":            "Trauma",
    "has_arrhythmia":        "Arrhythmia",
    "missing_hr":            "HR (missing)",
    "missing_spo2":          "SpO2 (missing)",
    "missing_sbp":           "SBP (missing)",
}

def _fmt(name: str) -> str:
    return _FEATURE_DISPLAY.get(name, name.replace("_", " ").title())


def _shap_local_plot(shap_values: np.ndarray, feature_vector: np.ndarray) -> str:
    """Compact SHAP bar plot for a single patient."""
    order  = np.argsort(np.abs(shap_values))[::-1][:6]
    labels = [_fmt(FEATURE_NAMES[i]) for i in order]
    vals   = shap_values[order]
    colors = ["#d62728" if v > 0 else "#1f77b4" for v in vals]

    fig, ax = plt.subplots(figsize=(5, 2.6))
    ax.barh(labels, vals, color=colors, height=0.5)
    ax.axvline(0, color="#888", linewidth=0.7)
    ax.set_xlabel("SHAP value", fontsize=8)
    ax.set_title("Local SHAP — This Patient", fontsize=9, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7.5)
    ax.invert_yaxis()
    fig.tight_layout(pad=0.5)
    return _fig_to_b64(fig)


def _shap_global_plot(bundle: _ModelBundle) -> str:
    """Compact global SHAP bar chart."""
    shap_vals = bundle.gbm_explainer.shap_values(bundle.background_X)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]
    mean_abs = np.abs(shap_vals).mean(axis=0)
    order    = np.argsort(mean_abs)[::-1][:8]
    labels   = [_fmt(FEATURE_NAMES[i]) for i in order]

    fig, ax = plt.subplots(figsize=(5, 2.6))
    ax.barh(labels, mean_abs[order], color="#2c7bb6", height=0.5)
    ax.set_xlabel("Mean |SHAP value|", fontsize=8)
    ax.set_title("Global Feature Importance", fontsize=9, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7.5)
    ax.invert_yaxis()
    fig.tight_layout(pad=0.5)
    return _fig_to_b64(fig)


def _lime_local_plot(
    bundle: _ModelBundle, feature_vector: np.ndarray
) -> str:
    """Compact LIME local surrogate plot."""
    def predict_fn(X: np.ndarray) -> np.ndarray:
        return bundle.gbm.predict_proba(X)

    explanation = bundle.lime_explainer.explain_instance(
        data_row=feature_vector,
        predict_fn=predict_fn,
        num_features=6,
        top_labels=1,
    )
    label  = list(explanation.as_map().keys())[0]
    items  = explanation.as_list(label=label)
    names  = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = ["#d62728" if v > 0 else "#1f77b4" for v in values]

    fig, ax = plt.subplots(figsize=(5, 2.6))
    ax.barh(names, values, color=colors, height=0.5)
    ax.axvline(0, color="#888", linewidth=0.7)
    ax.set_xlabel("LIME weight", fontsize=8)
    ax.set_title("LIME — Sanity Check", fontsize=9, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7)
    ax.invert_yaxis()
    fig.tight_layout(pad=0.5)
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Public result dataclass
# ---------------------------------------------------------------------------

@dataclass
class StructuredInferenceResult:
    risk_level: str
    survival_probability: float
    cardiac_risk_score: float
    recommendations: List[Recommendation]
    # XAI artefacts (base64 PNG)
    shap_local_plot_b64: str = ""
    shap_global_plot_b64: str = ""
    lime_local_plot_b64: str = ""
    # Secondary model output
    lr_survival_probability: float = 0.0
    # SHAP values for top features (for text recommendations)
    top_shap_features: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Heuristic rule layer – safety guardrail (Section IV-B)
# ---------------------------------------------------------------------------

def _apply_heuristic_rules(
    spo2: Optional[float],
    heart_rate: Optional[float],
    current_risk: str,
    consciousness: Optional[str] = None,
    systolic_bp: Optional[float] = None,
    resp_rate: Optional[float] = None,
) -> str:
    """
    Safety guardrail — ensures obvious high-risk states are never under-triaged.
    Based on clinical triage heuristics (Section IV-B).
    """
    risk_order = {"guarded": 0, "high": 1, "critical": 2}

    def upgrade(current: str, target: str) -> str:
        return target if risk_order.get(target, 0) > risk_order.get(current, 0) else current

    result = current_risk

    # Critical triggers
    if spo2 is not None and spo2 < 88:
        result = "critical"
    if heart_rate is not None and heart_rate > 140:
        result = "critical"
    if consciousness is not None and consciousness.lower() in ("pain", "unresponsive"):
        result = "critical"
    if resp_rate is not None and resp_rate > 30:
        result = upgrade(result, "critical")

    # High triggers
    if spo2 is not None and spo2 < 94:
        result = upgrade(result, "high")
    if heart_rate is not None and heart_rate > 120:
        result = upgrade(result, "high")
    if consciousness is not None and consciousness.lower() == "verbal":
        result = upgrade(result, "high")
    if systolic_bp is not None and (systolic_bp < 90 or systolic_bp > 180):
        result = upgrade(result, "high")
    if resp_rate is not None and resp_rate > 24:
        result = upgrade(result, "high")

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _bounded(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return float(np.clip(value, lo, hi))


def run_structured_models(payload: IntakePayload) -> StructuredInferenceResult:
    """
    Run the full inference pipeline described in Section IV-B and IV-C.

    Steps:
      1.  Extract prehospital feature vector with clipping & missingness flags.
      2.  GBM (XGBoost + Platt calibration) predicts risk probability.
      3.  LR baseline predicts risk probability (scaled features).
      4.  Heuristic rule layer enforces safety floor on risk level.
      5.  SHAP local + global explanations.
      6.  LIME local explanation (secondary sanity-check).
      7.  Construct clinical recommendations from top SHAP features.
    """
    bundle = _get_bundle()
    fv = payload_to_feature_vector(payload).reshape(1, -1)

    # ---- Model predictions ---------------------------------------------------
    gbm_prob = float(bundle.gbm.predict_proba(fv)[0, 1])
    lr_prob  = float(bundle.lr.predict_proba(bundle.scaler.transform(fv))[0, 1])

    # Cardiac risk score: GBM raw probability normalised to 0-10 scale
    cardiac_risk_score = _bounded(gbm_prob * 10, 0, 10)

    # Survival probability (paper metric)
    survival_probability = _bounded(1.0 - gbm_prob)

    # Initial risk level from GBM threshold
    # Thresholds calibrated against balanced 40/60 cohort:
    # >= 0.65 → critical, 0.35–0.65 → high, < 0.35 → guarded
    if gbm_prob >= 0.65:
        risk_level = "critical"
    elif gbm_prob >= 0.35:
        risk_level = "high"
    else:
        risk_level = "guarded"

    # Apply heuristic rule guardrail (Section IV-B)
    risk_level = _apply_heuristic_rules(
        spo2=payload.vitals.spo2,
        heart_rate=payload.vitals.heart_rate,
        current_risk=risk_level,
        consciousness=payload.vitals.consciousness_level,
        systolic_bp=payload.vitals.blood_pressure_systolic,
        resp_rate=payload.vitals.respiratory_rate,
    )

    # ---- SHAP local explanation ----------------------------------------------
    raw_shap_2d = bundle.gbm_explainer.shap_values(fv)   # shape (1, n_features)
    if isinstance(raw_shap_2d, list):
        raw_shap_2d = raw_shap_2d[1]
    raw_shap = raw_shap_2d[0]                             # shape (n_features,)
    shap_local_b64 = _shap_local_plot(raw_shap, fv[0])

    # ---- SHAP global (population) explanation --------------------------------
    shap_global_b64 = _shap_global_plot(bundle)

    # ---- LIME local explanation (secondary) ----------------------------------
    lime_b64 = _lime_local_plot(bundle, fv[0])

    # ---- Top SHAP features for text recommendations --------------------------
    top_idx  = np.argsort(np.abs(raw_shap))[::-1][:5]
    top_feats = [
        {"feature": FEATURE_NAMES[i], "shap_value": round(float(raw_shap[i]), 4)}
        for i in top_idx
    ]

    # ---- Build clinical recommendations from SHAP drivers --------------------
    recommendations = _build_xai_recommendations(top_feats, risk_level, payload)

    return StructuredInferenceResult(
        risk_level=risk_level,
        survival_probability=round(survival_probability, 3),
        cardiac_risk_score=round(cardiac_risk_score, 2),
        recommendations=recommendations,
        shap_local_plot_b64=shap_local_b64,
        shap_global_plot_b64=shap_global_b64,
        lime_local_plot_b64=lime_b64,
        lr_survival_probability=round(_bounded(1.0 - lr_prob), 3),
        top_shap_features=top_feats,
    )


# ---------------------------------------------------------------------------
# XAI-driven recommendations
# ---------------------------------------------------------------------------

_FEATURE_RECS: Dict[str, Recommendation] = {
    "spo2": Recommendation(
        title="Hypoxia Alert (SHAP)",
        detail="SpO₂ is a top risk driver. Titrate oxygen to maintain SpO₂ ≥ 94%; prepare high-flow equipment and airway adjuncts.",
    ),
    "heart_rate": Recommendation(
        title="Tachycardia Alert (SHAP)",
        detail="Heart rate is a major contributor to elevated risk. Prepare cardiac monitoring and 12-lead ECG on arrival.",
    ),
    "systolic_bp": Recommendation(
        title="Hypotension Alert (SHAP)",
        detail="Systolic BP is driving risk upward. Prepare IV access, fluid resuscitation, and vasopressor readiness.",
    ),
    "consciousness_numeric": Recommendation(
        title="Altered Consciousness (SHAP)",
        detail="Reduced consciousness level detected as a significant risk factor. Prepare rapid neuro assessment and airway protection.",
    ),
    "has_chest_pain": Recommendation(
        title="ACS Pathway (SHAP)",
        detail="Chest pain is a significant predictor. Activate cath-lab pathway, prepare antiplatelet therapy, troponin kits.",
    ),
    "has_dyspnea": Recommendation(
        title="Respiratory Bundle (SHAP)",
        detail="Dyspnoea is flagged as a risk contributor. Set up BiPAP/CPAP, bronchodilators, and airway adjuncts.",
    ),
    "has_trauma": Recommendation(
        title="Trauma Readiness (SHAP)",
        detail="Trauma indicator is a significant predictor. Notify surgery, prep blood products and imaging suite.",
    ),
    "age": Recommendation(
        title="Age-Related Risk (SHAP)",
        detail="Patient age is contributing to elevated risk. Ensure geriatric or paediatric protocols are available as appropriate.",
    ),
}

_FALLBACK_RECS = [
    Recommendation(
        title="Airway & Oxygenation",
        detail="Ensure airway patency and titrate oxygen to keep SpO₂ above 94%.",
    ),
    Recommendation(
        title="Cardiac Monitoring",
        detail="Prepare 12-lead ECG on arrival and continue telemetry monitoring.",
    ),
]


def _build_xai_recommendations(
    top_feats: List[Dict],
    risk_level: str,
    payload: IntakePayload,
) -> List[Recommendation]:
    """Map top SHAP features to clinically actionable recommendations."""
    recs: List[Recommendation] = []
    seen = set()
    for feat_info in top_feats:
        fname = feat_info["feature"]
        if fname in _FEATURE_RECS and fname not in seen:
            recs.append(_FEATURE_RECS[fname])
            seen.add(fname)

    if not recs:
        recs = _FALLBACK_RECS.copy()

    # Always add ventilation note if ventilator in use
    if payload.oxygen_support and "vent" in payload.oxygen_support.lower():
        recs.append(
            Recommendation(
                title="Ventilation Hand-off",
                detail="Coordinate with respiratory therapy for ventilator hand-off on arrival.",
            )
        )

    return recs