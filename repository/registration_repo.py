from typing import Optional
from config.supabase import supabase_admin

async def get_user_registrations(user_qr_code: str) -> list[dict]:
    try:
        res = await (
            supabase_admin.table("registrations")
            .select("id, event_id, registered_at, attended_at")
            .eq("user_qr_code", user_qr_code)
            .order("registered_at")
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def create_registration(reg_data: dict) -> dict:
    res = await (
        supabase_admin.table("registrations")
        .insert(reg_data)
        .execute()
    )
    return res.data[0]

async def get_registration_by_id(reg_id: str, select: str = "*", user_qr_code: Optional[str] = None) -> Optional[dict]:
    try:
        query = supabase_admin.table("registrations").select(select).eq("id", reg_id)
        if user_qr_code:
            query = query.eq("user_qr_code", user_qr_code)
            
        res = await query.single().execute()
        return res.data
    except Exception:
        return None

async def update_registration(reg_id: str, update_data: dict) -> None:
    await (
        supabase_admin.table("registrations")
        .update(update_data)
        .eq("id", reg_id)
        .execute()
    )

async def get_all_registrations(select: str = "user_qr_code, attended_at") -> list[dict]:
    try:
        res = await (
            supabase_admin.table("registrations")
            .select(select)
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def get_registrations_for_event(event_id: str, select: str = "user_qr_code, registered_at, attended_at") -> list[dict]:
    try:
        res = await (
            supabase_admin.table("registrations")
            .select(select)
            .eq("event_id", event_id)
            .order("registered_at")
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def delete_registrations_for_user(user_qr_code: str) -> None:
    await (
        supabase_admin.table("registrations")
        .delete()
        .eq("user_qr_code", user_qr_code)
        .execute()
    )

async def get_attended_count() -> int:
    try:
        res = await (
            supabase_admin.table("registrations")
            .select("user_qr_code")
            .not_.is_("attended_at", "null")
            .execute()
        )
        # Returns distinct users attended
        return len({r["user_qr_code"] for r in (res.data or [])})
    except Exception:
        return 0
