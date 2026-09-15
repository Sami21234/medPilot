# MedPilot - System Architecture & Design
 
**Personalized Disease Prediction & Medicine Recommendation System**
Two-role clinical workflow: Patient submits symptoms → AI predicts → Doctor validates → Final result released.
 
---
 
## 1. Actors & Core Principle
 
| Actor | Role |
|---|---|
| **Patient** | Submits symptoms, views their case status and final (doctor-validated) result |
| **Doctor** | Logs in, reviews AI predictions queued for review, confirms or overrides the diagnosis |
| **(Future) Admin** | Manages doctor verification, system oversight - not in initial scope |
 
**Core principle: AI proposes, doctor disposes.** The model's prediction is never shown to the patient as final - it enters a `pending` state until a doctor confirms or overrides it. This is a human-in-the-loop design, standard practice for any clinical decision-support tool, and it's also what makes this defensible: the AI is an assistant, not an unsupervised diagnostician.
 
---
 
## 2. High-Level Design (HLD)
 
### 2.1 Component Diagram (textual)
 
```
┌─────────────────┐     ┌──────────────────┐
│  Patient Portal │     │  Doctor Portal   │
│(submit symptoms,│     │ (review queue,   │
│   view results) │     │  validate/edit)  │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └──────────┬────────────┘
                    │ HTTPS / REST API
                    ▼
         ┌───────────────────────┐
         │   Flask Backend API   │
         │  ┌─────────────────┐  │
         │  │  Auth & RBAC    │  │
         │  ├─────────────────┤  │
         │  │  Case Management│  │
         │  ├─────────────────┤  │
         │  │  ML Inference   │  │
         │  └─────────────────┘  │
         └───────────┬───────────┘
                     │
      ┌──────────────┼────────────────┐
      ▼              ▼               ▼
┌───────────┐  ┌─────────────┐  ┌───────────────┐
│  Database │  │Trained Model│  │ Reference Data│
│ (users,   │  │(.pkl/.joblib)│ │ (disease info,│
│  cases)   │  │             │  │  meds, diets) │
└───────────┘  └─────────────┘  └───────────────┘
```
 
### 2.2 Data Flow
 
1. Patient registers/logs in → submits a symptom checklist
2. Backend validates input, passes symptoms to the ML inference module
3. Model returns a predicted disease + confidence score
4. A **Case** record is created with status `pending_review` - patient sees "submitted, awaiting doctor review," not the raw prediction
5. Doctor portal lists all `pending_review` cases, ranked by submission time
6. Doctor opens a case, sees the AI's prediction + confidence + the patient's raw symptoms, and either **confirms** or **overrides** with their own diagnosis
7. Case status becomes `validated`; the disease's medication/diet/precaution/workout info is attached and released to the patient
8. Patient views the final, doctor-validated result
### 2.3 Why this shape
 
- Separating "predict" from "release to patient" is what makes the doctor's validation meaningful rather than decorative
- Reference data (descriptions, medications, diets, precautions, workouts) is static and small (41 diseases) - no need for a live lookup service, just a well-indexed table
---
 
## 3. Low-Level Design (LLD)
 
### 3.1 Database Schema
 
```
users
  id (PK)
  name
  email (unique)
  password_hash
  role            -- 'patient' | 'doctor'
  created_at
 
doctors                          patients
  user_id (PK, FK -> users.id)     user_id (PK, FK -> users.id)
  specialization                   age
  license_number                   gender
  is_verified (bool)
 
diseases
  id (PK)
  name (unique, normalized)
  description
 
medications / diets / precautions / workouts
  id (PK)
  disease_id (FK -> diseases.id)
  content
 
symptoms
  id (PK)
  name (unique, normalized)
  severity_weight        -- from Symptom-severity.csv
 
cases
  id (PK)
  patient_id (FK -> users.id)
  symptoms_submitted      -- JSON array of symptom names/ids
  predicted_disease_id (FK -> diseases.id)
  confidence_score
  status                  -- 'pending_review' | 'validated' | 'rejected'
  doctor_id (FK -> users.id, nullable until validated)
  doctor_notes
  final_disease_id (FK -> diseases.id, nullable - set on validation)
  created_at
  validated_at
```
 
