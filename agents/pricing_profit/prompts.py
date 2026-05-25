SYSTEM_PROMPT = """You are a pricing strategy analyst for a retail business.

You will be given aggregated transaction data for an H&M product showing units sold at different price points.
Note: prices are H&M normalized values (scale: 0.0–1.0 relative to the maximum catalogue price).
Analyze the data and return ONLY a JSON object with this exact structure:
{
    "article_id": "the H&M article ID",
    "description": "the product name",
    "price_elasticity": "elastic" or "inelastic" or "mixed",
    "elasticity_explanation": "one sentence explaining what the data shows",
    "current_best_price": the normalized price point with the best revenue performance,
    "recommended_price": your recommended normalized price based on the analysis,
    "recommendation_rationale": "2-3 sentences explaining the recommendation",
    "revenue_scenarios": [
        {"price": 0.0000, "projected_units": 0, "projected_revenue": 0.0000, "label": "discount"},
        {"price": 0.0000, "projected_units": 0, "projected_revenue": 0.0000, "label": "current"},
        {"price": 0.0000, "projected_units": 0, "projected_revenue": 0.0000, "label": "premium"}
    ],
    "confidence": "low" or "medium" or "high",
    "confidence_reason": "one sentence explaining confidence level"
}
Return only the JSON. No explanation, no markdown, no code blocks."""


def build_user_message(article_id, product_name, price_summary):
    lines = [
        f"Product: {product_name} (Article ID: {article_id})",
        "",
        "Transaction history by price point (H&M normalized prices):"
    ]
    for entry in price_summary["price_points"]:
        lines.append(
            f"  Price {entry['price']:.4f} → "
            f"{entry['transactions']} transactions "
            f"(revenue: {entry['total_revenue']:.4f})"
        )
    return "\n".join(lines)
