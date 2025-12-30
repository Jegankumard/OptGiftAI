# import dependencies

import nltk
import pandas as pd
import numpy as np
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression
from collections import Counter

# Ensure nltk downloads
nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("vader_lexicon", quiet=True)

# Gift recommender system logic
class GiftRecommender:
    def __init__(self, products):
        self.products = products
        self.df = pd.DataFrame(products)
        
        # Initialize NLP tools
        self.stop_words = set(stopwords.words("english"))
        self.lemmatizer = WordNetLemmatizer()
        self.sentiment = SentimentIntensityAnalyzer()

        # Preprocess all product descriptions
        self.df["combined_text"] = (
            self.df["title"].fillna("") + " " + 
            self.df["description"].fillna("") + " " + 
            self.df["tags"].apply(lambda x: " ".join(x) if isinstance(x, list) else str(x))
        )
        self.df["clean_text"] = self.df["combined_text"].apply(self.preprocess_text)

        # Vectorization (TF-IDF)
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["clean_text"])

        # Train Logistic Regression (Simulated for Hybrid)
        median_price = self.df["price"].median()
        self.df["target_label"] = (self.df["price"] > median_price).astype(int)
        
        # Safety fix for single-class data
        if self.df["target_label"].nunique() < 2:
            self.df.loc[0, "target_label"] = 1 - self.df.loc[0, "target_label"]

        self.lr_model = LogisticRegression()
        self.lr_model.fit(self.tfidf_matrix, self.df["target_label"])

    # Feature engineering: Text Preprocessing
    def preprocess_text(self, text):
        tokens = nltk.word_tokenize(str(text).lower())
        tokens = [self.lemmatizer.lemmatize(t) for t in tokens if t.isalnum()]
        return " ".join(tokens)

    # CONTENT-BASED FILTERING (Text Similarity)
    def get_content_based(self, query, top_k=6):
        clean_query = self.preprocess_text(query)
        query_vec = self.vectorizer.transform([clean_query])
        
        # Cosine Similarity
        cosine_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Sort
        top_indices = cosine_sim.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            product = self.products[idx].copy()
            product['confidence'] = round(float(cosine_sim[idx]) * 100, 1)
            product['model_used'] = "Content-Based (Cosine Similarity)"
            results.append(product)
        return results

    # COLLABORATIVE FILTERING (Popularity/User Behavior)
    def get_collaborative_based(self, interactions, top_k=6):
        """
        Uses interaction data (database logs) to find popular items.
        If no data exists, returns random items (Cold Start solution).
        """
        if not interactions:
            # COLD START: Return random items if no one has interacted yet
            return self.get_random_recommendations(top_k, "Collaborative (Cold Start)")
            
        # Count frequency of product_ids in interactions
        product_counts = Counter([i.product_id for i in interactions])
        
        # Get most common product IDs
        most_common_ids = [int(pid) for pid, count in product_counts.most_common(top_k)]
        results = []
        
        # Find product details for these IDs
        for pid in most_common_ids:
            prod = next((p for p in self.products if p['id'] == pid), None)
            if prod:
                p_copy = prod.copy()
                p_copy['confidence'] = 95.0  # High confidence for popular items
                p_copy['model_used'] = "Collaborative (Popularity)"
                results.append(p_copy)
                
        # Fill remaining slots if we don't have enough popular items
        if len(results) < top_k:
            needed = top_k - len(results)
            results.extend(self.get_random_recommendations(needed, "Collaborative (Filler)"))   
        return results

    # --- 3. HYBRID FILTERING (Content + Probability) ---
    def get_hybrid_based(self, query, top_k=6):
        """
        Combines Cosine Similarity (Relevance) with Logistic Regression (Quality/Conversion Probability).
        """
        clean_query = self.preprocess_text(query)
        query_vec = self.vectorizer.transform([clean_query])
        
        # Content Score
        cosine_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Probability Score (Logistic Regression)
        probs = self.lr_model.predict_proba(self.tfidf_matrix)[:, 1]
        
        # Weighted Average (70% Relevance + 30% Quality)
        hybrid_scores = (0.7 * cosine_sim) + (0.3 * probs)
        
        top_indices = hybrid_scores.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            product = self.products[idx].copy()
            product['confidence'] = round(float(hybrid_scores[idx]) * 100, 1)
            product['model_used'] = "Hybrid (Content + Logistic Regression)"
            results.append(product)
        return results

    def get_random_recommendations(self, k, model_name):
        import random
        selected = random.sample(self.products, min(k, len(self.products)))
        results = []
        for p in selected:
            p_copy = p.copy()
            p_copy['confidence'] = 50.0
            p_copy['model_used'] = model_name
            results.append(p_copy)
        return results
    