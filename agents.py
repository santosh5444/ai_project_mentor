import os
import re
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Primary and fallback models on Groq
PRIMARY_MODEL = "qwen/qwen3.8-27b"
FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"]

def get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key or not key.strip():
        raise ValueError("GROQ_API_KEY is not set in .env file!")
    return Groq(api_key=key.strip(), timeout=60.0, max_retries=3)

def ask_ai(prompt: str, client: Groq, max_tokens: int = 1500, temperature: float = 0.7, system_prompt: Optional[str] = None) -> str:
    """Executes completion with primary model and automatic fallback."""
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS
    last_error = None

    for model in models_to_try:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
            content = chat_completion.choices[0].message.content or ""
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Groq model attempts failed. Last error: {last_error}")

# =====================================================================
# 1. Idea Evaluation Agent (Infosys Req 1)
# =====================================================================
def idea_agent(project_idea: str, client: Groq) -> str:
    prompt = f"""
You are the AI Project Idea Evaluation Agent for university engineering/computer science capstones.

Student Project Idea:
"{project_idea}"

Provide a structured academic evaluation with the following exact sections:
### 1. Academic Suitability & Value
Explain why this project is suitable for an academic final-year or semester capstone. Highlight its academic rigor and relevance.

### 2. Core Problem & Beneficiaries
Define the core real-world problem being solved and the primary user personas who benefit.

### 3. Innovation & Unique Selling Proposition (USP)
Identify the innovative angles, architectural choices, or unique differentiator that will impress academic evaluators.

### 4. Feasibility & Assessment Scorecard
- **Feasibility:** High / Medium / Low (with justification)
- **Difficulty Level:** Beginner / Intermediate / Advanced
- **Innovation Level:** High / Medium / Low
- **Estimated Duration:** 6-8 Weeks
- **Recommendation:** Proceed with project / Refine scope

### 5. Evaluator First Impressions
Summary of how an external academic viva examiner would perceive this topic.
"""
    return ask_ai(prompt, client, max_tokens=1200)

# =====================================================================
# 2. Scope Definition Agent (Infosys Req 2)
# =====================================================================
def scope_agent(project_idea: str, client: Groq) -> str:
    prompt = f"""
You are the AI Project Scope Definition Agent.

Student Project Idea:
"{project_idea}"

Define the comprehensive academic scope:
### 1. Primary Objectives
State 3-4 clear, measurable objectives the system must achieve.

### 2. Top 5 Core Features
Provide detailed technical descriptions for the 5 essential functional features.

### 3. Functional Requirements (FR)
Bullet list of user interactions, system inputs, processing logic, and expected outputs.

### 4. Non-Functional Requirements (NFR)
Bullet points for Performance, Latency, Security, Scalability, and Usability.

### 5. Project Boundaries (Out of Scope)
Explicitly list 3-4 items that should intentionally NOT be built within the college timeline to prevent scope creep.

### 6. Tangible Deliverables
List of required academic deliverables (Working prototype, SRS document, Source repository, Test suite, Final presentation).
"""
    return ask_ai(prompt, client, max_tokens=1200)

# =====================================================================
# 3. Technology Recommendation Agent (Infosys Req 3)
# =====================================================================
def technology_agent(project_idea: str, client: Groq) -> str:
    prompt = f"""
You are the AI Technology Recommendation Agent.

Student Project Idea:
"{project_idea}"

Recommend a modern, industry-standard, yet student-friendly tech stack. For each category, state the recommended technology and explain WHY it was chosen:

### 1. Frontend / User Interface
Recommended framework (e.g. Streamlit for fast ML UI, React/Next.js for web apps, Flutter for mobile) and justification.

### 2. Backend API Framework
Recommended framework (e.g. FastAPI, Flask, Django, Node.js/Express) and justification.

### 3. AI / Machine Learning / LLM Frameworks
Recommended libraries (e.g. Groq SDK, LangChain, Hugging Face, PyTorch, Scikit-learn, OpenCV) and justification.

### 4. Database & Vector Storage
Recommended database (e.g. SQLite / PostgreSQL for relational data; ChromaDB / FAISS / Pinecone for vector embeddings) and justification.

### 5. Deployment & Containerization
Recommended tools (e.g. Docker, Render, Hugging Face Spaces, Streamlit Community Cloud) with free tier availability.

### 6. Development Tools & Libraries
List of essential supporting Python packages or utilities.
"""
    return ask_ai(prompt, client, max_tokens=1200)

