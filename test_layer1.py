import asyncio
from src.validators.dns_http_checker import DomainValidator

test_urls = [
    "https://openai.com",
    "https://anthropic.com",
    "https://thisisadeaddomainthatdoesnotexist12345.com",
    "https://google.com"
]

async def main():
    validator = DomainValidator()
    print("Testing Layer 1 Domain & HTTP Validator...\n")
    results = await validator.validate_batch(test_urls)
    
    for r in results:
        status_icon = "✅" if r["is_valid"] else "❌"
        print(f"{status_icon} URL: {r['url']} | Status: {r['status']} | Valid: {r['is_valid']}")

if __name__ == "__main__":
    asyncio.run(main())
    