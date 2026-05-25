from agents.product_discovery.agent import ProductDiscoveryAgent

agent = ProductDiscoveryAgent()

print("\n=== SIMILAR PRODUCT SEARCH ===")
queries = [
    "comfortable black casual top",
    "elegant evening dress",
    "warm winter jacket"
]
for query in queries:
    print(f"\nQuery: '{query}'")
    results = agent.find_similar_products(query, n_results=3)
    for r in results:
        m = r["metadata"]
        print(f"  {m['article_id']} | {m['prod_name']} | {m['colour_group_name']} | distance: {r['distance']:.3f}")

print("\n=== PRODUCT ANALYSIS (multimodal) ===")
article_id = "0108775015"
result = agent.analyze_product(article_id)
if result:
    print(f"\n  Article     : {result['article_id']}")
    print(f"  Has image   : {result['has_image']}")
    print(f"  Category    : {result['category']}")
    print(f"  Style       : {', '.join(result['style_attributes'])}")
    print(f"  Occasions   : {', '.join(result['occasion'])}")
    print(f"  USPs        : {', '.join(result['unique_selling_points'])}")
    if result.get("visual_attributes"):
        print(f"  Visual      : {', '.join(result['visual_attributes'])}")
    if result.get("trend_alignment"):
        print(f"  Trends      : {', '.join(result['trend_alignment'])}")

print("\n=== TREND DISCOVERY ===")
for category in ["Garment Upper body", "Garment Lower body"]:
    print(f"\nCategory: {category}")
    trend = agent.discover_trends(category)
    if trend:
        print(f"  Dom styles  : {', '.join(trend['dominant_styles'])}")
        print(f"  Dom colours : {', '.join(trend['dominant_colours'])}")
        print(f"  Emerging    : {', '.join(trend['emerging_attributes'])}")
        print(f"  Gaps        : {', '.join(trend['opportunity_gaps'])}")
        print(f"  Summary     : {trend['trend_summary']}")
