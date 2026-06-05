import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.models import ExcelAIReport, ExcelCheckResult, ExcelUpload, ImprovementAction
from app.services.action_creator import create_improvement_actions
from app.services.ai_analyzer import generate_ai_excel_report
from app.services.basic_checker import analyze_excel_basic
from app.services.excel_reader import get_data_summary, get_preview_data, read_excel_file


def save_uploaded_file(file_content: bytes, original_filename: str) -> tuple[str, str]:
    ext = Path(original_filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name
    file_path.write_bytes(file_content)
    return str(file_path), ext.lstrip(".")


def run_full_diagnosis(db: Session, upload: ExcelUpload) -> dict:
    df = read_excel_file(upload.file_path)
    preview = get_preview_data(df)
    summary = get_data_summary(df)

    upload.row_count = summary["row_count"]
    upload.column_count = summary["column_count"]
    upload.status = "checking"

    check_results_raw = analyze_excel_basic(df)
    db.query(ExcelCheckResult).filter(ExcelCheckResult.upload_id == upload.id).delete()

    for r in check_results_raw:
        db.add(ExcelCheckResult(
            upload_id=upload.id,
            check_type=r["check_type"],
            target_column=r.get("target_column"),
            target_row=r.get("target_row"),
            message=r["message"],
            severity=r["severity"],
        ))

    upload.status = "ai_analyzing"
    db.flush()

    ai_input = {
        **summary,
        "check_results": check_results_raw,
        "file_name": upload.file_name,
    }
    ai_report_data = generate_ai_excel_report(ai_input)

    upload.detected_business_type = ai_report_data.get("business_type", "汎用業務管理")
    upload.status = "completed"

    db.query(ExcelAIReport).filter(ExcelAIReport.upload_id == upload.id).delete()
    improvements_text = json.dumps(ai_report_data.get("top_improvements", []), ensure_ascii=False)
    db.add(ExcelAIReport(
        upload_id=upload.id,
        report_json=json.dumps(ai_report_data, ensure_ascii=False),
        summary=ai_report_data.get("summary", ""),
        risk_level=ai_report_data.get("risk_level", "中"),
        improvement_suggestions=improvements_text,
    ))

    db.query(ImprovementAction).filter(ImprovementAction.upload_id == upload.id).delete()
    actions_data = create_improvement_actions(ai_report_data, check_results_raw)
    for a in actions_data:
        db.add(ImprovementAction(
            upload_id=upload.id,
            title=a["title"],
            description=a["description"],
            priority=a["priority"],
            owner=a.get("owner", ""),
            due_date=a.get("due_date"),
            status=a["status"],
        ))

    db.commit()
    db.refresh(upload)

    return {
        "upload": upload,
        "preview": preview,
        "check_results": check_results_raw,
        "ai_report": ai_report_data,
        "actions": actions_data,
    }
