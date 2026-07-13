"""
Analysis Router — /api/analysis/*
File upload, run analysis, history, PDF download
"""
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from backend.utils.database import get_db
from backend.utils.auth import get_current_user
from backend.models.db_models import User, Analysis
from backend.models.schemas import AnalysisOut, AnalysisSummary
from backend.services.file_analyzer import analyze_file
from backend.services.ai_service import run_analysis
from backend.services.pdf_service import generate_pdf

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

UPLOAD_DIR  = os.getenv("UPLOAD_DIR",  "./uploads")
REPORTS_DIR = os.getenv("REPORTS_DIR", "./reports")
MAX_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

os.makedirs(UPLOAD_DIR,  exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


@router.post("/run", response_model=AnalysisOut)
async def run(
    target_type:   str        = Form(...),
    analysis_mode: str        = Form(...),
    language:      str        = Form("hinglish"),
    input_text:    str        = Form(""),
    title:         str        = Form(""),
    file:          Optional[UploadFile] = File(None),
    db:            AsyncSession = Depends(get_db),
    user:          User         = Depends(get_current_user),
):
    # Validate
    valid_targets = {"software","firmware","hardware","code","network"}
    valid_modes   = {"full","components","logic","security","bugs"}
    if target_type not in valid_targets:
        raise HTTPException(400, f"Invalid target_type. Choose from: {valid_targets}")
    if analysis_mode not in valid_modes:
        raise HTTPException(400, f"Invalid analysis_mode. Choose from: {valid_modes}")
    if not input_text.strip() and not file:
        raise HTTPException(400, "Provide either input_text or a file")

    # ── Handle file upload ────────────────────────────────────────────────────
    file_path  = ""
    file_name  = ""
    file_size  = 0
    file_type  = ""
    file_info  = None

    if file and file.filename:
        content = await file.read()
        if len(content) > MAX_SIZE_MB * 1024 * 1024:
            raise HTTPException(413, f"File too large. Max {MAX_SIZE_MB}MB")

        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        async with aiofiles.open(file_path, "wb") as f_out:
            await f_out.write(content)

        file_name = file.filename
        file_size = len(content)
        file_info = await analyze_file(file_path, file_name, target_type)
        file_info["file_path_original"] = file_path   # needed for vision model
        file_type = file_info.get("file_type", "")

    # ── Create DB record ──────────────────────────────────────────────────────
    record = Analysis(
        user_id       = user.id,
        title         = title or (file_name or input_text[:60] or "Analysis"),
        target_type   = target_type,
        analysis_mode = analysis_mode,
        language      = language,
        input_text    = input_text[:10000],
        file_name     = file_name,
        file_path     = file_path,
        file_size     = file_size,
        file_type     = file_type,
        status        = "running",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # ── Run AI analysis ────────────────────────────────────────────────────────
    ai_result = await run_analysis(
        target_type   = target_type,
        analysis_mode = analysis_mode,
        language      = language,
        user_text     = input_text,
        file_info     = file_info,
    )

    # ── Update DB record ──────────────────────────────────────────────────────
    record.result_md   = ai_result["result_md"]
    record.tokens_used = ai_result["tokens_used"]
    record.duration_ms = ai_result["duration_ms"]
    record.risk_level  = ai_result.get("risk_level", "Unknown")
    record.complexity  = ai_result.get("complexity", "Unknown")
    record.confidence  = ai_result.get("confidence", 0.0)
    record.status      = "done" if ai_result["success"] else "error"
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/history", response_model=list[AnalysisSummary])
async def history(
    limit:  int = 20,
    offset: int = 0,
    db:     AsyncSession = Depends(get_db),
    user:   User         = Depends(get_current_user),
):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == user.id)
        .order_by(desc(Analysis.created_at))
        .limit(min(limit, 50))
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_one(
    analysis_id: int,
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Analysis not found")
    return record


@router.get("/{analysis_id}/pdf")
async def download_pdf(
    analysis_id: int,
    background:  BackgroundTasks,
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Analysis not found")

    # Generate PDF if not already done
    if not record.report_path or not os.path.exists(record.report_path):
        pdf_path = generate_pdf(
            analysis_id   = record.id,
            username      = user.username,
            target_type   = record.target_type,
            analysis_mode = record.analysis_mode,
            file_name     = record.file_name,
            result_md     = record.result_md,
            risk_level    = record.risk_level,
            complexity    = record.complexity,
            confidence    = record.confidence,
            tokens_used   = record.tokens_used,
            reports_dir   = REPORTS_DIR,
        )
        record.report_path = pdf_path
        await db.commit()

    return FileResponse(
        path          = record.report_path,
        media_type    = "application/pdf",
        filename      = f"re-report-{analysis_id:06d}.pdf",
    )


@router.delete("/{analysis_id}", status_code=204)
async def delete_analysis(
    analysis_id: int,
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Analysis not found")
    # Clean up files
    for path in [record.file_path, record.report_path]:
        if path and os.path.exists(path):
            try: os.remove(path)
            except: pass
    await db.delete(record)
    await db.commit()
