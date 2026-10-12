from typing import List, Dict, Any

# Primary AI source registries and targeted domain paths
TARGET_SOURCES = {
    "product_pages": ["/about", "/pricing", "/products", "/features", "/docs"],
    "external_registries": [
        "site:github.com",
        "site:huggingface.co",
        "site:ycombinator.com/companies",
        "site:producthunt.com/products"
    ]
}

def generate_target_suburls(base_url: str) -> List[str]:
    """Generates high-priority sub-page paths to scrape deeper context."""
    base = base_url.rstrip("/")
    sub_paths = ["", "/about", "/pricing", "/product", "/docs"]
    return [f"{base}{path}" for path in sub_paths]

def build_discovery_query(company_name: str) -> List[str]:
    """Builds search queries targeted to top tech & AI databases."""
    return [
        f'"{company_name}" site:github.com',
        f'"{company_name}" site:huggingface.co',
        f'"{company_name}" site:ycombinator.com/companies'
    ]
