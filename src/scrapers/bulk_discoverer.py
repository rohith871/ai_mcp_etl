import os
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse

INPUT_CSV_PATH = "data/raw/input_urls.csv"

BLOCKED_DOMAINS = {
    "twitter.com", "x.com", "linkedin.com", "github.com", "facebook.com",
    "youtube.com", "instagram.com", "medium.com", "wikipedia.org",
    "google.com", "apple.com", "microsoft.com", "amazon.com", "discord.com",
    "discord.gg", "producthunt.com", "ycombinator.com", "substack.com",
    "reddit.com", "arxiv.org", "huggingface.co", "theresanaiforthat.com"
}

def clean_domain(url: str) -> str | None:
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

async def fetch_urls(url: str, client: httpx.AsyncClient) -> set[str]:
    print(f"🔍 Crawling: {url}")
    found = set()
    try:
        resp = await client.get(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=20.0,
            follow_redirects=True
        )
        if resp.status_code == 200:
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', resp.text)
            for u in urls:
                cleaned = clean_domain(u)
                if cleaned:
                    found.add(cleaned)
    except Exception as e:
        print(f"⚠️ Error reading {url}: {e}")
    return found

async def main():
    # Expand with diverse curated AI sources, YC AI startup feeds, and awesome lists
    TARGET_SOURCES = [
        "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md",
        "https://raw.githubusercontent.com/Hannibal0416/Awesome-LLM/main/README.md",
        "https://raw.githubusercontent.com/eugeneyan/open-source-llms/main/README.md",
        "https://raw.githubusercontent.com/WB-DA/awesome-ai-tools/main/README.md",
        "https://raw.githubusercontent.com/sindresorhus/awesome/main/readme.md",
        "https://raw.githubusercontent.com/ashishpatel26/500-AI-Machine-learning-Deep-learning-Computer-vision-NLP-Projects-with-code/main/README.md"
    ]

    async with httpx.AsyncClient() as client:
        tasks = [fetch_urls(src, client) for src in TARGET_SOURCES]
        results = await asyncio.gather(*tasks)

    all_discovered = set()
    for res in results:
        all_discovered.update(res)

    existing = set()
    if os.path.exists(INPUT_CSV_PATH):
        try:
            df_old = pd.read_csv(INPUT_CSV_PATH)
            if "url" in df_old.columns:
                existing = set(df_old["url"].dropna().astype(str).tolist())
        except Exception:
            pass

    merged = sorted(list(existing.union(all_discovered)))
    pd.DataFrame({"url": merged}).to_csv(INPUT_CSV_PATH, index=False)
    
    print(f"\n🎉 Bulk Discovery Finished!")
    print(f"📥 Added {len(merged) - len(existing)} new domain URLs.")
    print(f"📊 Total Target URLs ready in '{INPUT_CSV_PATH}': {len(merged)}")

if __name__ == "__main__":
    asyncio.run(main())