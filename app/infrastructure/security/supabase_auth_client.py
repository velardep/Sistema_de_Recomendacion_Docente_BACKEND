import httpx

class SupabaseAuthClient:
    def __init__(self, supabase_url: str, anon_key: str):
        self.base = supabase_url.rstrip("/")
        self.anon_key = anon_key

    async def signup(self, email: str, password: str) -> dict:
        url = f"{self.base}/auth/v1/signup"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

    async def login_password(self, email: str, password: str) -> dict:
        url = f"{self.base}/auth/v1/token?grant_type=password"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

    async def get_user(self, access_token: str) -> dict:
        url = f"{self.base}/auth/v1/user"
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.json()
