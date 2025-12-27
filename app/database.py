"""
Supabase database connection for NBA shot data.
"""
import os
from functools import lru_cache
from typing import List, Optional

from supabase import create_client, Client

# Get from environment or Supabase dashboard
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


@lru_cache(maxsize=1)
def get_supabase() -> Optional[Client]:
    """Get Supabase client (cached)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY env vars.")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_players(search: str = "", min_shots: int = 100, limit: int = 100) -> List[dict]:
    """Get players matching search with shot counts."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    # Use RPC for aggregation (you'll need to create this function in Supabase)
    # For now, we'll do a simpler query
    query = supabase.table("shots").select("player_name")
    
    if search:
        query = query.ilike("player_name", f"%{search}%")
    
    # Get unique players with counts using RPC
    # This is a simplified version - for production, create an RPC function
    result = supabase.rpc("get_players_with_stats", {
        "search_term": search,
        "min_shot_count": min_shots,
        "result_limit": limit
    }).execute()
    
    return result.data if result.data else []


def get_player_shots(player_name: str, years: Optional[List[int]] = None, limit: int = 2500) -> List[dict]:
    """Get shots for a specific player."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    query = supabase.table("shots").select("*").eq("player_name", player_name)
    
    if years:
        query = query.in_("year", years)
    
    query = query.limit(limit)
    result = query.execute()
    
    return result.data if result.data else []


def get_player_stats(player_name: str, years: Optional[List[int]] = None) -> Optional[dict]:
    """Get aggregated stats for a player."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    # Call RPC function for aggregated stats
    result = supabase.rpc("get_player_stats", {
        "p_player_name": player_name,
        "p_years": years
    }).execute()
    
    return result.data[0] if result.data else None


def get_available_years() -> List[int]:
    """Get all available years in the database."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    result = supabase.rpc("get_available_years").execute()
    return [r["year"] for r in result.data] if result.data else []

