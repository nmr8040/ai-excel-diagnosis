import io
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))


def export_report_csv(upload, check_results, ai_report, actions) -> bytes:
    rows = []

    rows.append(["=== 診断レポート ===", ""])
    rows.append(["ファイル名", upload.file_name])
    rows.append(["業務種別", upload.detected_business_type or ""])
    rows.append(["データ件数", upload.row_count])
    rows.append(["異常件数", len(check_results)])
    rows.append(["", ""])

    if ai_report:
        report_data = json.loads(ai_report.report_json)
        rows.append(["=== AI診断サマリー ===", ""])
        rows.append(["要約", ai_report.summary or ""])
        rows.append(["リスクレベル", ai_report.risk_level or ""])
        rows.append(["AIコメント", report_data.get("ai_comment", "")])
        rows.append(["", ""])

        rows.append(["=== 重要な指摘 ===", ""])
        for issue in report_data.get("top_issues", [])[:5]:
            rows.append([issue.get("title", ""), issue.get("description", "")])
        rows.append(["", ""])

        rows.append(["=== 改善ポイント ===", ""])
        for imp in report_data.get("top_improvements", [])[:5]:
            rows.append([imp.get("title", ""), imp.get("description", "")])

    rows.append(["", ""])
    rows.append(["=== 基本チェック結果 ===", ""])
    rows.append(["種別", "列", "重要度", "メッセージ"])
    for r in check_results:
        rows.append([r.check_type, r.target_column or "", r.severity, r.message])

    rows.append(["", ""])
    rows.append(["=== 改善アクション ===", ""])
    rows.append(["タイトル", "優先度", "担当者", "期限", "ステータス"])
    for a in actions:
        rows.append([a.title, a.priority, a.owner or "", a.due_date or "", a.status])

    df = pd.DataFrame(rows)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, encoding="utf-8-sig")
    return buffer.getvalue().encode("utf-8-sig")


def export_report_excel(upload, check_results, ai_report, actions) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_rows = [
            ["ファイル名", upload.file_name],
            ["業務種別", upload.detected_business_type or ""],
            ["データ件数", upload.row_count],
            ["異常件数", len(check_results)],
        ]
        if ai_report:
            report_data = json.loads(ai_report.report_json)
            summary_rows.extend([
                ["リスクレベル", ai_report.risk_level or ""],
                ["要約", ai_report.summary or ""],
                ["AIコメント", report_data.get("ai_comment", "")],
            ])
        pd.DataFrame(summary_rows, columns=["項目", "内容"]).to_excel(writer, sheet_name="サマリー", index=False)

        if ai_report:
            report_data = json.loads(ai_report.report_json)
            issues_df = pd.DataFrame(report_data.get("top_issues", []))
            if not issues_df.empty:
                issues_df.to_excel(writer, sheet_name="重要指摘", index=False)
            imp_df = pd.DataFrame(report_data.get("top_improvements", []))
            if not imp_df.empty:
                imp_df.to_excel(writer, sheet_name="改善ポイント", index=False)

        checks_df = pd.DataFrame([
            {"種別": r.check_type, "列": r.target_column, "行": r.target_row, "重要度": r.severity, "メッセージ": r.message}
            for r in check_results
        ])
        if not checks_df.empty:
            checks_df.to_excel(writer, sheet_name="基本チェック", index=False)

        actions_df = pd.DataFrame([
            {"タイトル": a.title, "内容": a.description, "優先度": a.priority, "担当者": a.owner, "期限": a.due_date, "ステータス": a.status}
            for a in actions
        ])
        if not actions_df.empty:
            actions_df.to_excel(writer, sheet_name="改善アクション", index=False)

    buffer.seek(0)
    return buffer.read()


def export_report_pdf(upload, check_results, ai_report, actions) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontName="HeiseiMin-W3", fontSize=16)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontName="HeiseiMin-W3", fontSize=12)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="HeiseiMin-W3", fontSize=9)

    story = []
    story.append(Paragraph("AI Excel 診断レポート", title_style))
    story.append(Spacer(1, 10))

    summary_data = [
        ["ファイル名", upload.file_name],
        ["業務種別", upload.detected_business_type or "未推定"],
        ["データ件数", str(upload.row_count)],
        ["異常件数", str(len(check_results))],
    ]
    if ai_report:
        summary_data.append(["リスクレベル", ai_report.risk_level or ""])
    t = Table(summary_data, colWidths=[80 * mm, 90 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "HeiseiMin-W3"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    if ai_report:
        report_data = json.loads(ai_report.report_json)
        story.append(Paragraph("AI診断サマリー", heading_style))
        story.append(Paragraph(ai_report.summary or "", body_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph(f"AIコメント: {report_data.get('ai_comment', '')}", body_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("重要な指摘 TOP5", heading_style))
        for issue in report_data.get("top_issues", [])[:5]:
            story.append(Paragraph(f"・[{issue.get('priority', '')}] {issue.get('title', '')}: {issue.get('description', '')}", body_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("改善ポイント TOP5", heading_style))
        for imp in report_data.get("top_improvements", [])[:5]:
            story.append(Paragraph(f"・[{imp.get('priority', '')}] {imp.get('title', '')}: {imp.get('description', '')}", body_style))
        story.append(Spacer(1, 10))

    story.append(Paragraph("改善アクション", heading_style))
    for a in actions[:10]:
        story.append(Paragraph(f"・[{a.priority}] {a.title}（{a.status}）", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
