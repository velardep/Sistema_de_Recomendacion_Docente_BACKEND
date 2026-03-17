from typing import Optional

import httpx
import asyncio


class SupabaseAuthClient:
    def __init__(self, supabase_url: str, anon_key: str, client: Optional[httpx.AsyncClient] = None):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.client = client

        self.timeout = httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0)


    async def signup(self, email: str, password: str) -> dict:
        url = f"{self.base}/auth/v1/signup"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

    async def login_password(self, email: str, password: str) -> dict:
        url = f"{self.base}/auth/v1/token?grant_type=password"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

    async def get_user(self, access_token: str) -> dict:
        url = f"{self.base}/auth/v1/user"
        headers = {"apikey": self.anon_key, "Authorization": f"Bearer {access_token}"}

        last_exc = None
        client = self.client or httpx.AsyncClient(timeout=self.timeout)
        close_after = self.client is None

        try:
            for attempt in range(3):
                try:
                    r = await client.get(url, headers=headers)
                    r.raise_for_status()
                    return r.json()
                except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                    last_exc = e
                    await asyncio.sleep(0.4 * (attempt + 1))
            raise httpx.ReadTimeout(f"Supabase auth timeout after retries: {last_exc}")
        finally:
            if close_after:
                await client.aclose()

