from datetime import datetime, timezone
from typing import Optional

from config.supabase import supabase_admin

async def get_user_by_github_id(github_id: str) -> Optional[dict]:
    try:
        res = await (
            supabase_admin.table("users")
            .select("github_id, name, email, avatar_url, qr_code_data, role, registered_event_id, attended_at")
            .eq("github_id", github_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        return None

async def create_user(user_data: dict) -> dict:
    res = await supabase_admin.table("users").insert(user_data).execute()
    return res.data[0]

async def update_user_by_github_id(github_id: str, update_data: dict) -> None:
    await (
        supabase_admin.table("users")
        .update(update_data)
        .eq("github_id", github_id)
        .execute()
    )

async def get_user_by_qr_code(qr_code_data: str, select: str = "*") -> Optional[dict]:
    try:
        res = await (
            supabase_admin.table("users")
            .select(select)
            .eq("qr_code_data", qr_code_data)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        return None

async def get_users_by_qr_codes(qr_codes: list[str], select: str = "*") -> list[dict]:
    try:
        res = await (
            supabase_admin.table("users")
            .select(select)
            .in_("qr_code_data", qr_codes)
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def update_user_by_qr_code(qr_code_data: str, update_data: dict) -> None:
    await (
        supabase_admin.table("users")
        .update(update_data)
        .eq("qr_code_data", qr_code_data)
        .execute()
    )

async def get_paginated_users(offset: int, limit: int, search: str = "") -> tuple[list[dict], int]:
    query = (
        supabase_admin.table("users")
        .select("github_id, name, email, avatar_url, role, created_at, participant_type, student_id, university, study_year, organization, job_role", count="exact")
        .order("role")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if search:
        query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")
    
    res = await query.execute()
    return res.data or [], res.count or 0

async def get_all_participants() -> list[dict]:
    try:
        res = await (
            supabase_admin.table("users")
            .select("qr_code_data, name, email, role")
            .eq("role", "participant")
            .order("name")
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def get_registered_participant_count() -> int:
    try:
        res = await supabase_admin.table("users").select("id", count="exact").eq("role", "participant").execute()
        return res.count or 0
    except Exception:
        return 0

async def delete_user_by_github_id(github_id: str) -> None:
    await (
        supabase_admin.table("users")
        .delete()
        .eq("github_id", github_id)
        .execute()
    )

async def nullify_registered_event_id(event_id: str) -> None:
    await (
        supabase_admin.table("users")
        .update({"registered_event_id": None})
        .eq("registered_event_id", event_id)
        .execute()
    )
