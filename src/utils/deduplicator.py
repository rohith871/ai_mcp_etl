import re
import hashlib
from typing import Set, List, Dict, Any
from urllib.parse import urlparse

class PipelineDeduplicator:
    def __init__(self):
        self.seen_domains: Set[str] = set()
        self.seen_content_hashes: Set[str] = set()

    @staticmethod
    def normalize_domain(url: str) -> str:
        """Extract canonical domain identifier (e.g., 'https://www.openai.com/about' -> 'openai.com')."""
        url = url.strip().lower()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.split(":")[0]  # Remove port if present
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def filter_duplicate_urls(self, urls: List[str]) -> List[str]:
        """Deduplicate input URL list based on canonical domain."""
        unique_urls = []
        for url in urls:
            domain = self.normalize_domain(url)
            if domain not in self.seen_domains:
                self.seen_domains.add(domain)
                unique_urls.append(url)
        return unique_urls

    def is_duplicate_content(self, text: str) -> bool:
        """SHA-256 hash check on normalized text to drop identical scraped landing pages."""
        # Clean text to essential alphanumeric words to handle tiny dynamic changes (timestamps, tokens)
        normalized_text = re.sub(r'\W+', '', text.lower())
        content_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
        
        if content_hash in self.seen_content_hashes:
            return True
        
        self.seen_content_hashes.add(content_hash)
        return False

