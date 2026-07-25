from pydantic import BaseModel, Field
from typing import List, Optional


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    db_status: str


class SkillItem(BaseModel):
    skill: str
    job_count: int


class TopSkillsResponse(BaseModel):
    total_returned: int
    skills: List[SkillItem]


class SkillRecommendationItem(BaseModel):
    skill: str
    similarity_score: float
    similarity_pct: float


class SkillRecommendationResponse(BaseModel):
    target_skill: str
    total_returned: int
    recommendations: List[SkillRecommendationItem]


class PredictRequest(BaseModel):
    skills: List[str] = Field(
        ...,
        example=["Python", "AWS", "Docker", "Machine Learning"],
        description="List of technical skills to use for salary prediction."
    )
    country: str = Field(
        ...,
        example="us",
        description="Target country code: 'gb' (UK) or 'us' (US)."
    )


class FeatureContributionItem(BaseModel):
    feature: str
    value: float
    shap_value: float


class PredictResponse(BaseModel):
    predicted_salary_usd: float
    predicted_salary_local: float
    currency: str
    country: str
    skills_matched: List[str]
    note: str
    base_value_log: Optional[float] = None
    feature_contributions: Optional[List[FeatureContributionItem]] = None
