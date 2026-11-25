"""
Enterprise Google Indexing API Rotator (Python Engine)
Loads all Service Account JSON keys from service_accounts/ directory and data/keys.json.
Rotates accounts round-robin with automatic 24h cooldown on 429 quota exhaustion.
Directly invokes Google Indexing API v3 (URL_UPDATED).
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
import aiohttp
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class GCPIndexingRotator:
    def __init__(self, keys_dir: str = "service_accounts", keys_file: str = "data/keys.json"):
        self.keys_dir = keys_dir
        self.keys_file = keys_file
        self.account_pool: List[Dict[str, Any]] = []
        self.current_idx: int = 0
        self.cooldowns: Dict[str, float] = {}  # email -> timestamp
        self.token_cache: Dict[str, tuple] = {}  # email -> (token, expire_ts)
        self.load_keys()

    def load_keys(self):
        """Loads keys from service_accounts/ folder and data/keys.json."""
        self.account_pool.clear()
        
        # 1. Load from service_accounts/*.json
        if os.path.isdir(self.keys_dir):
            for fname in os.listdir(self.keys_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.keys_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "client_email" in data and "private_key" in data:
                                self.account_pool.append({
                                    "id": fname,
                                    "email": data["client_email"],
                                    "key_data": data
                                })
                    except Exception as e:
                        logger.error(f"[GCP Rotator] Failed to load {fname}: {e}")

        # 2. Load from data/keys.json array
        if os.path.isfile(self.keys_file):
            try:
                with open(self.keys_file, "r", encoding="utf-8") as f:
                    keys_list = json.load(f)
                    if isinstance(keys_list, list):
                        for i, data in enumerate(keys_list):
                            if isinstance(data, dict) and "client_email" in data and "private_key" in data:
                                # Avoid duplicate emails
                                if not any(acc["email"] == data["client_email"] for acc in self.account_pool):
                                    self.account_pool.append({
                                        "id": f"keys_json_{i}_{data.get('project_id', 'sa')}",
                                        "email": data["client_email"],
                                        "key_data": data
                                    })
            except Exception as e:
                logger.error(f"[GCP Rotator] Failed to load {self.keys_file}: {e}")

        # 3. Load from data/vault_keys.dat or environment variables (Production Safe Vault)
        vault_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "vault_keys.dat"),
            "data/vault_keys.dat",
            os.path.join(os.getcwd(), "data", "vault_keys.dat")
        ]
        vault_raw = None
        for vp in vault_candidates:
            if os.path.isfile(vp):
                try:
                    with open(vp, "r", encoding="utf-8") as vf:
                        vault_raw = vf.read().strip()
                    if vault_raw:
                        break
                except Exception:
                    pass

        if not vault_raw:
            vault_raw = os.environ.get("GCP_SA_KEYS_BASE64") or os.environ.get("GCP_KEYS_VAULT")

        if vault_raw:
            try:
                import zlib
                import base64
                decompressed = zlib.decompress(base64.b64decode(vault_raw.encode("ascii")))
                vault_keys = json.loads(decompressed)
                if isinstance(vault_keys, list):
                    for i, data in enumerate(vault_keys):
                        if isinstance(data, dict) and "client_email" in data and "private_key" in data:
                            if not any(acc["email"] == data["client_email"] for acc in self.account_pool):
                                self.account_pool.append({
                                    "id": f"vault_{i}_{data.get('project_id', 'sa')}",
                                    "email": data["client_email"],
                                    "key_data": data
                                })
            except Exception as e:
                logger.error(f"[GCP Rotator] Failed to decompress vault keys: {e}")

        # Prioritize verified working Search Console owner accounts (instantreelsdownload, myindexingtool005, myindexingtool004)
        self.account_pool.sort(key=lambda a: 0 if any(x in a.get("email", "") for x in ("instantreelsdownload", "myindexingtool005", "myindexingtool004")) else 1)

        logger.info(f"[GCP Rotator] Loaded {len(self.account_pool)} service accounts.")

    def _is_cooling_down(self, email: str) -> bool:
        if email in self.cooldowns:
            if time.time() > self.cooldowns[email]:
                del self.cooldowns[email]
                return False
            return True
        return False

    def get_next_account(self) -> Optional[Dict[str, Any]]:
        """Returns the next non-cooldown account, keeping working verified accounts prioritized."""
        if not self.account_pool:
            return None

        # Filter available non-cooldown accounts
        available = [acc for acc in self.account_pool if not self._is_cooling_down(acc["email"])]
        if not available:
            return None

        # Prefer verified Search Console owner accounts and rotate among them
        preferred = [acc for acc in available if any(x in acc.get("email", "") for x in ("instantreelsdownload", "myindexingtool005", "myindexingtool004"))]
        pool = preferred if preferred else available

        acc = pool[self.current_idx % len(pool)]
        self.current_idx = (self.current_idx + 1) % len(pool)
        return acc

    def _get_access_token(self, email: str, key_data: Dict[str, Any]) -> str:
        """Generates Google OAuth2 Bearer token with local memory cache."""
        now = time.time()
        if email in self.token_cache:
            tok, exp = self.token_cache[email]
            if now < exp - 120:
                return tok

        SCOPES = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_info(
            key_data, scopes=SCOPES
        )
        credentials.refresh(Request())
        self.token_cache[email] = (credentials.token, now + 3500)
        return credentials.token

    async def submit_url(self, target_url: str, action: str = "URL_UPDATED", max_retries: int = 15) -> Dict[str, Any]:
        """
        Submits URL to Google Indexing API v3.
        Rotates to next account if 429 quota or auth error occurs.
        """
        attempts_limit = max(len(self.account_pool), max_retries)
        for attempt in range(attempts_limit):
            account = self.get_next_account()
            if not account:
                return {
                    "success": False,
                    "target_url": target_url,
                    "error": "All GCP service accounts in pool are in cooldown or none loaded."
                }

            email = account["email"]
            try:
                token = self._get_access_token(email, account["key_data"])
                endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                payload = {
                    "url": target_url,
                    "type": action
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(endpoint, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        resp_text = await resp.text()
                        if resp.status == 200:
                            data = json.loads(resp_text)
                            return {
                                "success": True,
                                "status": 200,
                                "service_account": email,
                                "target_url": target_url,
                                "response": data
                            }
                        elif resp.status == 429:
                            logger.warning(f"[GCP Rotator] 429 Quota exhausted for {email}. Adding 24h cooldown.")
                            self.cooldowns[email] = time.time() + (24 * 3600)
                            continue  # Retry with next account
                        else:
                            logger.warning(f"[GCP Rotator] API Status {resp.status} on {email}: {resp_text}")
                            return {
                                "success": False,
                                "status": resp.status,
                                "service_account": email,
                                "target_url": target_url,
                                "error": resp_text
                            }

            except Exception as e:
                logger.error(f"[GCP Rotator] Error submitting via {email}: {e}")
                # Cooldown broken or auth-failed account so rotator tries next active account
                self.cooldowns[email] = time.time() + (24 * 3600)
                continue

        return {
            "success": False,
            "target_url": target_url,
            "error": "Failed after rotating through available service accounts."
        }

    async def submit_batch(self, urls: List[str], action: str = "URL_UPDATED") -> List[Dict[str, Any]]:
        """Submits a batch of URLs sequentially or micro-batched with delay."""
        results = []
        for url in urls:
            res = await self.submit_url(url, action=action)
            results.append(res)
        return results

# Singleton instance
gcp_rotator = GCPIndexingRotator()
