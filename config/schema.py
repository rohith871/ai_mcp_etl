from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

class CompanySchema(BaseModel):
    company_name: str
    website_url: str
    logo_url: Optional[str] = Field("https://via.placeholder.com/150", description="Direct Image URL of company logo or favicon")
    github_url: Optional[str] = Field(None, description="Official GitHub repository or organization URL")
    one_liner: str
    long_description: str
    year_founded: Optional[int] = None
    classification_tier: str = Field(..., description="Must be 'AI Native', 'AI Enabled', or 'AI Adjacent' ONLY")
    primary_category: str
    sub_categories: List[str] = []
    use_cases: List[str] = []
    model_types_supported: List[str] = []
    deployment_options: List[str] = []
    supported_frameworks: List[str] = []
    has_api: bool = False
    open_source_status: str
    target_audience: List[str] = []
    pricing_model: str
    key_products: List[str] = []
    hq_location: Optional[str] = None
    data_confidence_score: float
    extraction_flags: List[str] = []
    