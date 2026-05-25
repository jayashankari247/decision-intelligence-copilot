import csv
import os
from sentence_transformers import SentenceTransformer
import chromadb
from agents.product_discovery.prompts import build_product_text


class ProductEmbeddings:

    def __init__(self, persist_dir="data/product_discovery/chroma_db"):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("hm_products")

    def build_index(self, articles_csv, max_articles=10000):
        if self.collection.count() > 0:
            print(f"Index already exists with {self.collection.count()} products. Skipping rebuild.")
            return

        print(f"Building product index — loading {max_articles} articles...")
        articles = []
        with open(articles_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_articles:
                    break
                articles.append(row)

        texts = [build_product_text(row) for row in articles]
        ids = [row["article_id"] for row in articles]
        metadatas = [
            {
                "article_id": row["article_id"],
                "prod_name": row.get("prod_name", ""),
                "product_type_name": row.get("product_type_name", ""),
                "product_group_name": row.get("product_group_name", ""),
                "colour_group_name": row.get("colour_group_name", ""),
                "department_name": row.get("department_name", ""),
                "garment_group_name": row.get("garment_group_name", ""),
                "detail_desc": row.get("detail_desc", "")[:200]
            }
            for row in articles
        ]

        print(f"  Generating embeddings for {len(texts)} products...")
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

        print(f"Index built with {self.collection.count()} products.")

    def find_similar(self, query_text, n_results=5):
        query_embedding = self.model.encode(query_text).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        similar = []
        for i in range(len(results["ids"][0])):
            similar.append({
                "article_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return similar

    def get_by_category(self, product_group, n_results=20):
        results = self.collection.query(
            query_texts=[product_group],
            n_results=n_results
        )
        return results["metadatas"][0] if results["metadatas"] else []

    def get_image_path(self, article_id, images_dir="data/product_discovery/images"):
        subfolder = str(article_id)[:3]
        path = os.path.join(images_dir, subfolder, f"{article_id}.jpg")
        return path if os.path.exists(path) else None