**Why a separate `final_disease_id` from `predicted_disease_id`:** preserves an audit trail. If a doctor overrides the AI, both the original prediction and the doctor's final call are kept - this is important for later measuring how often the AI and doctor agree, which is a genuinely useful metric for this project (a form of model validation against expert judgment).
 
### 3.2 API Endpoints
 
| Endpoint | Method | Actor | Purpose |
|---|---|---|---|
| `/api/auth/register` | POST | Both | Create account (role selected at signup) |
| `/api/auth/login` | POST | Both | Returns session/JWT token |
| `/api/patient/predict` | POST | Patient | Submit symptoms → creates a `pending_review` case |
| `/api/patient/cases/<id>` | GET | Patient | View own case status/result |
| `/api/doctor/cases?status=pending_review` | GET | Doctor | List cases awaiting review |
| `/api/doctor/cases/<id>/validate` | POST | Doctor | Confirm or override prediction, moves case to `validated` |
| `/api/diseases/<id>` | GET | Both | Disease description, medication, diet, precaution, workout info |
 
### 3.3 Module Structure
 
```
src/
  auth.py            -- signup/login, password hashing, session/JWT, role-check decorators
  models.py           -- ORM models matching the schema above
  ml_service.py        -- loads model once at startup, exposes predict(symptoms) -> (disease, confidence)
  routes/
    patient.py
    doctor.py
    disease_info.py
  data_prep.py          -- cleaning + normalization
  train.py              -- model training
```
 
### 3.4 Sequence: Patient Submission → Doctor Validation
 
```
Patient          Backend API        ML Service        Database         Doctor
  |--submit symptoms-->|                 |                |               |
  |                     |--predict()---->|                |               |
  |                     |<--disease,conf-|                |               |
  |                     |--create Case (status=pending)--->|               |
  |<--"submitted, pending review"--------|                |               |
  |                     |                |                |<--fetch pending cases--|
  |                     |                |                |--case list--->|
  |                     |                |                |<--validate(case_id, decision)--|
  |                     |--update Case (status=validated)->|               |
  |<--final result available--------------------------------|              |
```
 
---
 
## 3.5 NLP - Symptom Extraction from Free Text
 
**Feature**: patients can type symptoms in their own words ("bad cough, really tired, chest feels tight") instead of only selecting from a 132-item checklist. A lightweight NLP layer maps free text to the structured symptom set the model actually requires.
 
**Approach**: keyword/phrase matching against the known 132 symptom names (plus common synonyms - e.g., "tired" → `fatigue`, "chest tight" → `chest_pain`), rather than a heavyweight custom NLP model - appropriately sized for this dataset, consistent with Section 5's scaling philosophy (right-sized, not maximal).
 
**Where it lives**: `src/nlp_symptom_extraction.py`, called before `ml_service.predict()` in the patient submission flow.
 
## 3.6 Dashboard & Reporting (Doctor-Facing)
 
Per the mentor's spec's "Dashboard & Reporting" section, applied to this domain:
- **Case queue view**: pending cases awaiting review, sortable by submission time
- **AI/doctor agreement rate**: percentage of cases where the doctor confirmed vs. overrode the AI's prediction - a genuinely meaningful validation metric for this specific project, not available in the original spec's e-commerce framing
- **Disease frequency trends**: which diseases are most commonly predicted/confirmed over time
## 3.7 Model Candidates (evaluated honestly, not preselected)
 
