# 🎓 AI Academic Project Mentor (AAPM)
> *"Your Intelligent AI Guide from Project Idea to Final Submission"An enterprise-grade, agentic AI platform built strictly according to the **Infosys Capstone Lecture Specification**. It streamlines academic project guidance by orchestrating multiple specialized AI agents to generate feasibility blueprints, track 8-week milestones, and provide supervisor dashboards with real-time mentorship.

---

## 🏗️ Architecture & Specialized AI Agents

```
                     Student / Faculty Login
                                │
                ┌──────────────┴──────────────┐
                ▼                             ▼
        [Student Portal]              [Faculty Portal]
                │                             │
    Project Idea (2-3 lines)         Monitor All Teams
                │                    Review Blueprints
                ▼                    Add Supervisor Remarks
       AI Orchestrator (Groq)
                │
   ┌────────────┼────────────┬────────────┬────────────┬────────────┐
   ▼            ▼            ▼            ▼            ▼            ▼
Idea         Scope         Tech       Timeline       Risk     Documentation
Agent        Agent         Stack       Planning     Agent         Agent
                           Agent        Agent                     (UML & SRS)
   └────────────┬────────────┴────────────┴────────────┴────────────┘
                ▼
      Master Mentor Synthesis (Executive Report & Project Blueprint)
                │
        ┌───────┴────────┐
        ▼                ▼
8-Week Progress    Conversational AI Mentor
Tracking Agent     (Text + Mic / Audio Speech)
```

### 🤖 The 7 Core Specialist Agents:
1. **Idea Evaluation Agent:** Evaluates feasibility, innovation, academic capstone suitability, and estimated timeline.
2. **Scope Definition Agent:** Formulates objectives, top 5 core features, Functional (FR) and Non-Functional Requirements (NFR), and boundaries.
3. **Technology Recommendation Agent:** Recommends modern, cost-effective tech stack (Frontend, Backend, AI/LLM, Database, Cloud Deployment).
4. **Timeline Planning Agent:** Formulates an 8-Phase Academic Execution Roadmap from problem formulation to thesis submission.
5. **Risk Assessment Agent:** Dedicated detection of dataset unavailability, API cost/limits, and deployment failures with actionable mitigations.
6. **Documentation Agent:** Generates formal Abstract, Synopsis, Literature Survey, PPT Presentation outline, and **Mermaid.js System Architecture diagrams**.
7. **Progress Tracking Agent:** Evaluates weekly student task updates against phase milestones, assigns an academic score (0-100), and provides actionable next steps.

---

## ✨ Key Features

- **⚡ 5x Faster Parallel Inference:** Executes specialist agents concurrently via Groq's high-speed inference engine (`ThreadPoolExecutor`).
- **👥 Role-Based Authentication & Supervisor Pairing:** Clean Student and Faculty portals powered by PostgreSQL or SQLite (`mentor.db`) with assigned faculty mentors.
- **👨‍🏫 Official University Grading Rubric:** Supervisors assign official internal marks across Implementation (35 pts), SRS/Architecture (25 pts), Testing (20 pts), and Project Quality (20 pts).
- **🎓 Verifiable Milestone Sign-off:** Faculty can grant official phase approvals and sign-offs with timestamps.
- **📋 Mandatory Supervisor Directives:** Guides set actionable requirement checklists directly visible on student dashboards.
- **👥 Capstone Team Rosters & Roll Numbers:** Support for multi-student teams with roll numbers, automatically embedded into formal reports.
- **💻 Deep AI Code Audit & Progress Engine:** Students submit working code files or snippets; the AI audits code quality, security, provides refactored code snippets, and updates completion percentage.
- **💬 Interactive AI Mentor with Mic & Speech:** Conversational pair-programming assistant aware of the project's exact stack, supporting text chat, microphone voice input (Groq Whisper), and natural voice audio playback.
- **📄 1-Click Academic Export:** Download complete formal Academic Reports as formatted **Word Documents (`.docx`)** with official Supervisor Endorsement Certificates, or Markdown (`.md`).

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Python 3.10+ is installed and environment dependencies are available:
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Set your Groq API key in `.env`:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 3. Launch the Application
```bash
streamlit run app.py
```

---

## 🔑 Pre-Seeded Demo Accounts

You can use the **1-Click Demo Login** buttons on the login screen or enter the credentials below:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **👨‍🎓 Student** | `student1` | `student123` | Create blueprints, submit progress, chat with mentor |
| **👨‍🏫 Faculty** | `faculty1` | `faculty123` | Monitor student teams, view logs, submit supervisor feedback |

*(New accounts can also be created instantly using the **Create Account** tab).*

---

## 🐳 Docker & PostgreSQL Production Deployment

### 1. One-Click Launch with Docker Compose
To run both the **PostgreSQL 16 database** and the **Streamlit Web Application** in isolated Docker containers:

```bash
# 1. Set your Groq API Key
export GROQ_API_KEY="your_groq_api_key_here"   # On Linux/macOS
$env:GROQ_API_KEY="your_groq_api_key_here"      # On Windows PowerShell

# 2. Build and run containers
docker compose up --build
```
Your application will be live at `http://localhost:8501` backed by a persistent PostgreSQL database on port `5432`!

### 2. Standalone Cloud PostgreSQL (Neon / Supabase / Railway)
If you prefer a hosted PostgreSQL instance without running a local database container:
1. Create a database on [Neon.tech](https://neon.tech) or [Supabase.com](https://supabase.com).
2. Add your connection URL to `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@ep-xyz.neon.tech/neondb?sslmode=require
   ```
3. Run the migration script to transfer all existing records from local SQLite to PostgreSQL:
   ```bash
   python migrate_to_postgres.py
   ```
4. Start the app:
   ```bash
   streamlit run app.py
   ```
The app will automatically detect PostgreSQL and use it as its primary database!