# =====================================================================
# 4. Timeline Planning Agent (Infosys Req 4 - 8 Academic Phases)
# =====================================================================
def timeline_agent(project_idea: str, client: Groq) -> str:
    prompt = f"""
You are the AI Timeline Planning Agent.

Student Project Idea:
"{project_idea}"

Create a detailed, actionable 8-Phase Academic Execution Roadmap (corresponding to the standard 8-week university capstone cycle):

### 📅 Phase 1: Problem Identification & Literature Survey (Week 1)
- Key research papers, problem formulation, and feasibility signoff.

### 📅 Phase 2: Requirement Gathering & SRS Specification (Week 2)
- Functional/Non-functional requirement documentation, user stories, and use-case matrix.

### 📅 Phase 3: System Architecture & UML Design (Week 3)
- Architectural diagram, database schema (ERD), API endpoints, and sequence diagrams.

### 📅 Phase 4: Core Backend & AI/ML Pipeline Setup (Week 4)
- Model integration, data preprocessing, API routes, and core business logic.

### 📅 Phase 5: Frontend Integration & UI Development (Week 5)
- UI screens, connecting frontend to backend APIs, and state management.

### 📅 Phase 6: System Testing & Performance Validation (Week 6)
- Unit tests, model accuracy evaluation, edge-case handling, and bug fixes.

### 📅 Phase 7: Deployment & Containerization (Week 7)
- Dockerfile creation, cloud deployment, and live demonstration readiness.

### 📅 Phase 8: Project Documentation, PPT & Viva Voce Prep (Week 8)
- Final thesis report compiling, slide deck preparation, and mock defense practice.
"""
    return ask_ai(prompt, client, max_tokens=1300)

# =====================================================================
# 5. Risk Assessment Agent (Infosys Req 5 - Dedicated Risk Agent)
# =====================================================================
def risk_agent(project_idea: str, client: Groq) -> str:
    prompt = f"""
You are the AI Project Risk Assessment Agent.

Student Project Idea:
"{project_idea}"

Analyze project risks and provide concrete, actionable mitigations based on academic project realities:

### ⚠️ Risk 1: Dataset Unavailability & Quality Issues
- **Potential Risk:** Specific challenges regarding data collection, size, or labeling for this project.
- **Actionable Solution:** Specific Kaggle datasets, synthetic data generation, open APIs, or public repositories to use.

### ⚠️ Risk 2: API Rate Limits & Cloud Costs
- **Potential Risk:** Exceeding paid LLM/cloud allowances or API throttling during live evaluation.
- **Actionable Solution:** Use of free-tier providers (Groq, Hugging Face free inference, Ollama local fallbacks), token caching, and prompt optimization.

### ⚠️ Risk 3: Deployment & Live Demo Failures
- **Potential Risk:** Application crashing during final faculty viva or viva room Wi-Fi issues.
- **Actionable Solution:** Docker containerization, local fallback video demo, and pre-cached offline sample responses.

### ⚠️ Risk 4: Scope Creep & Deadline Overrun
- **Potential Risk:** Over-promising features leading to an incomplete deliverable.
- **Actionable Solution:** Strict MVP (Minimum Viable Product) prioritization guidelines.
"""
    return ask_ai(prompt, client, max_tokens=1200)

# =====================================================================
# 6. Documentation Agent (Infosys Req 6 - Abstract, UML, PPT, Manual)
# =====================================================================
def documentation_agent(project_idea: str, client: Groq) -> str:
    prompt = f"""
You are the AI Academic Documentation Agent.

Student Project Idea:
"{project_idea}"

Generate a complete academic documentation blueprint:

### 1. Ready-to-Use Formal Abstract (120-150 words)
Write a publication-ready academic abstract covering Background, Problem, Proposed Methodology, and Expected Outcomes.

### 2. Formal Project Synopsis
A 2-paragraph formal synopsis suitable for initial department proposal approval.

### 3. Literature Survey Outline
List 3 key domain methodologies or landmark algorithms relevant to this topic with brief comparative analysis.

### 4. System Architecture Diagram (Mermaid.js Code)
Provide a VALID Mermaid.js diagram enclosed strictly in ```mermaid ... ``` code fences showing the data flow from Student/User -> Frontend -> Backend/API -> AI Agent / Model -> Database / Output.
Keep node names alphanumeric without parentheses to ensure valid syntax.

### 5. 10-Slide Academic PPT Outline
List Slide 1 to 10 titles and 2 bullet points for each slide for the final Viva Voce presentation.

### 6. User Manual & Verification Checklist
Step-by-step setup guide for external examiners to run the project.
"""
    return ask_ai(prompt, client, max_tokens=1500)

