import csv
import random
import os

random.seed(42)

ARTICLES_FILE = "data/product_discovery/articles.csv"
OUTPUT_FILE = "data/inventory_supply/inventory_snapshot.csv"
WAREHOUSES = ["North", "South", "East", "West"]


def generate_snapshot(max_articles=500):
    os.makedirs("data/inventory_supply", exist_ok=True)

    article_ids = []
    with open(ARTICLES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_articles:
                break
            article_ids.append(row["article_id"])

    print(f"Generating inventory snapshot for {len(article_ids)} articles...")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["article_id", "current_stock", "reorder_point", "lead_time_days", "warehouse"]
        )
        writer.writeheader()

        for article_id in article_ids:
            reorder_point = random.randint(30, 150)
            # ~30% chance below reorder point to simulate realistic at-risk items
            if random.random() < 0.30:
                current_stock = random.randint(0, reorder_point - 1)
            else:
                current_stock = random.randint(reorder_point, 500)

            writer.writerow({
                "article_id": article_id,
                "current_stock": current_stock,
                "reorder_point": reorder_point,
                "lead_time_days": random.randint(7, 21),
                "warehouse": random.choice(WAREHOUSES)
            })

    print(f"Saved {len(article_ids)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_snapshot()
