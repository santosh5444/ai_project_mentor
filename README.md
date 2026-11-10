# 🎓 AI Academic Project Mentor (AAPM)
> *"Your Intelligent AI Guide from Project Idea to Final Submission"*

An enterprise-grade, agentic AI platform built strictly according to the **Infosys Capstone Lecture Specification**. It streamlines academic project guidance by orchestrating multiple specialized AI agents to generate feasibility blueprints, track 8-week milestones, conduct mock viva examinations, and provide supervisor dashboards.

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
      Master Mentor Synthesis (Executive Report & Viva Voce Guide)
                │
        ┌───────┴────────┐
        ▼                ▼
8-Week Progress    Conversational
Tracking Agent     AI Mentor (Q&A)
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
- **👥 Role-Based Authentication & Supervisor Pairing:** Clean Student and Faculty portals powered by a local SQLite database (`mentor.db`) with assigned faculty mentors.
- **👨‍🏫 Official University Grading Rubric:** Supervisors assign official internal marks across Implementation (35 pts), SRS/Architecture (25 pts), Testing (20 pts), and Viva readiness (20 pts).
- **🎓 Verifiable Milestone Sign-off & Viva Clearance:** Faculty can grant official phase approvals and viva clearances with timestamps.
- **📋 Mandatory Supervisor Directives:** Guides set actionable requirement checklists directly visible on student dashboards.
- **👥 Capstone Team Rosters & Roll Numbers:** Support for multi-student teams with roll numbers, automatically embedded into formal reports.
- **💻 Deep AI Code Audit & Progress Engine:** Students submit working code files or snippets; the AI audits code quality, security, provides refactored code snippets, and updates completion percentage.
- **🧪 Automated Unit Test Generator (Pytest):** Generates ready-to-run `test_suite.py` test cases, boundary checks, and error assertions for submitted student code.
- **🎓 External Examiner Mock Viva Simulator:** Simulates a 5-question university viva voce defense, scores technical answers (1-10), and issues a verifiable Viva Readiness Certificate.
- **💬 Interactive AI Mentor:** Conversational assistant aware of the project's exact stack, offering real-time architecture, debugging, and milestone coaching.
- **📄 1-Click Multi-Format Academic Export:** Download complete formal Academic Reports as formatted **Word Documents (`.docx`)** with official Supervisor Endorsement Certificates, **PowerPoint Presentation Decks (`.pptx`)**, or Markdown (`.md`).

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

*(New accounts can also be created instantly using the **New Registration** tab).*
