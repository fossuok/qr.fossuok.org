import asyncio
from typing import Optional
from fastapi import HTTPException
from config.supabase import supabase_admin
from models.event import Event

async def get_active_event() -> Optional[Event]:
    """
    Fetches the first active event from the database.
    """
    try:
        response = await asyncio.to_thread(
            supabase_admin.table("events")
            .select("*")
            .eq("is_active", True)
            .limit(1)
            .execute
        )
        if response.data:
            return Event(**response.data[0])
        return None
    except Exception as e:
        # If the table doesn't exist yet or other error, return None
        return None

async def get_event_by_id(event_id: str) -> Optional[Event]:
    """
    Fetches an event by its ID.
    """
    try:
        response = await asyncio.to_thread(
            supabase_admin.table("events")
            .select("*")
            .eq("id", event_id)
            .single()
            .execute
        )
        if response.data:
            return Event(**response.data)
        return None
    except Exception:
        return None
