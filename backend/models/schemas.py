"""
Pydantic schemas — request/response models
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    username:     str
    user_id:      int


class UserOut(BaseModel):
    id:         int
    username:   str
    email:      str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Analysis ──────────────────────────────────────────────────────────────────
class AnalysisRequest(BaseModel):
    target_type:   str
    analysis_mode: str
    language:      str = "hinglish"
    input_text:    str = ""
    title:         Optional[str] = None


class AnalysisOut(BaseModel):
    id:            int
    title:         str
    target_type:   str
    analysis_mode: str
    language:      str
    file_name:     str
    file_size:     int
    file_type:     str
    result_md:     str
    report_path:   str
    risk_level:    str
    complexity:    str
    confidence:    float
    tokens_used:   int
    duration_ms:   int
    status:        str
    created_at:    datetime
    model_config = {"from_attributes": True}


class AnalysisSummary(BaseModel):
    id:            int
    title:         str
    target_type:   str
    analysis_mode: str
    file_name:     str
    risk_level:    str
    complexity:    str
    status:        str
    created_at:    datetime
    model_config = {"from_attributes": True}
