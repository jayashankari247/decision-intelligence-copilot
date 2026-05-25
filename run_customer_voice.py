from agents.customer_voice.agent import CustomerVoiceAgent

agent = CustomerVoiceAgent()

print("Running Customer Voice Agent on 50 reviews...\n")
results = agent.analyze_from_csv(max_reviews=50)

print("\n=== RESULTS ===\n")
for i, r in enumerate(results, 1):
    print(f"Review {i}:")
    print(f"  Sentiment : {r['sentiment']} (score: {r['score']})")
    print(f"  Star rating given : {r['source_rating']}")
    print(f"  Department : {r['department']}")
    print(f"  Themes : {', '.join(r['themes'])}")
    print(f"  Positives : {', '.join(r['positives'])}")
    print(f"  Negatives : {', '.join(r['negatives'])}")
    print(f"  Unmet needs : {', '.join(r['unmet_needs']) if r['unmet_needs'] else 'none'}")
    print()

print("=== EXECUTIVE SUMMARY ===\n")
summary = agent.summarize_results(results)
if summary:
    print(f"Reviews analyzed   : {summary['total_reviews']}")
    print(f"Avg sentiment score: {summary['avg_sentiment_score']}")
    print(f"Sentiment breakdown: {summary['sentiment_breakdown']}")
    print(f"\nTop themes     : {', '.join(summary['top_themes'])}")
    print(f"Top positives  : {', '.join(summary['top_positives'])}")
    print(f"Top negatives  : {', '.join(summary['top_negatives'])}")
    print(f"Top unmet needs: {', '.join(summary['top_unmet_needs'])}")
    print(f"\nSummary: {summary['executive_summary']}")

print("\n=== TARGETED SEARCH ===\n")
searches = [
    "complaints about petite sizing missing",
    "quality problems with fabric or stitching in skirts",
    "customers who loved the fit and would recommend"
]
for query in searches:
    result = agent.search_reviews(query, n_results=15)
    if result:
        print(f"Q: {query}")
        print(f"  Answer     : {result['direct_answer']}")
        print(f"  Departments: {', '.join(result['departments_affected'])}")
        print(f"  Sentiment  : {result['sentiment']}")
        print(f"  Action     : {result['recommendation']}")
        print()