import anthropic
import json
import csv
import os
from dotenv import load_dotenv
from agents.customer_voice.prompts import SYSTEM_PROMPT, build_user_message
from agents.customer_voice.embeddings import ReviewEmbeddings
from shared.schemas import validate


class CustomerVoiceAgent:

    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.data_file = os.getenv("CUSTOMER_REVIEWS_FILE")
        self.embeddings = ReviewEmbeddings()
        self.embeddings.build_index(self.data_file)

    def _call_claude(self, system_text, user_content, max_tokens=512):
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

    def analyze_review(self, review_text, title=None, department=None):
        user_message = build_user_message(review_text, title, department)
        try:
            response = self._call_claude(SYSTEM_PROMPT, user_message, max_tokens=512)
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            print(f"Claude returned invalid JSON for: {review_text[:50]}...")
            return None
        except (anthropic.APIConnectionError, anthropic.BadRequestError) as e:
            print(f"API error: {e}")
            return None

    def analyze_from_csv(self, filepath=None, max_reviews=10):
        filepath = filepath or self.data_file
        results, skipped = [], 0

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                if i >= max_reviews:
                    break
                review_text = row.get("Review Text", "").strip()
                if not review_text:
                    skipped += 1
                    continue
                title      = row.get("Title", "").strip() or None
                department = row.get("Department Name", "").strip() or None
                print(f"  Analyzing review {i + 1}/{max_reviews}...")
                result = self.analyze_review(review_text, title, department)
                if result:
                    result["source_rating"] = int(row.get("Rating", 0))
                    result["department"]    = department
                    results.append(result)

        print(f"\nDone. Analyzed {len(results)} reviews, skipped {skipped} empty.")
        return results

    def summarize_results(self, results):
        if not results:
            print("No results to summarize.")
            return None

        all_themes, all_positives, all_negatives, all_unmet_needs = [], [], [], []
        sentiment_counts = {"positive": 0, "negative": 0, "mixed": 0, "neutral": 0}
        scores = []

        for r in results:
            all_themes.extend(r.get("themes", []))
            all_positives.extend(r.get("positives", []))
            all_negatives.extend(r.get("negatives", []))
            all_unmet_needs.extend(r.get("unmet_needs", []))
            sentiment_counts[r.get("sentiment", "neutral")] = \
                sentiment_counts.get(r.get("sentiment", "neutral"), 0) + 1
            if r.get("score") is not None:
                scores.append(r["score"])

        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        summary_input = f"""
You have analyzed {len(results)} customer reviews. Here is the aggregated data:

Sentiment breakdown: {sentiment_counts}
Average sentiment score: {avg_score} (scale: -1.0 to 1.0)

All themes mentioned: {all_themes}
All positives mentioned: {all_positives}
All negatives mentioned: {all_negatives}
All unmet needs mentioned: {all_unmet_needs}

Return ONLY a JSON object with this structure:
{{
    "total_reviews": {len(results)},
    "avg_sentiment_score": {avg_score},
    "sentiment_breakdown": {sentiment_counts},
    "top_themes": ["the 5 most frequently mentioned themes"],
    "top_positives": ["the 5 most frequently mentioned positives"],
    "top_negatives": ["the 5 most frequently mentioned negatives"],
    "top_unmet_needs": ["the 5 most important unmet needs"],
    "executive_summary": "2-3 sentence plain English summary of what customers are saying overall"
}}
Return only the JSON. No explanation, no markdown, no code blocks."""

        system = "You are a customer experience analyst. Synthesize review data into executive insights."
        try:
            response = self._call_claude(system, summary_input, max_tokens=1024)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("Claude returned invalid JSON for summary.")
                return None
            return validate("customer_voice_summary", result)
        except anthropic.APIConnectionError:
            print("Could not connect to Anthropic API")
            return None

    def get_reviews_for_article(self, article_id, max_reviews=20):
        print(f"  Looking up reviews for article: {article_id}")
        mapping_file = os.path.join(os.path.dirname(self.data_file), "article_review_map.csv")

        if not os.path.exists(mapping_file):
            print("  Mapping file not found — falling back to semantic search")
            return self.search_reviews(f"clothing product article {article_id}")

        clothing_id = None
        with open(mapping_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["article_id"] == article_id:
                    clothing_id = row["clothing_id"]
                    break

        if not clothing_id:
            print(f"  No mapping found for {article_id} — falling back to semantic search")
            return self.search_reviews(f"clothing product article {article_id}")

        print(f"  Mapped to Clothing ID {clothing_id}")
        reviews = []
        with open(self.data_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("Clothing ID", "").strip() == clothing_id:
                    text = row.get("Review Text", "").strip()
                    if text:
                        reviews.append({
                            "review_text": text,
                            "rating":     row.get("Rating", "?"),
                            "department": row.get("Department Name", "?"),
                        })
                if len(reviews) >= max_reviews:
                    break

        if not reviews:
            print(f"  No reviews found for Clothing ID {clothing_id}")
            return None

        print(f"  Found {len(reviews)} reviews — analyzing...")
        review_block = "\n\n".join([
            f"Review (Rating: {r['rating']}, Dept: {r['department']}):\n{r['review_text']}"
            for r in reviews
        ])
        prompt = f"""Product: H&M Article {article_id}
(Note: these reviews are from a comparable clothing product in the same category)

{len(reviews)} customer reviews:

{review_block}

Return ONLY a JSON object:
{{
    "article_id": "{article_id}",
    "review_count": {len(reviews)},
    "direct_answer": "1-2 sentence summary of what customers think about this product type",
    "supporting_evidence": ["3-5 specific quotes or observations from the reviews"],
    "departments_affected": ["relevant departments or product categories"],
    "sentiment": "positive" or "negative" or "mixed",
    "recommendation": "one actionable recommendation for this product based on customer feedback"
}}
Return only the JSON. No explanation, no markdown, no code blocks."""

        system = "You are a customer experience analyst providing product-level insights."
        try:
            response = self._call_claude(system, prompt, max_tokens=1024)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for article review lookup")
                return None
            return validate("customer_voice_search", result)
        except (anthropic.APIConnectionError, anthropic.BadRequestError) as e:
            print(f"  API error: {e}")
            return None

    def search_reviews(self, query, n_results=20):
        print(f"  Searching reviews for: '{query}'")
        matches = self.embeddings.search(query, n_results=n_results)
        print(f"  Found {len(matches)} relevant reviews")

        review_texts = "\n\n".join([
            f"Review {i+1} (Rating: {m['metadata'].get('rating', '?')}, "
            f"Dept: {m['metadata'].get('department', '?')}):\n{m['review_text']}"
            for i, m in enumerate(matches)
        ])
        prompt = f"""A user asked: "{query}"

Here are the {len(matches)} most relevant customer reviews:

{review_texts}

Answer the user's question based on these reviews. Return ONLY a JSON object:
{{
    "query": "{query}",
    "relevant_review_count": {len(matches)},
    "direct_answer": "a direct answer to the question in 1-2 sentences",
    "supporting_evidence": ["3-5 specific quotes or paraphrases from the reviews that support the answer"],
    "departments_affected": ["list of departments mentioned in relevant reviews"],
    "sentiment": "positive" or "negative" or "mixed",
    "recommendation": "one actionable recommendation for the business based on this feedback"
}}
Return only the JSON. No explanation, no markdown, no code blocks."""

        system = "You are a customer experience analyst answering specific questions about customer feedback."
        try:
            response = self._call_claude(system, prompt, max_tokens=1024)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("Claude returned invalid JSON for search.")
                return None
            return validate("customer_voice_search", result)
        except anthropic.APIConnectionError:
            print("Could not connect to Anthropic API")
            return None
