import asyncio
import random
import re
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from config.settings import HTTP_TIMEOUT

BROWSER_HEADERS = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"}
]

# Generic/System GitHub endpoints to filter out
GITHUB_IGNORE = {
    "github.com/about", "github.com/pricing", "github.com/features", 
    "github.com/login", "github.com/signup", "github.com/sponsors",
    "github.com/join", "github.com/topics", "github.com/trending"
}

class ContentFetcher:
    def __init__(self, timeout: float = HTTP_TIMEOUT, proxy_url: Optional[str] = None, max_retries: int = 3):
        self.timeout = timeout
        self.proxy_url = proxy_url
        self.max_retries = max_retries

    def _extract_github_url(self, soup: BeautifulSoup, raw_html: str) -> Optional[str]:
        """Deterministic extraction of official GitHub repository or org URL."""
        found_urls = set()

        # 1. Check all anchor tags explicitly
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if "github.com/" in href.lower():
                found_urls.add(href)

        # 2. Regex scan across raw HTML body for missed links
        raw_matches = re.findall(r'https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?', raw_html)
        for match in raw_matches:
            found_urls.add(match)

        # 3. Filter out generic non-repo/non-org GitHub URLs
        valid_github_urls = []
        for url in found_urls:
            cleaned_url = url.split("?")[0].rstrip("/")
            if not any(ignore_path in cleaned_url.lower() for ignore_path in GITHUB_IGNORE):
                # Ensure it points to an org or repo (e.g. github.com/org or github.com/org/repo)
                parts = cleaned_url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
                if len(parts) >= 1 and parts[0]:
                    valid_github_urls.append(cleaned_url)

        # Prefer specific repository URLs over generic org URLs
        valid_github_urls.sort(key=lambda u: len(u.split("/")), reverse=True)
        return valid_github_urls[0] if valid_github_urls else None

    def _extract_smart_content(self, html_content: str, target_url: str) -> tuple[str, str, Optional[str]]:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Logo / Favicon URL
        logo_url = None
        meta_og = soup.find("meta", property="og:image")
        icon_link = soup.find("link", rel=lambda r: r and "icon" in r.lower())

        if meta_og and meta_og.get("content"):
            logo_url = meta_og["content"]
        elif icon_link and icon_link.get("href"):
            logo_url = icon_link["href"]

        if logo_url and not logo_url.startswith("http"):
            logo_url = f"{target_url.rstrip('/')}/{logo_url.lstrip('/')}"
        if not logo_url:
            logo_url = f"{target_url.rstrip('/')}/favicon.ico"

        # 2. Deterministically Extract GitHub Repository URL
        github_url = self._extract_github_url(soup, html_content)

        # 3. Extract Metadata & Text Content
        meta_desc = ""
        meta_elem = soup.find("meta", attrs={"name": "description"})
        if meta_elem and meta_elem.get("content"):
            meta_desc = f"Meta Description: {meta_elem['content']}\n"

        headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:10]]
        heading_text = "Key Headings: " + " | ".join(headings) + "\n"

        for element in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
            element.decompose()
        
        main_text = soup.get_text(separator=" ", strip=True)[:6000]
        smart_content = f"{meta_desc}{heading_text}\nMain Content:\n{main_text}"

        return smart_content, logo_url, github_url

    async def fetch_page(self, url: str) -> Dict[str, Any]:
        headers = random.choice(BROWSER_HEADERS)
        client_kwargs = {"follow_redirects": True, "timeout": self.timeout}
        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url

        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    smart_content, logo_url, github_url = self._extract_smart_content(response.text, url)
                    return {
                        "url": url,
                        "success": True,
                        "content": smart_content,
                        "logo_url": logo_url,
                        "github_url": github_url
                    }
        except Exception as e:
            return {"url": url, "success": False, "error": str(e)}

        return {"url": url, "success": False, "error": "HTTP Error"}
