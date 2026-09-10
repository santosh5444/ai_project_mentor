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
