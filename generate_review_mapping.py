import csv
import random
import os
from collections import defaultdict

random.seed(42)

ARTICLES_FILE = "data/product_discovery/articles.csv"
REVIEWS_FILE = "data/customer_reviews/Womens Clothing E-Commerce Reviews.csv"
OUTPUT_FILE = "data/customer_reviews/article_review_map.csv"

DEPARTMENT_TO_PRODUCT_GROUP = {
    "Tops":    "Garment Upper body",
    "Dresses": "Garment Full body",
    "Bottoms": "Garment Lower body",
    "Intimate": "Underwear/nightwear",
    "Jackets": "Garment Upper body",
    "Trend":   "Garment Upper body",
}


def generate_mapping():
    # Group H&M article_ids by product_group
    articles_by_group = defaultdict(list)
    with open(ARTICLES_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            group = row.get("product_group_name", "").strip()
            if group:
                articles_by_group[group].append(row["article_id"])

    print(f"Loaded H&M articles across {len(articles_by_group)} product groups")

    # Collect unique clothing_id → department from reviews
    clothing_ids = {}
    with open(REVIEWS_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row.get("Clothing ID", "").strip()
            dept = row.get("Department Name", "").strip()
            if cid and cid not in clothing_ids:
                clothing_ids[cid] = dept

    print(f"Found {len(clothing_ids)} unique Clothing IDs to map")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["clothing_id", "article_id", "department", "product_group"]
        )
        writer.writeheader()
        for clothing_id, department in sorted(clothing_ids.items()):
            product_group = DEPARTMENT_TO_PRODUCT_GROUP.get(
                department, "Garment Upper body"
            )
            candidates = articles_by_group.get(product_group, [])
            article_id = random.choice(candidates) if candidates else "0108775015"
            writer.writerow({
                "clothing_id": clothing_id,
                "article_id": article_id,
                "department": department,
                "product_group": product_group
            })

    print(f"Saved mapping to {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_mapping()
