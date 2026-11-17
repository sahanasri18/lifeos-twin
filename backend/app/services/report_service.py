"""PDF decision reports for synthetic Nova City scenarios."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

from app.knowledge.retriever import retriever
from app.models.scenario_history import SavedScenario


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _base_story(title: str, subtitle: str) -> tuple[list, dict]:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#123047"), spaceAfter=5))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#176477"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#536574")))
    story = [_paragraph(title, styles["ReportTitle"]), _paragraph(subtitle, styles["SmallNote"]), Spacer(1, 7 * mm)]
    return story, styles


def _metric_table(scenarios: list[SavedScenario], styles: dict) -> Table:
    rows = [["Scenario", "Traffic", "Water", "Electricity", "Risk"]]
    for item in scenarios:
        rows.append([
            item.name,
            f"{item.result.traffic.projected:,.1f} {item.result.traffic.unit}",
            f"{item.result.water.projected:,.1f} {item.result.water.unit}",
            f"{item.result.electricity.projected:,.1f} {item.result.electricity.unit}",
            item.result.risk_level,
        ])
    table = Table(rows, repeatRows=1, colWidths=[48 * mm, 29 * mm, 29 * mm, 32 * mm, 22 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17384b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#cbd5dc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f7")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _evidence_for(scenario: SavedScenario) -> list[dict]:
    query = f"{scenario.request.district_id} population growth traffic water electricity infrastructure planning"
    return retriever.search(query, limit=3)


def build_scenario_report(scenario: SavedScenario) -> bytes:
    story, styles = _base_story("LifeOS Twin · Decision Report", f"Nova City / Scenario: {scenario.name} / Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    story += [_paragraph("Scenario overview", styles["Section"]),
              _paragraph(f"District: {scenario.request.district_id}", styles["BodyText"]),
              _paragraph(f"Population change: {scenario.request.population_change_percent:+g}%", styles["BodyText"]),
              _paragraph(f"Commercial growth: {scenario.request.commercial_growth_percent:+g}%", styles["BodyText"]),
              _paragraph(f"Green-space change: {scenario.request.green_space_change_percent:+g}%", styles["BodyText"]),
              Spacer(1, 4 * mm), _paragraph("Projected indicators", styles["Section"]), _metric_table([scenario], styles),
              _paragraph("Model assumptions", styles["Section"])]
    for assumption in scenario.result.assumptions:
        story.append(_paragraph(f"- {assumption}", styles["BodyText"]))
    evidence = _evidence_for(scenario)
    story.append(_paragraph("Retrieved knowledge references", styles["Section"]))
    if evidence:
        for source in evidence:
            story.append(_paragraph(f"{source['id']} — {source['title']} ({source['domain']}); retrieval score {source['score']:.3f}", styles["SmallNote"]))
    else:
        story.append(_paragraph("No relevant knowledge references were retrieved for this scenario.", styles["SmallNote"]))
    story += [Spacer(1, 5 * mm), _paragraph("Interpretation and limitations", styles["Section"]),
              _paragraph("These are deterministic estimates generated from fictional Nova City demonstration data. Retrieved notes are synthetic planning material, not independently verified real-world evidence. A lower projected value is not automatically a better policy outcome; review service levels, costs, equity, environmental effects and local constraints before making decisions.", styles["SmallNote"])]
    output = BytesIO()
    SimpleDocTemplate(output, pagesize=A4, rightMargin=17*mm, leftMargin=17*mm, topMargin=17*mm, bottomMargin=17*mm, title="LifeOS Twin Decision Report", author="LifeOS Twin").build(story)
    return output.getvalue()


def build_comparison_report(scenarios: list[SavedScenario]) -> bytes:
    story, styles = _base_story("LifeOS Twin · Scenario Comparison", f"Nova City / {len(scenarios)} scenarios / Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    story += [_paragraph("Side-by-side projected indicators", styles["Section"]), _metric_table(scenarios, styles)]
    for metric, label in (("traffic", "Traffic"), ("water", "Water"), ("electricity", "Electricity")):
        values = [(item.name, getattr(item.result, metric).projected, getattr(item.result, metric).unit) for item in scenarios]
        low = min(values, key=lambda row: row[1]); high = max(values, key=lambda row: row[1])
        story += [_paragraph(f"{label} comparison", styles["Section"]),
                  _paragraph(f"Lowest projected value: {low[0]} — {low[1]:,.1f} {low[2]}", styles["BodyText"]),
                  _paragraph(f"Highest projected value: {high[0]} — {high[1]:,.1f} {high[2]}", styles["BodyText"])]
    story += [_paragraph("Scenario assumptions", styles["Section"])]
    for item in scenarios:
        story.append(_paragraph(item.name, styles["Heading3"]))
        story.append(_paragraph(f"District {item.request.district_id}; population {item.request.population_change_percent:+g}%; commercial growth {item.request.commercial_growth_percent:+g}%; green-space change {item.request.green_space_change_percent:+g}%.", styles["BodyText"]))
        for assumption in item.result.assumptions:
            story.append(_paragraph(f"- {assumption}", styles["SmallNote"]))
    story += [Spacer(1, 5*mm), _paragraph("Decision caution", styles["Section"]),
              _paragraph("This report compares model outputs only. It does not calculate project costs, implementation feasibility, distributional impacts or uncertainty ranges. Lower values should not be treated as a recommendation without considering service quality and policy objectives. All city data and knowledge references are synthetic.", styles["SmallNote"])]
    output = BytesIO()
    SimpleDocTemplate(output, pagesize=A4, rightMargin=17*mm, leftMargin=17*mm, topMargin=17*mm, bottomMargin=17*mm, title="LifeOS Twin Scenario Comparison", author="LifeOS Twin").build(story)
    return output.getvalue()


def build_investigation_report(result: dict) -> bytes:
    """Build an exportable audit report without exposing private document contents."""
    audit = result.get("audit_metadata", {})
    story, styles = _base_story(
        "LifeOS Twin · Investigation Audit Report",
        f"Run {audit.get('run_id', 'not recorded')} / Generated {audit.get('generated_at', 'unknown')}"
    )
    story += [
        _paragraph("Investigation question", styles["Section"]),
        _paragraph(result.get("question", ""), styles["BodyText"]),
        _paragraph("Scenario and recommendation", styles["Section"]),
        _paragraph(f"District: {result.get('district_id', 'unknown')}", styles["BodyText"]),
        _paragraph(result.get("recommendation", "No recommendation recorded."), styles["BodyText"]),
    ]
    scenario = result.get("scenario_result", {})
    metric_rows = [["Indicator", "Baseline", "Projected", "Change", "Unit"]]
    for key, label in (("traffic", "Traffic"), ("water", "Water"), ("electricity", "Electricity")):
        metric = scenario.get(key, {})
        metric_rows.append([label, str(metric.get("baseline", "—")), str(metric.get("projected", "—")),
                            f"{metric.get('change_percent', 0):+.2f}%", str(metric.get("unit", ""))])
    table = Table(metric_rows, repeatRows=1, colWidths=[28*mm, 31*mm, 31*mm, 25*mm, 35*mm])
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17384b")),
                               ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                               ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                               ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5dc")),
                               ("FONTSIZE", (0,0), (-1,-1), 8), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story += [_paragraph("Calculated indicators", styles["Section"]), table]
    decision = result.get("decision_analysis", {})
    story.append(_paragraph("Decision options", styles["Section"]))
    for option in decision.get("ranking", []):
        story.append(_paragraph(f"Rank {option.get('rank')}: {option.get('label')} — score {option.get('score')}/100; risk {option.get('risk_level')}", styles["BodyText"]))
    debate = result.get("specialist_debate", {})
    story.append(_paragraph("Specialist consensus", styles["Section"]))
    story.append(_paragraph(f"Consensus option: {debate.get('consensus_option', 'not recorded')}; votes: {debate.get('consensus_vote_count', 0)}/{debate.get('consensus_agent_count', 0)}", styles["BodyText"]))
    for item in debate.get("dissent", []):
        story.append(_paragraph(f"Dissent — {item.get('agent')}: {item.get('preferred_option')} — {item.get('reason')}", styles["BodyText"]))
    story.append(_paragraph("Verification and evidence scope", styles["Section"]))
    verification = result.get("verification", {})
    story.append(_paragraph(f"Verification: {'PASSED' if verification.get('passed') else 'NEEDS REVIEW'}; checks: {verification.get('checks', {})}", styles["SmallNote"]))
    story.append(_paragraph(f"Knowledge scope: {result.get('knowledge_scope', 'unknown')}. Evidence IDs: {', '.join(result.get('evidence_ids', [])) or 'none'}", styles["SmallNote"]))
    story.append(_paragraph("Audit fingerprint", styles["Section"]))
    story.append(_paragraph(f"Run ID: {audit.get('run_id', 'not recorded')}<br/>Input SHA-256: {audit.get('input_sha256', 'not recorded')}<br/>{audit.get('reproducibility_note', '')}", styles["SmallNote"]))
    story.append(_paragraph("Limitations", styles["Section"]))
    for limitation in result.get("limitations", []):
        story.append(_paragraph(f"- {limitation}", styles["SmallNote"]))
    output = BytesIO()
    SimpleDocTemplate(output, pagesize=A4, rightMargin=17*mm, leftMargin=17*mm, topMargin=17*mm, bottomMargin=17*mm, title="LifeOS Twin Investigation Audit", author="LifeOS Twin").build(story)
    return output.getvalue()
