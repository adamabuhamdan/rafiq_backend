# Rafiq — AI-Powered Clinical Companion 🩺

> **"Your intelligent companion, always by your side."**

Rafiq (Arabic: رفيق, meaning *companion*) is a smart healthcare backend that acts as a **personal clinical assistant** for patients living with chronic diseases such as Diabetes, Hypertension, and Endocrine disorders. Rather than replacing doctors, Rafiq bridges the gap between clinical visits — offering real-time guidance, automated medication management, and proactive health monitoring around the clock.

---

## 🌟 The Problem Rafiq Solves

Patients with chronic conditions face a silent daily struggle:

- **Between appointments**, they have no one to ask when symptoms arise.
- **Medication schedules** are complex, easy to forget, and hard to optimize.
- **Paper prescriptions** get lost or misread.
- **Missed doses** and drug interactions go undetected until they cause harm.
- **Doctors and families** lack real-time visibility into a patient's health trends.

Rafiq addresses all of these gaps in a single, cohesive AI-driven system.

---

## 🚀 Core Features

| Feature | Description |
|---|---|
| 🧠 **Multi-Agent Clinical Brain** | Routes patient queries to specialist AI agents (Diabetes, BP, Endocrine) and synthesizes a unified, coherent response. |
| 💊 **Intelligent Medication Scheduling** | Generates personalized, conflict-free medication schedules based on the patient's wake/sleep times and medication types. |
| 📸 **OCR Prescription Scanning** | Uses Gemini Vision to extract medication names, doses, and frequencies from prescription photos. |
| ⚠️ **Drug-Drug Interaction Check** | Automatically detects potentially dangerous interactions between a patient's current medications. |
| 📋 **Automated Health Reporting** | Generates structured weekly clinical summaries for sharing with doctors and family members. |
| ⏰ **Background Monitoring** | A persistent scheduler that detects missed doses and keeps all cloud services alive. |
| 🔐 **Secure Authentication** | JWT-based auth integrated with Supabase for secure, stateless sessions. |

---

## 🧠 Architecture: Multi-Agent Orchestration

Rafiq's intelligence is built on an **Orchestrate → Specialize → Synthesize** pattern:

```
Patient Message
      │
      ▼
┌─────────────────────┐
│   Orchestrator      │  ← Classifies intent, retrieves medical history
└─────────────────────┘
      │
      ├─────────────────────┬──────────────────────┐
      ▼                     ▼                      ▼
┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐
│ Diabetes     │   │  Blood Pressure  │   │  Glands/Endo.   │
│ Agent        │   │  Agent           │   │  Agent          │
└──────────────┘   └──────────────────┘   └─────────────────┘
      │                     │                      │
      └─────────────────────┴──────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   Synthesizer    │  ← Merges responses, resolves conflicts
                  └──────────────────┘
                            │
                            ▼
                    Unified Response
```

### 1. 🎯 Orchestrator
The single entry point for all patient messages. It:
- Classifies medical **intent** from natural language (e.g., "My sugar is 280 and I feel dizzy")
- Detects **multiple intents** in a single message
- Executes relevant specialist agents **in parallel** for fast responses
- Injects the patient's **full medical context** (diseases, vitals, medications)

### 2. 🩺 Specialist Clinical Agents

| Agent | Domain |
|---|---|
| **Diabetes Agent** | Blood glucose monitoring, hypo/hyperglycemia guidance |
| **Blood Pressure Agent** | Systolic/diastolic trend analysis, hypertension management |
| **Glands (Endocrine) Agent** | Thyroid function, hormonal balance advice |
| **Pharmacy Agent** | Prescription OCR, interaction checks, schedule generation |

### 3. 🔗 Synthesizer
When multiple agents respond, the Synthesizer merges their outputs into:
- A **coherent, non-contradictory** clinical response
- A **consistent, empathetic** tone
- A single message — not a list of disjointed agent outputs

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/signup` | Register a new patient account |
| `POST` | `/api/v1/auth/login` | Authenticate and receive a JWT |
| `GET` | `/api/v1/patients/me` | Retrieve current patient's medical profile |
| `POST` | `/api/v1/patients/` | Create a new patient profile |
| `PATCH` | `/api/v1/patients/` | Update an existing patient profile |
| `POST` | `/api/v1/chat/` | Send a message to the clinical AI brain |
| `POST` | `/api/v1/pharmacy/scan` | Scan a prescription image via OCR |
| `GET` | `/api/v1/pharmacy/medications` | List all of a patient's medications |
| `POST` | `/api/v1/pharmacy/medications` | Add a new medication |
| `DELETE` | `/api/v1/pharmacy/medications/{id}` | Remove a medication |
| `POST` | `/api/v1/pharmacy/schedule` | Generate an AI-optimized medication schedule |
| `POST` | `/api/v1/pharmacy/interactions` | Check for drug-drug interactions |
| `GET` | `/api/v1/reports/weekly` | Generate a weekly health summary report |
| `GET` | `/api/v1/settings/` | Retrieve user notification/app settings |
| `PATCH` | `/api/v1/settings/` | Update user settings |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | FastAPI (fully async) |
| **AI Engine** | Google Gemini 2.5 Flash |
| **Database & Auth** | Supabase (PostgreSQL + JWT) |
| **Vector Database** | Qdrant (clinical context & semantic memory) |
| **Background Scheduler** | APScheduler |
| **Deployment** | Railway (via Procfile + Uvicorn) |
| **Language** | Python 3.10+ |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- A [Supabase](https://supabase.com/) project with auth enabled
- A [Qdrant](https://qdrant.tech/) cluster (cloud or local)
- A [Google AI Studio](https://aistudio.google.com/) API key (Gemini)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/rafiq_backend.git
cd rafiq_backend

# Create a virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux / macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

```env
# .env
GEMINI_API_KEY=your_google_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
```

### 3. Run the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs (Swagger UI) at `http://localhost:8000/docs`.

---

## 🚀 Deployment (Railway)

The project includes a `Procfile` for one-click deployment on [Railway](https://railway.app/):

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Simply connect your GitHub repository to a new Railway project, add your environment variables in the Railway dashboard, and deploy.

---

## 📁 Project Structure

```
rafiq_backend/
├── app/
│   ├── agents/
│   │   ├── clinical/           # Specialist AI agents (Diabetes, BP, Glands)
│   │   ├── functional/         # Pharmacy & utility agents
│   │   ├── tools/              # Shared agent tools
│   │   └── orchestrator.py     # Main multi-agent router & synthesizer
│   ├── api/
│   │   └── routes/             # FastAPI route handlers
│   │       ├── auth.py
│   │       ├── chat.py
│   │       ├── patient.py
│   │       ├── pharmacy.py
│   │       ├── reports.py
│   │       └── settings.py
│   ├── core/                   # Config, security, background scheduler
│   ├── db/                     # Supabase & Qdrant client setup
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business logic layer
│   └── main.py                 # FastAPI app entry point
├── .env.example
├── Procfile
└── requirements.txt
```

---

## 🔒 Security Notes

- All endpoints (except `/auth/signup` and `/auth/login`) require a valid **JWT Bearer token** in the `Authorization` header.
- Tokens are issued and verified by Supabase Auth.
- Sensitive keys are never committed — use `.env` locally and Railway's secret manager in production.

---

*Rafiq — Built to be the clinical companion every chronic patient deserves.*