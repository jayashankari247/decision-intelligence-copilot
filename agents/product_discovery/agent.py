import anthropic
import json
import base64
import os
from dotenv import load_dotenv
from agents.product_discovery.embeddings import ProductEmbeddings
from agents.product_discovery.prompts import (
    PRODUCT_ANALYSIS_PROMPT, TREND_DISCOVERY_PROMPT,
    CATALOG_SEARCH_PROMPT, CATALOG_SUMMARY_PROMPT
)
from shared.schemas import validate


class ProductDiscoveryAgent:

    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.articles_file = os.getenv("ARTICLES_FILE", "data/product_discovery/articles.csv")
        self.embeddings = ProductEmbeddings()
        self.embeddings.build_index(self.articles_file)

    def _encode_image(self, image_path):
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    def _call_claude(self, system_text, user_content, max_tokens=1024):
        return self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=[{
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_content}],
        )

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return None

    def analyze_product(self, article_id):
        results = self.embeddings.collection.get(ids=[article_id])
        if not results["ids"]:
            print(f"  Article {article_id} not found in index")
            return None

        text    = results["documents"][0]
        content = []
        image_path = self.embeddings.get_image_path(article_id)
        if image_path:
            print(f"  Including product image for {article_id}")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": self._encode_image(image_path),
                },
            })
        content.append({"type": "text", "text": f"Analyze this product:\n{text}"})

        try:
            response = self._call_claude(PRODUCT_ANALYSIS_PROMPT, content)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print(f"  Claude returned invalid JSON for article {article_id}")
                return None
            result["article_id"] = article_id
            result["has_image"]  = image_path is not None
            return result
        except (anthropic.APIConnectionError, anthropic.BadRequestError) as e:
            print(f"  API error: {e}")
            return None

    def find_similar_products(self, query, n_results=5):
        print(f"  Finding products similar to: '{query}'")
        similar = self.embeddings.find_similar(query, n_results)
        print(f"  Found {len(similar)} similar products")
        return similar

    def discover_trends(self, product_group):
        print(f"  Discovering trends in: {product_group}")
        products = self.embeddings.get_by_category(product_group, n_results=20)
        if not products:
            print(f"  No products found for {product_group}")
            return None

        product_list = "\n".join([
            f"- {p.get('prod_name', '')} | {p.get('colour_group_name', '')} | {p.get('detail_desc', '')[:100]}"
            for p in products
        ])
        prompt = f"Category: {product_group}\n\nProducts:\n{product_list}"

        try:
            response = self._call_claude(TREND_DISCOVERY_PROMPT, prompt)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for trend discovery")
            return result
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None

    def search_catalog(self, query, n_results=20):
        print(f"  Searching catalog for: '{query}'")
        matches = self.embeddings.find_similar(query, n_results=n_results)
        print(f"  Found {len(matches)} matching products")

        product_list = "\n".join([
            f"- {m['metadata'].get('prod_name', '')} | "
            f"{m['metadata'].get('colour_group_name', '')} | "
            f"{m['metadata'].get('product_group_name', '')} | "
            f"{m['metadata'].get('detail_desc', '')[:80]}"
            for m in matches
        ])
        prompt = f"User question: {query}\n\nMatching products:\n{product_list}"

        try:
            response = self._call_claude(CATALOG_SEARCH_PROMPT, prompt)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for catalog search")
                return None
            result["total_matches"] = len(matches)
            return validate("product_discovery_search", result)
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None

    def summarize_catalog(self):
        print("  Summarizing product catalog across categories...")
        categories = [
            "Garment Upper body", "Garment Lower body", "Garment Full body",
            "Accessories", "Shoes", "Underwear/nightwear",
        ]
        all_products = []
        for category in categories:
            all_products.extend(self.embeddings.get_by_category(category, n_results=10))

        if not all_products:
            print("  No products found for catalog summary")
            return None

        print(f"  Analyzing {len(all_products)} products across {len(categories)} categories...")
        product_list = "\n".join([
            f"- {p.get('prod_name', '')} | {p.get('colour_group_name', '')} | "
            f"{p.get('product_group_name', '')} | {p.get('garment_group_name', '')}"
            for p in all_products
        ])
        prompt = f"Total products sampled: {len(all_products)}\n\nProduct catalog:\n{product_list}"

        try:
            response = self._call_claude(CATALOG_SUMMARY_PROMPT, prompt)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for catalog summary")
                return None
            result["total_products_sampled"] = len(all_products)
            return validate("product_discovery_summary", result)
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None
