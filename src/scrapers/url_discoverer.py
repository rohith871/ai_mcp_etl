import os
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse

INPUT_CSV_PATH = "data/raw/input_urls.csv"
PROCESSED_CSV_PATH = "data/processed/processed_companies.csv"

BLOCKED_DOMAINS = {
    "twitter.com", "x.com", "linkedin.com", "github.com", "facebook.com",
    "youtube.com", "instagram.com", "medium.com", "wikipedia.org",
    "google.com", "apple.com", "microsoft.com", "amazon.com", "discord.com",
    "discord.gg", "producthunt.com", "ycombinator.com", "substack.com",
    "reddit.com", "arxiv.org", "huggingface.co", "theresanaiforthat.com"
}

def normalize_domain(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain or domain in BLOCKED_DOMAINS or "." not in domain:
            return None
        return f"https://{domain}"
    except Exception:
        return None

def load_seen_domains() -> set[str]:
    seen = set()
    # Check processed CSV
    if os.path.exists(PROCESSED_CSV_PATH):
        try:
            df = pd.read_csv(PROCESSED_CSV_PATH)
            for col in ["website_url", "source_url"]:
                if col in df.columns:
                    for u in df[col].dropna():
                        d = normalize_domain(str(u))
                        if d: seen.add(d)
        except Exception as e:
            print(f"⚠️ Warning reading processed file: {e}")

    # Check existing input CSV
    if os.path.exists(INPUT_CSV_PATH):
        try:
            df = pd.read_csv(INPUT_CSV_PATH)
            if "url" in df.columns:
                for u in df["url"].dropna():
                    d = normalize_domain(str(u))
                    if d: seen.add(d)
        except Exception as e:
            print(f"⚠️ Warning reading input file: {e}")
            
    return seen

async def fetch_urls_from_source(source_url: str, client: httpx.AsyncClient, seen_domains: set, target_queue: list, target_limit: int = 500):
    if len(target_queue) >= target_limit:
        return

    print(f"🔍 Searching AI directory/source: {source_url}")
    try:
        resp = await client.get(
            source_url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=20.0,
            follow_redirects=True
        )
        if resp.status_code == 200:
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', resp.text)
            for u in urls:
                cleaned = normalize_domain(u)
                if cleaned and cleaned not in seen_domains:
                    seen_domains.add(cleaned)
                    target_queue.append(cleaned)
                    if len(target_queue) >= target_limit:
                        break
    except Exception as e:
        print(f"⚠️ Failed source {source_url}: {e}")

async def discover_fresh_500():
    print("🚀 Initializing Smart AI Company Discovery Engine...")
    seen_domains = load_seen_domains()
    print(f"🧠 Total existing processed/queued domains loaded: {len(seen_domains)}")

    DISCOVERY_SOURCES = [
        "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md",
        "https://raw.githubusercontent.com/Hannibal0416/Awesome-LLM/main/README.md",
        "https://raw.githubusercontent.com/eugeneyan/open-source-llms/main/README.md",
        "https://raw.githubusercontent.com/WB-DA/awesome-ai-tools/main/README.md",
        "https://raw.githubusercontent.com/mahseema/awesome-ai-tools/main/README.md",
        "https://raw.githubusercontent.com/slavakurilyak/awesome-ai-agents/main/README.md",
        "https://raw.githubusercontent.com/e2b-dev/awesome-ai-agents/main/README.md"
    ]

    target_queue = []
    async with httpx.AsyncClient() as client:
        for source in DISCOVERY_SOURCES:
            if len(target_queue) >= 500:
                break
            await fetch_urls_from_source(source, client, seen_domains, target_queue, target_limit=500)

    print(f"\n🎉 Discovery Complete!")
    print(f"📥 Discovered exactly {len(target_queue)} fresh, unvisited AI company URLs.")
    
    os.makedirs(os.path.dirname(INPUT_CSV_PATH), exist_ok=True)
    pd.DataFrame({"url": target_queue}).to_csv(INPUT_CSV_PATH, index=False)
    print(f"💾 Overwritten '{INPUT_CSV_PATH}' with current 500 batch targets.")

if __name__ == "__main__":
    asyncio.run(discover_fresh_500())
