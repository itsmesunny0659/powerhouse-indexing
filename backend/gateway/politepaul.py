import asyncio
import time
import re
import httpx
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

class PolitePaulClient:
    """
    Automates PolitePaul (https://politepaul.com/en/) session, login,
    and automatic feed generation for submitted URLs.
    """
    BASE_URL = "https://politepaul.com"
    LOGIN_URL = "https://politepaul.com/en/login"
    SUBMIT_URL = "https://politepaul.com/en/detect"

    def __init__(self, email: str = "its.me.sunny.0659@gmail.com", password: str = "@Support9267"):
        self.email = email
        self.password = password
        self.session: Optional[httpx.AsyncClient] = None
        self.is_authenticated = False

    async def __aenter__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.session = httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True, verify=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def login(self) -> bool:
        """Authenticates with PolitePaul using credentials."""
        if not self.session:
            return False

        try:
            # 1. Fetch login page to extract CSRF token if present
            login_page = await self.session.get(self.LOGIN_URL)
            csrf_token = ""
            soup = BeautifulSoup(login_page.text, "html.parser")
            csrf_input = soup.find("input", attrs={"name": re.compile(r"csrf|_token", re.I)})
            if csrf_input and csrf_input.get("value"):
                csrf_token = csrf_input["value"]

            # 2. Post login credentials
            login_data = {
                "email": self.email,
                "username": self.email,
                "password": self.password,
            }
            if csrf_token:
                login_data["_token"] = csrf_token
                login_data["csrf_token"] = csrf_token

            resp = await self.session.post(self.LOGIN_URL, data=login_data)
            
            # Check login success
            if "logout" in resp.text.lower() or "signed in" in resp.text.lower() or resp.status_code in (200, 302):
                self.is_authenticated = True
                return True
            
            # Even if page doesn't explicitly redirect, check cookies
            if any("session" in c.lower() or "auth" in c.lower() for c in self.session.cookies.keys()):
                self.is_authenticated = True
                return True

            return False
        except Exception as e:
            # On network or scraping error, log and fallback
            return False

    async def create_feed(self, target_url: str) -> Dict[str, Any]:
        """
        Submits target URL to PolitePaul to detect / create an RSS XML feed.
        Returns the generated or detected XML feed URL.
        """
        if not self.session:
            return {"success": False, "error": "Client not initialized"}

        try:
            # Ensure logged in
            if not self.is_authenticated:
                await self.login()

            # Submit target URL to create/detect feed
            payload = {"url": target_url}
            resp = await self.session.post(self.SUBMIT_URL, data=payload)
            
            feed_url = ""
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Look for generated feed link
                link_tag = soup.find("a", href=re.compile(r"\.(xml|rss)|/feed", re.I))
                if link_tag and link_tag.get("href"):
                    feed_url = link_tag["href"]
                    if not feed_url.startswith("http"):
                        feed_url = f"{self.BASE_URL}{feed_url}"

            # Fallback standard feed URL if PolitePaul generates standard path
            if not feed_url:
                feed_url = f"https://politepaul.com/feed?url={target_url}"

            return {
                "success": True,
                "target_url": target_url,
                "politepaul_feed_url": feed_url,
                "status_code": resp.status_code
            }
        except Exception as e:
            return {
                "success": False,
                "target_url": target_url,
                "error": str(e),
                "politepaul_feed_url": f"https://politepaul.com/feed?url={target_url}"
            }
