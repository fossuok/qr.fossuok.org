from typing import Optional

from config.supabase import supabase_admin


async def get_active_event_dict() -> Optional[dict]:
    try:
        res = await (
            supabase_admin.table("events")
            .select("id, title, description, location, start_time, end_time, image_url, whatsapp_link, is_active")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        return None

async def get_event_by_id(event_id: str, select: str = "*") -> Optional[dict]:
    try:
        res = await (
            supabase_admin.table("events")
            .select(select)
            .eq("id", event_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None

async def get_all_events() -> list[dict]:
    try:
        res = await (
            supabase_admin.table("events")
            .select("id, title, description, location, start_time, end_time, image_url, whatsapp_link, is_active, created_at")
            .order("is_active", desc=True)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def get_all_active_events() -> list[dict]:
    try:
        res = await (
            supabase_admin.table("events")
            .select("id, title, description, location, start_time, end_time, whatsapp_link")
            .eq("is_active", True)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []

async def deactivate_all_active_events_except(event_id: Optional[str] = None) -> None:
    query = supabase_admin.table("events").update({"is_active": False}).eq("is_active", True)
    if event_id:
        query = query.neq("id", event_id)
    await query.execute()

async def create_event(event_data: dict) -> None:
    await supabase_admin.table("events").insert(event_data).execute()

async def update_event(event_id: str, update_data: dict) -> None:
    await (
        supabase_admin.table("events")
        .update(update_data)
        .eq("id", event_id)
        .execute()
    )

async def delete_event(event_id: str) -> None:
    await (
        supabase_admin.table("events")
        .delete()
        .eq("id", event_id)
        .execute()
    )