# =====================================================================
# 7. Master Mentor Synthesis Agent
# =====================================================================
def mentor_agent(project_idea: str, idea: str, scope: str, technology: str, planning: str, risks: str, documentation: str, client: Groq) -> str:
    prompt = f"""
You are the Lead Academic Project Mentor synthesizing all specialist agent reports.

Project Idea: "{project_idea}"

--- SPECIALIST AGENT SUMMARIES ---
[Idea Assessment]: {idea[:450]}
[Scope Definition]: {scope[:450]}
[Tech Stack]: {technology[:450]}
[Timeline Planning]: {planning[:450]}
[Risk Assessment]: {risks[:450]}
[Documentation Summary]: {documentation[:450]}

--- TASK ---
Provide a Master Mentor Evaluation with the following sections:

### 🏆 1. Executive Evaluation & Potential Academic Score
- Overall Feasibility Score: XX / 100
- Innovation Rating: XX / 100
- Mentor Summary Verdict.

### 🎯 2. Approved Architecture & Core Milestones
A 3-bullet synthesis of the recommended system architecture and MVP definition.

### ❓ 3. Viva Voce Q&A Preparation (Top 5 Tough Examiner Questions)
Provide 5 high-yield technical questions university examiners ask for this topic, along with ideal, high-scoring answers.

### 💡 4. Top 3 Golden Rules for Final Project Success
Practical advice for the student team to score an 'A' grade.
"""
    return ask_ai(prompt, client, max_tokens=1500)

# =====================================================================
# 8. Parallel Orchestration Pipeline (Runs 1-6 in parallel, then 7)
# =====================================================================
def run_project_mentor_pipeline(project_idea: str, progress_callback=None) -> Dict[str, Any]:
    """Runs specialist agents in parallel using ThreadPoolExecutor for 5x speedup."""
    client = get_groq_client()
    results = {}

    if progress_callback:
        progress_callback("⚡ Orchestrating 5 Specialist Agents in parallel via Groq...", 0.20)

    # Run agents 1 to 6 concurrently
    tasks = {
        "idea": lambda: idea_agent(project_idea, client),
        "scope": lambda: scope_agent(project_idea, client),
        "technology": lambda: technology_agent(project_idea, client),
        "planning": lambda: timeline_agent(project_idea, client),
        "risks": lambda: risk_agent(project_idea, client),
        "documentation": lambda: documentation_agent(project_idea, client),
    }

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_agent = {executor.submit(fn): name for name, fn in tasks.items()}
        completed_count = 0
        total_tasks = len(tasks)

        for future in as_completed(future_to_agent):
            agent_name = future_to_agent[future]
            try:
                results[agent_name] = future.result()
            except Exception as e:
                results[agent_name] = f"Error generating {agent_name} section: {str(e)}"
            completed_count += 1
            if progress_callback:
                progress_callback(
                    f"✅ Completed {completed_count}/{total_tasks}: {agent_name.capitalize()} Agent finished",
                    0.20 + (0.55 * (completed_count / total_tasks))
                )

    if progress_callback:
        progress_callback("🏆 Master Mentor Agent: Synthesizing full blueprint & Viva Voce guide...", 0.85)

    results["mentor_report"] = mentor_agent(
        project_idea=project_idea,
        idea=results.get("idea", ""),
        scope=results.get("scope", ""),
        technology=results.get("technology", ""),
        planning=results.get("planning", ""),
        risks=results.get("risks", ""),
        documentation=results.get("documentation", ""),
        client=client
    )

    if progress_callback:
        progress_callback("🎉 Complete Academic Project Blueprint successfully generated!", 1.0)

    return results