Per the mentor's "AI & Machine Learning Models" section, the following go into the model comparison once we reach the training step - the winner is whichever actually performs best on held-out data, not decided in advance:
- Logistic Regression (simple baseline)
- Random Forest
- Gradient Boosting (e.g. HistGradientBoosting)
- A small Neural Network (per the spec's deep-learning mention) - included and evaluated fairly; tree-based models often win on small tabular binary-feature data like this, and if so, that result gets reported honestly rather than forced toward deep learning
## 3.8 Optional Stretch Goals (not required for core system)
 
- **Graph-based**: a symptom–disease association graph as an explainability visual on the doctor portal ("here's why the model predicted this")
- **Feedback loop (RL-adjacent)**: doctor overrides logged and periodically used to retrain/re-evaluate the model - a legitimate "learns from feedback" story without claiming true reinforcement learning
---
 
## 4. Security & Access Control
 
- **Password hashing**: bcrypt/werkzeug, never plaintext
- **Role-based access control**: every route explicitly checks `role == 'doctor'` or `role == 'patient'`; a patient token can never reach a doctor endpoint, enforced server-side (not just hidden in the UI)
- **Doctor verification**: doctor accounts should require a license number field, flagged `is_verified = False` until manually approved - prevents anyone from self-registering as a doctor and validating cases
- **Audit trail**: every case retains who validated it and when, plus both the AI's original prediction and the doctor's final call, never overwritten
- **Data sensitivity**: this is health data - even as a student project, treat patient records as sensitive; don't log raw symptom submissions in plaintext application logs
---
 
## 5. Scaling Considerations - Ideal vs. What We'll Actually Build
 
Being honest about this split matters more than listing buzzwords. Here's the ideal architecture for real traffic, and what's actually appropriate for this project's real scope and timeline:
 
| Concern | Ideal (large-scale production) | What we'll actually build |
|---|---|---|
| **Database** | PostgreSQL with read replicas | SQLite for development; PostgreSQL if actually deployed, since it's still free-tier friendly (Render/Railway) |
| **Model serving** | Separate inference microservice, horizontally scaled | Model loaded once at Flask app startup, in-process - genuinely sufficient at this traffic scale |
| **Caching** | Redis for reference data (disease info) | Not needed yet - 41 diseases is small enough to query directly with proper indexing; flagged as a future optimization if traffic grows |
| **Async processing** | Celery + message queue if inference is slow | Not needed - this model's inference is near-instant (small tabular model, not deep learning), so synchronous request/response is fine |
| **Load balancing** | Multiple app instances behind a load balancer | Single instance is fine for this project's real scope; documented as the first thing to add if usage genuinely grew |
| **Rate limiting** | API gateway-level throttling | Flask-Limiter, a lightweight in-app rate limiter - reasonable given the smaller scope |
| **Monitoring** | Prometheus/Grafana, centralized logging | Basic application logging - enough for a project at this stage |
 
**The honest takeaway:** the "textbook" scaling answer (microservices, message queues, Kubernetes) would be over-engineering for a project like this, the same way the fabricated-metrics dashboard we flagged earlier was over-engineering for FORESIGHT. The right architecture is one that's correctly *sized* to the actual problem, not the most impressive-sounding one. It's genuinely good practice to know what the scaled-up version would look like (this table) while building the version that's actually appropriate now.
 
---
 
## 6. Non-Functional Requirements
 
- **Latency**: prediction should return in well under 1 second - trivial for a tabular symptom-based model, no special engineering needed
- **Availability**: not mission-critical infrastructure; standard single-instance uptime is acceptable for a student project
- **Consistency**: a case's status transition (`pending_review` → `validated`) must be atomic - no state where a case appears validated without a doctor's decision recorded
- **Auditability**: every diagnosis validation must be traceable to a specific doctor and timestamp
---
 
## 7. Tech Stack (finalized)
 
| Layer | Choice |
|---|---|
| Backend | Flask |
| Database | SQLite (dev) → PostgreSQL (if deployed) |
| ORM | SQLAlchemy |
| Auth | Flask-Login (session-based) or JWT via Flask-JWT-Extended |
| ML | scikit-learn (model TBD after evaluation) |
| Frontend | HTML/CSS/JS (custom-built) |
| Deployment | Render |
 
---
 
## 8. What This Changes About Our Build Order
 
Given this design, the build order becomes:
1. Data cleaning (already started) → feature/target finalization
2. Model training + evaluation (accuracy, precision/recall/F1, confusion matrix)
3. Database schema implementation (`models.py`)
4. Auth (signup/login, role-based)
5. Patient submission flow → case creation
6. Doctor review/validation flow
7. Disease info attachment (medications/diets/precautions/workouts) on validation
8. Frontend (custom UI, both portals)
9. Deployment