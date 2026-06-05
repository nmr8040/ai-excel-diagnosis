from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import ExcelAIReport, ExcelCheckResult, ExcelUpload, ImprovementAction
from app.services.diagnosis_service import run_full_diagnosis, save_uploaded_file
from app.services.export_service import export_report_csv, export_report_excel, export_report_pdf

router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    allowed = {".xlsx", ".xls", ".csv"}
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in allowed:
        raise HTTPException(400, f"対応形式: {', '.join(allowed)}")

    content = await file.read()
    file_path, file_type = save_uploaded_file(content, file.filename)

    upload = ExcelUpload(
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        status="uploaded",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    result = run_full_diagnosis(db, upload)

    return {
        "id": upload.id,
        "file_name": upload.file_name,
        "status": upload.status,
        "business_type": upload.detected_business_type,
        "row_count": upload.row_count,
        "anomaly_count": len(result["check_results"]),
        "redirect_url": f"/report/{upload.id}",
    }


@router.get("/uploads")
async def list_uploads(db: Session = Depends(get_db)):
    uploads = db.query(ExcelUpload).order_by(ExcelUpload.uploaded_at.desc()).all()
    return [
        {
            "id": u.id,
            "file_name": u.file_name,
            "business_type": u.detected_business_type,
            "row_count": u.row_count,
            "status": u.status,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
        }
        for u in uploads
    ]


@router.get("/uploads/{upload_id}")
async def get_upload(upload_id: int, db: Session = Depends(get_db)):
    upload = (
        db.query(ExcelUpload)
        .options(joinedload(ExcelUpload.check_results), joinedload(ExcelUpload.ai_report), joinedload(ExcelUpload.improvement_actions))
        .filter(ExcelUpload.id == upload_id)
        .first()
    )
    if not upload:
        raise HTTPException(404, "診断結果が見つかりません")
    return {"upload": upload}


@router.post("/actions")
async def create_action(
    upload_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("中"),
    owner: str = Form(""),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
):
    action = ImprovementAction(
        upload_id=upload_id,
        title=title,
        description=description,
        priority=priority,
        owner=owner,
        due_date=due_date or None,
        status="未着手",
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return {"id": action.id, "message": "改善アクションを作成しました"}


@router.put("/actions/{action_id}")
async def update_action(
    action_id: int,
    title: str = Form(None),
    description: str = Form(None),
    priority: str = Form(None),
    owner: str = Form(None),
    due_date: str = Form(None),
    status: str = Form(None),
    db: Session = Depends(get_db),
):
    action = db.query(ImprovementAction).filter(ImprovementAction.id == action_id).first()
    if not action:
        raise HTTPException(404, "アクションが見つかりません")

    if title is not None:
        action.title = title
    if description is not None:
        action.description = description
    if priority is not None:
        action.priority = priority
    if owner is not None:
        action.owner = owner
    if due_date is not None:
        action.due_date = due_date or None
    if status is not None:
        action.status = status

    db.commit()
    return {"message": "更新しました"}


@router.get("/export/{upload_id}/{format}")
async def export_report(upload_id: int, format: str, db: Session = Depends(get_db)):
    upload = db.query(ExcelUpload).filter(ExcelUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "診断結果が見つかりません")

    check_results = db.query(ExcelCheckResult).filter(ExcelCheckResult.upload_id == upload_id).all()
    ai_report = db.query(ExcelAIReport).filter(ExcelAIReport.upload_id == upload_id).first()
    actions = db.query(ImprovementAction).filter(ImprovementAction.upload_id == upload_id).all()

    base_name = upload.file_name.rsplit(".", 1)[0]

    def _content_disposition(filename: str) -> str:
        ascii_name = "report" + filename[filename.rfind("."):]
        encoded = quote(filename)
        return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"

    if format == "csv":
        content = export_report_csv(upload, check_results, ai_report, actions)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": _content_disposition(f"{base_name}_report.csv")},
        )
    if format == "excel":
        content = export_report_excel(upload, check_results, ai_report, actions)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": _content_disposition(f"{base_name}_report.xlsx")},
        )
    if format == "pdf":
        content = export_report_pdf(upload, check_results, ai_report, actions)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": _content_disposition(f"{base_name}_report.pdf")},
        )

    raise HTTPException(400, "対応形式: csv, excel, pdf")
