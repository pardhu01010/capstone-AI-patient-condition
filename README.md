# Patient Condition Prediction & AI Hospital Command Center

An advanced, real-time AI triage and predictive modeling system designed to bridge the gap between prehospital emergency care (ambulances) and hospital command centers. This system transmits patient telemetry, analyzes it on the fly using structured machine learning models (XGBoost) and semantic search (Qdrant), and presents actionable, AI-driven recommendations directly to medical staff.

---

## 🎯 Project Overview

This project simulates a next-generation emergency medical pipeline. It consists of a dual-frontend architecture connected to a powerful Python/FastAPI backend:

1. **Ambulance UI:** A field-ready interface used by paramedics to log patient vitals, symptoms, administered medications, and upload ECGs/injury photos. Features a 3D ambulance visualization to signify real-time connectivity.
2. **Hospital Command Dashboard:** A high-tech, real-time monitoring center for hospital staff. As soon as an ambulance transmits data, the dashboard instantly updates with AI-generated risk levels, survival probabilities, and specific hospital preparation protocols.
3. **AI Backend:** A robust processing engine that calculates risk scores using XGBoost, generates model explainability charts using SHAP/LIME, retrieves contextual hospital protocols using Qdrant (Semantic Search / RAG), and compiles a natural language summary using Groq LLMs.

---

## 📸 Screenshots

| Ambulance UI (Field Interface) | Hospital Command Dashboard |
| :---: | :---: |
| <img src="docs/ambulance_ui.png" width="400" alt="Ambulance UI Screenshot" /> <br> *(Hint: Save your screenshot as `docs/ambulance_ui.png` or replace this link)* | <img src="docs/hospital_ui.png" width="400" alt="Hospital UI Screenshot" /> <br> *(Hint: Save your screenshot as `docs/hospital_ui.png` or replace this link)* |

---

## 🚀 Tech Stack

### Backend
- **Framework:** FastAPI (Python)
- **Machine Learning:** Scikit-Learn, XGBoost, SHAP, LIME
- **Vector Database (RAG):** Qdrant (FastEmbed for embeddings)
- **Database ORM:** Prisma Client Python
- **Database Provider:** PostgreSQL (Supabase)
- **LLM Integration:** Groq API (Mixtral) with Langfuse telemetry

### Frontends
- **Framework:** React 19 + Vite (TypeScript)
- **Styling & Animations:** Vanilla CSS, GSAP (GreenSock)
- **3D Rendering (Ambulance UI):** Three.js, React Three Fiber, React Three Drei
- **Data Visualization (Hospital UI):** Recharts
- **Icons:** Lucide React
- **Network:** Axios

---

## 📂 File Structure

```
Patient_Condition_Prediction/
│
├── apps/                        # Frontend Monorepo
│   ├── ambulance_ui/            # Field-interface for Paramedics
│   │   ├── src/pages/           # Main views (Ambulance form)
│   │   ├── package.json         # React + Three.js dependencies
│   │   └── ...
│   └── hospital_ui/             # Command Center for Hospital Staff
│       ├── src/pages/           # Real-time dashboard view
│       ├── package.json         # React + Recharts dependencies
│       └── ...
│
├── backend/                     # AI & API Engine
│   ├── data/                    # Datasets for model training/inference
│   ├── services/                # Core AI logic
│   │   ├── inference.py         # XGBoost & SHAP Explainability
│   │   ├── llm.py               # Groq summary generation
│   │   ├── medication.py        # Rule-based medication plans
│   │   └── rag.py               # Qdrant Semantic Search
│   ├── main.py                  # FastAPI router and entrypoint
│   ├── schemas.py               # Pydantic data models
│   └── storage.py               # Prisma database operations
│
├── schema.prisma                # Database schema for Supabase
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Production Python dependencies
└── .env                         # Environment variables
```

---

## ⚙️ Key Features

- **Real-Time Transmission:** Data submitted from the Ambulance UI instantly appears on the Hospital Dashboard.
- **Predictive Risk Modeling:** Uses an XGBoost Gradient Boosting Machine to calculate a 0-100% survival probability and cardiac risk score.
- **Explainable AI (XAI):** Generates SHAP beeswarm/waterfall plots and LIME surrogates on the backend, ensuring medical staff can trust and interpret the AI's reasoning.
- **Retrieval-Augmented Generation (RAG):** Uses FastEmbed and Qdrant to semantically search a library of hospital protocols based on the patient's symptoms, offering tailored preparation steps (e.g., "Activate Cath Lab").
- **Cloud-Ready Architecture:** Designed for deployment on Render (Backend) and Vercel (Frontends) with thread-pooled AI tasks to prevent event-loop blocking on serverless/free-tier infrastructure.

---

## 🛠️ Local Setup & Installation

### 1. Database Setup (Supabase)
Create a PostgreSQL database on Supabase and retrieve the Connection String and Direct URL.
Create a `.env` file in the root directory:
```env
SUPABASE_DATABASE_URL="postgresql://user:password@aws-0-region.pooler.supabase.com:6543/postgres?pgbouncer=true"
DIRECT_URL="postgresql://user:password@aws-0-region.pooler.supabase.com:5432/postgres"
GROQ_API_KEY="your-groq-key"
```

### 2. Backend Initialization
Make sure you have Python 3.10+ installed.
```bash
# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Generate Prisma Client
prisma generate

# Push schema to Supabase
prisma db push

# Start the FastAPI server
uv run uvicorn backend.main:app --reload
```

### 3. Frontend Initialization
You will need Node.js installed. Open two new terminal tabs.

**Terminal 1 (Ambulance UI):**
```bash
cd apps/ambulance_ui
npm install
npm run dev
```

**Terminal 2 (Hospital UI):**
```bash
cd apps/hospital_ui
npm install
npm run dev
```

---

## ☁️ Deployment Notes

- **Backend (Render):** Set `PRISMA_BINARY_CACHE_DIR=/opt/render/project/src/.prisma-binary` to prevent binary deletion during build phases. Use `pip install -r requirements.txt && prisma py fetch && prisma generate` for the Build Command.
- **Frontend (Vercel):** Ensure `VITE_API_URL` is set to the live backend URL in the Vercel Environment Variables.
