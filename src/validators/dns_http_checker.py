import asyncio
import dns.resolver
import httpx
from typing import Dict, List, Any
from tqdm.asyncio import tqdm
from config.settings import CONCURRENT_CHECKS, HTTP_TIMEOUT

# Common browser user-agent to bypass basic anti-bot blocks
BROWSER_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Status codes that indicate an active live domain (even if protected behind Cloudflare)
LIVE_STATUS_CODES = {200, 301, 302, 307, 308, 403, 401}

class DomainValidator:
    def __init__(self, timeout: float = HTTP_TIMEOUT, concurrency: int = CONCURRENT_CHECKS):
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(concurrency)

    def verify_dns(self, domain: str) -> bool:
        """Check if domain resolves via A or AAAA DNS records."""
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        try:
            dns.resolver.resolve(clean_domain, 'A')
            return True
        except Exception:
            try:
                dns.resolver.resolve(clean_domain, 'AAAA')
                return True
            except Exception:
                return False

    async def validate_url(self, url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Perform HTTP HEAD (or fallback GET) request to verify active URL."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        # Fast path: DNS resolution check
        if not self.verify_dns(domain):
            return {"url": url, "status": "DNS_FAILED", "is_valid": False, "final_url": None}

        async with self.semaphore:
            try:
                # Try HEAD request first
                response = await client.head(url, follow_redirects=True, timeout=self.timeout)
                if response.status_code in LIVE_STATUS_CODES:
                    return {"url": url, "status": response.status_code, "is_valid": True, "final_url": str(response.url)}

                # Fallback to GET if HEAD method fails
                response = await client.get(url, follow_redirects=True, timeout=self.timeout)
                is_valid = response.status_code in LIVE_STATUS_CODES
                return {"url": url, "status": response.status_code, "is_valid": is_valid, "final_url": str(response.url)}
            except httpx.RequestError:
                return {"url": url, "status": "CONNECTION_FAILED", "is_valid": False, "final_url": None}

    async def validate_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Validate a batch of URLs concurrently with a progress bar."""
        async with httpx.AsyncClient(headers=BROWSER_HEADER) as client:
            tasks = [self.validate_url(u, client) for u in urls]
            results = await tqdm.gather(*tasks, desc="Layer 1: Validating Domains & HTTP Status")
            return results

