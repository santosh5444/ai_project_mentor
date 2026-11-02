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
    add_chat_message, get_chat_messages,
    get_project_by_invite_code, link_faculty_to_project_by_code
)

import agents
from agents import (
    run_project_mentor_pipeline,
    progress_tracking_agent,
    conversational_mentor_agent,
    transcribe_audio_groq,
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Clean Content Card */
    .clean-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    
    /* Status Badges */
    .badge-approved {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-review {
        background-color: #FEF08A;
        color: #854D0E;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-revision {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-progress {
        background-color: #E1EFFE;
        color: #1E429F;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* Metric Card */
    .kpi-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .kpi-val {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1E3A8A;
    }
    .kpi-lbl {
        font-size: 0.78rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
    }

    /* Modern Dashboard Sidebar Navigation Menu Buttons */
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 9px 14px !important;
        border-radius: 8px !important;
        margin-bottom: 2px !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background-color: #EFF6FF !important;
        border-color: #93C5FD !important;
        color: #1D4ED8 !important;
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
        border-radius: 8px !important;
        margin-bottom: 2px !important;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.25) !important;
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

if "voice_transcription" not in st.session_state:
    st.session_state["voice_transcription"] = ""

def render_voice_speech_player(text_to_speak: str, persona_name: str = "AI Mentor", auto_play: bool = True):
    """Renders browser-native speech synthesis with audio wave animation and manual replay button."""
    clean_text = text_to_speak.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ').strip()
    html_code = f"""
    <div id="speech-wrapper" style="display:flex; align-items:center; justify-content:space-between; background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:10px; padding:10px 16px; margin:10px 0;">
        <div style="display:flex; align-items:center; gap:12px;">
            <div id="wave-box" style="font-size:1.5rem;">🎙️</div>
            <div>
                <div style="font-weight:700; color:#1E3A8A; font-size:0.92rem;">Spoken Mentor Audio: <span style="font-weight:400; color:#475569;">{persona_name}</span></div>
                <div style="font-size:0.8rem; color:#64748B;">Interactive Voice Session • SpeechSynthesis</div>
            </div>
        </div>
        <div>
            <button id="viva-speak-btn" onclick="triggerVivaSpeech()" style="background:#2563EB; color:white; border:none; padding:7px 16px; border-radius:6px; font-weight:600; font-size:0.85rem; cursor:pointer; display:flex; align-items:center; gap:6px; box-shadow:0 2px 4px rgba(37,99,235,0.2);">
                🔊 Listen to Mentor
            </button>
        </div>
    </div>
    <script>
    function triggerVivaSpeech() {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            var utterance = new SpeechSynthesisUtterance("{clean_text}");
            utterance.rate = 0.98;
            utterance.pitch = 1.0;
            var voices = window.speechSynthesis.getVoices();
            for (var i = 0; i < voices.length; i++) {{
                var v = voices[i];
                if (v.lang && v.lang.indexOf('en') !== -1 && (v.name.indexOf('Natural') !== -1 || v.name.indexOf('Google') !== -1 || v.name.indexOf('Zira') !== -1 || v.name.indexOf('Samantha') !== -1 || v.name.indexOf('David') !== -1)) {{
                    utterance.voice = v;
                    break;
                }}
            }}
            utterance.onstart = function() {{
                var btn = document.getElementById('viva-speak-btn');
                if (btn) {{ btn.innerText = '🗣️ Mentor Speaking...'; btn.style.background = '#059669'; }}
                var wb = document.getElementById('wave-box');
                if (wb) wb.innerText = '🔊';
            }};
            utterance.onend = function() {{
                var btn = document.getElementById('viva-speak-btn');
                if (btn) {{ btn.innerText = '🔊 Replay Mentor Voice'; btn.style.background = '#2563EB'; }}
                var wb = document.getElementById('wave-box');
                if (wb) wb.innerText = '🎙️';
            }};
            utterance.onerror = function() {{
                var btn = document.getElementById('viva-speak-btn');
                if (btn) btn.innerText = '🔊 Replay Voice';
            }};
            window.speechSynthesis.speak(utterance);
        }}
    }}
    {'setTimeout(triggerVivaSpeech, 400);' if auto_play else ''}
    </script>
    """
    components.html(html_code, height=75)


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

def extract_mermaid_code(doc_text: str) -> str:
    match = re.search(r"```(?:mermaid)?\s*([\s\S]*?)```", doc_text)
    if match:
        code = match.group(1).strip()
        if any(kw in code for kw in ["graph", "sequenceDiagram", "flowchart", "classDiagram"]):
            return code
    return """graph TD
    User[Student / User] --> Frontend[Streamlit Interface]
    Frontend --> Backend[API / Controller]
    Backend --> Orchestrator[AI Multi-Agent Pipeline]
    Orchestrator --> DB[(Storage / Vector Store)]
    Orchestrator --> Result[Academic Deliverables & Code Audit]"""

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
# AUTHENTICATION SCREEN (Clean, Centered, Minimalist)
# =====================================================================
def render_auth_screen():
    st.write("")
    c_space1, c_main, c_space2 = st.columns([1, 2.0, 1])

    with c_main:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">🎓</div>
            <h2 style="color: #1E3A8A; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.5px;">AI Academic Project Mentor</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin: 0;">Intelligent Planning, Progress Tracking & 1-on-1 Mentorship Platform</p>
        </div>
        """, unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "📝 Create Account"])

        with auth_tab1:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            with st.form("signin_form", clear_on_submit=False):
                login_id = st.text_input(
                    "Username or Email",
                    placeholder="Enter your username or email address",
                    key="login_id"
                )
                login_pwd = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your account password",
                    key="login_pwd"
                )
                
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("🚀 Sign In", type="primary", use_container_width=True)

                if submitted:
                    if not login_id.strip() or not login_pwd.strip():
                        st.warning("Please enter your username/email and password.")
                    else:
                        u = authenticate_user(login_id.strip(), login_pwd.strip())
                        if u:
                            st.session_state["user"] = u
                            st.rerun()
                        else:
                            st.error("❌ Incorrect username/email or password. Please check and try again.")

            st.markdown("""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-top: 14px; font-size: 0.82rem; color: #64748B;">
                💡 <b>Quick Tip:</b> You can sign in using either your <b>username</b> or your registered <b>email address</b>. Press <b>Enter</b> to instantly sign in.
            </div>
            """, unsafe_allow_html=True)

        with auth_tab2:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            with st.form("signup_form"):
                fname = st.text_input("Full Name *", placeholder="e.g. Priya Patel")
                r_uname = st.text_input("Choose Username *", placeholder="e.g. priyap")
                r_email = st.text_input("Email Address *", placeholder="e.g. priya@gmail.com")
                r_pwd = st.text_input("Password *", type="password", placeholder="Choose a password")
                r_role = st.selectbox("I am a:", ["student", "faculty"], format_func=lambda x: "👨‍🎓 Student" if x == "student" else "👨‍🏫 Faculty / Mentor")

                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                create_btn = st.form_submit_button("✨ Create Account", type="primary", use_container_width=True)

                if create_btn:
                    if not fname.strip() or not r_uname.strip() or not r_email.strip() or not r_pwd.strip():
                        st.warning("Please fill in all fields (Full Name, Username, Email, and Password).")
                    else:
                        ok, msg = register_user(
                            username=r_uname.strip(),
                            password=r_pwd.strip(),
                            role=r_role,
                            full_name=fname.strip(),
                            email=r_email.strip()
                        )
                        if ok:
                            st.success(f"🎉 {msg}")
                        else:
                            st.error(f"❌ {msg}")

# =====================================================================
# SIDEBAR (Global Project Switcher & Navigation)
# =====================================================================
def render_sidebar():
    user = st.session_state["user"]
    with st.sidebar:
        st.markdown("### 🎓 AAPM Workspace")
        role_title = "👨‍🎓 Student" if user["role"] == "student" else "👨‍🏫 Faculty Mentor"
        st.markdown(f"**{user['full_name']}**")
        st.caption(f"{role_title}")

        st.divider()

        if user["role"] == "student":
            # Global Project Switcher (Fast lightweight fetch)
            projects = get_student_project_list(user["id"])
            if projects:
                proj_map = {p["id"]: p['title'] for p in projects}
                ids = list(proj_map.keys())

                curr_id = st.session_state.get("current_project_id")
                if curr_id is None or curr_id not in ids:
                    curr_id = ids[0]
                    st.session_state["current_project_id"] = curr_id
                    st.session_state["active_project"] = None

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
                    st.session_state["active_project"] = None
                    st.rerun()

                # Session-level caching of active project to prevent redundant DB calls
                if not st.session_state.get("active_project") or st.session_state.get("active_project", {}).get("id") != st.session_state["current_project_id"]:
                    st.session_state["active_project"] = get_project_by_id(st.session_state["current_project_id"])

                active_p = st.session_state.get("active_project")
                if active_p:
                    st.session_state["active_blueprint"] = active_p.get("blueprint")
                    st.session_state["active_title"] = active_p.get("title")
                    if active_p.get("faculty_name"):
                        st.caption(f"👨‍🏫 Mentor: **{active_p['faculty_name']}**")
            else:
                st.info("No projects yet. Click 'New Project Proposal' below!")

            st.markdown("---")
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#64748B; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;'>Navigation</p>", unsafe_allow_html=True)
            nav_items = [
                "📌 Project Overview",
                "📑 Blueprint & Specifications",
                "💻 Code Submission & AI Audit",
                "💬 Ask AI Mentor",
                "➕ New Project Proposal"
            ]
            if "student_active_nav" not in st.session_state or st.session_state["student_active_nav"] not in nav_items:
                st.session_state["student_active_nav"] = "📌 Project Overview"

            for item in nav_items:
                is_selected = (st.session_state["student_active_nav"] == item)
                btn_type = "primary" if is_selected else "secondary"
                if st.button(item, key=f"snav_{item}", type=btn_type, use_container_width=True):
                    st.session_state["student_active_nav"] = item
                    st.rerun()

            st.divider()
            if st.button("🚪 Logout", use_container_width=True, key="logout_student"):
                st.session_state["user"] = None
                st.session_state["current_project_id"] = None
                st.session_state["active_blueprint"] = None
                st.rerun()
            return st.session_state["student_active_nav"]

        else:
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#64748B; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;'>Navigation</p>", unsafe_allow_html=True)
            fac_items = [
                "👨‍🏫 My Assigned Student Teams",
                "🏛️ Department Projects Registry"
            ]
            if "faculty_active_nav" not in st.session_state or st.session_state["faculty_active_nav"] not in fac_items:
                st.session_state["faculty_active_nav"] = "👨‍🏫 My Assigned Student Teams"

            for item in fac_items:
                is_selected = (st.session_state["faculty_active_nav"] == item)
                btn_type = "primary" if is_selected else "secondary"
                if st.button(item, key=f"fnav_{item}", type=btn_type, use_container_width=True):
                    st.session_state["faculty_active_nav"] = item
                    st.rerun()

            st.divider()
            if st.button("🚪 Logout", use_container_width=True, key="logout_faculty"):
                st.session_state["user"] = None
                st.session_state["current_project_id"] = None
                st.rerun()
            return st.session_state["faculty_active_nav"]

# =====================================================================
# STUDENT PAGES
# =====================================================================

# 1. Project Overview & Milestones
def page_student_overview(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("No project active. Please click **'➕ New Project Proposal'** in the sidebar to start your first project!")
        return

    proj = st.session_state.get("active_project")
    if not proj or proj.get("id") != curr_id:
        proj = get_project_by_id(curr_id)
        st.session_state["active_project"] = proj
    if not proj:
        st.warning("Project not found.")
        return

    st.markdown(f"## 📌 {proj['title']}")
    st.caption(f"Created on {str(proj['created_at'])[:10]}")

    inv_code = proj.get("invite_code") or f"PRJ-{proj['id']:04d}"
    stud_college = proj.get("student_college") or user.get("college", "Your College")
    fac_college = proj.get("faculty_college", "")
    fac_name = proj.get("faculty_name")

    # Project Invite Code Banner for Cross-College Mentorship
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1.5px solid #3B82F6; border-radius: 10px; padding: 14px 18px; margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="font-size: 0.85rem; font-weight: 700; color: #1E40AF; text-transform: uppercase; letter-spacing: 0.5px;">🔑 Project Invite Code (Cross-College Mentorship)</span>
                <div style="font-size: 1.6rem; font-weight: 800; color: #1E3A8A; font-family: monospace; letter-spacing: 2px; margin-top: 2px;">{inv_code}</div>
                <div style="font-size: 0.85rem; color: #1E40AF; margin-top: 2px;">Share this code with your project supervisor from <b>any college, university, or industry</b> to link them to your workspace.</div>
            </div>
            <div style="text-align: right; margin-top: 5px;">
                <span style="background: {'#059669' if fac_name else '#2563EB'}; color: white; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                    {'🤝 Supervisor Connected' if fac_name else '⏳ Awaiting Guide Connection'}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Current Milestone</div><div class="kpi-val">Phase {proj["current_phase"]}/8</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Total Completion</div><div class="kpi-val">{int(proj["progress_percent"])}%</div></div>', unsafe_allow_html=True)
    guide_display = fac_name if fac_name else "Awaiting Guide"
    col3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Assigned Faculty</div><div style="font-size:1.05rem; font-weight:700; color:#1E3A8A; padding-top:6px;">{guide_display}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Review Status</div><div style="padding-top:8px;">{get_status_badge(proj["status"])}</div></div>', unsafe_allow_html=True)

    st.write("")
    st.progress(float(proj["progress_percent"]) / 100.0)

    # 👨‍🏫 FACULTY SUPERVISOR DIRECTIVE & EVALUATION BOX
    st.markdown("#### 👨‍🏫 Faculty Guide Guidance & Evaluation")
    f_box_col1, f_box_col2 = st.columns([1.5, 1])

    with f_box_col1:
        if proj.get("sign_off_date"):
            st.success(f"🎓 **Official Viva Voce Clearance Granted!** Signed off on {proj['sign_off_date']} by {proj.get('faculty_name', 'Faculty Supervisor')} ({fac_college or 'Faculty Dept'}).")
        elif proj.get("status") == "Needs Revision":
            st.error("⚠️ **Code Revision Requested by Supervisor:** Please address the required action items below.")
        elif fac_name:
            st.info(f"👨‍🏫 **Project Guide:** {fac_name} ({proj.get('faculty_dept', 'Engineering')}) • 🏛️ **{fac_college or 'Faculty Institution'}**")
            if stud_college and fac_college and stud_college != fac_college:
                st.caption(f"🌐 **Inter-Institutional Mentorship Active:** Student ({stud_college}) ↔ Mentor ({fac_college})")
        else:
            st.warning(f"⏳ **No Supervisor Connected Yet:** Send your Project Code **`{inv_code}`** to your mentor so they can join!")

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
            new_team = st.text_area(
                "Team Members & Roll Numbers:",
                value=curr_team,
                placeholder="List all team members with roll numbers, for example:\n1. D.RAMA SANTOSH REDDY (Lead) - 21CS001\n2. Teammate Two - 21CS002",
                height=85
            )
            if st.form_submit_button("💾 Save Updated Team Roster", type="primary"):
                update_project_team(proj["id"], new_team)
                st.success("Team roster updated! Will reflect on exported reports.")
                st.rerun()

    # Project Idea Summary
    st.markdown(f"""
    <div class="clean-card">
        <h4 style="margin:0 0 6px 0; color:#1E3A8A;">💡 Project Statement</h4>
        <p style="margin:0; color:#4B5563;">{proj['project_idea']}</p>
    </div>
    """, unsafe_allow_html=True)

    # 8-Phase Progress Roadmap
    st.markdown("#### 🗺️ 8-Phase Academic Execution Roadmap")
    for p_num, p_name in PHASES:
        if p_num < proj["current_phase"]:
            st.markdown(f"✅ **Week {p_num}: {p_name}** — *Completed & Verified*")
        elif p_num == proj["current_phase"]:
            st.markdown(f"⏳ **Week {p_num}: {p_name}** — **CURRENT ACTIVE PHASE (Submit code in 'Code Submission & AI Audit')**")
        else:
            st.markdown(f"⚪ **Week {p_num}: {p_name}** — *Upcoming*")

# 2. Blueprint & Specifications (Clean Document View, No 8 Nested Tabs!)
def page_student_blueprint(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("Please select or create a project first.")
        return

    proj = st.session_state.get("active_project")
    if not proj or proj.get("id") != curr_id:
        proj = get_project_by_id(curr_id)
        st.session_state["active_project"] = proj
    if not proj:
        st.warning("Project not found.")
        return

    bp = proj.get("blueprint", {})
    stud_college = proj.get("student_college") or user.get("college", "")
    fac_college = proj.get("faculty_college", "")
    fac_name = proj.get("faculty_name") or "Unassigned Guide"

    # Header with 1-Click Downloads
    h_col1, h_col2, h_col3, h_col4 = st.columns([2.5, 1, 1, 1])
    with h_col1:
        st.markdown(f"## 📑 Academic Blueprint: {proj['title']}")
        st.caption(f"Team: **{proj.get('team_members', user['full_name'])}** ({stud_college}) • Supervisor: **{fac_name}** ({fac_college or 'Faculty'}) • 🔑 Code: `{proj.get('invite_code', 'PRJ-CODE')}`")
    with h_col2:
        docx_data = generate_docx_report(
            project_title=proj["title"],
            student_name=user["full_name"],
            blueprint=bp,
            team_members=proj.get("team_members", user["full_name"]),
            faculty_name=fac_name,
            faculty_feedback=proj.get("faculty_feedback", ""),
            faculty_score=proj.get("faculty_score"),
            sign_off_date=proj.get("sign_off_date"),
            student_college=stud_college,
            faculty_college=fac_college
        )
        st.download_button(
            label="📄 Word (.docx)",
            data=docx_data,
            file_name=f"{proj['title'].replace(' ', '_')}_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    with h_col3:
        pptx_data = generate_pptx_deck(
            project_title=proj["title"],
            student_name=user["full_name"],
            blueprint=bp,
            team_members=proj.get("team_members", user["full_name"]),
            faculty_name=fac_name
        )
        st.download_button(
            label="📽️ Slides (.pptx)",
            data=pptx_data,
            file_name=f"{proj['title'].replace(' ', '_')}_Presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True
        )
    with h_col4:
        md_data = generate_markdown_report(
            project_title=proj["title"],
            student_name=user["full_name"],
            blueprint=bp,
            team_members=proj.get("team_members", user["full_name"]),
            faculty_name=fac_name,
            student_college=stud_college,
            faculty_college=fac_college
        )
        st.download_button(
            label="📥 Markdown (.md)",
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

    proj = st.session_state.get("active_project")
    if not proj or proj.get("id") != curr_id:
        proj = get_project_by_id(curr_id)
        st.session_state["active_project"] = proj
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
                    st.session_state["active_project"] = None

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

    # Past History Table
    st.divider()
    st.markdown("#### 📜 Submission History")
    if logs:
        for log in reversed(logs):
            with st.expander(f"Week {log['week_number']}: {log['phase_name']} — Score: {log['ai_score']}/100 ({str(log['created_at'])[:10]})"):
                st.markdown(f"**Tasks Completed:** {log['tasks_completed']}")
                if log.get("submitted_code"):
                    st.code(log["submitted_code"], language=log.get("code_language", "python"))
                st.markdown(log["ai_feedback"])
                if log.get("faculty_comment"):
                    st.warning(f"👨‍🏫 **Faculty Remark:** {log['faculty_comment']}")
    else:
        st.caption("No past submissions.")

# 4. AI Mentor Chat & Voice Assistant (Unified Text & Microphone)
def page_student_chat(user: dict):
    curr_id = st.session_state.get("current_project_id")
    if not curr_id:
        st.info("Please select or create a project first from the sidebar.")
        return

    proj = st.session_state.get("active_project")
    if not proj or proj.get("id") != curr_id:
        proj = get_project_by_id(curr_id)
        st.session_state["active_project"] = proj
    if not proj:
        st.warning("Project not found.")
        return

    st.markdown(f"## 💬 Ask AI Mentor")
    st.caption(f"Intelligent guide for **{proj['title']}** (Phase {proj['current_phase']}/8). Ask questions, brainstorm architecture, debug code, or speak naturally into your microphone.")

    proj_context = f"Project: {proj['title']}\nIdea: {proj['project_idea']}\nPhase: {proj['current_phase']}/8\nProgress: {proj['progress_percent']}%"

    # Quick Suggestion Prompts
    q1, q2, q3, q4 = st.columns(4)
    quick_text = None
    if q1.button("💡 Architecture Advice", use_container_width=True):
        quick_text = "What architecture patterns or modular structure do you recommend for my project?"
    if q2.button("🛠️ Debugging Strategy", use_container_width=True):
        quick_text = "What is the best way to handle asynchronous background tasks and error handling in this stack?"
    if q3.button("📊 Code Review Tips", use_container_width=True):
        quick_text = "What best practices and clean code conventions should our team follow before our next review?"
    if q4.button("🚀 Presentation Tips", use_container_width=True):
        quick_text = "How can we structure an engaging project demo and walkthrough for our milestone presentation?"

    # 🎙️ Inline Microphone Voice Input Section
    with st.expander("🎙️ Speak to AI Mentor (Microphone Input)", expanded=False):
        c_mic, c_mic_txt = st.columns([1, 1.4])
        with c_mic:
            st.caption("Press record, speak into your mic, and stop:")
            audio_input = st.audio_input("Microphone input:", key=f"chat_mic_{curr_id}")
            if audio_input:
                with st.spinner("Transcribing your speech with Groq Whisper Turbo..."):
                    audio_bytes = audio_input.read()
                    transcribed = transcribe_audio_groq(audio_bytes)
                    if transcribed:
                        st.session_state["mic_speech_text"] = transcribed

        with c_mic_txt:
            spoken_val = st.session_state.get("mic_speech_text", "")
            confirmed_speech = st.text_area(
                "Review or edit your spoken message:",
                value=spoken_val,
                placeholder="Speak into the microphone on the left and your transcribed words will appear here...",
                height=90,
                key="speech_confirm_box"
            )
            if st.button("💬 Send Voice Question", type="primary", use_container_width=True):
                if confirmed_speech.strip():
                    quick_text = confirmed_speech.strip()
                    st.session_state["mic_speech_text"] = ""

    st.markdown("---")

    # Chat History Stream
    history = get_chat_messages(curr_id)
    for idx, msg in enumerate(history):
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="🧑‍🏫"):
                # Spoken audio player button for the latest assistant answer
                if idx == len(history) - 1:
                    render_voice_speech_player(msg["content"][:300], persona_name="AI Mentor", auto_play=False)
                st.markdown(msg["content"])
        else:
            with st.chat_message("user", avatar="👨‍🎓"):
                st.markdown(msg["content"])

    # Chat Input
    user_input = st.chat_input("Ask your AI Mentor anything about your project (or use the mic above)...")
    if quick_text:
        user_input = quick_text

    if user_input:
        add_chat_message(curr_id, user["id"], "user", user_input)
        with st.chat_message("user", avatar="👨‍🎓"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🧑‍🏫"):
            with st.spinner("AI Mentor is thinking..."):
                reply = conversational_mentor_agent(proj_context, history, user_input)
                render_voice_speech_player(reply[:300], persona_name="AI Mentor", auto_play=True)
                st.markdown(reply)
                add_chat_message(curr_id, user["id"], "assistant", reply)
                st.rerun()

# 6. New Project Proposal Wizard
def page_student_new_project(user: dict):
    st.markdown("## ➕ Propose New Capstone Project")
    st.caption("Enter a title, assign your faculty supervisor, and describe your idea in 2-3 lines. 6 AI specialist agents will build your complete academic blueprint in parallel.")

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
    fac_options = [0] + [f["id"] for f in faculties]
    fac_map = {0: "⚡ Connect Later via Project Code"}
    for f in faculties:
        fac_map[f["id"]] = f"{f['full_name']}"

    c_t1, c_t2 = st.columns([1.5, 1.2])
    with c_t1:
        p_title = st.text_input("Project Title:", value=st.session_state.get("n_title", ""), placeholder="e.g. AI Customer Support Chatbot")
    with c_t2:
        p_fac_choice = st.selectbox(
            "Assign Faculty Supervisor:",
            options=fac_options,
            format_func=lambda x: fac_map[x],
            help="Select a faculty from your department or choose 'Connect Later via Project Code'."
        )
        p_fac_id = p_fac_choice if p_fac_choice != 0 else None

    p_team = st.text_area(
        "👥 Team Members & Roll Numbers (Add all team members and roll numbers here):",
        value=f"{user['full_name']} (Lead)",
        placeholder="List all team members with roll numbers, for example:\n1. D.RAMA SANTOSH REDDY (Lead) - 21CS001\n2. Teammate Two - 21CS002\n3. Teammate Three - 21CS003",
        height=85,
        help="You can type or paste all your teammates' names and roll numbers here. You can also update this anytime from Project Overview."
    )
    st.caption("💡 *You can list all your team members and roll numbers above (comma-separated or line-by-line). You can also edit this anytime later from 'Project Overview'.*")

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
                    st.session_state["active_project"] = None
                    st.session_state["active_blueprint"] = blueprint
                    st.session_state["active_title"] = p_title.strip()

                    new_proj = get_project_by_id(new_id)
                    code_msg = f" Project Invite Code: **{new_proj.get('invite_code', '')}**" if new_proj else ""
                    prog_box.success(f"🎉 Project generated and saved!{code_msg} Navigate to 'Project Overview' or 'Blueprint' in the sidebar.")
                    st.rerun()
            except Exception as e:
                prog_box.empty()
                st.error(f"Error generating blueprint: {str(e)}")

# =====================================================================
# FACULTY PAGES
# =====================================================================
def page_faculty_teams(user: dict):
    st.markdown("## 👨‍🏫 My Assigned Student Teams")
    st.caption(f"Supervisor: **{user['full_name']}**")

    # 🔗 Connect to Student Project via Invite Code
    with st.expander("🔗 Connect to a Student Project using Project Invite Code", expanded=True):
        st.markdown("<p style='font-size:0.9rem; color:#4B5563; margin-bottom:10px;'>Enter the student's unique Project Code (e.g. <code>PRJ-7918</code>) below to connect to their project.</p>", unsafe_allow_html=True)
        c_code_input, c_btn = st.columns([3, 1])
        with c_code_input:
            target_code = st.text_input("Enter Student Project Code:", key="fac_link_code_input", placeholder="e.g. PRJ-7918").strip().upper()
        with c_btn:
            st.write("")
            btn_link = st.button("🤝 Connect as Supervisor", type="primary", use_container_width=True)
        
        if btn_link:
            if not target_code:
                st.warning("Please enter a valid Project Code.")
            else:
                cand = get_project_by_invite_code(target_code)
                if not cand:
                    st.error("❌ No project found with this invite code. Please verify the code with the student.")
                else:
                    ok, msg = link_faculty_to_project_by_code(user["id"], target_code)
                    if ok:
                        st.success(f"🎉 {msg}")
                        st.rerun()
                    else:
                        st.warning(msg)

    st.write("")
    my_projs = get_all_projects_for_faculty(user["id"])
    if not my_projs:
        st.info("No student teams currently assigned to you. Enter a student's Project Code above to connect!")
        return

    # Team cards
    for p in my_projs:
        sign_badge = "🎓 Signed Off" if p.get("sign_off_date") else get_status_badge(p["status"])
        stud_col = p.get("student_college", "Student College")
        fac_col = user.get("college", "")
        cross_col_badge = f'<span style="background:#EEF2FF; color:#4338CA; padding:3px 9px; border-radius:12px; font-size:0.78rem; font-weight:600; margin-left:8px;">🌐 Cross-College ({stud_col})</span>' if (stud_col and fac_col and stud_col != fac_col) else ""
        code_badge = f'<span style="background:#F1F5F9; color:#475569; padding:3px 8px; border-radius:6px; font-family:monospace; font-weight:700; font-size:0.82rem;">🔑 {p.get("invite_code", "PRJ-CODE")}</span>'

        st.markdown(f"""
        <div class="clean-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; color:#1E3A8A;">{p['title']} &nbsp; {code_badge}</h4>
                <div>{sign_badge}</div>
            </div>
            <p style="color:#4B5563; font-size:0.9rem; margin:8px 0;">
                👥 <b>Team:</b> {p.get('team_members', p['student_name'])} ({stud_col}) {cross_col_badge}<br/>
                📅 <b>Milestone:</b> Phase {p['current_phase']}/8 &nbsp;|&nbsp;
                📊 <b>Progress:</b> {int(p['progress_percent'])}% &nbsp;|&nbsp;
                🏆 <b>Internal Score:</b> {p.get('faculty_score', 'Not graded')}/100
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Detailed Review & Evaluation Studio
        with st.expander(f"🔍 Audit & Evaluate: {p['title']} ({p['student_name']})"):
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
            inv = ap.get('invite_code')
            inv_tag = f"&nbsp;<code style='font-size:0.8rem; color:#4B5563;'>{inv}</code>" if inv else ""
            st.markdown(f"""
            <div class="clean-card">
                <div style="display:flex; justify-content:space-between;">
                    <h4 style="margin:0; color:#1E3A8A;">{ap['title']} {inv_tag}</h4>
                    <div>{get_status_badge(ap['status'])}</div>
                </div>
                <div style="font-size:0.88rem; color:#4B5563; margin-top:6px;">
                    👨‍🎓 <b>Student:</b> {ap['student_name']} ({ap.get('student_college', 'Engineering College')}) &nbsp;|&nbsp;
                    👨‍🏫 <b>Assigned Mentor:</b> {ap.get('faculty_name', 'None')} ({ap.get('faculty_college', '')}) &nbsp;|&nbsp;
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
