from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExcelUpload(Base):
    __tablename__ = "excel_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    detected_business_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="uploaded")

    check_results: Mapped[list["ExcelCheckResult"]] = relationship(back_populates="upload", cascade="all, delete-orphan")
    ai_report: Mapped[Optional["ExcelAIReport"]] = relationship(back_populates="upload", cascade="all, delete-orphan", uselist=False)
    improvement_actions: Mapped[list["ImprovementAction"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class ExcelCheckResult(Base):
    __tablename__ = "excel_check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("excel_uploads.id"), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_column: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    upload: Mapped["ExcelUpload"] = relationship(back_populates="check_results")


class ExcelAIReport(Base):
    __tablename__ = "excel_ai_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("excel_uploads.id"), nullable=False, unique=True, index=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    improvement_suggestions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    upload: Mapped["ExcelUpload"] = relationship(back_populates="ai_report")


class ImprovementAction(Base):
    __tablename__ = "improvement_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("excel_uploads.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="中")
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="未着手")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    upload: Mapped["ExcelUpload"] = relationship(back_populates="improvement_actions")
