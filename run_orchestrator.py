from orchestrator.orchestrator import Orchestrator

orchestrator = Orchestrator()

queries = [
    # Customer Voice — broad summarization
    "What are customers saying about our products overall?",
    # Customer Voice — targeted search
    "How many customers complained about petite sizing being unavailable?",
    # Product Discovery — targeted search
    "How many options do we have for black tops?",
    # Product Discovery — targeted search
    "Do we have casual tops available across multiple colours?",
    # Product Discovery — broad summary
    "Give me an overall summary of our product catalog by category.",
    # Pricing only — H&M article
    "What is the optimal price for article 0108775015?",
    # Both Customer Voice + Pricing — H&M article
    "What do customers think about and what should we charge for article 0108775015?",
    # Inventory — broad summary
    "Which products are at risk of stockout and need urgent replenishment?",
    # Inventory — specific article
    "What is the replenishment status for article 0108775015?",
    # Campaign — portfolio summary
    "Which products should we consider running a promotion or price discount on?",
    # Campaign — specific article
    "Should we run a campaign or discount for article 0108775015?"
]

for query in queries:
    result = orchestrator.run(query)
    print(f"\n{result['formatted']}")
    print("=" * 60)
