from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class CompanySchema(BaseModel):
    company_name: str
    website_url: str
    logo_url: Optional[str] = None
    github_url: Optional[str] = None
    short_description: str  # <--- Changed from one_liner
    long_description: Optional[str] = None
    year_founded: Optional[int] = None
    classification_tier: str
    primary_category: str
    sub_categories: List[str] = []
    use_cases: List[str] = []
    model_types_supported: List[str] = []
    deployment_options: List[str] = []
    supported_frameworks: List[str] = []
    has_api: bool = False
    open_source_status: Optional[str] = None  # <--- Default to None instead of "Unknown" if not found
    target_audience: List[str] = []
    pricing_model: Optional[str] = None      # <--- Default to None instead of "Unknown" if not found
    key_products: List[str] = []
    hq_location: Optional[str] = None
    data_confidence_score: float = 0.9
    extraction_flags: List[str] = []

