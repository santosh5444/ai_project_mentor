import io
from datetime import datetime
from typing import Dict, Any, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_border(cell, **kwargs):
    """Sets borders on table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders')
        tcPr.append(tcBorders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = tcBorders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tcBorders.append(element)
            for key in ["val", "color", "sz", "space"]:
                if key in edge_data:
                    element.set(qn('w:{}'.format(key)), str(edge_data[key]))

def generate_docx_report(
    project_title: str,
    student_name: str,
    blueprint: Dict[str, Any],
    team_members: str = "",
    faculty_name: str = "",
    faculty_feedback: str = "",
    faculty_score: Optional[int] = None,
    sign_off_date: Optional[str] = None,
    student_college: str = "",
    faculty_college: str = ""
) -> io.BytesIO:
    """Generates an academic project blueprint report in .docx format with supervisor evaluation sheet and institution credentials."""
    doc = Document()

    # Document Title Page
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("ACADEMIC PROJECT BLUEPRINT\n& SPECIFICATION REPORT")
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(30, 58, 138)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_p.add_run(f"Project Title: {project_title}\n")
    sub_run.font.size = Pt(14)
    sub_run.font.bold = True
    sub_run.font.color.rgb = RGBColor(75, 85, 99)

    tag_p = doc.add_paragraph()
    tag_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tag_run = tag_p.add_run("AI Academic Project Mentor (AAPM) • Infosys Capstone Standard\n")
    tag_run.font.size = Pt(10)
    tag_run.font.italic = True

    # Metadata Box
    meta_data = [
        ("Student / Team Members:", team_members if team_members else student_name),
        ("Student Institution:", student_college if student_college else "Engineering College"),
        ("Faculty Project Guide:", faculty_name if faculty_name else "Department Project Supervisor"),
        ("Guide Institution:", faculty_college if faculty_college else "Mentoring Institution"),
        ("Academic Year:", datetime.now().strftime("%Y")),
        ("Generated Date:", datetime.now().strftime("%B %d, %Y")),
        ("Approval Status:", f"APPROVED & SIGNED OFF ({sign_off_date})" if sign_off_date else "Under Academic Supervision")
    ]
    if student_college and faculty_college and student_college != faculty_college:
        meta_data.append(("Collaboration Type:", "Inter-Institutional Academic Mentorship (Cross-College)"))

    meta_table = doc.add_table(rows=len(meta_data), cols=2)
    meta_table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, (label, val) in enumerate(meta_data):
        cell_lbl = meta_table.cell(i, 0)
        cell_lbl.text = label
        cell_lbl.paragraphs[0].runs[0].font.bold = True
        cell_val = meta_table.cell(i, 1)
        cell_val.text = str(val)

    # Official Supervisor Endorsement Certificate if signed off or graded
    if sign_off_date or faculty_score or faculty_feedback:
        doc.add_paragraph()
        cert_h = doc.add_heading("CERTIFICATE OF FACULTY SUPERVISION", level=2)
        cert_h.runs[0].font.color.rgb = RGBColor(30, 58, 138)
        
        cert_p = doc.add_paragraph()
        cert_p.add_run("This is to certify that the capstone project titled ")
        cert_p.add_run(f'"{project_title}"').bold = True
        cert_p.add_run(f" submitted by ")
        cert_p.add_run(f"{team_members if team_members else student_name}").bold = True
        if student_college:
            cert_p.add_run(f" ({student_college})")
        cert_p.add_run(" has been reviewed, monitored, and evaluated under my mentorship")
        if faculty_college:
            cert_p.add_run(f" at {faculty_college}")
        cert_p.add_run(".")

        if student_college and faculty_college and student_college != faculty_college:
            collab_p = doc.add_paragraph()
            collab_run = collab_p.add_run("ℹ️ Formal recognition of cross-institutional mentorship collaboration.")
            collab_run.font.italic = True
            collab_run.font.size = Pt(9.5)
            collab_run.font.color.rgb = RGBColor(100, 116, 139)

        if faculty_score:
            score_p = doc.add_paragraph()
            score_p.add_run(f"Official University Internal Score: {faculty_score} / 100").bold = True

        if faculty_feedback:
            feed_p = doc.add_paragraph()
            feed_p.add_run("Supervisor Assessment Remarks: ").bold = True
            feed_p.add_run(faculty_feedback)

        if sign_off_date:
            sign_p = doc.add_paragraph()
            sign_p.add_run(f"Official Viva Voce Clearance Granted on {sign_off_date} by {faculty_name} ({faculty_college or 'Faculty Supervisor'}).").bold = True

    doc.add_page_break()

    # Sections mapping
    sections = [
        ("1. Master Mentor Executive Report", blueprint.get("mentor_report", "")),
        ("2. Project Idea & Feasibility Evaluation", blueprint.get("idea", "")),
        ("3. Project Scope & Requirements Specification", blueprint.get("scope", "")),
        ("4. Recommended Technology Stack", blueprint.get("technology", "")),
        ("5. 8-Phase Academic Execution Timeline", blueprint.get("planning", "")),
        ("6. Risk Assessment & Mitigation Strategy", blueprint.get("risks", "")),
        ("7. Academic Documentation, Abstract & Synopsis", blueprint.get("documentation", ""))
    ]

    for heading_title, content in sections:
        h = doc.add_heading(heading_title, level=1)
        h.runs[0].font.color.rgb = RGBColor(30, 64, 175)
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)

        # Parse markdown-like content into clean docx paragraphs
        lines = content.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Clean up Mermaid code block markers if in documentation
            if line_str.startswith("```"):
                continue

            if line_str.startswith("### "):
                sub_h = doc.add_heading(line_str.replace("### ", ""), level=2)
                sub_h.runs[0].font.color.rgb = RGBColor(55, 65, 81)
                sub_h.paragraph_format.space_before = Pt(8)
                sub_h.paragraph_format.space_after = Pt(3)
            elif line_str.startswith("## "):
                sub_h = doc.add_heading(line_str.replace("## ", ""), level=2)
                sub_h.runs[0].font.color.rgb = RGBColor(55, 65, 81)
            elif line_str.startswith("- ") or line_str.startswith("* "):
                p = doc.add_paragraph(line_str[2:], style='List Bullet')
                p.paragraph_format.space_after = Pt(2)
            else:
                p = doc.add_paragraph(line_str)
                p.paragraph_format.space_after = Pt(4)

        doc.add_paragraph()

    # Save to memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_markdown_report(
    project_title: str,
    student_name: str,
    blueprint: Dict[str, Any],
    team_members: str = "",
    faculty_name: str = "",
    student_college: str = "",
    faculty_college: str = ""
) -> str:
    """Generates pure markdown report string with institution attribution."""
    collab_str = f"**Collaboration:** Inter-Institutional Academic Mentorship ({student_college} ↔ {faculty_college})\n" if (student_college and faculty_college and student_college != faculty_college) else ""
    return f"""# ACADEMIC PROJECT BLUEPRINT & SPECIFICATION