# =====================================================================
# 9. AI Code Audit & Progress Tracking Agent (Infosys Req 7 - Advanced)
# =====================================================================
def progress_tracking_agent(
    project_title: str,
    project_idea: str,
    week_number: int,
    phase_name: str,
    tasks_completed: str,
    submitted_code: str = "",
    code_language: str = "python",
    blockers: str = "",
    github_link: str = "",
    client: Optional[Groq] = None
) -> Dict[str, Any]:
    """Evaluates student's weekly progress and performs deep code audit against academic milestone deliverables."""
    if client is None:
        client = get_groq_client()

    has_code = bool(submitted_code and submitted_code.strip())
    code_section = f"""
STUDENT SUBMITTED CODE ({code_language.upper()}):
```{code_language}
{submitted_code[:4000]}
```
""" if has_code else "STUDENT SUBMITTED CODE: [No code submitted for this week - evaluated on task summary only]"

    prompt = f"""
You are the Senior Academic Project Evaluator and Technical Code Auditor.

PROJECT SPECIFICATION:
- Title: "{project_title}"
- Idea Statement: "{project_idea}"

WEEKLY SUBMISSION DETAILS:
- Week Number: {week_number} of 8
- Academic Phase: {phase_name}
- Student Task Summary:
{tasks_completed}
- Blockers / Challenges Reported:
{blockers if blockers else "None reported"}
- Repository Link:
{github_link if github_link else "Not submitted"}

{code_section}

--- EVALUATION TASK ---
Perform a rigorous academic and technical evaluation. Provide your review structured in two main parts:

## PART A: MILESTONE PROGRESS EVALUATION
### 1. Milestone Verification Status
[VERIFIED & COMPLIANT / PARTIALLY MET / REVISION REQUIRED]
Explain whether the tasks and deliverables fulfill the academic requirements for Week {week_number} ({phase_name}).

### 2. Academic Score Breakdown
- **Deliverables Completeness (0-40):** XX/40
- **Code Hygiene & Architecture (0-25):** XX/25
- **Error Handling & Robustness (0-20):** XX/20
- **Documentation & Comments (0-15):** XX/15
- **TOTAL PERFORMANCE SCORE:** XX / 100

### 3. Key Mentor Recommendations & Next Week Deliverables
3 clear technical tasks the student must deliver next.

## PART B: DEEP CODE AUDIT & VIVA DEFENSE
### 1. Code Quality & Modularity Analysis
Evaluate function design, separation of concerns, and clean coding standards.

### 2. Security & Edge Case Vulnerabilities
Identify any potential pitfalls (e.g. unhandled exceptions, exposed secrets, missing input validation).

### 3. Recommended Code Refactoring
Provide a concise, production-ready refactored code snippet showing how the student can optimize their implementation.

### 4. Technical Viva Voce Defense Question
Provide 1 tough technical question an external examiner would ask regarding this specific code/module, along with the ideal answer.

---
At the very end of your response, output two single lines in this exact format:
SCORE: <integer 0-100>
PERCENT: <integer 0-100 total project completion>
"""
    response_text = ask_ai(prompt, client, max_tokens=1500)

    # Separate Part A and Part B for clean UI display
    part_a = response_text
    part_b = ""
    if "## PART B:" in response_text:
        splits = response_text.split("## PART B:")
        part_a = splits[0].strip()
        part_b = "## PART B:" + splits[1].strip()

    # Parse numeric score and percent
    score = 82
    percent = min(100, week_number * 12 + 10)

    score_match = re.search(r"SCORE:\s*(\d+)", response_text)
    if score_match:
        try:
            score = max(0, min(100, int(score_match.group(1))))
        except Exception:
            pass

    percent_match = re.search(r"PERCENT:\s*(\d+)", response_text)
    if percent_match:
        try:
            percent = max(0, min(100, int(percent_match.group(1))))
        except Exception:
            pass

    return {
        "feedback": part_a,
        "code_audit": part_b,
        "full_text": response_text,
        "score": score,
        "percent": percent
    }

# =====================================================================
# 10. Conversational AI Mentor Assistant
# =====================================================================
def conversational_mentor_agent(project_context: str, chat_history: List[Dict[str, str]], user_message: str, client: Optional[Groq] = None) -> str:
    """Provides interactive mentorship, code advice, and viva defense coaching."""
    if client is None:
        client = get_groq_client()

    system_prompt = f"""
You are the AI Academic Project Mentor (AAPM), an encouraging yet academically rigorous university project advisor.
You are mentoring a student on their engineering project.

PROJECT CONTEXT:
{project_context}

YOUR ROLE:
- Give concise, clear, and technically sound advice.
- If the student asks for coding help, provide clean, modular Python/tech code snippets.
- If asked about viva voce, conduct mock Q&A with constructive feedback.
- Keep the student motivated and focused on meeting their deadlines.
"""
    # Build history context
    history_str = ""
    for msg in chat_history[-6:]:
        history_str += f"{msg['role'].capitalize()}: {msg['content']}\n"

    prompt = f"""
Chat History:
{history_str}

Student: {user_message}

AI Mentor:"""

    return ask_ai(prompt, client, max_tokens=1000, system_prompt=system_prompt)

# =====================================================================
# 11. Interactive Voice Viva Voce Defense Simulator Agents
# =====================================================================

def transcribe_audio_groq(audio_bytes: bytes, filename: str = "recording.wav", client: Optional[Groq] = None) -> str:
    """Transcribes student spoken audio using Groq's high-speed Whisper model."""
    if client is None:
        client = get_groq_client()
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes, "audio/wav"),
            model="whisper-large-v3-turbo",
            response_format="json",
            temperature=0.0
        )
        return transcription.text.strip()
    except Exception:
        # Fallback to standard whisper-large-v3
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes, "audio/wav"),
            model="whisper-large-v3",
            response_format="json"
        )
        return transcription.text.strip()

