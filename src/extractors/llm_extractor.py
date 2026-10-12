import re
import json
import httpx
import asyncio
from typing import Dict, Any, Optional
from groq import Groq
from config.settings import GROQ_API_KEY, GROQ_MODEL
from config.schema import CompanySchema

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "qwen2.5-coder:7b"

SYSTEM_PROMPT = """You are an expert AI market analyst for 'AI Orbit'.
Analyze the page content and extract structured JSON matching this schema.

STRICT CLASSIFICATION RULE:
This database is ONLY for AI companies or AI products.
If the company is NOT an AI company/product, set "classification_tier": "Non-AI".

CRITICAL LOGO RULE:
- "logo_url" MUST be a true company logo, square brand icon, or high-resolution favicon URL.
- DO NOT use banner images, promotional marketing graphics, hero section product screenshots, or feature illustration posters. If no clear logo URL is found, leave it null or use the scraped favicon hint.

CRITICAL FIELD RULES:
- Change "one_liner" to "short_description" (1 punchy sentence summary).
- For "open_source_status" and "pricing_model", if exact details are NOT explicitly found in the page text, leave them as null (do NOT output "Unknown").

Schema format:
{
    "company_name": "Official Name",
    "website_url": "URL",
    "logo_url": "True company logo or icon URL (NO posters/banners)",
    "github_url": "https://github.com/..." or null,
    "short_description": "1-sentence summary",
    "long_description": "Detailed description",
    "year_founded": 2024 or null,
    "classification_tier": "AI Native | AI Enabled | AI Adjacent | Non-AI",
    "primary_category": "Generative AI | AI Infrastructure | AI Agents | Model Context Protocol (MCP) | Developer Tools | Computer Vision | NLP / Speech | Robotics | Data & Analytics | Other",
    "sub_categories": [],
    "use_cases": [],
    "model_types_supported": [],
    "deployment_options": [],
    "supported_frameworks": [],
    "has_api": false,
    "open_source_status": "Fully Open Source | Open Weights | Proprietary | Freemium / Hybrid | null",
    "target_audience": [],
    "pricing_model": "Free Tier / Freemium | Usage-Based | Subscription | Custom Enterprise | Completely Free | null",
    "key_products": [],
    "hq_location": "City, Country" or null,
    "data_confidence_score": 0.95,
    "extraction_flags": []
}
Output STRICT JSON ONLY."""

class SchemaExtractor:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def _clean_raw_json(self, raw_text: str) -> str:
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            return json_match.group(0).strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    async def extract_async(self, text: str, url: str, logo_hint: str = None, github_hint: str = None) -> Optional[Dict[str, Any]]:
        user_prompt = (
            f"Website URL: {url}\n"
            f"Extracted Logo Hint: {logo_hint}\n"
            f"Extracted GitHub Link Hint: {github_hint}\n\n"
            f"Content:\n{text}"
        )

        raw_content = None

        # ==========================================
        # PRIMARY: Local Ollama (qwen2.5-coder:7b)
        # ==========================================
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(OLLAMA_URL, json=payload)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if "choices" in res_json and len(res_json["choices"]) > 0:
                        raw_content = res_json["choices"][0]["message"]["content"]
                else:
                    print(f"⚠️ Ollama HTTP {resp.status_code} for {url}. Switching to Groq fallback...")
        except Exception as e:
            print(f"⚠️ Local Ollama unreachable for {url}: {e}. Switching to Groq fallback...")

        # ==========================================
        # FALLBACK: Groq API (With Rate-Limit Catching)
        # ==========================================
        if not raw_content and self.groq_client:
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                )
                raw_content = response.choices[0].message.content
                print(f"  ↪️ Extracted successfully via Groq Fallback for: {url}")
            except Exception as e:
                # Catches rate limits (429) or other API blocks gracefully and continues pipeline
                print(f"❌ Groq Fallback failed/Rate-limited for {url}: {e}. Skipping URL...")
                return None

        if not raw_content:
            return None

        # ==========================================
        # Validation & Normalization
        # ==========================================
        try:
            cleaned = self._clean_raw_json(raw_content)
            data = json.loads(cleaned)
            data["website_url"] = url
            
            if data.get("has_api") is None:
                data["has_api"] = False

            # Prioritize clean favicon/logo hints if LLM returned a banner poster URL
            if logo_hint and (not data.get("logo_url") or "banner" in data.get("logo_url", "").lower() or "hero" in data.get("logo_url", "").lower()):
                data["logo_url"] = logo_hint

            if github_hint:
                data["github_url"] = github_hint

            if data.get("classification_tier") == "Non-AI":
                return None

            validated = CompanySchema(**data)
            return validated.model_dump()
        except Exception as e:
            print(f"⚠️ Schema validation error for {url}: {e}")
            return None

