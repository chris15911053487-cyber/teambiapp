"""Auth endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.auth_service import exchange_app_credentials
from app.settings import load_company_profiles

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    company_name: str = Field(..., description="企业显示名")
    passphrase: str = Field(..., description="当日暗号 YYYYMMDD")


@router.post("/token")
def post_token(body: TokenRequest):
    profiles = load_company_profiles()
    if not profiles:
        raise HTTPException(
            status_code=503,
            detail="未配置企业凭证：请设置环境变量 TB_COMPANY_PROFILES_JSON",
        )
    row = profiles.get(body.company_name)
    if not row:
        raise HTTPException(status_code=404, detail="未知企业")
    try:
        result = exchange_app_credentials(
            app_id=row["app_id"],
            app_secret=row["app_secret"],
            tenant_id=row["tenant_id"],
            company_name=body.company_name,
            passphrase=body.passphrase,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"换票失败: {e}") from e
    return result.model_dump()
