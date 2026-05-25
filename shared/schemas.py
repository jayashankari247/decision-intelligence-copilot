from pydantic import BaseModel, ValidationError, model_validator
from typing import Optional, List

# Fields that should always be lowercase (enums Claude varies on)
_LOWERCASE_FIELDS = {"confidence", "price_elasticity", "sentiment"}
# Fields that should always be uppercase
_UPPERCASE_FIELDS = {"replenishment_status", "promotion_recommendation", "demand_trend",
                     "trend", "urgency"}


class _Base(BaseModel):
    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def _normalise_case(cls, data):
        if not isinstance(data, dict):
            return data
        for key, val in data.items():
            if isinstance(val, str):
                if key in _LOWERCASE_FIELDS:
                    data[key] = val.lower()
                elif key in _UPPERCASE_FIELDS:
                    data[key] = val.upper()
        return data


# ── Customer Voice ────────────────────────────────────────────────────────────

class CustomerVoiceSearchOutput(_Base):
    direct_answer: str
    relevant_review_count: Optional[int] = None
    review_count: Optional[int] = None
    sentiment: str
    departments_affected: Optional[List[str]] = []
    supporting_evidence: Optional[List[str]] = []
    recommendation: Optional[str] = None
    article_id: Optional[str] = None
    query: Optional[str] = None


class CustomerVoiceSummaryOutput(_Base):
    total_reviews: int
    avg_sentiment_score: float
    sentiment_breakdown: Optional[dict] = {}
    top_themes: Optional[List[str]] = []
    top_positives: Optional[List[str]] = []
    top_negatives: Optional[List[str]] = []
    top_unmet_needs: Optional[List[str]] = []
    executive_summary: str


# ── Pricing & Profit ──────────────────────────────────────────────────────────

class RevenueScenario(_Base):
    price: float
    projected_units: int
    projected_revenue: float
    label: str


class PricingOutput(_Base):
    article_id: str
    description: Optional[str] = None
    price_elasticity: str
    elasticity_explanation: Optional[str] = None
    current_best_price: float
    recommended_price: float
    recommendation_rationale: str
    revenue_scenarios: List[RevenueScenario]
    confidence: str
    confidence_reason: Optional[str] = None


# ── Product Discovery ─────────────────────────────────────────────────────────

class CategoryBreakdown(_Base):
    category: str
    product_count: int


class ProductDiscoverySearchOutput(_Base):
    direct_answer: str
    total_matches: Optional[int] = None
    colour_variety: Optional[List[str]] = []
    style_variety: Optional[List[str]] = []
    coverage_assessment: Optional[str] = None
    gap_identified: Optional[str] = None


class ProductDiscoverySummaryOutput(_Base):
    total_products_sampled: Optional[int] = None
    categories_represented: Optional[List[str]] = []
    dominant_colours: Optional[List[str]] = []
    dominant_styles: Optional[List[str]] = []
    category_breakdown: Optional[List[CategoryBreakdown]] = []
    catalog_strengths: Optional[List[str]] = []
    catalog_gaps: Optional[List[str]] = []
    executive_summary: str


# ── Inventory & Supply ────────────────────────────────────────────────────────

class InventoryArticleOutput(_Base):
    article_id: Optional[str] = None
    replenishment_status: str
    days_until_stockout: int
    recommended_order_quantity: int
    recommended_order_date: str
    rationale: str
    risk_factors: Optional[List[str]] = []
    confidence: str


class WarehouseBreakdown(_Base):
    warehouse: str
    at_risk_count: int


class InventorySummaryOutput(_Base):
    total_at_risk: Optional[int] = None
    critical_count: int
    projected_stockout_this_week: int
    top_priority_articles: Optional[List[str]] = []
    warehouse_breakdown: Optional[List[WarehouseBreakdown]] = []
    immediate_actions: Optional[List[str]] = []
    executive_summary: str


# ── Campaign Intelligence ─────────────────────────────────────────────────────

class CampaignArticleOutput(_Base):
    article_id: Optional[str] = None
    promotion_recommendation: str
    suggested_discount_pct: int
    campaign_type: str
    demand_trend: Optional[str] = None
    demand_change_pct: Optional[float] = None
    campaign_timing: Optional[str] = None
    rationale: str
    risk_of_inaction: Optional[str] = None


class PromotionCandidate(_Base):
    article_id: str
    demand_change_pct: Optional[float] = None
    recommended_discount_pct: Optional[int] = None
    urgency: Optional[str] = None


class CampaignSummaryOutput(_Base):
    total_candidates: Optional[int] = None
    high_urgency_count: int
    recommended_campaign_types: Optional[List[str]] = []
    top_promotion_candidates: Optional[List[PromotionCandidate]] = []
    immediate_actions: Optional[List[str]] = []
    executive_summary: str


# ── Validation helper ─────────────────────────────────────────────────────────

_SCHEMAS = {
    "customer_voice_search":        CustomerVoiceSearchOutput,
    "customer_voice_summary":       CustomerVoiceSummaryOutput,
    "pricing":                      PricingOutput,
    "product_discovery_search":     ProductDiscoverySearchOutput,
    "product_discovery_summary":    ProductDiscoverySummaryOutput,
    "inventory_article":            InventoryArticleOutput,
    "inventory_summary":            InventorySummaryOutput,
    "campaign_article":             CampaignArticleOutput,
    "campaign_summary":             CampaignSummaryOutput,
}


def validate(schema_key: str, data: dict) -> dict:
    schema = _SCHEMAS.get(schema_key)
    if not schema:
        return data
    try:
        return schema.model_validate(data).model_dump()
    except ValidationError as e:
        print(f"  [schema] {schema_key} — {e.error_count()} field(s) invalid, returning raw")
        return data
