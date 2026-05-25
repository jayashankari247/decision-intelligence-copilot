from agents.pricing_profit.agent import PricingProfitAgent

PRICING_FILE = "data/pricing/online_retail_II.xlsx"

# A few well-known stock codes from the UCI dataset to try
STOCK_CODES = ["85123A", "71053", "84406B"]

agent = PricingProfitAgent()

for code in STOCK_CODES:
    print(f"\nAnalyzing {code}...")
    result = agent.analyze_pricing(code, PRICING_FILE)

    if result:
        print(f"\n  Product       : {result['description']}")
        print(f"  Elasticity    : {result['price_elasticity']} — {result['elasticity_explanation']}")
        print(f"  Best price    : £{result['current_best_price']}")
        print(f"  Recommended   : £{result['recommended_price']}")
        print(f"  Rationale     : {result['recommendation_rationale']}")
        print(f"  Confidence    : {result['confidence']} — {result['confidence_reason']}")
        print(f"  Scenarios:")
        for s in result["revenue_scenarios"]:
            print(f"    {s['label']:10} £{s['price']:.2f} → {s['projected_units']} units, £{s['projected_revenue']:.2f} revenue")
