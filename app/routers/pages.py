import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import ExcelAIReport, ExcelCheckResult, ExcelUpload, ImprovementAction
from app.services.excel_reader import get_preview_data, read_excel_file

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_dashboard_stats(db: Session) -> dict:
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_uploads = db.query(ExcelUpload).count()
    monthly_diagnoses = db.query(ExcelUpload).filter(
        ExcelUpload.uploaded_at >= month_start,
        ExcelUpload.status == "completed",
    ).count()
    total_anomalies = db.query(ExcelCheckResult).count()
    pending_actions = db.query(ImprovementAction).filter(ImprovementAction.status != "完了").count()
    high_priority_actions = db.query(ImprovementAction).filter(
        ImprovementAction.priority == "高",
        ImprovementAction.status != "完了",
    ).count()

    recent_uploads = (
        db.query(ExcelUpload)
        .options(joinedload(ExcelUpload.ai_report), joinedload(ExcelUpload.check_results), joinedload(ExcelUpload.improvement_actions))
        .order_by(ExcelUpload.uploaded_at.desc())
        .limit(5)
        .all()
    )

    all_actions = (
        db.query(ImprovementAction)
        .options(joinedload(ImprovementAction.upload))
        .order_by(ImprovementAction.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_uploads": total_uploads,
        "monthly_diagnoses": monthly_diagnoses,
        "total_anomalies": total_anomalies,
        "pending_actions": pending_actions,
        "high_priority_actions": high_priority_actions,
        "recent_uploads": recent_uploads,
        "all_actions": all_actions,
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = _get_dashboard_stats(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "active": "dashboard", **stats})


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "active": "upload"})


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, db: Session = Depends(get_db)):
    uploads = (
        db.query(ExcelUpload)
        .options(joinedload(ExcelUpload.ai_report), joinedload(ExcelUpload.check_results), joinedload(ExcelUpload.improvement_actions))
        .order_by(ExcelUpload.uploaded_at.desc())
        .all()
    )
    history_items = []
    for u in uploads:
        history_items.append({
            "upload": u,
            "anomaly_count": len(u.check_results),
            "action_count": len(u.improvement_actions),
        })
    return templates.TemplateResponse("history.html", {"request": request, "active": "history", "history_items": history_items})


@router.get("/actions", response_class=HTMLResponse)
async def actions_page(request: Request, db: Session = Depends(get_db)):
    actions = (
        db.query(ImprovementAction)
        .options(joinedload(ImprovementAction.upload))
        .order_by(ImprovementAction.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("actions.html", {"request": request, "active": "actions", "actions": actions})


@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_db)):
    uploads = (
        db.query(ExcelUpload)
        .filter(ExcelUpload.status == "completed")
        .order_by(ExcelUpload.uploaded_at.desc())
        .all()
    )
    return templates.TemplateResponse("export.html", {"request": request, "active": "export", "uploads": uploads})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from app.config import AI_PROVIDER, OPENAI_MODEL
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active": "settings",
        "ai_provider": AI_PROVIDER,
        "openai_model": OPENAI_MODEL,
    })


@router.get("/detail/{upload_id}", response_class=HTMLResponse)
async def detail_page(upload_id: int, request: Request, db: Session = Depends(get_db)):
    upload = (
        db.query(ExcelUpload)
        .options(joinedload(ExcelUpload.check_results), joinedload(ExcelUpload.ai_report), joinedload(ExcelUpload.improvement_actions))
        .filter(ExcelUpload.id == upload_id)
        .first()
    )
    if not upload:
        return templates.TemplateResponse("error.html", {"request": request, "message": "診断結果が見つかりません"}, status_code=404)

    preview = None
    try:
        df = read_excel_file(upload.file_path)
        preview = get_preview_data(df)
    except Exception:
        preview = {"columns": [], "rows": [], "total_rows": 0, "total_columns": 0}

    ai_report_data = {}
    if upload.ai_report:
        ai_report_data = json.loads(upload.ai_report.report_json)

    return templates.TemplateResponse("detail.html", {
        "request": request,
        "active": "history",
        "upload": upload,
        "preview": preview,
        "ai_report": ai_report_data,
        "check_results": upload.check_results,
        "actions": upload.improvement_actions,
    })


@router.get("/report/{upload_id}", response_class=HTMLResponse)
async def report_page(upload_id: int, request: Request, db: Session = Depends(get_db)):
    upload = (
        db.query(ExcelUpload)
        .options(joinedload(ExcelUpload.check_results), joinedload(ExcelUpload.ai_report), joinedload(ExcelUpload.improvement_actions))
        .filter(ExcelUpload.id == upload_id)
        .first()
    )
    if not upload:
        return templates.TemplateResponse("error.html", {"request": request, "message": "診断結果が見つかりません"}, status_code=404)

    ai_report_data = {}
    if upload.ai_report:
        ai_report_data = json.loads(upload.ai_report.report_json)

    return templates.TemplateResponse("report.html", {
        "request": request,
        "active": "history",
        "upload": upload,
        "ai_report": ai_report_data,
        "check_results": upload.check_results,
        "actions": upload.improvement_actions,
        "anomaly_count": len(upload.check_results),
    })
