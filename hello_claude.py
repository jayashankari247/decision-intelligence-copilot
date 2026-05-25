import anthropic
import json
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

def analyze_review(review_text):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system="""You are a customer sentiment analyst.
Analyze the review provided and return ONLY a JSON object with this exact structure:
{
    "sentiment": "positive" or "negative" or "mixed" or "neutral",
    "score": a number from -1.0 (very negative) to 1.0 (very positive),
    "themes": ["list", "of", "themes", "mentioned"],
    "positives": ["list of positive aspects mentioned"],
    "negatives": ["list of negative aspects mentioned"]
}
Return only the JSON. No explanation, no markdown, no code blocks.""",
            messages=[
                {"role": "user", "content": f"Review: {review_text}"}
            ]
        )

        raw_text = response.content[0].text
        result = json.loads(raw_text)
        return result

    except json.JSONDecodeError:
        print("Claude returned invalid JSON — raw response was:")
        print(raw_text)
        return None
    except anthropic.APIConnectionError:
        print("Could not connect to Anthropic API")
        return None
    except anthropic.BadRequestError as e:
        print(f"Bad request: {e}")
        return None
reviews = [
    "The headphones sound amazing but the ear cushions fell apart after 2 months.",
    "Absolute rubbish. Stopped working after one week. Total waste of money.",
    "Decent product for the price. Nothing extraordinary but gets the job done."
]

for review in reviews:
    result = analyze_review(review)
    if result:
        print(f"Sentiment: {result['sentiment']:10} Score: {result['score']:5}  | {review[:60]}")
        