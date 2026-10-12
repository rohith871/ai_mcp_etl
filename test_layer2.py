import asyncio
from src.scrapers.fetcher import ContentFetcher

async def main():
    fetcher = ContentFetcher()
    test_url = "https://anthropic.com"
    
    print(f"Testing Layer 2 Content Fetcher on {test_url}...\n")
    result = await fetcher.fetch_page(test_url)
    
    if result["success"]:
        print(f"✅ Successfully fetched content!")
        print(f"Clean Content Snippet (first 300 chars):\n{result['content'][:300]}...\n")
        print(f"Extracted Text Length: {result['clean_length']} characters")
    else:
        print(f"❌ Failed to fetch content: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
    