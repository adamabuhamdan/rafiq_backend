# Rafiq Backend (رفيق)

Rafiq is an AI-powered clinical assistant designed to support patients with chronic diseases (Diabetes, Hypertension, etc.) by providing real-time clinical guidance, medication scheduling, and health tracking.

## 🚀 Key Features

*   **Multi-Agent Clinical Brain**: A specialized system that routes medical queries to expert agents (Diabetes, BP, Glands) and synthesizes a unified response.
*   **Intelligent Medication Scheduling**: Automatically generates optimal schedules based on the patient's circadian rhythm (wake/sleep times).
*   **OCR Prescription Scanning**: Uses Gemini Vision to extract medications from prescription photos.
*   **Drug-Drug Interaction Check**: Checks for potential clinical conflicts between medications.
*   **Automated Health Reporting**: Generates weekly clinical reports for doctors and families.
*   **Background Monitoring**: A background scheduler that detects missed doses and pings services to ensure high availability.

---

## 🧠 Architecture: Multi-Agent Orchestration

Rafiq is powered by a sophisticated multi-agent clinical brain designed to provide specialized, accurate, and empathetic medical guidance. The system follows an **Orchestrate-Specialize-Synthesize** pattern:

### 1. The Orchestrator (Router)
The **Orchestrator** is the entry point for every patient message. It performs the following critical tasks:
*   **Intent Classification**: Analyzes the patient's message in real-time to detect multiple medical intents (e.g., "My sugar is high and I feel dizzy").
*   **Parallel Execution**: If multiple intents are detected, it triggers the relevant specialized agents simultaneously to ensure fast response times.
*   **Context Injection**: It retrieves the patient's specific medical history (diseases, wake/sleep times) from Supabase and passes it to the specialists.

### 2. Specialized Clinical Agents
Each agent is a specialist in its domain, equipped with specific medical prompts and logic:
*   **Diabetes Agent**: Monitors glucose levels and provides guidance on hypoglycemia/hyperglycemia.
*   **Blood Pressure (BP) Agent**: Analyzes systolic/diastolic trends and provides advice on hypertension management.
*   **Glands (Endocrine) Agent**: Specializes in thyroid and hormonal balance advice.
*   **Pharmacy Agent**: A functional expert that scans prescriptions via OCR, detects interactions, and generates medication schedules.

### 3. The Synthesizer
When multiple specialists provide advice, the **Synthesizer** merges their outputs. It ensures:
*   **Coherence**: The response flows naturally and doesn't feel like disjointed messages.
*   **Conflict Resolution**: It ensures advice from one specialist doesn't contradict another.
*   **Tone Matching**: Maintains a consistent, supportive personality.

---

## 🛠️ Setup & Installation

### 1. Environment Preparation
Ensure you have Python 3.10+ installed.

```bash
# Create a virtual environment
python -m venv venv

# Activate on Windows
source venv/Scripts/activate
# OR on Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory and add your credentials:

```env
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
```

### 3. Running the Server
Run the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 Technology Stack

*   **Backend Framework**: FastAPI (Asynchronous)
*   **AI Engine**: Google Gemini 2.0 Flash / Pro
*   **Database & Auth**: Supabase (PostgreSQL)
*   **Vector Database**: Qdrant (Clinical Context)
*   **Scheduler**: APScheduler (Background tasks)

---

*Rafiq: Your intelligent clinical companion, always by your side.*