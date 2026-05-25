def analyze_sentiment(review_text):
    text = review_text.lower()
    if "great" in text or "love" in text:
        return "positive"
    elif "terrible" in text or "hate" in text:
        return "negative"
    else:
        return "neutral"

result = analyze_sentiment("This is terrible")
#print(result)
product = {
    "name": "Wireless Headphones",
    "price": 79.99,
    "category": "Electronics",
    "in_stock": True
}

#print(product["name"])
#print(product["price"])

product["price"] = 89.99
#print(product["price"])

product["rating"] = 4.5
#print(product)

reviews = [
    "I love this product, works great!",
    "Terrible quality, broke after one day.",
    "It's okay, nothing special.",
    "Absolutely fantastic, best purchase ever!",
    "Hate it, complete waste of money."
]

results = []

for review in reviews:
    sentiment = analyze_sentiment(review)
    result = {
        "review": review,
        "sentiment": sentiment
    }
    results.append(result)

#print(results)
for item in results:
    print(f"Review: '{item['review']}' was classified as: {item['sentiment']}")   
    
customer_name = "Shankari"
product = "Wireless Headphones"

prompt = f"""
You are a customer sentiment analyst.
Analyze the following review for the product '{product}' 
submitted by customer '{customer_name}'.
"""
#print(prompt)

import os
from datetime import datetime

now = datetime.now()
#print(f"Script ran at: {now}")
#print(f"Current directory: {os.getcwd()}")

import csv

with open("sample_reviews.csv", "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        print(f"{row['product']} | Rating: {row['rating']} | {row['review']}")

import csv

def load_reviews(filename):
    reviews = []
    try:
        with open(filename, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                reviews.append(row)
        print(f"Loaded {len(reviews)} reviews from {filename}")
    except FileNotFoundError:
        print(f"Error: Could not find file '{filename}'")
    except Exception as e:
        print(f"Unexpected error loading file: {e}")
    return reviews

good_result = load_reviews("sample_reviews.csv")
bad_result = load_reviews("file_that_doesnt_exist.csv")

