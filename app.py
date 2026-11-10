import streamlit as st
import streamlit.components.v1 as components
import json
import re
import importlib
from datetime import datetime

import database
from database import (
    authenticate_user, register_user, get_faculty_users,
    save_project, delete_project, update_project_faculty,
    get_student_projects, get_student_project_list, get_all_projects_for_faculty, get_project_by_id,
    update_project_progress, update_faculty_feedback,
    update_faculty_evaluation, update_project_team,
    add_progress_log, update_progress_log_faculty_review, get_progress_logs,
    add_chat_message, get_chat_messages
)

import agents
from agents import (
    run_project_mentor_pipeline,
    progress_tracking_agent,
    conversational_mentor_agent,
    generate_pytest_suite,
    viva_defense_simulator
)

import export_utils
from export_utils import (
    generate_docx_report,
    generate_markdown_report,
    generate_pptx_deck
)

# =====================================================================
# Page Configuration & Clean Styling
# =====================================================================
st.set_page_config(
    page_title="AI Academic Project Mentor (AAPM)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif !important;
        letter-spacing: -0.01em;
    }
    
    /* Clean Main Container */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1240px !important;
    }
    
    /* Modern SaaS Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #2563EB 100%) !important;
        border-radius: 16px !important;
        padding: 2rem 2.2rem !important;
        color: #FFFFFF !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 12px 30px -6px rgba(30, 58, 138, 0.28) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        position: relative;
        overflow: hidden;
    }

    /* Auth Card Container */
    .auth-card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 20px !important;
        padding: 2.2rem !important;
        box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04) !important;
        border-top: 4px solid #2563EB !important;
    }

    /* Demo Profile Cards */
    .demo-profile-card {
        background: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 12px 14px !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    .demo-profile-card:hover {
        background: #EFF6FF !important;
        border-color: #93C5FD !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.1) !important;
    }
    
    /* Modern Elevated Content Card */
    .clean-card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 14px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 4px 12px 0 rgba(0, 0, 0, 0.02) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    .clean-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 10px 20px -3px rgba(0, 0, 0, 0.04) !important;
    }
    
    /* Modern Metric KPI Card */
    .kpi-card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 1.15rem 1.25rem !important;
        text-align: center !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
    }
    .kpi-card:hover {
        transform: translateY(-2px) !important;
        border-color: #CBD5E1 !important;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06) !important;
    }
    .kpi-val {
        font-size: 1.75rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        line-height: 1.2 !important;
        margin-top: 4px !important;
        letter-spacing: -0.02em !important;
    }
    .kpi-lbl {
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    /* Status Badges */
    .badge-approved {
        background-color: #ECFDF5 !important;
        color: #047857 !important;
        border: 1px solid #A7F3D0 !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-review {
        background-color: #FEFCE8 !important;
        color: #A16207 !important;
        border: 1px solid #FEF08A !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-revision {
        background-color: #FEF2F2 !important;
        color: #B91C1C !important;
        border: 1px solid #FECACA !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-progress {
        background-color: #EFF6FF !important;
        color: #1D4ED8 !important;
        border: 1px solid #BFDBFE !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    /* Buttons Overhaul */
    button[kind="primary"] {
        background: linear-gradient(135deg, #1E40AF 0%, #2563EB 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        border-radius: 10px !important;
        padding: 0.55rem 1.3rem !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35) !important;
    }
    button[kind="secondary"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        border-color: #CBD5E1 !important;
        background: #F8FAFC !important;
        color: #0F172A !important;
    }

    /* Modern Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #F1F5F9 !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 4px !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: #64748B !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0F172A !important;
        background: rgba(255, 255, 255, 0.5) !important;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #1E40AF !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    }

    /* Input & Textarea Elements */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        font-size: 0.92rem !important;
        transition: all 0.15s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        margin-bottom: 0.75rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
    }

    /* Sidebar Navigation Menu Buttons */
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 9px 14px !important;
        border-radius: 10px !important;
        margin-bottom: 4px !important;
        transition: all 0.15s ease-in-out !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background-color: #EFF6FF !important;
        border-color: #BFDBFE !important;
        color: #1D4ED8 !important;
        transform: translateX(2px) !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background: linear-gradient(135deg, #1E40AF 0%, #2563EB 100%) !important;
        border: 1px solid #1D4ED8 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 9px 14px !important;
        border-radius: 10px !important;
        margin-bottom: 4px !important;
        box-shadow: 0 3px 8px rgba(37, 99, 235, 0.3) !important;
    }

    /* Print Stylesheet */
    @media print {
        [data-testid="stSidebar"], header, .stDeployButton, footer, button, .stDownloadButton, [data-testid="stToolbar"] {
            display: none !important;
        }
        .main .block-container {
            padding: 10px !important;
            max-width: 100% !important;
        }
        .clean-card, .kpi-card, .hero-banner {
            border: 1px solid #94A3B8 !important;
            page-break-inside: avoid;
        }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# State Initialization
# =====================================================================
if "user" not in st.session_state:
    st.session_state["user"] = None

if "current_project_id" not in st.session_state:
    st.session_state["current_project_id"] = None

if "active_blueprint" not in st.session_state:
    st.session_state["active_blueprint"] = None

if "active_title" not in st.session_state:
    st.session_state["active_title"] = ""

def format_date(val) -> str:
    if not val:
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]

@st.cache_data(show_spinner=False)
def get_cached_docx(project_id, project_title, student_name, blueprint, team_members, faculty_name, faculty_feedback, faculty_score, sign_off_date):
    buf = generate_docx_report(
        project_title=project_title,
        student_name=student_name,
        blueprint=blueprint,
        team_members=team_members,
        faculty_name=faculty_name,
        faculty_feedback=faculty_feedback,
        faculty_score=faculty_score,
        sign_off_date=sign_off_date
    )
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def get_cached_pptx(project_id, project_title, student_name, blueprint, team_members, faculty_name):
    buf = generate_pptx_deck(
        project_title=project_title,
        student_name=student_name,
        blueprint=blueprint,
        team_members=team_members,
        faculty_name=faculty_name
    )
    return buf.getvalue()

def extract_mermaid_code(doc_text: str) -> str:
    match = re.search(r"```(?:mermaid)?\s*([\s\S]*?)```", doc_text)
    if match:
        code = match.group(1).strip()
        if any(kw in code for kw in ["graph", "sequenceDiagram", "flowchart", "classDiagram"]):
            return code
    return """graph TD
    User[Student / User] --> Frontend[Streamlit Web App]
    Frontend --> Controller[FastAPI Orchestrator]
    Controller --> Agents[AI Specialist Agents]
    Agents --> DB[(SQLite / Vector Store)]
    Agents --> Result[Academic Deliverables & Code Audit]"""

def render_mermaid(mermaid_code: str, height: int = 420):
    """Renders a responsive visual Mermaid.js flowchart in Streamlit using CDN."""
    cleaned_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
    if not any(kw in cleaned_code for kw in ["graph", "flowchart", "sequenceDiagram", "classDiagram"]):
        cleaned_code = """graph TD
    User[Student / User] --> Frontend[Streamlit Web App]
    Frontend --> Controller[FastAPI Orchestrator]
    Controller --> Agents[AI Specialist Agents]
    Agents --> DB[(SQLite / Vector Store)]
    Agents --> Result[Academic Deliverables & Code Audit]"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 15px;
                background-color: #FAFAFA;
                border-radius: 8px;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            .mermaid {{
                width: 100%;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
{cleaned_code}
        </div>
        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'neutral',
                flowchart: {{ useMaxWidth: true, htmlLabels: true, curve: 'basis' }}
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_content, height=height, scrolling=True)

def get_status_badge(status: str) -> str:
    s = (status or "In Progress").strip()
    if "Approved" in s:
        return f'<span class="badge-approved">✅ {s}</span>'
    elif "Review" in s:
        return f'<span class="badge-review">⏳ {s}</span>'
    elif "Revision" in s:
        return f'<span class="badge-revision">⚠️ {s}</span>'
    return f'<span class="badge-progress">🔵 {s}</span>'

# Standard 8 Academic Phases
PHASES = [
    (1, "Phase 1: Problem Identification & Literature Survey"),
    (2, "Phase 2: Requirement Gathering & SRS Specification"),
    (3, "Phase 3: System Architecture & UML Design"),
    (4, "Phase 4: Core Backend & AI/ML Pipeline Setup"),
    (5, "Phase 5: Frontend Integration & UI Development"),
    (6, "Phase 6: System Testing & Performance Validation"),
    (7, "Phase 7: Deployment & Containerization"),
    (8, "Phase 8: Project Documentation, PPT & Viva Voce Prep")
]

# =====================================================================
# AUTHENTICATION SCREEN (Modern SaaS Design System)
# =====================================================================
def render_auth_screen():
    st.write("")
    c_space1, c_main, c_space2 = st.columns([1, 2.3, 1])

    with c_main:
        # High-end Hero Header
        st.markdown("""
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-flex; align-items: center; gap: 6px; background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; font-size: 0.78rem; font-weight: 700; padding: 4px 14px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                ✨ Infosys Internship Capstone Edition • Multi-Agent Architecture
            </div>
            <h1 style="font-size: 2.1rem; font-weight: 800; color: #0F172A; margin: 0 0 8px 0; letter-spacing: -0.03em;">
                AI Academic Project Mentor
            </h1>
            <p style="color: #64748B; font-size: 0.95rem; margin: 0 auto; max-width: 540px; line-height: 1.5;">
                Autonomous project scoping, real-time code auditing, automated Pytest generation, and university viva voce preparation.
            </p>
        </div>
        """, unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "📝 Register New Account"])
        with auth_tab1:
            st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
            uname = st.text_input("Username or Email", key="auth_uname", placeholder="e.g. student1 or aarav@college.edu")
            pwd = st.text_input("Password", type="password", key="auth_pwd", placeholder="••••••••")
            if st.button("Sign In to Workspace", type="primary", use_container_width=True):
                u = authenticate_user(uname, pwd)
                if u:
                    st.session_state["user"] = u
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with auth_tab2:
            st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
            fname = st.text_input("Full Name", placeholder="e.g. Priya Patel")
            r_uname = st.text_input("Choose Username", placeholder="e.g. priyap")
            r_email = st.text_input("College Email", placeholder="e.g. priya@college.edu")
            r_dept = st.selectbox("Department", [
                "Computer Science & Engineering",
                "Artificial Intelligence & Data Science",
                "Information Technology",
                "Software Systems"
            ])
            r_pwd = st.text_input("Password", type="password", placeholder="••••••••")
            r_role = st.selectbox("Role", ["student", "faculty"], format_func=lambda x: "👨‍🎓 Student" if x == "student" else "👨‍🏫 Faculty / Mentor")

            if st.button("Create Account & Access", type="primary", use_container_width=True):
                if not fname or not r_uname or not r_pwd:
                    st.warning("Please fill in required fields.")
                else:
                    ok = register_user(r_uname, r_pwd, r_role, fname, r_email, r_dept)
                    if ok:
                        st.success("Account created successfully! Please switch to the Sign In tab.")
                    else:
                        st.error("Username already taken.")

        # Trust / Capabilities Footer
        st.markdown("""
        <div style="margin-top: 26px; padding-top: 18px; border-top: 1px solid #E2E8F0;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; text-align: center; margin-bottom: 12px;">
                CAPSTONE ACADEMIC SUITE FEATURES
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 10px 12px; font-size: 0.8rem; color: #334155; font-weight: 600;">
                    🤖 <b>7 Specialized AI Agents</b><br/><span style="font-size:0.72rem; color:#64748B; font-weight:400;">Idea, Scope, Tech, Risks, Blueprint</span>
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 10px 12px; font-size: 0.8rem; color: #334155; font-weight: 600;">
                    🧪 <b>Auto Pytest Generation</b><br/><span style="font-size:0.72rem; color:#64748B; font-weight:400;">Unit test suites & boundary cases</span>
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 10px 12px; font-size: 0.8rem; color: #334155; font-weight: 600;">
                    🎓 <b>Mock Viva Voce Defense</b><br/><span style="font-size:0.72rem; color:#64748B; font-weight:400;">External examiner scoring & certificate</span>
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 10px 12px; font-size: 0.8rem; color: #334155; font-weight: 600;">
                    📄 <b>DOCX & Slides Export</b><br/><span style="font-size:0.72rem; color:#64748B; font-weight:400;">University report & PowerPoint deck</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# SIDEBAR (Global Project Switcher & Navigation)
# =====================================================================
def render_sidebar():
    user = st.session_state["user"]
    with st.sidebar:
        # Sleek User Profile Card
        role_badge = "STUDENT LEAD" if user["role"] == "student" else "FACULTY SUPERVISOR"
        role_bg = "#EFF6FF" if user["role"] == "student" else "#FEF3C7"
        role_color = "#1D4ED8" if user["role"] == "student" else "#92400E"
        role_border = "#BFDBFE" if user["role"] == "student" else "#FDE68A"
        avatar_char = "👨‍🎓" if user["role"] == "student" else "👨‍🏫"

        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px; margin-bottom: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="width:40px; height:40px; border-radius:50%; background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); display:flex; align-items:center; justify-content:center; font-size:1.3rem; box-shadow: 0 3px 8px rgba(37,99,235,0.25);">
                    {avatar_char}
                </div>
                <div style="flex:1; overflow:hidden;">
                    <div style="font-weight:700; color:#0F172A; font-size:0.92rem; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;">{user['full_name']}</div>
                    <div style="display:inline-block; margin-top:2px; font-size:0.68rem; font-weight:700; padding:2px 8px; border-radius:9999px; background:{role_bg}; color:{role_color}; border:1px solid {role_border}; letter-spacing:0.04em;">
                        {role_badge}
                    </div>
                </div>
            </div>
            <div style="margin-top:10px; font-size:0.75rem; color:#64748B; border-top:1px solid #F1F5F9; padding-top:8px;">
                🏛️ {user.get('department', 'Engineering')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if user["role"] == "student":
            # Global Project Switcher (Fast lightweight fetch)
            projects = get_student_project_list(user["id"])
            if projects:
                proj_map = {p["id"]: f"#{p['id']} - {p['title']}" for p in projects}
                ids = list(proj_map.keys())

                curr_id = st.session_state.get("current_project_id")
                if curr_id is None or curr_id not in ids:
                    curr_id = ids[0]
                    st.session_state["current_project_id"] = curr_id
                    st.session_state["active_project_data"] = None

                idx = ids.index(curr_id) if curr_id in ids else 0
                chosen = st.selectbox(
                    "📌 Active Project:",
                    options=ids,
                    index=idx,
                    format_func=lambda x: proj_map[x],
                    key="sidebar_proj_sel"
                )
                if chosen != st.session_state.get("current_project_id"):
                    st.session_state["current_project_id"] = chosen
                    st.session_state["active_project_data"] = None
                    st.rerun()

                # Single shared query per render cycle
                active_p = st.session_state.get("active_project_data")
                if not active_p or active_p.get("id") != st.session_state["current_project_id"]:
                    active_p = get_project_by_id(st.session_state["current_project_id"])
                    st.session_state["active_project_data"] = active_p

                if active_p:
                    st.session_state["active_blueprint"] = active_p.get("blueprint")
                    st.session_state["active_title"] = active_p.get("title")
                    if active_p.get("faculty_name"):
                        st.caption(f"👨‍🏫 Guide: **{active_p['faculty_name']}**")
            else:
                st.session_state["active_project_data"] = None
                st.info("No projects yet. Click 'New Project Proposal' below!")

            st.markdown("<div style='margin: 12px 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)
            nav_choice = st.radio(
                "Workspace Navigation:",
                [
                    "📌 Project Overview",
                    "📑 Blueprint & Specifications",
                    "💻 Code Submission & AI Audit",
                    "💬 Ask AI Mentor",
                    "➕ New Project Proposal"
                ],
                key="student_nav"
            )
            st.markdown("<div style='margin: 16px 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)
            if st.button("🚪 Sign Out", use_container_width=True):
                st.session_state["user"] = None
                st.session_state["current_project_id"] = None
                st.session_state["active_blueprint"] = None
                st.rerun()
            return nav_choice

        else:
            nav_choice = st.radio(
                "Faculty Navigation:",
                [
                    "👨‍🏫 My Assigned Student Teams",
                    "🏛️ Department Projects Registry"
                ],
                key="faculty_nav"
            )
            st.markdown("<div style='margin: 16px 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)
            if st.button("🚪 Sign Out", use_container_width=True):
                st.session_state["user"] = None
                st.session_state["current_project_id"] = None
                st.rerun()
            return nav_choice

# =====================================================================
# STUDENT PAGES
# =====================================================================

# 1. Project Overview & Milestones
def page_student_overview(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("No project active. Please click **'➕ New Project Proposal'** in the sidebar to start your first project!")
        return

    proj = st.session_state.get("active_project_data")
    if not proj or proj.get("id") != curr_id:
        proj = get_project_by_id(curr_id)
        st.session_state["active_project_data"] = proj

    if not proj:
        st.warning("Project not found.")
        return

    # Modern SaaS Hero Banner
    st.markdown(f"""
    <div class="hero-banner">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
            <div style="max-width: 780px;">
                <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25); padding:4px 12px; border-radius:9999px; font-size:0.75rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:10px;">
                    🎓 CAPSTONE PROJECT #{proj['id']} &nbsp;•&nbsp; 🔑 CODE: {proj.get('invite_code', 'PRJ')} &nbsp;•&nbsp; REGISTERED {format_date(proj.get('created_at'))}
                </div>
                <h1 style="color:#FFFFFF; font-size:1.85rem; font-weight:800; margin:0 0 8px 0; letter-spacing:-0.02em;">
                    {proj['title']}
                </h1>
                <p style="color:rgba(255,255,255,0.85); font-size:0.92rem; margin:0; line-height:1.45;">
                    {proj['project_idea']}
                </p>
            </div>
            <div style="text-align:right;">
                <div style="background:rgba(255,255,255,0.12); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.2); border-radius:12px; padding:12px 18px; display:inline-block; text-align:center;">
                    <div style="font-size:0.7rem; font-weight:700; color:rgba(255,255,255,0.75); text-transform:uppercase; letter-spacing:0.05em;">Milestone Progress</div>
                    <div style="font-size:1.75rem; font-weight:800; color:#FFFFFF;">{int(proj['progress_percent'])}%</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Current Milestone</div><div class="kpi-val">Phase {proj["current_phase"]}/8</div><div style="font-size:0.75rem; color:#64748B; margin-top:3px;">Academic Roadmap</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Total Completion</div><div class="kpi-val">{int(proj["progress_percent"])}%</div><div style="font-size:0.75rem; color:#10B981; margin-top:3px;">On Track</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Assigned Faculty</div><div style="font-size:1.05rem; font-weight:700; color:#1E3A8A; padding-top:6px;">{proj.get("faculty_name", "Unassigned")}</div><div style="font-size:0.75rem; color:#64748B; margin-top:3px;">{proj.get("faculty_dept", "Department Guide")}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Review Status</div><div style="padding-top:8px;">{get_status_badge(proj["status"])}</div><div style="font-size:0.75rem; color:#64748B; margin-top:5px;">University Standing</div></div>', unsafe_allow_html=True)

    st.write("")
    st.progress(float(proj["progress_percent"]) / 100.0)

    # 👨‍🏫 FACULTY SUPERVISOR DIRECTIVE & EVALUATION BOX
    st.markdown("#### 👨‍🏫 Faculty Guide Guidance & Evaluation")
    f_box_col1, f_box_col2 = st.columns([1.5, 1])

    with f_box_col1:
        if proj.get("sign_off_date"):
            st.success(f"🎓 **Official Viva Voce Clearance Granted!** Signed off on {proj['sign_off_date']} by {proj.get('faculty_name', 'Faculty Supervisor')}.")
        elif proj.get("status") == "Needs Revision":
            st.error("⚠️ **Code Revision Requested by Supervisor:** Please address the required action items below.")
        else:
            st.info(f"👨‍🏫 **Project Guide:** {proj.get('faculty_name', 'Faculty')} ({proj.get('faculty_dept', 'Engineering')})")

        if proj.get("faculty_feedback"):
            st.markdown(f"**Supervisor Remarks:**\n> {proj['faculty_feedback']}")

        if proj.get("supervisor_action_items"):
            st.markdown(f"**📋 Required Action Items Before Next Review:**\n{proj['supervisor_action_items']}")
        else:
            st.caption("No specific action items assigned by your guide yet.")

    with f_box_col2:
        if proj.get("faculty_score"):
            st.markdown(f"""
            <div class="kpi-card" style="border: 2px solid #10B981; background: #ECFDF5;">
                <div class="kpi-lbl">Official University Internal Score</div>
                <div class="kpi-val" style="color: #059669;">{proj['faculty_score']} / 100</div>
                <div style="font-size:0.8rem; color:#047857;">Graded by {proj.get('faculty_name', 'Guide')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="kpi-card">
                <div class="kpi-lbl">Internal Score</div>
                <div style="font-size:1.1rem; color:#64748B; padding-top:10px;">Pending Supervisor Grading</div>
            </div>
            """, unsafe_allow_html=True)

    # Capstone Team Members Section
    st.markdown("#### 👥 Capstone Project Team")
    curr_team = proj.get("team_members", user["full_name"])
    st.markdown(f"**Registered Team Members:** `{curr_team}`")
    with st.expander("✏️ Update Team Members & Roll Numbers"):
        with st.form("edit_team_form"):
            new_team = st.text_input("Team Members & Roll Numbers:", value=curr_team, placeholder="e.g. Aarav Sharma (21CS045), Sneha Reddy (21CS052)")
            if st.form_submit_button("Save Team Members"):
                update_project_team(proj["id"], new_team)
                st.success("Team roster updated! Will reflect on exported Word reports.")
                st.rerun()

    # Weekly Performance & Milestone Velocity Chart
    logs = get_progress_logs(proj["id"])
    st.markdown("#### 📈 Milestone Performance Velocity")
    
    scores_by_week = {i: None for i in range(1, 9)}
    for l in logs:
        w = l.get("week_number", 1)
        sc = l.get("ai_score", 0)
        if 1 <= w <= 8:
            scores_by_week[w] = sc

    chart_rows = []
    for i in range(1, 9):
        val = scores_by_week[i]
        if val is None and i < proj["current_phase"]:
            val = min(92, 70 + (i * 3))
        chart_rows.append({
            "Milestone": f"Week {i}",
            "Audit Score": val if val is not None else 0,
            "Passing Benchmark": 75
        })

    import pandas as pd
    v_df = pd.DataFrame(chart_rows).set_index("Milestone")
    st.line_chart(v_df[["Audit Score", "Passing Benchmark"]], color=["#1E3A8A", "#10B981"], height=230)
    st.caption("🔵 **Milestone Audit Score** &nbsp;|&nbsp; 🟢 **University Passing Benchmark (75 pts)**")

    # 8-Phase Progress Roadmap as Visual Stepper Grid
    st.markdown("#### 🗺️ 8-Phase Academic Execution Roadmap")
    roadmap_html = '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px; margin-top:10px; margin-bottom:20px;">'
    for p_num, p_name in PHASES:
        clean_pname = p_name.split(": ", 1)[-1]
        if p_num < proj["current_phase"]:
            roadmap_html += f'''
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:12px 14px; display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:0.75rem; font-weight:800; color:#15803D; background:#DCFCE7; padding:2px 8px; border-radius:6px;">PHASE {p_num}</span>
                    <span style="font-size:0.8rem; font-weight:700; color:#16A34A;">✅ Verified</span>
                </div>
                <div style="font-size:0.85rem; font-weight:600; color:#14532D;">{clean_pname}</div>
            </div>'''
        elif p_num == proj["current_phase"]:
            roadmap_html += f'''
            <div style="background:#EFF6FF; border:2px solid #3B82F6; border-radius:12px; padding:12px 14px; box-shadow:0 4px 12px rgba(59,130,246,0.15); display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:0.75rem; font-weight:800; color:#1D4ED8; background:#DBEAFE; padding:2px 8px; border-radius:6px;">PHASE {p_num}</span>
                    <span style="font-size:0.78rem; font-weight:700; color:#2563EB;">⚡ ACTIVE</span>
                </div>
                <div style="font-size:0.88rem; font-weight:700; color:#1E3A8A;">{clean_pname}</div>
            </div>'''
        else:
            roadmap_html += f'''
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:12px 14px; opacity:0.85; display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:0.75rem; font-weight:700; color:#64748B; background:#F1F5F9; padding:2px 8px; border-radius:6px;">PHASE {p_num}</span>
                    <span style="font-size:0.78rem; color:#94A3B8;">Upcoming</span>
                </div>
                <div style="font-size:0.85rem; font-weight:500; color:#475569;">{clean_pname}</div>
            </div>'''
    roadmap_html += '</div>'
    st.markdown(roadmap_html, unsafe_allow_html=True)

# 2. Blueprint & Specifications (Clean Document View, No 8 Nested Tabs!)
def page_student_blueprint(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("Please select or create a project first.")
        return

    proj = st.session_state.get("active_project_data")
    if not proj or proj.get("id") != curr_id:
        proj = get_project_by_id(curr_id)
        st.session_state["active_project_data"] = proj

    if not proj:
        st.warning("Project not found.")
        return

    bp = proj.get("blueprint", {})

    # Action Toolbar Header with 1-Click Downloads
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="font-size:0.75rem; font-weight:700; color:#2563EB; text-transform:uppercase; letter-spacing:0.06em;">COMPREHENSIVE ACADEMIC BLUEPRINT</div>
                <h2 style="margin:4px 0 0 0; color:#0F172A; font-size:1.6rem; font-weight:800;">{proj['title']}</h2>
                <div style="font-size:0.85rem; color:#64748B; margin-top:4px;">
                    👥 Team: <b>{proj.get('team_members', user['full_name'])}</b> &nbsp;|&nbsp; 👨‍🏫 Guide: <b>{proj.get('faculty_name', 'Faculty')}</b>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    h_col1, h_col2, h_col3 = st.columns(3)
    with h_col1:
        docx_data = get_cached_docx(
            proj["id"],
            proj["title"],
            user["full_name"],
            bp,
            proj.get("team_members", user["full_name"]),
            proj.get("faculty_name", "Department Guide"),
            proj.get("faculty_feedback", ""),
            proj.get("faculty_score"),
            proj.get("sign_off_date")
        )
        st.download_button(
            label="📄 Download Word Report (.docx)",
            data=docx_data,
            file_name=f"{proj['title'].replace(' ', '_')}_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    with h_col2:
        pptx_data = get_cached_pptx(
            proj["id"],
            proj["title"],
            user["full_name"],
            bp,
            proj.get("team_members", user["full_name"]),
            proj.get("faculty_name", "Department Guide")
        )
        st.download_button(
            label="📽️ Download Slides (.pptx)",
            data=pptx_data,
            file_name=f"{proj['title'].replace(' ', '_')}_Presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True
        )
    with h_col3:
        md_data = generate_markdown_report(proj["title"], user["full_name"], bp)
        st.download_button(
            label="📥 Download Markdown (.md)",
            data=md_data,
            file_name=f"{proj['title'].replace(' ', '_')}_Blueprint.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.divider()

    # Clean, Linear Document Sections
    with st.expander("🏆 1. Master Mentor Executive Report & Viva Guide", expanded=True):
        st.markdown(bp.get("mentor_report", "No report available."))

    with st.expander("💡 2. Idea Feasibility & Suitability Scorecard", expanded=False):
        st.markdown(bp.get("idea", "No evaluation available."))

    with st.expander("🎯 3. Project Scope, Objectives & Features", expanded=False):
        st.markdown(bp.get("scope", "No scope available."))

    with st.expander("💻 4. Recommended Technology Stack & Justifications", expanded=False):
        st.markdown(bp.get("technology", "No tech stack available."))

    with st.expander("📅 5. 8-Phase Academic Execution Timeline", expanded=False):
        st.markdown(bp.get("planning", "No timeline available."))

    with st.expander("🛡️ 6. Risk Assessment & Actionable Solutions", expanded=False):
        st.markdown(bp.get("risks", "No risk analysis available."))

    with st.expander("📄 7. Academic Documentation, Abstract & Synopsis", expanded=False):
        st.markdown(bp.get("documentation", "No documentation available."))

    with st.expander("📐 8. System Architecture Diagram (Visual Interactive)", expanded=True):
        mermaid_code = extract_mermaid_code(bp.get("documentation", ""))
        render_mermaid(mermaid_code, height=420)
        with st.expander("📝 View / Copy Mermaid.js Architecture Code", expanded=False):
            st.code(mermaid_code, language="mermaid")

# 3. Code Submission & AI Audit (Clean 2-Column Interface)
def page_student_code_audit(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("Please select or create a project first.")
        return

    proj = get_project_by_id(curr_id)
    if not proj:
        st.warning("Project not found.")
        return

    st.markdown(f"## 💻 Code Submission & AI Technical Audit")
    st.caption(f"Project: **{proj['title']}** • Currently on **Phase {proj['current_phase']}: {PHASES[proj['current_phase']-1][1]}**")

    col_submit, col_audit = st.columns([1.1, 1.2])

    with col_submit:
        st.markdown("#### 📝 Submit Code for Current Phase")
        with st.form("clean_code_submit_form"):
            s_week = st.number_input("Week Number:", min_value=1, max_value=8, value=proj["current_phase"])
            s_phase = st.selectbox("Milestone Phase:", [p[1] for p in PHASES], index=min(7, proj["current_phase"]-1))
            s_summary = st.text_area("Tasks Accomplished this Week:", placeholder="e.g. Built FastAPI routes, integrated Qwen model, connected ChromaDB.", height=100)
            
            s_lang = st.selectbox("Code Language:", ["python", "javascript", "sql", "html", "other"])
            s_file = st.file_uploader("Upload Code File (.py, .js, .sql, .html, .txt):", type=["py", "js", "sql", "html", "txt", "ipynb"])
            
            file_code = ""
            if s_file:
                try:
                    file_code = s_file.read().decode("utf-8")
                    st.info(f"Loaded: `{s_file.name}`")
                except Exception:
                    pass

            s_code = st.text_area("Or Paste Code Snippet Directly:", value=file_code, height=180, placeholder="# Paste your Python / JS / backend code here...")
            s_blockers = st.text_input("Challenges / Blockers Faced (Optional):", placeholder="e.g. Model inference latency is high.")
            s_github = st.text_input("GitHub Repo / Branch URL (Optional):", placeholder="https://github.com/user/project")

            btn_submit = st.form_submit_button("🚀 Run AI Code Audit & Update Progress", type="primary", use_container_width=True)

        if btn_submit:
            if not s_summary.strip():
                st.warning("Please summarize the tasks accomplished.")
            else:
                with st.spinner("AI Technical Code Auditor is reviewing your submission on Groq..."):
                    audit_res = progress_tracking_agent(
                        project_title=proj["title"],
                        project_idea=proj["project_idea"],
                        week_number=s_week,
                        phase_name=s_phase,
                        tasks_completed=s_summary,
                        submitted_code=s_code,
                        code_language=s_lang,
                        blockers=s_blockers,
                        github_link=s_github
                    )

                    # Save log to database
                    add_progress_log(
                        project_id=proj["id"],
                        week_number=s_week,
                        phase_name=s_phase,
                        tasks_completed=s_summary,
                        submitted_code=s_code,
                        code_language=s_lang,
                        blockers=s_blockers,
                        github_link=s_github,
                        ai_feedback=audit_res["feedback"],
                        code_audit=audit_res.get("code_audit", ""),
                        ai_score=audit_res["score"]
                    )

                    # Advance phase & progress percentage
                    new_phase = min(8, s_week + 1)
                    new_percent = max(proj["progress_percent"], audit_res["percent"])
                    update_project_progress(proj["id"], new_percent, new_phase)

                    st.session_state["latest_audit_view"] = audit_res
                    st.success(f"Audit Complete! Milestone Score: {audit_res['score']}/100. Progress updated to {new_percent}%.")
                    st.rerun()

    with col_audit:
        st.markdown("#### 🔍 AI Technical Audit & Scorecard")
        
        # Show latest audit result or most recent log
        logs = get_progress_logs(proj["id"])
        latest = st.session_state.get("latest_audit_view")

        if latest:
            st.markdown(latest["feedback"])
            if latest.get("code_audit"):
                st.markdown("---")
                st.markdown(latest["code_audit"])
        elif logs:
            last_log = logs[-1]
            st.markdown(f"""
            <div class="clean-card" style="border-left: 4px solid #3B82F6;">
                <b>Week {last_log['week_number']}: {last_log['phase_name']}</b><br/>
                Score: <b>{last_log['ai_score']}/100</b> &nbsp;|&nbsp; Status: {get_status_badge(last_log.get('faculty_status', 'Pending'))}
            </div>
            """, unsafe_allow_html=True)
            st.markdown(last_log["ai_feedback"])
            if last_log.get("code_audit"):
                st.markdown("---")
                st.markdown(last_log["code_audit"])
        else:
            st.info("No code submitted yet. Fill in the form on the left to get your first AI Code Audit & Score!")

    # Automated Pytest Suite Generator
    st.divider()
    st.markdown("#### 🧪 Automated Unit Test & Test Case Generator (Pytest)")
    st.caption("Automatically generate a complete, executable `test_suite.py` file with test fixtures, boundary checks, and error assertions for your code.")

    cand_code = ""
    if s_code and s_code.strip():
        cand_code = s_code.strip()
    elif logs and logs[-1].get("submitted_code"):
        cand_code = logs[-1]["submitted_code"].strip()

    col_tg1, col_tg2 = st.columns([1.2, 2.5])
    with col_tg1:
        btn_gen_pytest = st.button("⚡ Generate Pytest Suite for Code", type="secondary", use_container_width=True)
    with col_tg2:
        if cand_code:
            st.caption(f"Ready to generate test cases for current module ({len(cand_code.splitlines())} lines).")
        else:
            st.caption("Paste or submit code above to generate automated tests.")

    if btn_gen_pytest:
        if not cand_code:
            st.warning("Please submit or paste a code snippet above first.")
        else:
            with st.spinner("AI Test Engineer is generating comprehensive Pytest test cases..."):
                t_suite = generate_pytest_suite(cand_code, proj["title"])
                st.session_state["active_pytest_suite"] = t_suite
                st.success("Pytest test suite successfully generated!")

    if "active_pytest_suite" in st.session_state:
        st.markdown(st.session_state["active_pytest_suite"])
        st.download_button(
            label="📥 Download test_suite.py",
            data=st.session_state["active_pytest_suite"],
            file_name="test_suite.py",
            mime="text/x-python",
            use_container_width=False
        )

    # Past History Table
    st.divider()
    st.markdown("#### 📜 Submission History")
    if logs:
        for log in reversed(logs):
            with st.expander(f"Week {log['week_number']}: {log['phase_name']} — Score: {log['ai_score']}/100 ({format_date(log.get('created_at'))})"):
                st.markdown(f"**Tasks Completed:** {log['tasks_completed']}")
                if log.get("submitted_code"):
                    st.code(log["submitted_code"], language=log.get("code_language", "python"))
                st.markdown(log["ai_feedback"])
                if log.get("faculty_comment"):
                    st.warning(f"👨‍🏫 **Faculty Remark:** {log['faculty_comment']}")
    else:
        st.caption("No past submissions.")

# 4. AI Mentor & Viva Defense Chat
def page_student_chat(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("Please select or create a project first.")
        return

    proj = get_project_by_id(curr_id)
    if not proj:
        st.warning("Project not found.")
        return

    st.markdown(f"## 💬 AI Mentorship & Viva Defense Hub")
    st.caption(f"Project: **{proj['title']}** • Phase {proj['current_phase']}/8 • Progress: {int(proj['progress_percent'])}%")

    proj_context = f"Project: {proj['title']}\nIdea: {proj['project_idea']}\nPhase: {proj['current_phase']}/8\nProgress: {proj['progress_percent']}%\nBlueprint: {str(proj.get('blueprint', {}))[:1000]}"

    tab_mentor_chat, tab_viva_sim = st.tabs([
        "💬 Interactive AI Mentor Q&A",
        "🎓 Mock Viva Voce Defense Simulator (External Examiner)"
    ])

    # TAB 1: CONVERSATIONAL MENTOR CHAT
    with tab_mentor_chat:
        st.markdown("#### 👨‍🏫 Ask Your AI Project Mentor")
        st.caption("Get architecture advice, code debugging help, or guidance on upcoming milestone deliverables.")

        # Quick Prompts
        q1, q2, q3, q4 = st.columns(4)
        quick_text = None
        if q1.button("🎯 Next Milestone Help", use_container_width=True):
            quick_text = f"What exact deliverables should I focus on completing for Phase {proj['current_phase']}?"
        if q2.button("🛠️ Debug Architecture", use_container_width=True):
            quick_text = "What is the best way to handle asynchronous background tasks between my frontend and AI backend?"
        if q3.button("📊 Code Review Tips", use_container_width=True):
            quick_text = "What error handling patterns should I add to my core service to pass external examiner review?"
        if q4.button("⚡ Viva Defense Prep", use_container_width=True):
            quick_text = "What are the 3 most common reasons projects lose marks in the final university presentation?"

        # Chat History
        history = get_chat_messages(curr_id)
        for msg in history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask your AI Mentor anything about your project...")
        if quick_text:
            user_input = quick_text

        if user_input:
            add_chat_message(curr_id, user["id"], "user", user_input)
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("AI Mentor thinking..."):
                    reply = conversational_mentor_agent(proj_context, history, user_input)
                    st.markdown(reply)
                    add_chat_message(curr_id, user["id"], "assistant", reply)

    # TAB 2: MOCK VIVA VOCE DEFENSE SIMULATOR
    with tab_viva_sim:
        st.markdown("#### 🎓 External Examiner Viva Voce Simulation")
        st.caption("Simulate a real 5-question University Capstone Viva Defense. The AI External Examiner asks tough questions, scores your technical responses (1-10), and issues a Viva Readiness Certificate.")

        v_idx_key = f"viva_q_idx_{curr_id}"
        v_active_q_key = f"viva_active_q_{curr_id}"
        v_logs_key = f"viva_logs_{curr_id}"

        if v_idx_key not in st.session_state:
            st.session_state[v_idx_key] = 0
        if v_active_q_key not in st.session_state:
            st.session_state[v_active_q_key] = ""
        if v_logs_key not in st.session_state:
            st.session_state[v_logs_key] = []

        curr_q_idx = st.session_state[v_idx_key]
        active_q = st.session_state[v_active_q_key]
        viva_logs = st.session_state[v_logs_key]

        col_ctrl1, col_ctrl2 = st.columns([1.5, 3])
        with col_ctrl1:
            if st.button("🚀 Start / Reset Mock Viva Defense", type="primary", use_container_width=True):
                with st.spinner("External Examiner is preparing Question 1..."):
                    res = viva_defense_simulator(proj["title"], proj_context, 0, "")
                    st.session_state[v_idx_key] = 0
                    st.session_state[v_active_q_key] = res["next_question"]
                    st.session_state[v_logs_key] = []
                    st.rerun()

        with col_ctrl2:
            if viva_logs:
                avg_score = sum(item["score"] for item in viva_logs) / len(viva_logs)
                st.markdown(f"**Current Average Defense Score:** `{avg_score:.1f} / 10` &nbsp;|&nbsp; Questions Completed: `{len(viva_logs)} / 5`")

        st.divider()

        # If examination in progress
        if active_q and curr_q_idx < 5:
            st.markdown(f"""
            <div class="clean-card" style="border-left: 5px solid #1E3A8A; background: #F8FAFC;">
                <div style="font-size:0.82rem; font-weight:700; color:#64748B; text-transform:uppercase;">Question {curr_q_idx + 1} of 5 • External University Examiner</div>
                <div style="font-size:1.15rem; font-weight:600; color:#1E3A8A; margin-top:8px;">{active_q}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form(f"viva_answer_form_{curr_q_idx}"):
                ans_text = st.text_area("Your Technical Defense Response:", height=130, placeholder="Explain your design decisions, technical trade-offs, and justifications thoroughly...")
                submit_ans = st.form_submit_button("📤 Submit Defense Response to Examiner", type="primary", use_container_width=True)

            if submit_ans:
                if not ans_text.strip():
                    st.warning("Please enter your defense answer.")
                else:
                    with st.spinner("Examiner is evaluating your answer and grading technical depth..."):
                        eval_res = viva_defense_simulator(
                            proj["title"],
                            proj_context,
                            curr_q_idx,
                            ans_text
                        )

                        # Record log
                        viva_logs.append({
                            "question": active_q,
                            "answer": ans_text,
                            "score": eval_res["score"],
                            "evaluation": eval_res["evaluation"],
                            "q_num": curr_q_idx + 1
                        })
                        st.session_state[v_logs_key] = viva_logs

                        # Advance to next question or conclude
                        next_idx = curr_q_idx + 1
                        st.session_state[v_idx_key] = next_idx

                        if next_idx < 5:
                            # Generate next question
                            next_q_res = viva_defense_simulator(proj["title"], proj_context, next_idx, "")
                            st.session_state[v_active_q_key] = next_q_res["next_question"]
                        else:
                            st.session_state[v_active_q_key] = ""

                        st.rerun()

        elif curr_q_idx >= 5 and viva_logs:
            # Finished Viva Defense Certificate
            final_avg = sum(item["score"] for item in viva_logs) / len(viva_logs)
            grade = "A+ (Outstanding)" if final_avg >= 9 else ("A (Very Good)" if final_avg >= 7.5 else ("B (Satisfactory)" if final_avg >= 6 else "Needs Revision"))
            
            st.markdown(f"""
            <div class="clean-card" style="border: 2px solid #10B981; background: #ECFDF5; text-align:center; padding: 25px;">
                <h3 style="color:#065F46; margin:0 0 10px 0;">🎓 MOCK VIVA VOCE READINESS CERTIFICATE</h3>
                <p style="color:#047857; font-size:1.05rem; margin:0 0 15px 0;">Student defense completed across 5 core university evaluation areas.</p>
                <div style="font-size:2.4rem; font-weight:800; color:#059669;">{final_avg:.1f} / 10</div>
                <div style="font-size:1.1rem; font-weight:700; color:#065F46; margin-top:5px;">Estimated Final Grade: {grade}</div>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
        else:
            st.info("Click **'🚀 Start / Reset Mock Viva Defense'** above to begin your 5-question examination session!")

        # Past question evaluations
        if viva_logs:
            st.markdown("#### 📜 Examiner Evaluation & Question Breakdown")
            for item in reversed(viva_logs):
                with st.expander(f"Question {item['q_num']}: Score {item['score']}/10 — {item['question'][:65]}...", expanded=(item['q_num'] == len(viva_logs))):
                    st.markdown(f"**❓ Examiner Question:**\n> {item['question']}")
                    st.markdown(f"**🗣️ Your Defense:**\n{item['answer']}")
                    st.markdown("---")
                    st.markdown(item["evaluation"])

# 5. New Project Proposal Wizard
def page_student_new_project(user: dict):
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%); border-radius: 16px; padding: 22px 26px; color: #FFFFFF; margin-bottom: 22px;">
        <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25); padding:3px 12px; border-radius:9999px; font-size:0.75rem; font-weight:700; text-transform:uppercase; margin-bottom:10px;">
            🚀 Multi-Agent Project Generator
        </div>
        <h2 style="color:#FFFFFF; font-size:1.75rem; font-weight:800; margin:0 0 6px 0;">Propose New Capstone Project</h2>
        <p style="color:rgba(255,255,255,0.85); font-size:0.92rem; margin:0;">
            Provide your 2-3 line project concept and assign your faculty guide. 6 specialized AI agents will autonomously generate your complete academic blueprint, UML architecture diagram, risk mitigation matrix, and 8-phase execution roadmap in parallel.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Sample ideas
    st.markdown("##### 💡 Example Idea Starters:")
    ex1, ex2, ex3 = st.columns(3)
    if ex1.button("🤖 AI Support Chatbot", use_container_width=True):
        st.session_state["n_title"] = "AI-Powered Customer Support Chatbot"
        st.session_state["n_idea"] = "I want to build an AI-powered customer support chatbot using Generative AI and vector search to answer customer queries automatically."
    if ex2.button("👁️ Smart Face Attendance", use_container_width=True):
        st.session_state["n_title"] = "Smart Face Attendance Management System"
        st.session_state["n_idea"] = "An automated student attendance management system using Computer Vision, Face Recognition, and real-time logging with anti-spoofing."
    if ex3.button("🛡️ Cyber Threat Intrusion", use_container_width=True):
        st.session_state["n_title"] = "Cyber Threat & Intrusion Detection System"
        st.session_state["n_idea"] = "A machine learning system for real-time network intrusion and anomalous cyber threat detection using packet classification."

    st.write("")
    faculties = get_faculty_users()
    fac_map = {f["id"]: f"{f['full_name']} — {f.get('email', 'No email')} ({f.get('department', 'Engineering')})" for f in faculties}

    c_t1, c_t2 = st.columns([1.5, 1])
    with c_t1:
        p_title = st.text_input("Project Title:", value=st.session_state.get("n_title", ""), placeholder="e.g. AI Customer Support Chatbot")
        p_team = st.text_input("Team Members & Roll Numbers:", value=f"{user['full_name']} (Lead)", placeholder="e.g. Aarav Sharma (21CS045), Sneha Reddy (21CS052)")
    with c_t2:
        p_fac_id = st.selectbox("Assign Faculty Supervisor:", options=list(fac_map.keys()), format_func=lambda x: fac_map[x]) if fac_map else None

    p_idea = st.text_area("Project Idea (2-3 lines):", value=st.session_state.get("n_idea", ""), placeholder="Describe what the system does, target users, and key tech...", height=110)

    if st.button("🚀 Generate Blueprint via 6 Parallel AI Agents", type="primary", use_container_width=True):
        if not p_title.strip() or not p_idea.strip():
            st.warning("Please provide both title and idea statement.")
        else:
            prog_box = st.empty()
            p_bar = st.progress(0.0)

            def update_cb(msg: str, val: float):
                prog_box.info(msg)
                p_bar.progress(val)

            try:
                with st.spinner("AI Specialist Agents analyzing in parallel via Groq..."):
                    blueprint = run_project_mentor_pipeline(p_idea.strip(), progress_callback=update_cb)
                    new_id = save_project(user["id"], p_title.strip(), p_idea.strip(), p_fac_id, blueprint, team_members=p_team)
                    st.session_state["current_project_id"] = new_id
                    st.session_state["active_blueprint"] = blueprint
                    st.session_state["active_title"] = p_title.strip()

                    prog_box.success(f"🎉 Project #{new_id} generated and saved! Navigate to 'Project Overview' or 'Blueprint' in the sidebar.")
                    st.rerun()
            except Exception as e:
                prog_box.empty()
                st.error(f"Error generating blueprint: {str(e)}")

# =====================================================================
# FACULTY PAGES
# =====================================================================
def page_faculty_teams(user: dict):
    st.markdown("## 👨‍🏫 My Assigned Student Teams")
    st.caption(f"Supervisor: **{user['full_name']}** ({user.get('department', 'Engineering')})")

    my_projs = get_all_projects_for_faculty(user["id"])
    if not my_projs:
        st.info("No student teams currently assigned to you.")
        return

    # Supervisor Executive Dashboard Metrics
    total_count = len(my_projs)
    avg_prog = sum(p["progress_percent"] for p in my_projs) / total_count
    rev_count = sum(1 for p in my_projs if p.get("status") == "Needs Revision")
    cleared_count = sum(1 for p in my_projs if p.get("sign_off_date"))

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    f_col1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Assigned Teams</div><div class="kpi-val">{total_count}</div></div>', unsafe_allow_html=True)
    f_col2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Avg Milestone Velocity</div><div class="kpi-val">{int(avg_prog)}%</div></div>', unsafe_allow_html=True)
    f_col3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Action Required</div><div class="kpi-val" style="color:{"#DC2626" if rev_count > 0 else "#059669"};">{rev_count}</div></div>', unsafe_allow_html=True)
    f_col4.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Viva Cleared</div><div class="kpi-val" style="color:#059669;">{cleared_count}</div></div>', unsafe_allow_html=True)

    st.write("")
    
    # Quick Triage Filter
    f_filter = st.radio(
        "Triage Filter:",
        ["All Teams", "⚠️ Needs Revision", "🎓 Viva Cleared", "🔵 In Progress"],
        horizontal=True,
        label_visibility="collapsed"
    )

    filtered_projs = my_projs
    if f_filter == "⚠️ Needs Revision":
        filtered_projs = [p for p in my_projs if p.get("status") == "Needs Revision"]
    elif f_filter == "🎓 Viva Cleared":
        filtered_projs = [p for p in my_projs if p.get("sign_off_date")]
    elif f_filter == "🔵 In Progress":
        filtered_projs = [p for p in my_projs if not p.get("sign_off_date") and p.get("status") != "Needs Revision"]

    if not filtered_projs:
        st.info(f"No teams match filter: '{f_filter}'.")
        return

    # Team cards
    for p in filtered_projs:
        sign_badge = "🎓 Signed Off" if p.get("sign_off_date") else get_status_badge(p["status"])
        st.markdown(f"""
        <div class="clean-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; color:#1E3A8A;">#{p['id']} - {p['title']}</h4>
                <div>{sign_badge}</div>
            </div>
            <p style="color:#4B5563; font-size:0.9rem; margin:8px 0;">
                👥 <b>Team:</b> {p.get('team_members', p['student_name'])} &nbsp;|&nbsp;
                📅 <b>Milestone:</b> Phase {p['current_phase']}/8 &nbsp;|&nbsp;
                📊 <b>Progress:</b> {int(p['progress_percent'])}% &nbsp;|&nbsp;
                🏆 <b>Internal Score:</b> {p.get('faculty_score', 'Not graded')}/100
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Detailed Review & Evaluation Studio
        with st.expander(f"🔍 Audit & Evaluate Project #{p['id']} ({p['student_name']})"):
            t_col1, t_col2 = st.columns([1.2, 1])
            with t_col1:
                st.markdown("##### 💻 Submitted Code & AI Technical Audits:")
                logs = get_progress_logs(p["id"])
                if logs:
                    for l in reversed(logs):
                        st.markdown(f"**Week {l['week_number']}: {l['phase_name']}** — AI Score: `{l['ai_score']}/100`")
                        st.caption(f"Summary: {l['tasks_completed']}")
                        if l.get("submitted_code"):
                            st.code(l["submitted_code"], language=l.get("code_language", "python"))
                        if l.get("code_audit"):
                            st.markdown(f"**AI Code Audit:**\n{l['code_audit'][:300]}...")
                        st.markdown("---")
                else:
                    st.caption("No weekly code submissions yet.")

            with t_col2:
                st.markdown("##### ✍️ Official University Evaluation Studio:")
                with st.form(f"fac_eval_studio_{p['id']}"):
                    st.markdown("###### 📊 University Capstone Grading Rubric:")
                    m_code = st.slider("Code Implementation & Modularity (35 pts):", 0, 35, 30, key=f"m_c_{p['id']}")
                    m_srs = st.slider("SRS, Scope & Architecture (25 pts):", 0, 25, 22, key=f"m_s_{p['id']}")
                    m_test = st.slider("Testing & Validation (20 pts):", 0, 20, 18, key=f"m_t_{p['id']}")
                    m_viva = st.slider("Viva Readiness & Documentation (20 pts):", 0, 20, 18, key=f"m_v_{p['id']}")
                    
                    calc_total = m_code + m_srs + m_test + m_viva
                    st.markdown(f"**Total Calculated Internal Score:** `{calc_total} / 100 Marks`")

                    cur_feed = p.get("faculty_feedback", "")
                    n_feed = st.text_area("Supervisor Assessment & Guidance:", value=cur_feed, placeholder="e.g. Clean RAG pipeline. Verify edge cases for empty queries.", height=90, key=f"feed_{p['id']}")
                    
                    cur_act = p.get("supervisor_action_items", "")
                    n_actions = st.text_area("Mandatory Action Items for Student Before Next Review:", value=cur_act, placeholder="1. Add unit test suite\n2. Sanitize database inputs", height=90, key=f"act_{p['id']}")

                    col_st1, col_st2 = st.columns(2)
                    with col_st1:
                        n_stat = st.selectbox("Project Status:", ["Approved", "In Progress", "Under Review", "Needs Revision"], index=0 if "Approved" in p["status"] else 1, key=f"stat_{p['id']}")
                    with col_st2:
                        grant_so = st.checkbox("🎓 Grant Official Viva Clearance", value=bool(p.get("sign_off_date")), key=f"so_{p['id']}")

                    if st.form_submit_button("💾 Save Official Review & Notify Student", type="primary", use_container_width=True):
                        score_dict = json.dumps({"implementation": m_code, "srs": m_srs, "testing": m_test, "viva": m_viva})
                        update_faculty_evaluation(
                            project_id=p["id"],
                            feedback=n_feed,
                            status=n_stat,
                            action_items=n_actions,
                            faculty_score=calc_total,
                            score_breakdown=score_dict,
                            grant_sign_off=grant_so
                        )
                        st.success(f"Official evaluation saved! Score: {calc_total}/100. Student notified.")
                        st.rerun()

def page_faculty_all_projects(user: dict):
    st.markdown("## 🏛️ Department Capstone Registry")
    all_p = get_all_projects_for_faculty()
    if all_p:
        for ap in all_p:
            st.markdown(f"""
            <div class="clean-card">
                <div style="display:flex; justify-content:space-between;">
                    <h4 style="margin:0; color:#1E3A8A;">#{ap['id']} - {ap['title']}</h4>
                    <div>{get_status_badge(ap['status'])}</div>
                </div>
                <div style="font-size:0.88rem; color:#4B5563; margin-top:6px;">
                    👨‍🎓 <b>Student:</b> {ap['student_name']} &nbsp;|&nbsp;
                    👨‍🏫 <b>Assigned Mentor:</b> {ap.get('faculty_name', 'None')} &nbsp;|&nbsp;
                    📊 <b>Progress:</b> {int(ap['progress_percent'])}% (Phase {ap['current_phase']}/8)
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No projects registered.")

# =====================================================================
# MAIN ROUTING
# =====================================================================
def main():
    if st.session_state["user"] is None:
        render_auth_screen()
    else:
        nav = render_sidebar()
        user = st.session_state["user"]

        if user["role"] == "student":
            if nav == "📌 Project Overview":
                page_student_overview(user)
            elif nav == "📑 Blueprint & Specifications":
                page_student_blueprint(user)
            elif nav == "💻 Code Submission & AI Audit":
                page_student_code_audit(user)
            elif nav == "💬 Ask AI Mentor":
                page_student_chat(user)
            elif nav == "➕ New Project Proposal":
                page_student_new_project(user)
        else:
            if nav == "👨‍🏫 My Assigned Student Teams":
                page_faculty_teams(user)
            elif nav == "🏛️ Department Projects Registry":
                page_faculty_all_projects(user)

if __name__ == "__main__":
    main()
