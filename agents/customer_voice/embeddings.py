import csv
import os
from sentence_transformers import SentenceTransformer
import chromadb


class ReviewEmbeddings:

    def __init__(self, persist_dir="data/customer_reviews/chroma_db"):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("customer_reviews")

    def build_index(self, reviews_csv, max_reviews=23000):
        if self.collection.count() > 0:
            print(f"Review index already exists with {self.collection.count()} reviews. Skipping rebuild.")
            return

        print(f"Building review index — loading up to {max_reviews} reviews...")
        reviews = []
        with open(reviews_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_reviews:
                    break
                review_text = row.get("Review Text", "").strip()
                if not review_text:
                    continue
                reviews.append(row)

        texts = [row["Review Text"].strip() for row in reviews]
        ids = [str(i) for i in range(len(reviews))]
        metadatas = [
            {
                "title": row.get("Title", "") or "",
                "rating": str(row.get("Rating", "")),
                "department": row.get("Department Name", "") or "",
                "recommended": str(row.get("Recommended IND", "")),
                "age": str(row.get("Age", "")),
                "review_text": review_text[:300]
            }
            for row, review_text in zip(reviews, texts)
        ]

        print(f"  Generating embeddings for {len(texts)} reviews...")
        batch_size = 256
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            embeddings = self.model.encode(batch_texts).tolist()
            self.collection.add(
                documents=batch_texts,
                embeddings=embeddings,
                ids=batch_ids,
                metadatas=batch_meta
            )
            print(f"  Indexed {min(i + batch_size, len(texts))}/{len(texts)}...")

        print(f"Review index built with {self.collection.count()} reviews.")

    def search(self, query, n_results=20):
        query_embedding = self.model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        matches = []
        for i in range(len(results["ids"][0])):
            matches.append({
                "review_text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return matches
