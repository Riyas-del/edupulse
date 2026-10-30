import os
import httpx
from typing import Optional, Dict, Any, List

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

class SupabaseClient:
    def __init__(self, url: str = SUPABASE_URL, key: str = SUPABASE_KEY):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    async def get_table(self, table_name: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.url}/rest/v1/{table_name}", headers=self.headers, params=params)
            if res.status_code == 200:
                return res.json()
            return []

    async def insert_record(self, table_name: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_configured:
            return None
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.url}/rest/v1/{table_name}", headers=self.headers, json=record)
            if res.status_code in (200, 201):
                return res.json()
            return None

    async def update_record(self, table_name: str, record_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_configured:
            return None
        async with httpx.AsyncClient() as client:
            res = await client.patch(f"{self.url}/rest/v1/{table_name}?id=eq.{record_id}", headers=self.headers, json=updates)
            if res.status_code in (200, 204):
                return updates
            return None

supabase_client = SupabaseClient()