**Project Title:** {project_title}  
**Student / Team:** {team_members if team_members else student_name} ({student_college if student_college else 'Engineering College'})  
**Project Guide:** {faculty_name if faculty_name else 'Department Supervisor'} ({faculty_college if faculty_college else 'Mentoring Institution'})  
{collab_str}**Generated On:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Standard:** Infosys AAPM Academic Capstone Specification  

---

## 1. Master Mentor Executive Report
{blueprint.get('mentor_report', '')}

---

## 2. Idea & Feasibility Evaluation
{blueprint.get('idea', '')}

---

## 3. Scope & Requirements Specification
{blueprint.get('scope', '')}

---

## 4. Recommended Technology Stack
{blueprint.get('technology', '')}

---

## 5. 8-Phase Academic Execution Timeline
{blueprint.get('planning', '')}

---

## 6. Risk Assessment & Mitigation Strategy
{blueprint.get('risks', '')}

---

## 7. Academic Documentation & Synopsis
{blueprint.get('documentation', '')}
"""


def generate_pptx_deck(
    project_title: str,
    student_name: str,
    blueprint: Dict[str, Any],
    team_members: str = "",
    faculty_name: str = ""
) -> io.BytesIO:
    """Generates a professional 10-slide academic capstone presentation (.pptx)."""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    prs = Presentation()
    # 16:9 widescreen layout
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    NAVY = RGBColor(30, 58, 138)
    SLATE = RGBColor(71, 85, 105)
    LIGHT_BG = RGBColor(248, 250, 252)
    DARK_BLUE = RGBColor(15, 23, 42)
    ACCENT_BLUE = RGBColor(37, 99, 235)

    def create_slide(title: str, subtitle: str = ""):
        slide = prs.slides.add_slide(blank_layout)

        # Top banner
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.2))
        tf = header_box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = NAVY

        if subtitle:
            p2 = tf.add_paragraph()
            p2.text = subtitle
            p2.font.size = Pt(13)
            p2.font.color.rgb = SLATE

        return slide

    def add_bullet_content(slide, bullets, left=Inches(0.8), top=Inches(1.8), width=Inches(11.7), height=Inches(5.0)):
        box = slide.shapes.add_textbox(left, top, width, height)
        tf = box.text_frame
        tf.word_wrap = True

        for i, text in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = text
            p.font.size = Pt(16)
            p.font.color.rgb = DARK_BLUE
            p.space_after = Pt(14)
            p.level = 0
        return box

    # Slide 1: Title Slide
    s1 = prs.slides.add_slide(blank_layout)
    title_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.0))
    t1 = title_box.text_frame
    t1.word_wrap = True

    p = t1.paragraphs[0]
    p.text = project_title.upper()
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = NAVY
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(16)

    p_sub = t1.add_paragraph()
    p_sub.text = "Final Academic Capstone Project Presentation"
    p_sub.font.size = Pt(18)
    p_sub.font.bold = True
    p_sub.font.color.rgb = ACCENT_BLUE
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.space_after = Pt(28)

    p_meta = t1.add_paragraph()
    team_str = team_members if team_members else student_name
    guide_str = faculty_name if faculty_name else "Department Project Guide"
    p_meta.text = f"Presented By: {team_str}\nProject Guide: {guide_str}\nAcademic Year: {datetime.now().strftime('%Y')}"
    p_meta.font.size = Pt(14)
    p_meta.font.color.rgb = SLATE
    p_meta.alignment = PP_ALIGN.CENTER

    # Slide 2: Problem Statement & Motivation
    s2 = create_slide("1. Problem Statement & Motivation", "Contextual background and core real-world pain points")
    add_bullet_content(s2, [
        "• Core Challenge: Addressing critical inefficiencies, manual bottlenecks, or lack of automation in the problem domain.",
        "• Motivation: Current solutions suffer from scalability constraints, high operational costs, or poor user experience.",
        "• Target Beneficiaries: Primary end-users, industry stakeholders, and academic research community.",
        "• Project Objective: Engineer an automated, intelligent, and scalable software solution to bridge this gap."
    ])

    # Slide 3: Scope & Core Objectives
    s3 = create_slide("2. Scope & Objectives", "Primary system capabilities and academic project boundaries")
    add_bullet_content(s3, [
        "• Primary Goal: Deliver an end-to-end verified prototype fulfilling university capstone specifications.",
        "• Core Feature 1: Intelligent core processing logic with modular service architecture.",
        "• Core Feature 2: Clean, accessible user interface optimized for seamless user onboarding.",
        "• Core Feature 3: Robust backend with persistent storage, API integrity, and error handling.",
        "• Explicit Scope Boundaries: Focus strictly on academic MVP requirements to eliminate deadline risk."
    ])

    # Slide 4: Literature Survey & Related Work
    s4 = create_slide("3. Literature Survey & Gap Analysis", "Evaluation of existing methodologies and academic benchmarks")
    add_bullet_content(s4, [
        "• Classical Approaches: Rely on rule-based heuristics or manual workflows with limited adaptiveness.",
        "• Existing Academic Benchmark: Recent literature demonstrates promise but suffers from high latency or high cost.",
        "• Identified Research Gap: Need for lightweight, cost-effective, and containerized deployment for real-time inference.",
        "• Our Proposed Approach: Modern multi-agent or modular architecture delivering superior accuracy and throughput."
    ])

    # Slide 5: System Architecture & Data Flow
    s5 = create_slide("4. System Architecture & Workflow", "High-level component interaction and data flow pipeline")
    add_bullet_content(s5, [
        "• Presentation Layer: Client frontend for input capture, state handling, and interactive reporting.",
        "• Application / Controller Layer: REST API / Controller managing authentication, validation, and orchestration.",
        "• Core Processing Engine: Specialized AI / Machine Learning agents operating concurrently for optimal speed.",
        "• Data Persistence Layer: Relational metadata storage paired with vector database / file storage.",
        "• Output Pipeline: Formatted reports, downloadable blueprints, and real-time validation signals."
    ])

    # Slide 6: Recommended Technology Stack
    s6 = create_slide("5. Technology Stack & Frameworks", "Production-grade, industry-standard toolchain")
    add_bullet_content(s6, [
        "• Frontend / User Interface: Streamlit / React for reactive, clean, and interactive user interactions.",
        "• Backend & API Engine: Python / FastAPI providing high-throughput async endpoint routing.",
        "• AI / LLM / ML Layer: Groq Inference Engine / LangChain / Hugging Face with open-source fallbacks.",
        "• Database & Vector Store: SQLite / PostgreSQL for application data; ChromaDB / FAISS for embeddings.",
        "• DevOps & Containerization: Docker containerization ready for cloud deployment on Render / AWS."
    ])

    # Slide 7: 8-Week Implementation Roadmap
    s7 = create_slide("6. 8-Week Implementation Roadmap", "Chronological milestone progression across the university semester")
    add_bullet_content(s7, [
        "• Weeks 1-2 (Phase 1 & 2): Problem formulation, literature survey, SRS specification, and guide signoff.",
        "• Weeks 3-4 (Phase 3 & 4): System architecture design, database schema, UML modeling, and core backend logic.",
        "• Weeks 5-6 (Phase 5 & 6): Frontend development, API integration, full-stack pipeline connection, and unit testing.",
        "• Weeks 7-8 (Phase 7 & 8): Cloud deployment, Docker containerization, comprehensive documentation, and viva defense."
    ])

    # Slide 8: Risk Management & Mitigation
    s8 = create_slide("7. Risk Assessment & Mitigations", "Proactive mitigation strategies for technical hurdles")
    add_bullet_content(s8, [
        "• Risk: Dataset Scarcity / Quality -> Mitigation: Kaggle open datasets, synthetic data augmentation, and public APIs.",
        "• Risk: API Costs & Token Limits -> Mitigation: Groq high-speed free tier, local Ollama fallbacks, and response caching.",
        "• Risk: Live Demo Connectivity Issues -> Mitigation: Pre-cached offline response fallback and local video demonstration.",
        "• Risk: Deadline Overrun -> Mitigation: Strict adherence to MVP milestone deliverables and weekly supervisor signoffs."
    ])

    # Slide 9: Software Testing & Validation
    s9 = create_slide("8. Software Testing & Quality Assurance", "Rigorous verification across functional and non-functional requirements")
    add_bullet_content(s9, [
        "• Unit Testing: Pytest automated test suites validating individual functions, inputs, and boundary edge cases.",
        "• Integration Testing: End-to-end API pipeline validation ensuring zero communication dropouts.",
        "• Security & Code Hygiene: Input sanitization, environment variable credential isolation, and clean modular code.",
        "• Code Audit: Deep automated inspection for maintainability, error handling, and performance bottlenecks."
    ])

    # Slide 10: Conclusion & Viva Voce Readiness
    s10 = create_slide("9. Conclusion & Viva Voce Readiness", "Summary of contributions and future research scope")
    add_bullet_content(s10, [
        "• Project Contributions: Successfully engineered a functional, scalable, and documented academic project.",
        "• Academic Rigor: Fulfills all capstone criteria, including SRS documentation, code audit, and guide review.",
        "• Future Enhancements: Support for mobile clients, automated CI/CD deployment pipelines, and advanced analytics.",
        "• Status: All deliverables completed and certified ready for university Viva Voce examination."
    ])

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

