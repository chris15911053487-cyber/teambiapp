"""Company list (names only)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.settings import load_company_profiles

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def list_companies():
    p = load_company_profiles()
    if not p:
        raise HTTPException(
            status_code=503,
            detail="未配置 TB_COMPANY_PROFILES_JSON",
        )
    return {"companies": [{"name": k} for k in p.keys()]}
